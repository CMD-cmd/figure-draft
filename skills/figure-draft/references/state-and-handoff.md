# 状态与阶段接续

状态文件服务于跨轮复用。短任务使用简短记录即可，不强制创建空文件或填完全部字段。

## figure-state.yaml 示例

```yaml
figure_id: Figure2
kind: schematic
stage: refine
workflow_owner: figure-draft
execution: imagegen
loaded_resources:
  - path: references/image-generation.md
    scope: refine
    valid_for: current raster schematic and selected style
purpose: manuscript_schematic
message: 三种材料在局部界面发生不同转化。
target_journal: null
current:
  content_master: figures/Figure2_v08.png
  native_master: null
  style_reference: references/selected_style.png
  geometry_reference: figures/Figure2_v08.png
  text_master: labels.json
  caption_master: caption_v08.txt
  manuscript_figure_version: v06
approved:
  content: true
  layout: true
  style: true
  science_author_review: pending
locked:
  - 面板顺序与物相身份
  - 同类构件使用共同几何
delta:
  - B 的引线末端对准实际颗粒
open_questions: []
evidence:
  claim_map: claim-map.tsv
references:
  - file: references/selected_style.png
    role: style_only
    controls: [line_weight, palette, texture]
qa:
  reviewed_version: v08
  whole_figure: passed
  final_size: pending
  local_details: passed
  native_reopen: pending
  vector_structure: pending
  independent_review: not_requested
publication:
  policy_checked_at: null
  policy_url: null
  eligibility: unverified
  ai_provenance: generation-log.json
next: 核对修改后的B局部与整图。
```

记录状态使用 `passed / failed / pending / not_requested / not_applicable`，附简短证据路径。只写真正做过的检查。新内容或图层改变使受影响的 QA 重新变为 pending。

`loaded_resources` 只列已使用资料，便于按需恢复，不是免读凭证；上下文中缺少必要规则或来源有变时补读相关章节。混合图可为各面板记录 `kind / source / backend / version / locked`，整图保持一个流程负责人。

## 文字台账

`labels.json` 用列表，至少含 `id` 和 `text`；可附 `panel`、`role`、`font`、`size_pt`、`anchor`、`runs` 与 `evidence_id`。

```json
[
  {"id":"A_title","text":"Polymer hydrolysis","panel":"A","role":"title"},
  {"id":"A_water","text":"H₂O","panel":"A","role":"label"},
  {"id":"C_ion","text":"Mg²⁺","panel":"C","role":"label"}
]
```

真实排版可以把 ₂ 或 ²⁺ 转成基准字符加原生上下标属性；显示文字和语义文本均保留以便检查。各对象用稳定 ID 关联，别只依赖图层序号或当前选择。

## 接续规则

- **只有论文/笔记**：进入 brief，补核心句与证据。
- **已批准内容和线框**：用户要画风候选时进 explore，要直接画矢量时进 vector；复用内容，不重启完整调研。
- **已有三稿待选**：review 后展示比较；用户保留选择权时等选择。
- **指定 PNG 复刻**：要求可编辑对象时进 vector，按目标 `.af`/SVG 选择工具；只要求位图局部修订时进 refine。
- **已有 .af 改一个标签**：读取目标对象与相邻区域；尚无已核任务副本时先保护原件，已有副本则接续改字并复查。
- **已有 SVG/参数脚本改字或连线**：进入 refine，保留图源，读 vector-editing；不启动位图生图或新Affinity工程。
- **表格新画数据图或改 R/Python 数据标记**：进入 plot，读 data-figures；继承已选后端、数据与统计口径，不启动三风格生图。仅改数据图外部面板标号时按原编辑源局部处理。
- **固定数据图加入混合版式**：进入 deliver 的组版；数据图作为已验证资产，保持原后端身份和标记。改数据或轴才回原后端。
- **只写/改图注、只改格式导出**：进入 deliver 的对应段落；缺源图或目标尺寸仅阻断依赖它的步骤。
- **只要求审图**：review，不修改主稿。
- **来自另一聊天**：先用聊天工具读取用户引用的聊天；确认当前版本与决定，旧工具授权不自动转移。
- **另一个执行者正在改同一图**：只读已保存版本；变更操作交给唯一写入者，引用快照标明版本与日期。

## 简短变更记录

每轮一行即可：`版本 → 请求/目的 → 实际改动 → 已检查 → 未解决 → 接受/待修`。

独立复核另存原报告、实际输入图清单和主执行者的采纳表。对外稿件只带读者需要的科学内容；技术失败和决策历史留在工作记录里。

跨能力库时把当前阶段、执行方式和已读文档随交接带上，详见[分工与交接](skill-handoff.md)。从 Figure-draft 开始时保持本入口负责流程；执行结果直接回到当前阶段。工具重连后重新获取文档身份；先前已确认的科学内容和布局仍可复用。
