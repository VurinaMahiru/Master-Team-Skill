# Claude 适配

自动协作目标为Claude Code。Claude网页端及不提供文件/代理工具的界面使用manual：用户加载技能文本并转交工单，不能承诺后台团队或自动跨聊天派单。来源见 [sources](sources.md)。

## 安装

Claude Code用户级目录为 `~/.claude/skills/master-team/`，项目级为 `.claude/skills/master-team/`，完整复制整个目录。技能可通过自然语言或 `/master-team` 调用；项目入口可合并到CLAUDE.md。此技能不新增自动执行hook，也不复制Codex工具名作为Claude工具。

首次调用或匹配到导入/学习请求时按[教学规则](onboarding.md)主动开始分步对话；在Claude网页端由用户先加载技能内容并发送首次使用提示。复制文件不会独立创建会话，本技能不为欢迎教学自动增加启动hook。

## 子代理与团队

Claude Code原生subagents适合父会话委派独立任务，使用parent_scoped；具体创建/恢复、工具权限及共享文件行为按当前会话声明核实。后台任务ID和普通聊天ID不能混用。

Agent teams是需要当前产品支持并显式启用的实验能力。只有工具确实可用且用户已授权团队协作时才使用队友/任务/消息机制；技能不自动启用实验设置。若团队仍受lead会话管理，保持parent_scoped；只有真实支持独立会话及所需生命周期能力时才使用persistent。

同工作目录并行改同文件仍会冲突。遵守宿主权限与本项目写占用；不要把agent teams或subagent称为硬隔离。可自定义agent配置不是此通用skill运行所必需。

## 交接限制

不保证lead转移、跨根会话接管、队友恢复或跨会话消息。当前宿主不支持就收尾旧成员并交接文件；未结束占用不释放。已授权的新会话可以接续已落盘任务，但不能声称继承了原宿主的活跃成员管理权。

当前官方agent teams文档明确lead固定，不能将领导权转给队友；进程内队友也不能由resume/rewind恢复。此技能的文件所有权generation不能突破这些限制。有宿主跨会话消息能力时另核实际工具与授权，不从agent teams的存在推断该能力。
