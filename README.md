# Paper Sharing PPT

`paper-sharing-ppt` 是一个 Codex skill，用于根据一篇选定的学术论文 PDF，制作中文组会论文分享 PowerPoint。

该 skill 面向研究生组会、文献汇报和论文精读分享场景。它以输入 PDF 为唯一内容依据，生成包含中文讲解、论文图表截图、公式展示和演讲者提示栏讲稿的 `.pptx` 文件。

## 输出内容

- 忠于论文原文的中文论文分享 PPTX。
- 极简学术风格：白底黑字，不使用花哨图标、渐变或装饰性元素。
- 16:9 横向页面，尺寸为 33.867 cm x 19.05 cm。
- 中文使用宋体，英文和公式使用 Times New Roman。
- 正文、表格文字和可见公式说明字号不小于 18 pt。
- 必须包含标题页、摘要、介绍、相关工作、方法、实验和总结板块。
- 对图像、表格、公式以及需要辅助讲解的页面添加演讲者提示栏。
- 论文中的图像、表格和居中公式优先通过 PDF 截图方式清晰展示。

## 主要排版规则

该 skill 强调克制、清晰、适合学术汇报的排版：

- 每页左上角或右上角标注板块小标题，例如 `Abstract`、`Introduction`、`Method`。
- 每页上下左右必须保留可见安全边距，任何内容不得顶满四周。
- 文本框不得重叠，图像、表格、公式不得遮挡文字。
- 文本框内文字使用单倍行距。
- 中文标点不能单独出现在一行开头，也不能和所属句子断开。
- 尽量使用段落文字，尤其是方法部分应避免分点。
- 不允许在可见页面中使用 Markdown 风格的 `-` 作为分点；确需分点时使用 PowerPoint 原生圆点。
- 方法部分应严格对应论文原文描述，优先采用原文的中文直译，并只做适度冗余删除。

## 仓库结构

```text
paper-sharing-ppt/
  SKILL.md
  README.md
  agents/
    openai.yaml
  assets/
    paper-sharing-style-reference.pptx
```

`assets/paper-sharing-style-reference.pptx` 是可复用样式参考资产，仅用于参考极简学术风格、版式间距、角标位置、公式页、图表页和备注栏使用方式。实际制作时应根据输入论文重新排版，不应机械套用该 PPT 作为固定模板。

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

本仓库只包含 skill 指令和复用样式参考资产。生成的 PPTX、渲染预览图、PDF 截图裁剪文件和临时构建文件不应提交到仓库中。
