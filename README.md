# Paper Sharing PPT

`paper-sharing-ppt` 是一个 agent skill，用于根据一篇选定的学术论文 PDF，制作中文组会论文分享 PowerPoint。

该 skill 面向研究生组会、文献汇报和论文精读分享场景。它以输入 PDF 为唯一内容依据，生成包含中文讲解、论文图表截图、公式展示和演讲者提示栏讲稿的 `.pptx` 文件。

## 分支说明

| 分支 | 目标环境 | 差异 |
| --- | --- | --- |
| `main` | Codex | 构建库可用 `@oai/artifact-tool`；安装到 `~/.codex/skills`；渲染用 `soffice` + `pdftoppm` |
| `DSH` | DeepSeek Harness（DeepSeek 模型） | 构建只用 `python-pptx`；安装到 `~/.dsh/skills`；渲染用 `office_render`；脚本按 skill 根目录的绝对路径调用；补了 `whenToUse` 触发词与依赖自检 |

脚本、`assets/style-spec.json` 与版式契约在两个分支上一致；差异只在环境契约与文档。合并 `main` 到 `DSH` 时，冲突通常只出现在 `SKILL.md` 的 Environment / Toolchain / Build 三节与 `README.md` 的安装段。

## 输出内容

- 忠于论文原文的中文论文分享 PPTX，不超过 30 页。
- 极简学术风格：白底黑字，不使用花哨图标、渐变或装饰性元素。
- 16:9 横向页面，尺寸为 33.867 cm × 19.05 cm（12192000 × 6858000 EMU）。
- 中文使用宋体，英文、数字和公式使用 Times New Roman。
- 正文、表格文字和可见公式说明字号不小于 18 pt。
- 必须包含标题页、摘要、介绍、相关工作、方法、实验和总结板块。
- 对图像、表格、公式以及需要辅助讲解的页面添加演讲者提示栏。
- 论文中的图像、表格和居中公式优先通过 PDF 截图方式清晰展示。

## 主要排版规则

- 每页左上角或右上角标注板块小标题，例如 `Abstract`、`Introduction`、`Method`；同一板块的角标位置、字号、偏移保持一致。
- 每页上下左右必须保留可见安全边距，正文内容内缩 ≥ 1.2 cm；角标与页码这类页眉页脚元素内缩 ≥ 0.4 cm。
- 除标题页外，每页右下角有 `n / N` 页码，14 pt 灰色 `#7F7F7F`。
- 文本框不得重叠，图像、表格、公式不得遮挡文字。
- 文本框内文字使用单倍行距。
- 中文标点不能单独出现在一行开头，也不能和所属句子断开。
- 尽量使用段落文字，尤其是方法部分应避免分点。
- 不允许在可见页面中使用 Markdown 风格的 `-` 作为分点；确需分点时使用 PowerPoint 原生圆点。
- 方法部分应严格对应论文原文描述，优先采用原文的中文直译，并只做适度冗余删除。
- 全篇黑白；`#C00000` 只允许用于重绘表格里标注最优值（配合加粗）。

## 仓库结构

```text
paper-sharing-ppt/
  SKILL.md
  README.md
  agents/
    openai.yaml            # Codex 界面元数据；DSH 不读取，保留只为 Codex 分支兼容
  scripts/
    crop_pdf.py         # 按 PDF 文字坐标确定性裁切图表与公式，并做对称留白
    fix_fonts.py        # 给每个 run 补齐 latin/ea/cs 字体与 lang，修正中英混排字体
    add_page_numbers.py # 右下角页码，14 pt 灰色，标题页跳过
    check_deck.py       # 机械性验收：字号、字体、边距、重叠、拉伸、备注、页码、页数
    validate_plan.py    # 生成前的页数与字数预算校验
    preflight.py        # 检查 python-pptx / Pillow / poppler 是否就绪
  assets/
    style-spec.json                 # 画布/边距/角标/字体/页码/色板的权威数值
    paper-sharing-style-reference.pptx
```

`assets/style-spec.json` 是版式数值的权威来源，`paper-sharing-style-reference.pptx` 是这些数值的视觉样例，两者冲突时以 JSON 与 `SKILL.md` 为准。参考资产只用于参考极简学术风格、版式间距、角标位置、公式页、图表页和备注栏使用方式，实际制作时应根据输入论文重新排版，不应机械套用。

## 环境依赖（DSH）

| 用途 | 依赖 | 说明 |
| --- | --- | --- |
| Python 运行时 | `load_workspace_dependencies` 返回的解释器 | 该解释器自带 `python-pptx`、`Pillow`；不要改用系统 `python`，也不要装包 |
| PDF 测量与裁切 | poppler：`pdfinfo`、`pdftotext`、`pdftoppm` | Windows 上 TeX Live 通常自带（`bin/windows`）；macOS `brew install poppler`；Debian/Ubuntu `apt install poppler-utils` |
| 版面渲染与目视检查 | `office` skill 的 `office_render` | 先 `skill('office')`，工具才会出现；不需要 LibreOffice |
| 依赖自检 | `python "$SKILL/scripts/preflight.py"` | 一次性列出缺什么；缺依赖时不要用手工裁切或猜字体的方式绕过 |

`office_render` 是 DSH 工具而不是可执行文件，`preflight.py` 无法探测它，只会在末尾提示。视觉验收是否可做取决于当前模型：`deepseek-flash` 支持图像输入；`deepseek-v4-pro` 会把图片替换成 `[Unsupported Image]`，此时只能跑机械门禁并如实声明未做目视检查。

## 制作流程

下面的 `$SKILL` 指 `skill` 工具报告的 skill 根目录（例如 `C:\Users\you\.dsh\skills\paper-sharing-ppt`）。脚本一律用它的绝对路径调用，不要假设当前工作目录就是 skill 目录。

```powershell
# 0. 依赖自检 + 先写大纲，校验页数与字数预算（可反复运行）
python "$SKILL/scripts/preflight.py"
python "$SKILL/scripts/validate_plan.py" --init build/plan.json
python "$SKILL/scripts/validate_plan.py" build/plan.json

# 1. 确定性裁切：rect 用 PDF point，原点在左上角，只需大致框住目标
python "$SKILL/scripts/crop_pdf.py" --pdf paper.pdf --page 3 `
    --rect 60,335,300,400 --out figures/eq1.png --manifest figures/eq1.json

# 2. 生成 build/deck.pptx（python-pptx 写成可重跑脚本；先加载 office-pptx skill）

# 3. 三道门禁：字体、页码、机械验收
python "$SKILL/scripts/fix_fonts.py" build/deck.pptx
python "$SKILL/scripts/add_page_numbers.py" build/deck.pptx
python "$SKILL/scripts/check_deck.py" build/deck.pptx

# 4. 渲染预览，逐页目视检查：先在会话里 skill('office')，再调用
#    office_render(input="build/deck.pptx", dpi=110)   # 省略 pages = 全部
#    需要 PDF 时用 office_convert(input="build/deck.pptx", format="pdf")
```

`fix_fonts.py`、`add_page_numbers.py` 都可以重复执行，第二次不会再改动文件；`check_deck.py` 与 `validate_plan.py` 有 error 时以非零码退出，适合作为交付前的门禁。

`check_deck.py` 覆盖的是"不需要眼睛"的部分：画布尺寸、页数、每个 run 的字体槽位、字号下限、安全边距、文本框重叠、图片拉伸与偏心、截图有效 dpi、备注长度、板块角标、页码。构图与美观仍需渲染后目视检查。

## 两类常见问题的成因与修法

**公式截图错位。** 手工框选页面后直接截取，会把上一行正文或图注的一小条墨迹一起带进来；同时裁切图里左右、上下留白不对称，图片框即使居中，公式看上去仍然偏。`crop_pdf.py` 的做法是把裁切框先裁到文字栏内，再按墨迹重新裁紧并补上等量留白，因此“把图片居中”就等于“把公式居中”。落位时只给宽度、让高度按比例跟随，并按 `left = (slide_width - width) / 2` 计算，不要手调坐标。

**正文英文变成宋体。** OOXML 里一个 run 的字体由 `<a:latin>`、`<a:ea>`、`<a:cs>` 三个槽位分别决定，PowerPoint 按字符所属文字系统逐字选择。多数构建库只暴露一个 `fontFace`，只写 `<a:latin>`，于是中文落到主题的东亚字体、英文落到 `<a:latin>`；一旦把 `fontFace` 设成宋体，英文就跟着变成宋体。正确做法是同一个 run 同时写 `latin=Times New Roman` 和 `ea=宋体`，无需按语言拆 run。`fix_fonts.py` 会在成品上统一补齐这三个槽位和 `lang`，与构建工具无关。

## 安装方式（DSH）

DSH 只发现这几个根目录下的 skill，且**只看根目录下一层**（`<root>/<name>/SKILL.md`，深层嵌套的 `**/SKILL.md` 不会被发现）：

| 优先级 | 根目录 |
| --- | --- |
| 100 | `<projectRoot>/.dsh/skills` |
| 200 | `<projectRoot>/.agents/skills` |
| 300 | profile 里配置的 `customSkillDirs` |
| 400 | `~/.dsh/skills` |
| 500 | `~/.agents/skills` |

最省事的做法是直接克隆 `DSH` 分支到用户级根目录：

```powershell
git clone -b DSH https://github.com/Skywalkerjieee/paper-sharing-ppt.git "$env:USERPROFILE\.dsh\skills\paper-sharing-ppt"
```

如果本地已经有这个仓库，用目录联接挂进去即可，不必复制：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.dsh\skills" | Out-Null
cmd /c mklink /J "$env:USERPROFILE\.dsh\skills\paper-sharing-ppt" "D:\Codefield\CODE_skill\paper-sharing-ppt"
```

DSH 会监听这些根目录，新增 skill 在下一个 catalog 生效，**不需要重启**。装好后会话里的 skill 目录会出现 `paper-sharing-ppt`，用 `skill` 工具按名字加载即可。

Codex 用户继续用 `main` 分支：

```powershell
git clone -b main https://github.com/Skywalkerjieee/paper-sharing-ppt.git "$env:USERPROFILE\.codex\skills\paper-sharing-ppt"
```

## 使用方式

给出一篇学术论文 PDF，然后直接描述任务即可，例如：

```text
用 paper-sharing-ppt 把这篇文章做成本周组会分享的 PPT。
```

或显式加载后使用：

```text
skill: paper-sharing-ppt
把这篇文章压成 25 页以内的组会汇报，方法部分要完整。
```

该 skill 期望输入为一篇选定论文 PDF。制作过程中必须以 PDF 为事实来源，不得编造论文中不存在的方法、数据集、实验结果、贡献或局限。

## 注意事项

本仓库只包含 skill 指令、脚本和复用样式参考资产。生成的 PPTX、渲染预览图、PDF 截图裁剪文件、裁切过程的 `.crop-cache` 目录和临时构建文件不应提交到仓库中。

`assets/paper-sharing-style-reference.pptx` 已按本 skill 的契约重建过一轮：字体槽位、板块角标、页码、边距、文本框重叠、图片偏心、缺省备注全部通过 `check_deck.py`。目前唯一保留的 28 条警告是截图有效 dpi 低于 220 —— 原始论文 PDF 不在仓库里，无法以 300 dpi 重裁这些图片。若要彻底消除，把原 PDF 放进来后用 `crop_pdf.py` 重新裁切并替换即可。

`DSH` 分支与 `main` 只共享脚本和契约；`SKILL.md` 的环境段、`README.md` 的安装/流程段是刻意不同的。向 `main` 合入脚本修复时，建议先合 `main` → `DSH`，再单独验证一次 `preflight.py` 与 `check_deck.py`，避免把 Codex 的渲染命令带回来。
