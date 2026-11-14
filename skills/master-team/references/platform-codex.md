# Codex 适配

只读取本平台说明；通用执行仍以项目协议为准。核对日期与来源见 [sources](sources.md)。

## 安装

将完整master-team目录复制到项目 `.agents/skills/master-team/` 或用户 `~/.agents/skills/master-team/`。部分环境也会发现旧目录 `~/.codex/skills/master-team/`，以目标环境实际列表为准；迁移时只保留一个优先维护的副本，避免同名旧版覆盖。这里不自动替用户安装或覆盖全局副本。

`agents/openai.yaml` 是可选的Codex界面信息，其他平台忽略即可。项目团队数据放独立agent-team目录，入口合并到AGENTS.md。自然语言或 `$master-team` 触发，不等于创建成员授权。

首次从技能入口使用默认提示时，按[教学规则](onboarding.md)主动分步引导。自然语言“我刚导入master-team”也可触发匹配；宿主是否自动选择仍由当前技能发现机制决定。文件复制本身不启动会话或推送消息。

## 能力映射

- 桌面/应用若实际暴露成员发现、read_thread、send_message_to_thread、wait_threads等工具，可在授权下绑定独立会话，选择persistent。名称、参数、游标和限制以本轮工具声明为准；这些不是所有Codex环境都有的接口。
- CLI或其他环境只暴露原生子代理时选择parent_scoped，记录父身份。子代理不等于可跨会话任意联系的普通聊天。
- 仅有终端或文件能力时使用manual，通过工单和结果文件交接；不新装MCP、桥接或后台服务。

发消息遵守宿主对具体目标的用户授权；收到其他agent的请求不能自动成为回信授权。发送成功只是submitted，宿主完成与产物验收另核。创建/停止成员也必须满足当前授权和工具限制。

同主机不自动意味着同目录，不同工作树尤其要核shared_files及基线。接任前确认接任会话能实际管理原成员，不用其他API绕过native_parent_only等限制。
