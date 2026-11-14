# 验证与边界

## 文件与静态检查

检查入口frontmatter、相对引用、项目占位符、模板JSON和schema。模板中的空白/null不代表实际团队。可用时运行skill-creator的quick_validate；其通过不代表协作运行通过。

Python 3.10+仅标准库检查工具：

```text
python scripts/team_check.py check --registry assets/worker_sessions.json
python scripts/team_check.py message-size --file MESSAGE.txt --budget 4096
python scripts/team_check.py dispatch --registry PROJECT/agent-team/worker_sessions.json --envelope DISPATCH.json
python scripts/team_check.py result --registry PROJECT/agent-team/worker_sessions.json --result RESULT.json
python scripts/team_check.py onboarding --state assets/onboarding_state.json
```

check校验主要结构、工单关联、结果状态、活动占用和依赖循环；dispatch拒绝旧所有者/代次、错误成员、未接受依赖和未冻结的范围；result核归属及候选。它不能证明消息已送达、外部副作用成功、宿主已结束或文件系统具有强制锁。

message-size未提供hard-limit时只报告预算超出；硬上限必须有宿主依据。工具不发消息、不停止成员。跨平台Windows与POSIX路径均按保守规则检查；符号链接和实际主机范围仍在派单时核实。

onboarding核进度结构并建议首次/恢复/暂停/直接任务的路线；--action来自用户明确意图，--project-root及--learner-scope用于防止误用他人/他项目进度。它只输出建议，不读自然语言、不修改进度、也不会在导入瞬间主动触发会话。

## 行为情景

针对协议有意义的失败场景运行离线检查：旧Master/代次、新旧attempt混淆、候选变化、重复结果、重叠目录写占用、未经接受依赖、未知运行不释放、v1迁移不覆盖原文件。测试文件属于开发交付，不必安装进技能。

教学另核首次进入、续接、暂停/关闭自动教学、跳过全课直做任务、已有团队与明确任务优先、维护技能不启动课程、跨项目/学习者状态隔离、版本升级不重学和模拟不等于真实完成。离线路线检查不证明模型会始终按期望提问；三平台真实对话教学需另行观察。

真实投递、停止、父子控制权和交接需要已授权的真实宿主会话验证；本次只改技能时不创建测试团队。报告按平台列静态检查、离线情景和未测运行项，不能将文档适配写成三个平台已实测。

## 产物验收

核候选及实际改动、关键失败修正、测试和必要视觉证据。保持项目要求的独立性。接任先验收在途交付，已完成发布不重做。功能说明文档要与最终字段、平台边界及默认配置一致。
