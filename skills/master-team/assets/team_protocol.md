# 工单状态与接任协议

版本 2.0.0。身份与当前状态以项目 `worker_sessions.json` 为准；通信格式见 [communication_context](communication_context.md)。登记表是协议记录，不是数据库事务锁或宿主权限系统。

## 身份和唯一写入者

`active_master_thread_id` 是当前协调会话的宿主身份；`generation` 仅在所有权实际转移时增加，压缩恢复同一所有者不增加。Worker派单前后核对发送者和 generation；旧Master的新增指令一律拒绝，除非用户及宿主明确重新授权并完成登记。

当前 Master 是登记表唯一写入者。它串行完成检查与登记，再投递消息；Worker通过结果或确认消息提出更新，不直接改登记表。文件系统没有强制互斥保障；若旧、新Master可能同时写入，先解决所有权，不能把登记记录当成抢锁成功。

成员使用逻辑 worker_id 与真实 session_id、host_id、session_kind、parent_session_id、transport 对应。保留平台原始身份，不把子代理ID当成独立聊天ID。每次派单先核角色、工具可用性、依赖、路径可达性及通信授权。

## 工单结构

用户任务 task_id 下有多个 ticket_id；每个ticket有不可变 attempt_id。改需求、基线或候选必须新建 attempt，不能修改已开始/完成attempt的目标掩盖变化。每个 Worker 默认只接一个活动 attempt。

当前快照字段及示例见 [registry schema](../schemas/registry.schema.json)、[task_record](task_record.md) 和 [worker_result](worker_result.json)。尝试开始后冻结其 goal、candidate_ref、reads/writes、worker_id、master_session_id 和 master_generation。

| 维度 | 可用状态 | 主要更新点 |
| --- | --- | --- |
| delivery | not_sent / pending_delivery / submitted / acknowledged / unknown | 投递前登记pending；工具确认提交只到submitted；Worker确认后acknowledged；超时/报错且未知是否送达为unknown |
| execution | planned / running / submitted / blocked / error / stopped | Worker开始才running；交付产物后submitted；无法继续则blocked/error；确认停止后stopped |
| runtime | unknown / idle / running / ended | 来自宿主实际运行信息；不能从Worker的done或静默推断ended |
| acceptance | pending / accepted / rejected | Master核候选、产物和证据后更新；accepted要求execution=submitted |

正常路径为 planned→running→submitted，再由 Master accepted/rejected。人工转交可由接收者确认后进入running。运行中可报告blocked/error；恢复后沿用同attempt继续running，但更改目标要新attempt。submitted/rejected为该轮交付结果，返工使用新attempt。不能把accepted退回pending覆盖历史。

## 派单与去重

1. 核当前所有者/generation、目标成员身份及授权、真实运行状态、已接受的依赖、允许路径和候选。
2. 确认同键未执行，登记planned、pending_delivery和写占用，再按宿主适配方式投递一次。工具提交成功仅记submitted。
3. Worker读取主记录及登记表相关项，核发送者/generation和自己的身份。相同键已执行/交付则回原状态或原结果，不重复副作用；未知状态先向Master查证。Master登记acknowledged/running。
4. 接收十字段结果时核 task/ticket/attempt/generation/candidate，并从宿主消息元数据核实际发送者属于登记的Worker；单份结果JSON不能证明发送身份。主记录中的旧轮结果不能覆盖新轮。结果可保留原派单generation，但须指向当前仍被继承、且未撤销的同一attempt，旧generation不能用来开启新工作。
5. Master读取证据后验收；单独核宿主是否结束。已确认runtime=ended才能释放占用，Worker的done本身不够。共享文件写任务不得在占用未知时重派。

## 写范围与依赖

reads/writes和claims使用项目相对、明确目录或文件路径，`.` 表示全项目；不使用通配符。将 `..`、绝对路径和符号链接/目录联接解析到真实目标核对，不能仅用字符串前缀判断安全。跨平台默认按大小写不敏感检查潜在冲突，避免Windows别名；实际写入前还要核文件系统。

父目录与子目录的写范围重叠，同一文件不同任务也重叠。Master自己的业务写入同样登记；只读任务不占写范围。独立文件可并行；需要隔离工作区时只在宿主实际支持且已授权的情况下使用，并写清产物合并责任。工具的静态检查不阻止代理绕过占用。

依赖引用 ticket_id/attempt_id，仅在其 acceptance=accepted 后解锁；依赖来源发生变化则重新核受影响候选。

## 异常与预算

- 投递未知：保留unknown及占用，查同键/真实会话状态；确认未接收才在同键下重试投递，不新建执行键规避去重。无法确认则阻塞并交代边界。
- 到期或无进度：先查真实状态；必要时在授权范围请求停止新增工作并保存结果。不据超时判死，不抢占未知写范围。
- 取消：记录取消意图，调用宿主已授权的停止能力或让Worker收尾；收到停止确认且runtime=ended后置stopped并释放。没有停止能力则保持占用并说明。
- 部分成功：保留已完成副作用及证据，先查实际目标状态；恢复只做剩余部分。发布/外部修改仍遵守对应用户授权。
- 验收预算：policy.max_review_rounds默认3，是可调整的本项目默认值。计完整交付验收，状态查询/补证不计。达到预算后记录未完和选项，不无界重试，也不在原授权足够时重复索权。

## 交接步骤

1. 用户明确任命或已有明确移交授权后，登记 `handoff_status=requested`；记录 from/to、源generation及待接收成员，保存[交接摘要](handoff_summary.md)。接任者此时只读。
2. 旧Master停止新增派单，登记 `quiescing`。核在途attempt、占用、外部副作用及真实运行状态，填 quiescence_evidence。可以保留运行中的Worker，但接任者必须具备实际管理它们的能力。
3. 核宿主是否允许转移成员控制权。parent_scoped或不可转移团队只交接已落盘状态；旧父会话继续负责在途子代理收尾。未经用户授权不创建替代成员。旧Master不可达而存在未知运行时保持blocked，不自动夺权。
4. 已确认旧Master停派、无并发登记写入且接任者可管理所需状态后，由旧Master作最后一次提交：previous=旧ID，active=新ID，generation+1，handoff_status=completed；在handoff中写 completed_at 和 transferred_by。旧Master此后不再改共享登记或派单。旧Master确已结束的恢复场景由用户授权的接任者提交，并记录证据及恢复理由，不能假造旧Master确认。
5. 新Master复核登记后确认，先处理/验收继承交付；Worker在执行新派单前读取新所有者。handoff_summary只存摘要，不单独证明所有权已经转移。

不具备这些条件时只输出可交接的文件与限制；不能承诺持续在线、跨进程互斥或跨平台自动接管。
