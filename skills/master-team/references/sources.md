# 平台依据与验证边界

核对日期：2026-11-14。平台文档和DSH默认分支会变化；执行时以本轮宿主工具声明及权限为准。以下仅是适配依据，不代表三个平台的端到端运行验证。

| 平台 | 官方一手资料 | 使用范围 |
| --- | --- | --- |
| Codex | https://learn.chatgpt.com/docs/build-skills | SKILL.md、.agents/skills目录、按需加载和openai.yaml；原developers.openai.com/codex/skills已重定向 |
| Codex | https://developers.openai.com/codex/multi-agent/ | 原生多代理的一般能力；不据此推断桌面跨聊天接口 |
| DeepSeek Harness | https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md | 项目.dsh/skills、.agents/skills及用户技能目录 |
| DeepSeek Harness | https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/subagent.md | 同任务树subagent及控制工具 |
| DeepSeek Harness | https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/tool-subagent-control/README.md | list_agents、send_message、wait_agent、interrupt_agent语义 |
| DeepSeek Harness | https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/tool-subagent/README.md | 默认subagent及本地/外部后端的后续消息差异 |
| Claude Code | https://code.claude.com/docs/en/skills | .claude/skills目录与技能调用 |
| Claude Code | https://code.claude.com/docs/en/sub-agents | 原生子代理与父会话委派 |
| Claude Code | https://code.claude.com/docs/en/agent-teams | 实验团队能力及生命周期限制 |

Codex桌面跨聊天工具及其逐目标授权来自当前宿主提供的工具声明，不宣称是所有Codex版本的公开API。Claude网页端与其他无工具界面只支持人工交接。DSH插件注册/预设目录覆盖须在目标环境确认。

仓库验证记录见根目录docs/validation-report.md；复制单个技能目录后可运行本包检查工具，安装到其他环境后仍须核实发现、文件可见性与通信授权。

2.1.0的教学触发沿用各平台技能发现/加载方式；Codex默认入口提示配置于agents/openai.yaml，其他平台读取通用SKILL.md与first_use提示。未添加导入监听或安装钩子，不把自然语言自动匹配保证成导入瞬间推送。教学内容与进度规则是本技能设计，真实对话效果需在宿主中观察。
