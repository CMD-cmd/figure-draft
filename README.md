# Figure-draft

一个通用的科研配图 Agent Skill。帮你想清楚图要表达什么、安排布局、寻找参考和比较画风，再把选定方案做成图形与文字可分别修改的稿件，并逐轮检查。

可以从一段论文笔记开始，也可以接着已有草稿、Affinity 文件、SVG 或 Python/R 图源继续。Agent 根据当前要求选择对应步骤。

本项目采用 [Agent Skills 开放格式](https://agentskills.io/home)。支持该格式的 AI Agent 可以按其技能机制加载；也可以把 `SKILL.md` 提供给其他 AI 助手作为工作指引。绘制、编辑和导出使用当前 Agent 可用的工具。

## 能做什么

| 你手上的材料 | 可以从这里开始 |
|---|---|
| 论文、实验记录、几条想法 | 梳理核心信息、科学关系和面板分工 |
| 已确定的内容 | 讨论构图、比例、阅读顺序和标签位置 |
| 目标期刊或参考图 | 分析布局、配色、形状和文字层级 |
| 内容与布局已确定 | 生成三种画风，逐张检查，再选择方向 |
| 已选中的草稿 | 调整局部形状、颜色、质感、箭头和文字 |
| 位图或草图 | 用 Affinity 或 SVG 重建形状与独立文字 |
| 数据表或 Python/R 图源 | 绘制或修改数据面板，核对数据编码和统计说明 |
| 已完成的图 | 审图、组版、写图注和导出 |

机制图、材料界面图、多尺度示意、制备流程、器件结构、图形摘要和混合多面板图，都有对应的设计入口。文献笔记收录了基础生物学、材料与生物材料领域的参考图分析，可按类型查阅。

## 安装

### 通用方式

1. 下载本仓库，保留 `skills/figure-draft` 整个文件夹。
2. 将它放入所用 Agent 的技能目录，按该平台的方式加载。
3. 在技能选择器中选用 Figure-draft，或在请求中点名它。

手动加载时，让 Agent 先读取 `skills/figure-draft/SKILL.md`，再按当前阶段读取对应的 `references/` 文件。保留 `scripts/` 和 `LICENSE`，需要检查图稿时即可使用配套脚本。

### Codex 示例

使用 Codex 时，可以发送：

```text
使用 $skill-installer，从 https://github.com/CMD-cmd/figure-draft/tree/main/skills/figure-draft 安装 Figure-draft。
```

安装完成后，在下一轮对话中使用。已有同名版本时，先保留自己修改过的文件，再更新。

## 开始使用

```text
用 Figure-draft，先讨论这张机制图应该承载哪些内容。
```

```text
内容和线框已经确定。用 Figure-draft 给我三种画风，并分别检查。
```

```text
用 Figure-draft 接着改第二稿，只调整材料质感和右侧引线。
```

```text
用 Figure-draft，把这张参考图做成 Affinity 可编辑矢量稿，形状和文字分开。
```

```text
用 Figure-draft 修改现有的 figure.af，修正 Panel B 的化学式上下标，再导出 PDF。
```

支持自动选用技能的平台，也可以根据“这张图怎么排”“第二稿的字体再调一下”等请求和画图上下文加载 Figure-draft。你说“先讨论”或“先审图”，就只完成对应的讨论或审查。具体调用方式按平台约定，例如 Codex 使用 `$figure-draft`。

如果希望科研配图优先走这个入口，可以把下面这条规则加入 Agent 的项目指令或自定义指令中（例如 `AGENTS.md`）：

```text
科研配图的讨论、制作、修改、审查和导出，默认使用 figure-draft，只读取当前阶段所需模块；明确指定的其他技能或已有流程继续沿用。
```

## 从已有图稿继续

告诉 Agent 当前文件、这次要改哪里，以及已经确定的内容和画风。它会沿用现有图源：`.af` 在 Affinity 中修改，SVG 或参数脚本直接改源文件，Python/R 数据图沿用原语言与数据口径。已完成的面板可以直接组版导出。

多轮任务可用 `figure-state.yaml` 和 `labels.json` 记录主文件、已定事项、文字台账与下一步，方便接续。

## 按任务准备工具

| 任务 | 所需能力 |
|---|---|
| 内容讨论、布局与参考分析 | AI Agent；查文献时使用浏览或文献工具 |
| 生成或修改示意位图 | 当前环境可用的图像生成工具 |
| Affinity 原生绘制 | Affinity 应用、可用的 MCP 连接及 SDK 文档 |
| SVG 或数据绘图 | 相应的编辑、渲染工具，或 Python/R 环境 |
| PDF 结构检查 | Python 与 PyMuPDF |

已安装 `nature-figure`、`paper-figure`、`affinity` 等技能时，Figure-draft 会按需使用它们。也可使用当前环境已有的工具，详见[工具与技能接入](skills/figure-draft/references/integrations.md)。

## 图是怎么检查的

每轮生成或修改后，查看局部和整图，并在最终刊印尺寸核对文字、颜色、引线、遮挡与阅读顺序。科学关系、原生对象可编辑性和导出结构分别检查。

仓库附带离线结构检查脚本 `audit_vector.py`。SVG 检查使用 Python 标准库；检查 PDF 时先安装 PyMuPDF：

```bash
python3 -m pip install -r requirements-audit.txt
python3 skills/figure-draft/scripts/audit_vector.py \
  --svg figure.svg --pdf figure.pdf --labels labels.json --out audit.json
```

按已有文件省略 `--pdf` 或 `--labels`。脚本输出 `PASS`、`REVIEW`、`FAIL` 或 `NOT_AUDITABLE`，表示本次结构检查的状态；具体含义与后续动作见[交付与检查](skills/figure-draft/references/delivery.md)。结构结果与实际看图一起使用。含真实照片或显微图的混合图，按面板来源分别检查。

运行脚本测试：

```bash
python3 -m unittest discover -s skills/figure-draft/scripts -p 'test_*.py'
```

## 目录

```text
skills/figure-draft/
  SKILL.md          阶段入口
  agents/           可选的 Codex 展示与调用配置
  references/       内容、布局、生图、矢量、数据与审查模块
  scripts/          矢量结构检查及测试
```

从[类型索引](skills/figure-draft/references/taxonomy.md)查图型，或读[材料界面图示例](skills/figure-draft/references/worked-example.md)了解各阶段怎样衔接与中途接续。

## 许可

本仓库的文档和脚本采用 [MIT License](LICENSE)。文献笔记保留原文链接与图号；使用文献中的图片时，按原出版物的许可和署名要求处理。
