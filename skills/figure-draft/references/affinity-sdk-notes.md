# Affinity 实作要点

仅在程序化重建或相关故障时读取。以下整理了原生矢量实现中的常见操作；函数签名与参数以当前 SDK 文档为准。

## 场景描述与原生对象

场景可使用 `group / path / text` 三类记录，包含稳定名称、局部坐标、层级、填充和描边。路径支持 `M/L/C/Z`，分别映射到 `CurveBuilder.beginXY / lineToXY / addBezierXY / close`，多个轮廓组成 `PolyCurve`。文档构建脚本不包含生成图的像素描摹网格。

调用 `AddChildNodesCommandBuilder` 时明确插入父对象、层级与前后位置。需要保留自由曲线位置时，按 SDK 支持情况设置 `forcePixelAlignment=false`。图层顺序通过实际渲染验证。

## 易错点

| 场景 | 操作原则 | 验证 |
|---|---|---|
| 多文档 | 每次按 `sessionUuid` 重新获取目标，核对路径 | 不把 `Document.current` 作为长期身份 |
| 变换后量尺寸 | 读 spread 坐标边界/变换矩阵 | `baseBox` 可能仍是局部原框 |
| 组合图层 | SDK 没有某 group factory 时用文档支持的 container | 看子对象归属与选择行为 |
| 原生渐变 | 按文档提供 stops，明确坐标变换 | 对照原稿检查方向、尺度、透明度和色带 |
| 导入 SVG | 检查单位、viewBox、渐变坐标和嵌套 transform | 原生渲染与交换文件逐区比较 |
| 裁剪形状 | 使用实际支持的曲线容器/clip 结构 | 检查裁边、线端和导出后是否出现切痕 |
| 混合描边 | 设置 cap/join、dash 语义和宽度 | 放大看链端、孔口和圆框接缝 |
| 螺钉/板遮挡 | 钉杆在板体后；钉头按装配关系在板表面前 | 不能用整块白色覆盖掩盖穿插 |
| 金属/矿物质感 | 原生渐变与有限曲线细节 | PDF/SVG有无意外栅格化，主体有无玻璃感 |
| 字体 | 枚举 `Font.all` 并核对 PostScript 名 | PDF 字体清单与实际字形一并检查 |
| 上下标 | `StoryBuilder` 与 glyph attributes | 每个字符切换前重置 `superSubType` |

## 文字对象示意

建立 `StoryBuilder`，先设置字体、字号和填充，再按字符或文字 run 写入。对于 H₂O、Mg²⁺ 等，可用基准字符加 `SuperSubType.Subscript/Superscript`。后续普通字符恢复 `None`。创建 `ArtTextNodeDefinition.createFromStoryBuilder` 后按实际边界平移对齐，保持 scale 为自然比例。

上述只是方法索引；执行前读取当前 `storybuilder.js`、`glyphatts.js`、`nodes.js` 与 `fonts.js` 所需段落，不盲抄历史函数签名。

## 原生报告建议字段

记录文件路径/hash、应用版本、文档尺寸/DPI、文本对象清单及语义内容、文字 transforms、字体、曲线/容器/位图数量、层级、保存重开时间和结果。输出前后的节点数与文字数应与实际改动对应。

SVG/PDF 导出可能因换行、字体 run 或上下标拆分文字；导出文本节点数不必等于原生文字对象数。用文字台账逐项对应内容和外观，避免只比较数量。

若自动化不能切换工作室，使用可用且获准的 UI 能力切换并截图；此 UI 操作不能替代对象类型验证。若工具失败，先读具体错误和 SDK，针对性修正；不反复重建整份文档。
