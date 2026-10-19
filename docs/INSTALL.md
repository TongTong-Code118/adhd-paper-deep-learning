# 安装指南｜按平台逐步操作

> 本包是**可放进 GitHub 仓库的项目级 Skill + 本地 stdio MCP 工具**，不是能替用户在各平台后台注册权限的安装程序。每台要实际使用的机器都需确保 Python 包已安装。

## 开始前检查

1. Python 3.11+。
2. `python -m pip --version` 可执行。
3. 支持中文的系统字体：Linux `fonts-noto-cjk`、macOS 苹方、Windows 微软雅黑（使用**本机**字体，不上传字体文件）。
4. GitHub / Claude Code / Cursor 客户端本身已具备 MCP 与 Skill 功能，且所在组织允许使用。

### 通用初始化

在仓库根目录运行：

```bash
python -m pip install -e .
python scripts/diagnose.py
```

第一条安装名为 `adhd-paper-visual-mcp` 的 Python 包。第二条启动真正的 MCP 子进程，依次测试五个工具是否能返回 PNG。

确认成功后开始平台步骤。

## GitHub Copilot in VS Code

仓库预置：

- Skill：`.github/skills/adhd-paper-deep-learning/SKILL.md`
- MCP：`.mcp.json`（推荐的工作区项目配置）

打开仓库。通过 `MCP: List Servers` 找到 `adhd-paper-visuals`。首次加载配置可能弹出信任提示，确认你信任**自己下载的仓库**后再批准。若 `python` 不在 PATH，把 `.mcp.json` 中 `command` 改为解释器绝对路径。

进入 Agent Chat，输入：

> 使用 `adhd-paper-deep-learning` 阅读这份论文，调用 `render_paper_map` 给我生成真正可见的宏观结构图，并告诉我当前章节位置。

如果返回的是巨大 base64 文本而不是图，说明当前 UI 没有显示 ImageContent；检查客户端、MCP 日志或换成能显示图片的宿主。Skill 必须坦诚处理这一点。

## GitHub Copilot CLI

从**可信任的仓库目录**启动 Copilot CLI，工作区 `.mcp.json` 才有机会被加载。
如果第一次打开时未信任，按客户端提示批准工作区。

检查工具发现或在交互中明确要求 `render_paper_map`。**不要**把 `.vscode/mcp.json` 当 Copilot CLI 的默认配置；CLI 使用的配置键为 `mcpServers`。

## GitHub Copilot cloud agent

**这一步 GitHub repo ZIP 本身无法自动完成**：

1. 提交仓库到默认分支；检查 `.github/workflows/copilot-setup-steps.yml` 位于默认分支（否则不运行）。
2. 打开 GitHub.com 的仓库页面 → Settings → Copilot → MCP servers。
3. 打开 `configs/copilot-cloud-mcp.json`，复制整个 JSON 贴到 MCP configuration 并保存。
4. 这份配置只允许五个只读绘图工具。Cloud agent 的 setup steps 会安装 Python 3.11、Pillow 和 Noto CJK 字体。
5. 发起 cloud agent 任务，要求列工具、调用 `render_paper_map`，检查工作日志。

如果你的 Copilot 产品/组织没有此功能、权限不足、没有此设置入口或 setup steps 失败，需要联系管理员或按官方限制处理。

## Claude Code

Skill 在 `.claude/skills/adhd-paper-deep-learning/`，项目 MCP 在 `.mcp.json`。

1. 从仓库根目录启动 `claude`。
2. Claude Code 初次读取 `.mcp.json` 时，检查并批准项目 MCP 配置（**不要为了省事关闭所有安全确认**）。
3. `claude mcp list` / `/mcp` 查看连接状态。
4. 输入 `/adhd-paper-deep-learning` 或询问论文阅读任务，再要求真正 PNG 图。

## Cursor

Skill 在 `.cursor/skills/adhd-paper-deep-learning/`，项目 MCP 在 `.cursor/mcp.json`。

1. 在 Cursor 打开仓库，确保包已安装。
2. Settings → MCP / Tools 查找 `adhd-paper-visuals` 并启用。
3. Cursor CLI 可执行 `cursor-agent mcp list`、`cursor-agent mcp list-tools adhd-paper-visuals`。
4. 在 Agent Chat 中请求 `render_section_flow` 或 `render_concept_diagram`。

## 失败排查

| 症状 | 优先检查 |
|---|---|
| Skill 没触发 | `SKILL.md` 路径，项目是否打开，是否用具体任务或手动点名 |
| MCP 工具列表为空 | 配置键（`mcpServers` vs `servers`）、工作区信任、客户端 MCP 权限 |
| 找不到 Python | 改成已安装本包的解释器绝对路径 |
| `No module named adhd_paper_mcp` | 使用相同 Python 执行 `python -m pip install -e .` |
| 图片中文方块 | 安装本机 Noto CJK；或设置 `ADHD_PAPER_FONT` |
| 图片本身显示不了 | 执行 `python scripts/diagnose.py`；若协议通但 UI 不出图，是宿主显示能力问题 |
| 文字塞满卡片 / 工具错误 | 缩短节点名称；复杂内容拆成两张图；不是把字号无限调小 |
| GitHub 云端未注册 | 确认管理员已在 Settings → Copilot → MCP servers 贴入 JSON |
| 云端安装依赖失败 | 看 `copilot-setup-steps` 日志、Python / 字体 / pip 错误 |

## 官方文档

- [Agent Skills 通用规范](https://agentskills.io/specification)
- [GitHub Skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)
- [GitHub Repo MCP](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/configure-mcp-servers)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Cursor Skills](https://cursor.com/help/customization/skills)
- [Cursor MCP](https://docs.cursor.com/context/model-context-protocol)
- [MCP stdio 标准](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
