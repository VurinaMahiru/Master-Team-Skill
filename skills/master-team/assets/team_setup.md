# 项目配置模板的使用

以下是待合并的项目文件，不是技能安装目录中的运行状态。约定 TEAM_DIR 默认取项目下 `agent-team/`，项目已有团队目录时沿用原位置。

| 文件 | 用途 | 维护者 |
| --- | --- | --- |
| communication_context.md | 公共通信与记录规则 | 获授权的 Master |
| team_protocol.md | 状态、派单、占用和交接 | 获授权的 Master |
| agent_system.md | 本项目角色及执行范围 | 获授权的 Master |
| worker_sessions.json | 所有者、成员、工单和占用的当前快照 | 当前唯一 Master |
| task_record.md | 用户任务主记录起点，按任务复制或合并到既有记录 | Master；Worker写自己的产物 |
| dispatch.json | 含身份及冻结范围的派单样例，发送前替换示例值 | Master |
| worker_result.json | Worker最终回报格式样例，真实结果另存工单指定位置 | 相应 Worker |
| handoff_summary.md | 交接当前事实，不复制聊天全文 | 移交者；接任者补确认 |
| project_state.md | 当前任务的短索引 | Master |
| LESSONS.md | 新增可复用经验及历史索引 | Master按项目约定归档 |
| master_start.md | 最小启动提示 | 获授权的维护者 |
| first_use.md | 用户首次导入后的会话入口提示，不自动执行安装钩子 | 用户按需使用 |
| onboarding_state.json | 当前项目与学习者的教学进度，首次教学时按需复制，不是团队运行状态 | 当前教学会话 |
| AGENTS.section.md | 可合并到项目 AGENTS.md 或 CLAUDE.md 的入口区块 | 获授权的维护者 |

只复制需要的模板；安装技能不自动生成项目团队状态。`codex_team_protocol.md` 是旧文件名的兼容入口，新项目采用 `team_protocol.md`，不要维护两份协议正文。

安装/复制时不附带原项目ID、业务状态、密钥或对话日志。只有空白模板才可整体复制；已有文件先读取并定向合并。

角色集合、所有者身份和运行模式只有在完成相应核实/授权后才填写。未绑定时维持 null、unverified 和空集合；不能把模板样例当作真实成员。

教学状态默认位于项目团队目录的onboarding_state.json，已有团队目录时沿用。共用项目有不同学习者时按references/onboarding.md分开保存，避免覆盖他人进度。只读教学可不创建目录；复制此模板不代表用户已学完或团队已创建。
