## Master Team 协作入口

- 只有涉及团队配置、派工、恢复或交接时加载 master-team；普通任务沿用既有配置，不自动建队。
- 用户首次启用、表示已导入master-team或请求使用教学时，加载技能references/onboarding.md；每次只推进一步，已有进度则续接，用户可暂停或直接进入任务。维护技能本身不启动教学。
- 公共规则：`{{TEAM_DIR}}/communication_context.md`；状态与交接：`{{TEAM_DIR}}/team_protocol.md`；职责：`{{TEAM_DIR}}/agent_system.md` 本角色段。
- 当前身份/工单/占用读取 `{{TEAM_DIR}}/worker_sessions.json`；当前任务入口读取 `{{TEAM_DIR}}/project_state.md`。模板不等于真实运行状态。
- 按实际宿主工具及用户已有授权通信；新建成员、转移归属、发布等遵守相应约束。
- 新经验写 `{{LESSONS_FILE}}`；恢复优先读交接与未完工单，不重放全部历史。
