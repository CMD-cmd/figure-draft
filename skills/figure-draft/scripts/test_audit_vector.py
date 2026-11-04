"""Self-contained tests; temporary fixtures never alter user artwork."""
import base64
import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import audit_vector as av

SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80" viewBox="0 0 100 80"><defs><linearGradient id="g"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient></defs><path d="M0 0 L1 1 C2 2 3 3 4 4" fill="url(#g)"/><polygon points="1,1 2,2 3,1"/><text font-family="Arial" transform="translate(2 3)">Ca<tspan baseline-shift="super">2+</tspan></text></svg>'''


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.svg = self.write("figure.svg", SVG)
        self.labels = self.write("labels.json", json.dumps([{"id": "calcium", "text": "Ca²+"}]))

    def write(self, name, data):
        path = self.root / name
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
        return path

    def test_native_gradient_text_triangle_and_hash(self):
        report = av.audit(self.svg, labels_path=self.labels)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["svg"]["curve_commands"], 1)
        self.assertEqual(report["svg"]["text"], ["Ca2+"])
        self.assertTrue(report["svg"]["transforms"])
        self.assertTrue(report["svg"]["fonts"])
        self.assertEqual(len(report["checked_files"][0]["sha256"]), 64)
        self.assertTrue(any("No PDF" in s for s in report["limits"]))

    def test_forbidden_elements_and_dependencies(self):
        for payload in ['<image href="data:image/png;base64,eA=="/>', '<foreignObject/>', '<script/>', '<use href="other.svg#x"/>', '<style>@import "x.css";</style>', '<rect fill="url(https://example.invalid/x)"/>', '<rect onclick="run()"/>']:
            with self.subTest(payload=payload):
                path = self.write("bad.svg", '<svg>' + payload + '</svg>')
                self.assertEqual(av.audit(path)["exit_code"], 1)

    def test_stylesheet_processing_instruction(self):
        self.assertEqual(av.audit(self.write("pi.svg", '<?xml-stylesheet href="x.css"?><svg/>'))["status"], "FAIL")

    def test_missing_label(self):
        self.labels.write_text('[{"id":"wrong","text":"Na+"}]')
        self.assertEqual(av.audit(self.svg, labels_path=self.labels)["status"], "FAIL")

    def test_run_spacing_review_never_silently_passes(self):
        path = self.write("runs.svg", '<svg><text>Ca <tspan>2+</tspan></text></svg>')
        result = av.audit(path, labels_path=self.labels)
        self.assertEqual(result["status"], "REVIEW")
        self.assertEqual(result["findings"][0]["code"], "LABEL_RUN_VARIANT")

    def test_malformed_missing_and_invalid_labels(self):
        for path in [self.write("broken.svg", '<svg>'), self.root / "absent.svg"]:
            self.assertEqual(av.audit(path)["exit_code"], 2)
        for labels in ["{}", "[null]", '[{"id":"a","text":""}]', '[{"id":"a","text":"x"},{"id":"a","text":"y"}]']:
            with self.subTest(labels=labels):
                self.labels.write_text(labels)
                self.assertEqual(av.audit(self.svg, labels_path=self.labels)["status"], "NOT_AUDITABLE")

    def test_entity_declarations_not_auditable(self):
        self.assertEqual(av.audit(self.write("entity.svg", '<!DOCTYPE svg [<!ENTITY x "test">]><svg><text>&x;</text></svg>'))["exit_code"], 2)

    def test_large_geometry_is_review_only(self):
        data = '<svg>' + '<polygon points="0,0 1,1 2,0"/>' * 1001 + '</svg>'
        result = av.audit(self.write("many.svg", data))
        self.assertEqual(result["status"], "REVIEW")
        self.assertEqual(result["exit_code"], 0)

    def test_utf16_entity_declarations_not_auditable(self):
        data = '<!DOCTYPE svg [<!ENTITY x "test">]><svg><text>&x;</text></svg>'.encode("utf-16")
        self.assertEqual(av.audit(self.write("entity16.svg", data))["exit_code"], 2)

    def test_pdf_image_branch_without_dependency(self):
        class Page:
            rect = SimpleNamespace(width=100, height=80)
            def get_image_info(self): return [{"number": 0}]
            def get_bboxlog(self): return [("fill-image", (0, 0, 10, 10))]
            def get_images(self, full=True): return []
            def get_text(self, mode): return "Ca2+\n"
            def get_fonts(self, full=True): return []
        class Document:
            needs_pass = False
            page_count = 1
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def __iter__(self): return iter([Page()])
            def xref_length(self): return 1
            def xref_get_key(self, xref, key): return ("null", "null")
        fake_fitz = SimpleNamespace(open=lambda **kwargs: Document())
        with patch.object(av, "_load_fitz", return_value=fake_fitz):
            stats, findings = av.audit_pdf(b"mock", [])
        self.assertEqual(stats["pages"][0]["displayed_image_count"], 1)
        self.assertEqual(findings[0]["code"], "PDF_IMAGES")
        self.assertEqual(findings[0]["severity"], "FAIL")

    def test_standard_svg_dtd_offline_and_custom_dtd_rejected(self):
        prefix = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
        for encoding in ("utf-8", "utf-16"):
            result = av.audit(self.write("standard.svg", (prefix + SVG).encode(encoding)))
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["findings"][0]["fetched"])
        for declaration in ('<!DOCTYPE svg SYSTEM "https://example.invalid/a.dtd">', '<!DOCTYPE svg []>', prefix[:-1] + ' [<!ENTITY x "x">]>'):
            result = av.audit(self.write("custom.svg", declaration + '<svg/>'))
            self.assertEqual(result["status"], "NOT_AUDITABLE")

    def test_pdf_native_shading_is_not_a_bitmap_and_inline_bitmap_fails(self):
        try:
            fitz = av._load_fitz()
        except ImportError:
            self.skipTest("PyMuPDF unavailable")
        doc = fitz.open()
        page = doc.new_page(width=100, height=80)
        function = doc.get_new_xref()
        doc.update_object(function, '<< /FunctionType 2 /Domain [0 1] /C0 [1 0 0] /C1 [0 0 1] /N 1 >>')
        shade = doc.get_new_xref()
        doc.update_object(shade, f'<< /ShadingType 2 /ColorSpace /DeviceRGB /Coords [0 0 100 0] /Extend [true true] /Function {function} 0 R >>')
        doc.xref_set_key(page.xref, "Resources", f'<< /Shading << /Sh0 {shade} 0 R >> >>')
        stream = doc.get_new_xref()
        doc.update_object(stream, '<<>>')
        doc.update_stream(stream, b'q /Sh0 sh Q')
        page.set_contents(stream)
        data = doc.tobytes()
        stats, findings = av.audit_pdf(data, [])
        self.assertEqual(av.status_for(findings), "PASS")
        self.assertEqual(stats["pages"][0]["displayed_shading_count"], 1)
        self.assertEqual(stats["pages"][0]["displayed_image_count"], 0)
        self.assertEqual(stats["embedded_image_xrefs"], [])
        # Inline image has no Image XObject or resource entry: get_images alone
        # cannot detect it. Mix it with shading to prevent a blanket exemption.
        doc.update_stream(stream, b'q /Sh0 sh Q q 10 0 0 10 0 0 cm BI /W 1 /H 1 /BPC 8 /CS /RGB ID \xff\x00\x00 EI Q')
        stats, findings = av.audit_pdf(doc.tobytes(), [])
        self.assertEqual(av.status_for(findings), "FAIL")
        self.assertEqual(stats["pages"][0]["displayed_image_count"], 1)
        self.assertEqual(stats["pages"][0]["resource_image_count"], 0)
        self.assertEqual(stats["embedded_image_xrefs"], [])
        # A stencil is still a bitmap; current PyMuPDF calls it fill-imgmask.
        doc.update_stream(stream, b'q 10 0 0 10 0 0 cm BI /W 1 /H 1 /BPC 1 /IM true ID \x80 EI Q')
        stats, findings = av.audit_pdf(doc.tobytes(), [])
        self.assertEqual(av.status_for(findings), "FAIL")
        self.assertEqual(stats["pages"][0]["displayed_image_count"], 1)
        # TextPage can suppress low-alpha images. Paint operations must catch it.
        doc.xref_set_key(page.xref, "Resources", '<< /ExtGState << /GS0 << /ca 0.1 >> >> >>')
        doc.update_stream(stream, b'q /GS0 gs 10 0 0 10 0 0 cm BI /W 1 /H 1 /BPC 8 /CS /RGB ID \xff\x00\x00 EI Q')
        stats, findings = av.audit_pdf(doc.tobytes(), [])
        self.assertEqual(av.status_for(findings), "FAIL")
        self.assertEqual(stats["pages"][0]["displayed_image_count"], 1)
        # Embedded but unused Image XObjects also violate the contract.
        doc.update_stream(stream, b'q Q')
        image = doc.get_new_xref()
        doc.update_object(image, '<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /BitsPerComponent 8 /ColorSpace /DeviceRGB >>')
        doc.update_stream(image, b'\xff\x00\x00')
        stats, findings = av.audit_pdf(doc.tobytes(), [])
        self.assertEqual(av.status_for(findings), "FAIL")
        self.assertEqual(stats["embedded_image_xrefs"], [image])
        self.assertTrue(any(f["code"] == "PDF_IMAGE_OBJECTS" for f in findings))
        doc.close()

    def test_pdf_dependency_unavailable(self):
        path = self.write("fake.pdf", b"%PDF-1.7")
        with patch.object(av, "_load_fitz", side_effect=ImportError):
            result = av.audit(self.svg, pdf=path)
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(result["findings"][0]["code"], "PDF_DEPENDENCY")

    def test_cli_output_and_input_protection(self):
        out = self.root / "audit.json"
        before = self.svg.read_bytes()
        self.assertEqual(av.main(["--svg", str(self.svg), "--out", str(out)]), 0)
        self.assertEqual(json.loads(out.read_text())["status"], "PASS")
        with self.assertRaises(SystemExit):
            av.main(["--svg", str(self.svg), "--out", str(self.svg)])
        self.assertEqual(before, self.svg.read_bytes())

    def test_real_pdf_text_and_images_when_available(self):
        try:
            fitz = av._load_fitz()
        except ImportError:
            self.skipTest("PyMuPDF unavailable; dependency failure covered separately")
        doc = fitz.open()
        page = doc.new_page(width=100, height=80)
        page.insert_text((10, 20), "Ca2+")
        pdf = self.write("vector.pdf", doc.tobytes())
        result = av.audit(self.svg, pdf=pdf, labels_path=self.labels)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["pdf"]["pages"][0]["width_pt"], 100)
        # A synthetic one-pixel PNG, independent of any external image files.
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")
        page.insert_image(fitz.Rect(10, 30, 20, 40), stream=png)
        pdf.write_bytes(doc.tobytes())
        doc.close()
        result = av.audit(self.svg, pdf=pdf)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(f["code"] == "PDF_IMAGES" for f in result["findings"]))
        self.assertEqual(av.audit(self.svg, pdf=self.write("broken.pdf", b"broken"))["exit_code"], 2)


if __name__ == "__main__":
    unittest.main()
