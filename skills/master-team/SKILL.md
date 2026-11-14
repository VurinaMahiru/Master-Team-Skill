---
name: master-team
description: 在 Codex、DeepSeek Harness 或 Claude Code 中配置和维护 Master 与 Worker 协作，处理派工、验收和交接。用户首次启用、表示已导入 master-team 或询问用法时，自动分步对话教学；普通业务沿用既有团队。
metadata:
  author: VurinaMahiru
  version: "2.1.0"
---

# Master Team

用一套工单和验收协议协调多个角色；具体通信方式由当前宿主能力决定。Claude 适配目标是 Claude Code；Claude 网页端或其他聊天界面只使用人工交接模式。

## 首次使用先引导

首次启用，或用户说已导入/想学习master-team时，按[对话式教学](references/onboarding.md)主动开始一轮引导，不等用户掌握专门命令。每次只讲一个步骤、最多问一个关键问题；从当前会话和已有配置推断已知信息，不重复询问。

依次帮助用户理解用途、确认环境、选择角色、配置项目、模拟派工、开始首个真实任务。用户可暂停、继续、跳步、重学或直接进入任务；已有团队与明确业务任务优先，不强迫走完课程。审阅、修改或打包技能时不向开发者启动教学。

有文件权限时按项目和学习者记录[教学进度](assets/onboarding_state.json)，恢复时续接；不能落盘则在会话中保存简短进度。不在技能包模板内写用户状态，不将演练标成真实建队或完成任务。

复制技能文件本身通常不会创建会话或执行指令。本技能在首次被宿主加载并用于当前用户请求后自动引导；无法依靠技能文本在导入瞬间主动发消息。需要入口时用[首次使用提示](assets/first_use.md)，不擅自安装hook、服务或定时器。

## 先确定范围

- 只审阅、修改或安装技能：处理文件与验证，不启动成员、发送消息或创建运行中的团队。
- 用户要求团队协作：先复用现有成员；仅在用户及宿主已授权时创建或联系成员。技能本身不能替代宿主的发送消息授权。
- 继续任务或接任：先查身份、当前工单和在途占用，不重建团队或重做已完成交付。

只读目标项目入口、当前状态、本角色规则和一个适配说明；模板不是现行事实。保留既有规则、身份和未提交修改。

## 选择宿主和协作方式

1. 读取当前工具声明，核实成员发现、创建、投递、等待、停止、共享文件能力及各自授权。先记录未验证项，不为探测而发送或创建。
2. 只读对应说明：[Codex](references/platform-codex.md)、[DeepSeek Harness](references/platform-dsh.md)、[Claude](references/platform-claude.md)。安装目录也在对应说明中。
3. 已验证可联系的独立会话用 `persistent`；只能管理本父会话的子代理用 `parent_scoped`；缺少可用且已授权的通信方式用 `manual`。平台名称不保证模式可用。
4. 共享工作区也要验证。不同主机或隔离工作区仅传递能实际访问的产物；没有同步能力就由用户交接文件，不安装桥接或假称已送达。

## 配置与运行

- 新项目将所需 [assets](assets/team_setup.md) 合并到项目团队目录，替换 `{{TEAM_DIR}}` 与 `{{LESSONS_FILE}}`。有旧团队时先看[迁移说明](references/migration.md)，不以空模板覆盖登记表。
- 默认最小角色集合，按任务选择实现、验证等职责；[角色模板](assets/agent_system.md)另提供可选六角色方案。Master 默认协调验收；项目可配置其执行一般工作，但仍遵守原有权限和独立验收要求。
- 公共通信与记录只以 [communication_context](assets/communication_context.md) 为准；工单状态、占用和交接只以 [team_protocol](assets/team_protocol.md) 为准。其他入口仅链接，不复制整段规则。
- 工单使用[任务模板](assets/task_record.md)，消息参考[派单样例](assets/dispatch.json)，返回使用[结果模板](assets/worker_result.json)。`task_id / ticket_id / attempt_id / master_generation / candidate_ref` 必须对齐；旧轮次结果保留历史，不能当成新轮次完成。
- 消息大小、验收预算和等待时长放在[登记表 policy](assets/worker_sessions.json)。默认消息预算是 4096 UTF-8 字节的精简目标；宿主硬上限优先，超出后把详情放文件，不拆连发规避限制。
- 执行结束、交付和验收分开；原始证据按需保存，未失效证据可复用。超时、投递不明、取消、部分成功和写入冲突按协议处理，不自动重发、替补或释放未知占用。

## 验收与交接

Master 逐项核需求、候选、产物和相关证据。按项目要求独立验证；返工只改新 attempt，已通过且未变化的证据不重复全跑。[网页项目检查](references/web-project.md)仅在适用时加载。

使用[交接模板](assets/handoff_summary.md)保存当前身份、在途工单、占用、证据和下一步。新 Master 必须满足[交接步骤](assets/team_protocol.md)，记录 generation；宿主不能转移子代理归属时只交接文件，不宣称旧成员已被新会话接管。

## 验证和交付

按[验证说明](references/verification.md)执行。可选 Python 3.10+、仅标准库的[检查工具](scripts/team_check.py)用于登记表一致性、派单/结果归属、消息字节和 v1 迁移；它只读检查或写出新迁移文件，不发送消息、不启动成员，也不是运行时锁。

更新主任务和[状态索引](assets/project_state.md)；新增可复用结论写[经验索引](assets/LESSONS.md)。报告区分静态通过、真实投递、执行完成及验收通过。若要压缩成熟流程，按需读[效率说明](references/efficiency.md)。跨平台适配依据见[来源及验证边界](references/sources.md)。
