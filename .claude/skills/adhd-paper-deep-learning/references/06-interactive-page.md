# 轻交互论文陪读页面

用于用户要求网页，或完整陪读结束后希望保存一个可反复浏览的成果。页面是**本地独立 HTML**：不联网、无 CDN、无外部字体或框架。它呈现已核实的讲解，不会读取论文或自动生成事实。

## 最省 token 的生成路径

1. 从论文原文选出主问题、主张、关键章节、证据与局限。保留节号/页码；看不到的内容写为未确认。只放需要回看的要点，不复制整篇论文。
2. 写一个 UTF-8 JSON 文件。必填：`title`、`source`、`question`、`claim`、`sections`（1–12 节）。每节必填：`title`、`source`、`question`、`role`、`bridge`、`takeaway`。可选：`points`（最多 3 条）、`evidence`、`limit`、`concept`、`recall`。示例见仓库 `examples/study-page-input.json`。
3. 执行 `python <skill目录>/scripts/render_study_page.py input.json output.html`。脚本只用 Python 标准库，从固定模板生成单文件网页；当前宿主如需用 `python3`，使用可用的 Python 3.11+ 即可。
4. 打开 `output.html` 看实际页面：总览、章节切换、字号按钮、回忆答案、窄屏布局均应正常。最终只链接 HTML 成品，不粘贴源码。

`concept` 若出现，需提供 `term`、`analogy`、`mapping`、`mechanism`、`example`、`boundary`。`recall` 若出现，需提供 `question` 和 `answer`。页面默认只显示一个章节，回忆答案由读者自愿展开。所有输入文本都经过 HTML 转义。

## 内容边界

- `source` 写真实原文定位；未核实时明确写“待核”。
- `evidence` 只写原文直接支持的结果，`limit` 写不能推出什么。教学数值必须显式标为 `[教学示例]`。
- 章节卡片是**阅读导航**，不暗示相邻章节存在因果关系；若要表达依赖、比较或因果，必须在讲解中说明证据。
- 网页无需嵌入 MCP PNG：固定 HTML 卡片和交互已提供可见结构，省去大型 base64 图像。聊天中需要真正的论文图示时仍按需调用 MCP。不要为了凑页面而调用全部五个工具。
- 若用户只问一个概念或一张图，直接在聊天中解释；不要为很短的答案额外生成网页。
