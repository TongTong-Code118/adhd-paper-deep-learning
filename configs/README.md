# 平台配置速查

| 平台 | 项目级 Skill | 本地 MCP 配置 | 额外步骤 |
|---|---|---|---|
| GitHub Copilot（VS Code / CLI） | `.github/skills/adhd-paper-deep-learning/` | 根目录 `.mcp.json` | `python -m pip install -e .`；同意工作区信任 |
| GitHub Copilot cloud agent | 同上 | **GitHub 仓库设置**中的 MCP servers，复制 `copilot-cloud-mcp.json` | 启用 Copilot 权限；将 setup steps 合并到默认分支 |
| Claude Code | `.claude/skills/adhd-paper-deep-learning/` | 根目录 `.mcp.json` | `python -m pip install -e .`；接受项目 MCP 信任提示 |
| Cursor | `.cursor/skills/adhd-paper-deep-learning/` | `.cursor/mcp.json` | `python -m pip install -e .`；在 MCP Tools 中启用 |
| 旧版 VS Code 配置 | `.github/skills/...` | 可把 `vscode-mcp.example.json` 内容复制到 `.vscode/mcp.json` | 与根目录 `.mcp.json` 二选一，避免重复 |

**注意**
- `.mcp.json` 里的 `python` 必须与执行 `pip install -e .` 的 Python 相同。Linux/macOS 若命令是 `python3`，请替换。Windows 可能需要写 Python 解释器绝对路径。
- 当前仓库使用 stdio MCP，**不需要开放端口、API 密钥或云端服务器**。
- GitHub cloud agent 并不会自动读取 `configs/copilot-cloud-mcp.json`。必须有仓库管理员**手工粘贴**到仓库 Settings → Copilot → MCP servers。
- Skills 可由模型按相关性选择加载；不能保证每次自动使用。用户可以明确点名 `adhd-paper-deep-learning`。
- 这些工具只是图形渲染服务，不会自行读取论文 PDF；调用方需提供有原文依据的节点和 `source_note`。
- 若容器/机器缺少中文字体，需要安装 Noto Sans CJK 或设置 `ADHD_PAPER_FONT` 到**本机已安装**的字体路径。不要把字体文件上传进这个仓库。
- 如果平台无法显示 MCP ImageContent，服务仍会返回标准 PNG 二进制内容，但最终 UI 行为取决于客户端。
