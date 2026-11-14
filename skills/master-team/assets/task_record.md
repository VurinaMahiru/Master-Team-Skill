# 用户任务主记录

## 需求与授权

- task_id：填写本项目唯一编号
- 用户目标和验收条件：
- 已有授权、允许操作和重要限制：
- 项目根目录与团队目录：
- 候选及基线定位：

## 工单

每个ticket按需增加一节；每次attempt独立保留，不改写旧attempt。

### ticket 与 attempt

| 字段 | 内容 |
| --- | --- |
| task_id / ticket_id / attempt_id | 与登记表一致 |
| master_session_id / master_generation | 真实派单身份与代次 |
| worker_id / session_id / transport | 逻辑成员与宿主身份 |
| goal / candidate_ref | 本轮不可变目标与候选 |
| reads / writes | 明确项目相对路径，无通配符 |
| depends_on | 依赖ticket/attempt及验收状态 |
| deadline / max_review_rounds | 项目配置和本轮期限 |
| delivery / execution / runtime / acceptance | 四个维度分别记录 |
| report_ref / artifacts / evidence | 实际可访问路径与必要摘要 |

## 验收与收尾

- 逐项需求与产物核对：
- 已复用证据及适用候选：
- 新增验证、失败、未测及限制：
- 宿主实际结束/停止证据与写占用释放：
- 已发生外部副作用及剩余项：
- 最终结论与下一步：
