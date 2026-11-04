#!/usr/bin/env python3
"""Read-only, offline structural audit of SVG and optional PDF artifacts.

Exit 0 means no definite structural failure (REVIEW still requires human work),
1 means a definite contract failure, 2 means a requested input cannot be audited.
No status establishes visual quality or semantic editability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

LIMITS = [
    "Structural inspection only; no rendering, collision, clipping or visual QA.",
    "No proof of semantic editability, native application behavior, correct science, or absence of fragment mosaics.",
    "Zero embedded bitmaps is necessary but insufficient for a pure-vector deliverable.",
    "External resources are reported, never fetched; CSS and path syntax are inspected heuristically, not fully interpreted.",
    "Font metadata does not establish font availability, licensing or correct glyph rendering.",
    "Text matching uses NFKC and whitespace normalization; it does not establish correct superscript, subscript or charge typography.",
]


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).split())


def finding(code, severity, message, **details):
    return dict(code=code, severity=severity, message=message, **details)


def local_name(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def status_for(findings):
    levels = {f["severity"] for f in findings}
    return next((s for s in ("FAIL", "NOT_AUDITABLE", "REVIEW") if s in levels), "PASS")


def file_record(path, role):
    p = Path(path)
    data = p.read_bytes()
    return data, dict(role=role, path=str(p.resolve()), sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))


def external(reference):
    # Only document-local fragment references are self-contained.
    return bool(reference.strip()) and not reference.strip().startswith("#")


def check_labels(labels, text_runs, source):
    findings = []
    normalized = [normalize(t) for t in text_runs]
    joined = normalize(" ".join(text_runs))
    compact = re.sub(r"\s+", "", joined)
    for label in labels:
        expected = normalize(label["text"])
        if expected in normalized:
            continue
        # Multi-line/run extraction can insert spaces. Never silently accept it.
        if expected in joined or re.sub(r"\s+", "", expected) in compact:
            findings.append(finding("LABEL_RUN_VARIANT", "REVIEW", "Expected text may span runs or have extraction spacing differences; verify exact glyphs, superscripts/subscripts and charges manually.", source=source, label=label))
        else:
            findings.append(finding("LABEL_MISSING", "FAIL", "Expected live-text label was not found.", source=source, label=label))
    return findings


STANDARD_SVG_DTDS = {
    ("-//W3C//DTD SVG 1.0//EN", "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd"),
    ("-//W3C//DTD SVG 1.1//EN", "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"),
    ("-//W3C//DTD SVG 1.1 Basic//EN", "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-basic.dtd"),
    ("-//W3C//DTD SVG 1.1 Tiny//EN", "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny.dtd"),
}


class OfflineSVGBuilder(ET.TreeBuilder):
    """ElementTree does not load external DTDs; accept known identity only."""
    def __init__(self):
        super().__init__()
        self.standard_dtd = None

    def doctype(self, name, pubid, system):
        if name != "svg" or (pubid, system) not in STANDARD_SVG_DTDS:
            raise ValueError("Only recognized standard W3C SVG external DTD declarations are supported; no DTD is fetched.")
        self.standard_dtd = dict(name=name, public_id=pubid, system_id=system, fetched=False)


def audit_svg(data, labels):
    findings = []
    # Reject entity declarations and any custom internal subset before parsing.
    # Removing NUL bytes also recognizes ASCII declaration syntax in UTF-16/32.
    declarations = data.replace(b"\x00", b"")
    if re.search(br"<!\s*ENTITY\b|<!\s*DOCTYPE\b[^>]*\[", declarations, re.I):
        return {}, [finding("SVG_DTD", "NOT_AUDITABLE", "Entity declarations and custom internal DTD subsets are not supported.")]
    builder = OfflineSVGBuilder()
    try:
        root = ET.fromstring(data, parser=ET.XMLParser(target=builder))
    except (ET.ParseError, ValueError) as exc:
        return {}, [finding("SVG_PARSE", "NOT_AUDITABLE", str(exc))]
    if builder.standard_dtd:
        findings.append(finding("SVG_STANDARD_DTD", "INFO", "Recognized standard SVG DTD identity; external DTD was not fetched.", **builder.standard_dtd))
    if local_name(root.tag) != "svg":
        return {}, [finding("SVG_ROOT", "NOT_AUDITABLE", "Root element is not svg.")]
    counts, commands, fonts = Counter(), Counter(), Counter()
    transforms, texts, dependencies = [], [], []
    for element in root.iter():
        tag = local_name(element.tag)
        counts[tag] += 1
        if tag in {"image", "foreignObject", "script"}:
            findings.append(finding("SVG_FORBIDDEN_ELEMENT", "FAIL", f"{tag} violates the self-contained pure-vector contract.", element=tag, id=element.get("id")))
        if tag == "text":
            texts.append("".join(element.itertext()))
        if tag == "path":
            commands.update(re.findall(r"[MmZzLlHhVvCcSsQqTtAa]", element.get("d", "")))
        if element.get("transform"):
            transforms.append(dict(element=tag, id=element.get("id"), transform=element.get("transform")))
        for key, value in element.attrib.items():
            attr = local_name(key)
            if attr in {"font-family", "font-size", "font-style", "font-weight"}:
                fonts[f"{attr}: {value}"] += 1
            if attr.lower().startswith("on"):
                findings.append(finding("SVG_EVENT_HANDLER", "FAIL", "Executable event attribute is forbidden.", attribute=attr))
            if attr in {"href", "src"} and external(value):
                dependencies.append(dict(element=tag, attribute=attr, reference=value))
            if key == "{http://www.w3.org/XML/1998/namespace}base" and value:
                dependencies.append(dict(element=tag, attribute="xml:base", reference=value))
            if attr == "style":
                for name, val in re.findall(r"(font-(?:family|size|style|weight))\s*:\s*([^;]+)", value, re.I):
                    fonts[f"{name.lower()}: {val.strip()}"] += 1
        # Scan CSS and attribute URL references, including quoted forms.
        css = " ".join(element.attrib.values())
        if tag == "style":
            css += " " + "".join(element.itertext())
        for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css, re.I | re.S):
            if external(match.group(2)):
                dependencies.append(dict(element=tag, attribute="css-url", reference=match.group(2)))
        if re.search(r"@import\b", css, re.I):
            dependencies.append(dict(element=tag, attribute="css-import", reference=css))
        if "\\" in css:
            findings.append(finding("CSS_ESCAPES", "NOT_AUDITABLE", "Escaped CSS needs independent dependency inspection."))
    if re.search(br"<\?xml-stylesheet\b", data.replace(b"\x00", b""), re.I):
        dependencies.append(dict(element="processing-instruction", attribute="xml-stylesheet", reference="stylesheet processing instruction"))
    if dependencies:
        findings.append(finding("SVG_EXTERNAL_DEPENDENCIES", "FAIL", "Nonlocal resources or stylesheet imports violate the self-contained contract.", dependencies=dependencies))
    line_count = sum(commands[c] for c in "LlHhVv") + counts["line"]
    curve_count = sum(commands[c] for c in "CcSsQqTtAa")
    if line_count > 1000 or counts["polygon"] + counts["polyline"] > 1000:
        findings.append(finding("GEOMETRY_VOLUME", "REVIEW", "Large line/polygon counts warrant visual and native-object review; counts alone do not establish fragment mosaics.", line_commands_and_elements=line_count, polygon_and_polyline_elements=counts["polygon"] + counts["polyline"]))
    findings.extend(check_labels(labels, texts, "svg"))
    return dict(elements=dict(sorted(counts.items())), path_commands=dict(sorted(commands.items())), line_commands_and_elements=line_count, curve_commands=curve_count, text=texts, fonts=dict(sorted(fonts.items())), transforms=transforms, viewport={k: root.get(k) for k in ("width", "height", "viewBox")}), findings


def _load_fitz():
    import pymupdf
    return pymupdf


def audit_pdf(data, labels):
    try:
        fitz = _load_fitz()
    except ImportError:
        return {}, [finding("PDF_DEPENDENCY", "NOT_AUDITABLE", "PyMuPDF is unavailable; PDF was not inspected.")]
    findings, pages = [], []
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            if document.needs_pass:
                return {}, [finding("PDF_ENCRYPTED", "NOT_AUDITABLE", "PDF requires a password.")]
            if document.page_count == 0:
                return {}, [finding("PDF_EMPTY", "NOT_AUDITABLE", "PDF has no pages.")]
            # Include dead/unreferenced image objects as embedded bitmaps too.
            image_xrefs = [xref for xref in range(1, document.xref_length())
                           if document.xref_get_key(xref, "Subtype") == ("name", "/Image")]
            if image_xrefs:
                findings.append(finding("PDF_IMAGE_OBJECTS", "FAIL", "PDF contains embedded Image XObjects (including masks or unused objects).", xrefs=image_xrefs))
            all_text = []
            for index, page in enumerate(document):
                # get_image_info is built from TextPage image blocks. MuPDF can
                # rasterize native shadings into those blocks, so it is not a
                # reliable embedded-bitmap test. Bboxlog distinguishes actual
                # image paint operations (including inline images) from shades.
                images = page.get_image_info()
                operations = Counter(item[0] for item in page.get_bboxlog())
                actual_images = operations["fill-image"] + operations["fill-imgmask"]
                shadings = operations["fill-shade"]
                resource_images = page.get_images(full=True)
                text = page.get_text("text")
                all_text.extend(text.splitlines())
                pages.append(dict(page=index + 1, width_pt=page.rect.width, height_pt=page.rect.height, text=text, fonts=[list(font) for font in page.get_fonts(full=True)], displayed_image_count=actual_images, resource_image_count=len(resource_images), displayed_shading_count=shadings, image_info_entry_count=len(images), paint_operations=dict(sorted(operations.items()))))
                if actual_images or resource_images:
                    findings.append(finding("PDF_IMAGES", "FAIL", "PDF contains raster image paint operations (including inline images) or image resources.", page=index + 1, displayed_image_count=actual_images, resource_image_count=len(resource_images)))
                if len(images) > actual_images:
                    if shadings:
                        findings.append(finding("PDF_IMAGE_INFO_SHADINGS", "INFO", "TextPage image-info inventory includes rasterized inspection representations of native shadings; it is not an embedded-bitmap count. Image paint operations and Image XObjects are checked separately.", page=index + 1, image_info_entry_count=len(images), displayed_shading_count=shadings))
                    else:
                        findings.append(finding("PDF_IMAGE_INFO_UNRESOLVED", "NOT_AUDITABLE", "Image-info entries exceed image paint operations without native shadings to explain the discrepancy.", page=index + 1))
            findings.extend(check_labels(labels, all_text, "pdf"))
    except Exception as exc:
        return {}, [finding("PDF_READ", "NOT_AUDITABLE", f"Cannot inspect PDF: {type(exc).__name__}: {exc}")]
    return dict(pymupdf_version=getattr(fitz, "VersionBind", "unknown"), embedded_image_xrefs=image_xrefs, pages=pages), findings


def audit(svg, pdf=None, labels_path=None):
    report = dict(schema_version=1, status=None, checked_files=[], scopes=["SVG self-contained pure-vector structure and live-text inventory"], limits=LIMITS.copy(), findings=[], svg=None)
    labels = []
    if labels_path:
        try:
            data, record = file_record(labels_path, "labels")
            report["checked_files"].append(record)
            labels = json.loads(data)
            if not isinstance(labels, list) or any(not isinstance(x, dict) or not isinstance(x.get("id"), str) or not isinstance(x.get("text"), str) or not normalize(x["text"]) for x in labels):
                raise ValueError("Labels must be a JSON array of {id: string, text: nonempty string}.")
            if len({x["id"] for x in labels}) != len(labels):
                raise ValueError("Label IDs must be unique.")
            report["scopes"].append("Expected labels checked independently in each requested artwork")
        except (OSError, ValueError, UnicodeError) as exc:
            report["findings"].append(finding("LABELS_INPUT", "NOT_AUDITABLE", str(exc)))
            labels = []
    for path, role, inspect in [(svg, "svg", audit_svg)] + ([(pdf, "pdf", audit_pdf)] if pdf else []):
        try:
            data, record = file_record(path, role)
            report["checked_files"].append(record)
            report[role], findings = inspect(data, labels)
            report["findings"].extend(findings)
        except OSError as exc:
            report["findings"].append(finding("FILE_INPUT", "NOT_AUDITABLE", str(exc), source=role, path=str(path)))
    if pdf:
        report["scopes"].append("PDF page dimensions, text/fonts and raster image inventory using PyMuPDF")
    else:
        report["limits"].append("No PDF requested; PDF export was not inspected.")
    report["status"] = status_for(report["findings"])
    report["exit_code"] = {"PASS": 0, "REVIEW": 0, "FAIL": 1, "NOT_AUDITABLE": 2}[report["status"]]
    report["requires_visual_and_native_qa"] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", required=True)
    parser.add_argument("--pdf")
    parser.add_argument("--labels")
    parser.add_argument("--out", help="Write JSON report here (never to an input artwork).")
    args = parser.parse_args(argv)
    if args.out:
        output_path = Path(args.out)
        for source in (args.svg, args.pdf, args.labels):
            if not source:
                continue
            input_path = Path(source)
            if output_path.resolve() == input_path.resolve() or (output_path.exists() and input_path.exists() and output_path.samefile(input_path)):
                parser.error("--out must not overwrite an input file")
    report = audit(args.svg, args.pdf, args.labels)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        try:
            Path(args.out).write_text(output, encoding="utf-8")
        except OSError as exc:
            print(f"Cannot write report: {exc}", file=sys.stderr)
            return 2
    else:
        print(output, end="")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
