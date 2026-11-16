# Paper Sharing PPT

`paper-sharing-ppt` 是一个 Codex skill，用于根据一篇选定的学术论文 PDF，制作中文组会论文分享 PowerPoint。

该 skill 面向研究生组会、文献汇报和论文精读分享场景。它以输入 PDF 为唯一内容依据，生成包含中文讲解、论文图表截图、公式展示和演讲者提示栏讲稿的 `.pptx` 文件。

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
    openai.yaml
  scripts/
    crop_pdf.py         # 按 PDF 文字坐标确定性裁切图表与公式，并做对称留白
    fix_fonts.py        # 给每个 run 补齐 latin/ea/cs 字体与 lang，修正中英混排字体
    add_page_numbers.py # 右下角页码，14 pt 灰色，标题页跳过
    check_deck.py       # 机械性验收：字号、字体、边距、重叠、拉伸、备注、页码、页数
    validate_plan.py    # 生成前的页数与字数预算校验
  assets/
    style-spec.json                 # 画布/边距/角标/字体/页码/色板的权威数值
    paper-sharing-style-reference.pptx
```

`assets/style-spec.json` 是版式数值的权威来源，`paper-sharing-style-reference.pptx` 是这些数值的视觉样例，两者冲突时以 JSON 与 `SKILL.md` 为准。参考资产只用于参考极简学术风格、版式间距、角标位置、公式页、图表页和备注栏使用方式，实际制作时应根据输入论文重新排版，不应机械套用。

## 环境依赖

| 用途 | 依赖 |
| --- | --- |
| PDF 测量与裁切 | Python 3.8+、Pillow、poppler（`pdfinfo`、`pdftotext`、`pdftoppm`） |
| 字体与版面验收 | `python-pptx`、Pillow |
| 版面预览渲染（可选） | LibreOffice（`soffice`） |

Windows 上如果装有 TeX Live，poppler 工具通常已经随附在 `bin/windows` 目录。macOS 可用 `brew install poppler`，Debian/Ubuntu 可用 `apt install poppler-utils`。

## 制作流程

```powershell
# 0. 先写大纲，校验页数与字数预算（可反复运行）
python scripts/validate_plan.py --init build/plan.json
python scripts/validate_plan.py build/plan.json

# 1. 确定性裁切：rect 用 PDF point，原点在左上角，只需大致框住目标
python scripts/crop_pdf.py --pdf paper.pdf --page 3 `
    --rect 60,335,300,400 --out figures/eq1.png --manifest figures/eq1.json

# 2. 生成 build/deck.pptx（用 @oai/artifact-tool 或 python-pptx 写成可重跑脚本）

# 3. 三道门禁：字体、页码、机械验收
python scripts/fix_fonts.py build/deck.pptx
python scripts/add_page_numbers.py build/deck.pptx
python scripts/check_deck.py build/deck.pptx

# 4. 渲染预览，逐个页面目视检查
soffice --headless --convert-to pdf --outdir build build/deck.pptx
pdftoppm -r 110 -png build/deck.pdf build/slide
```

`fix_fonts.py`、`add_page_numbers.py` 都可以重复执行，第二次不会再改动文件；`check_deck.py` 与 `validate_plan.py` 有 error 时以非零码退出，适合作为交付前的门禁。

`check_deck.py` 覆盖的是"不需要眼睛"的部分：画布尺寸、页数、每个 run 的字体槽位、字号下限、安全边距、文本框重叠、图片拉伸与偏心、截图有效 dpi、备注长度、板块角标、页码。构图与美观仍需渲染后目视检查。

## 两类常见问题的成因与修法

**公式截图错位。** 手工框选页面后直接截取，会把上一行正文或图注的一小条墨迹一起带进来；同时裁切图里左右、上下留白不对称，图片框即使居中，公式看上去仍然偏。`crop_pdf.py` 的做法是把裁切框先裁到文字栏内，再按墨迹重新裁紧并补上等量留白，因此“把图片居中”就等于“把公式居中”。落位时只给宽度、让高度按比例跟随，并按 `left = (slide_width - width) / 2` 计算，不要手调坐标。

**正文英文变成宋体。** OOXML 里一个 run 的字体由 `<a:latin>`、`<a:ea>`、`<a:cs>` 三个槽位分别决定，PowerPoint 按字符所属文字系统逐字选择。多数构建库只暴露一个 `fontFace`，只写 `<a:latin>`，于是中文落到主题的东亚字体、英文落到 `<a:latin>`；一旦把 `fontFace` 设成宋体，英文就跟着变成宋体。正确做法是同一个 run 同时写 `latin=Times New Roman` 和 `ea=宋体`，无需按语言拆 run。`fix_fonts.py` 会在成品上统一补齐这三个槽位和 `lang`，与构建工具无关。

## 安装方式

将仓库克隆到 Codex skills 目录：

```powershell
git clone https://github.com/Skywalkerjieee/paper-sharing-ppt.git "$env:USERPROFILE\.codex\skills\paper-sharing-ppt"
```

安装后重启或刷新 Codex，使 skill 被重新发现。

## 使用方式

提供一篇学术论文 PDF，并要求 Codex 使用该 skill，例如：

```text
Use $paper-sharing-ppt to create a Chinese lab-meeting paper-sharing PPTX from this selected paper PDF.
```

该 skill 期望输入为一篇选定论文 PDF。制作过程中必须以 PDF 为事实来源，不得编造论文中不存在的方法、数据集、实验结果、贡献或局限。

## 注意事项

本仓库只包含 skill 指令、脚本和复用样式参考资产。生成的 PPTX、渲染预览图、PDF 截图裁剪文件、裁切过程的 `.crop-cache` 目录和临时构建文件不应提交到仓库中。

`assets/paper-sharing-style-reference.pptx` 已按本 skill 的契约重建过一轮：字体槽位、板块角标、页码、边距、文本框重叠、图片偏心、缺省备注全部通过 `check_deck.py`。目前唯一保留的 28 条警告是截图有效 dpi 低于 220 —— 原始论文 PDF 不在仓库里，无法以 300 dpi 重裁这些图片。若要彻底消除，把原 PDF 放进来后用 `crop_pdf.py` 重新裁切并替换即可。
