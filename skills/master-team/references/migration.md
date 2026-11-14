# v1 迁移与副本维护

1. 备份目标项目的原登记表和团队规则。技能包版本升级不自动改变任何现有团队。
2. 核旧模式、成员ID、模型、角色差异和真实运行；v1中的空tickets不证明没有在途工作。
3. 可运行 `python scripts/team_check.py migrate --input OLD.json --output NEW.json`。只写不存在的新文件，保留旧成员ID及未知扩展字段，旧原始表存legacy_v1，旧工单存legacy_tickets。迁移后mode=manual、能力未验证，旧活动工单放migration_unresolved，必须人工核对。
4. 输出只有在字段/在途事项核实后才可启用。发现active_ticket、旧tickets、交接中状态或未知运行时禁止自动替换现行表；legacy_unverified成员不能直接派工。
5. 将旧communication_context、agent_system等按目标项目约束定向合并，codex_team_protocol只作兼容引用，现行协议正文统一为team_protocol。已有session_handoff可合并复用，不堆叠“最新补充”。
6. 核同键状态、候选和写占用，不修改已执行目标或清空旧成果。通过检查后由当前合法所有者在已授权范围切换；生成新文件不等于所有权移交。

project_root和原业务事实来自目标项目，不从技能安装目录复制。只更新用户指定的副本；发布前检查同名旧版是否仍优先被加载。
