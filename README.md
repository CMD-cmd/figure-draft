# Figure-draft

一个用于科研配图的 Codex skill。帮你讨论图要讲什么、安排布局、寻找参考、比较画风，再把选定方案做成可编辑的图，并逐轮检查细节。

可以从任意阶段开始：一段论文笔记、一张参考图、已经选好的草稿，或需要改字的 Affinity 文件。每次只读取当前阶段需要的指导。

## 能做什么

| 你手上的材料 | 可以从这里开始 |
|---|---|
| 论文、实验记录、几条想法 | 梳理核心信息、科学关系和面板分工 |
| 已确定的内容 | 讨论构图、比例、阅读顺序和标签 |
| 目标期刊或参考图 | 分析布局、配色、形状和文字层级 |
| 内容与布局已确定 | 生成三种画风，逐张检查，再选择方向 |
| 已选中的草稿 | 调整局部形状、颜色、质感、箭头和文字 |
| 位图或草图 | 用 Affinity 或 SVG 重建形状与独立文字 |
| 数据表或 Python/R 图源 | 绘制数据面板，核对数据编码和统计说明 |
| 已完成的图 | 审图、组版、写图注和导出 |

机制图、材料界面图、多尺度示意、制备流程、器件结构、图形摘要和混合多面板图，都有对应的设计入口。文献笔记收录了基础生物学、材料与生物材料领域的参考图分析，可按类型查阅。

## 安装

把下面这句话发给 Codex：

```text
使用 $skill-installer，从 https://github.com/CMD-cmd/figure-draft/tree/main/skills/figure-draft 安装 Figure-draft。
```

安装完成后，在下一轮对话中使用。也可以把本仓库的 `skills/figure-draft` 文件夹放进自己的 Codex skills 目录。已有同名版本时，先保留自己修改过的文件，再更新。

## 开始使用

```text
用 $figure-draft，先讨论这张机制图应该承载哪些内容。
```

```text
内容和线框已经确定。用 $figure-draft 给我三种画风，并分别检查。
```

```text
用 $figure-draft 接着改第二稿，只调整材料质感和右侧引线。
```

```text
用 $figure-draft，把这张参考图做成 Affinity 可编辑矢量稿，形状和文字分开。
```

技能允许自动选用。你也可以直接聊“这张图怎么排”“第二稿的字体再调一下”，Codex 会结合请求和画图上下文选择模块。你说“先讨论”，就进入讨论阶段。

如果希望科研配图统一走这个入口，可以在自己的 `AGENTS.md` 中加入：

```text
科研配图的讨论、制作、修改、审查和导出，默认使用 figure-draft，只读取当前阶段所需模块；明确指定的其他技能或已有流程继续沿用。
```

## 按任务准备工具

| 任务 | 所需能力 |
|---|---|
| 内容讨论、布局与参考分析 | Codex；查文献时使用浏览或文献工具 |
| 生成或修改示意位图 | 当前环境可用的图像生成工具 |
| Affinity 原生绘制 | Affinity 应用、可用的 MCP 连接及 SDK 文档 |
| SVG 或数据绘图 | 相应的编辑、渲染工具，或 Python/R 环境 |
| PDF 结构检查 | Python 与 PyMuPDF |

已安装 `nature-figure`、`paper-figure`、`affinity` 等技能时，Figure-draft 会按需使用它们。也提供了使用现有工具直接工作的入口，详见[工具与技能接入](skills/figure-draft/references/integrations.md)。

## 图是怎么检查的

每轮修改后查看局部和整图，并在最终尺寸核对文字、颜色、引线与阅读顺序。可编辑性、科学关系和导出结构分别检查。

仓库附带 SVG/PDF 结构检查脚本。SVG 检查使用 Python 标准库；检查 PDF 时先安装 PyMuPDF：

```bash
python3 -m pip install -r requirements-audit.txt
python3 skills/figure-draft/scripts/audit_vector.py \
  --svg figure.svg --pdf figure.pdf --labels labels.json --out audit.json
```

按已有文件省略 `--pdf` 或 `--labels`。脚本输出 `PASS`、`REVIEW`、`FAIL` 或 `NOT_AUDITABLE`，具体含义见[交付与检查](skills/figure-draft/references/delivery.md)。结构结果与实际看图一起使用。

运行脚本测试：

```bash
python3 -m unittest discover -s skills/figure-draft/scripts -p 'test_*.py'
```

## 目录

```text
skills/figure-draft/
  SKILL.md          阶段入口
  agents/           显示名称与自动选用配置
  references/       内容、布局、生图、矢量、数据与审查模块
  scripts/          矢量结构检查及测试
```

从[类型索引](skills/figure-draft/references/taxonomy.md)查图型，或读[材料界面图示例](skills/figure-draft/references/worked-example.md)了解各阶段怎样衔接。

## 许可

本仓库的文档和脚本采用 [MIT License](LICENSE)。文献笔记保留原文链接与图号；使用文献中的图片时，按原出版物的许可和署名要求处理。
