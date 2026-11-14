# Master Team Skill

一个适用于 Codex、DeepSeek Harness 和 Claude Code 的团队协作技能。由 Master 协调分工和验收，Worker 完成具体工作，使用统一工单保留结果与交接状态。

A portable collaboration skill for Codex, DeepSeek Harness, and Claude Code, with role-based delegation, acceptance, handoff, and conversational onboarding.

**作者：VurinaMahiru · 版本：2.1.0**

## 主要功能

- 首次使用分步对话教学：每次只推进一步，支持暂停、续学、跳步或直接进入任务。
- 按需配置角色：最小分工、传统六角色和项目自定义职责均可使用。
- 工单去重与候选核对：区分任务、工单、执行轮次和 Master 所有权代次。
- 写范围与依赖检查：识别目录重叠，避免未验收依赖提前执行。
- 分开记录投递、执行、宿主运行和验收状态，保留未失效证据。
- 明确交接步骤与平台限制，提供旧登记表迁移和只读检查工具。

## 安装

复制仓库中完整的 [`skills/master-team`](skills/master-team/) 目录，而不是只复制 `SKILL.md`。

| 平台 | 项目级目录 | 用户级目录 |
| --- | --- | --- |
| Codex | `.agents/skills/master-team/` | `~/.agents/skills/master-team/` |
| DeepSeek Harness | `.dsh/skills/master-team/` 或 `.agents/skills/master-team/` | `~/.dsh/skills/master-team/` 或 `~/.agents/skills/master-team/` |
| Claude Code | `.claude/skills/master-team/` | `~/.claude/skills/master-team/` |

预设、插件和产品版本可能改变技能发现方式。安装后确认目标环境能读取入口；避免同名旧版覆盖。具体差异见技能中的三份平台说明。

## 首次使用

在能够读取技能的会话里发送：

> 我刚导入 master-team，请开始分步教学。每次只讲一步，根据我的回答继续。

Codex也可使用 `$master-team`，Claude Code可使用 `/master-team`，DSH用其当前界面支持的技能入口。

教学依次说明用途、确认环境、选择分工、配置项目、模拟派工和首个真实任务。自动引导发生在技能被宿主加载并用于请求之后；仅复制文件不会自行创建会话或推送消息。已有团队和明确任务优先，教学状态损坏也不应阻挡实际工作。

## 文件说明

| 位置 | 内容 |
| --- | --- |
| [技能入口](skills/master-team/SKILL.md) | 通用流程及按需加载路由 |
| `skills/master-team/assets/` | 项目规则、工单、结果、交接和教学进度模板 |
| `skills/master-team/references/` | 平台适配、教学、迁移、验证和来源说明 |
| `skills/master-team/schemas/` | 机器可读字段约定 |
| `skills/master-team/scripts/team_check.py` | Python 3.10+ 标准库检查工具 |
| `tests/` | 可在其他目录运行的离线回归测试 |
| [最终检修记录](docs/validation-report.md) | 验证范围及仍需实测的能力 |
| [Word 功能说明](outputs/master-team-v2-2026-11-14/MasterTeam_功能说明_V2.0.docx) | 已补入 2.1.0 教学章节，沿用原文件名 |

技能安装目录只放规则和空白模板；实际团队登记和学习进度写在目标项目的独立团队目录，不覆盖已有数据。

## 本地检查

从仓库根目录运行，核心检查和测试无需第三方 Python 包：

```text
python -B -m unittest discover -s tests -v
python skills/master-team/scripts/team_check.py check --registry skills/master-team/assets/worker_sessions.json
python skills/master-team/scripts/team_check.py onboarding --state skills/master-team/assets/onboarding_state.json
```

其他子命令包括 `dispatch`、`result`、`message-size` 和 `migrate`，参数见 `--help`。迁移只写不存在的新文件，不自动启用。

## 能力边界

技能根据真实宿主能力选择独立会话、父会话子代理或人工交接。文件中的身份登记不是运行时锁，检查工具不证明消息已送达、外部操作成功或宿主已停止写入。

Claude适配目标为Claude Code；无代理工具的聊天界面只使用人工交接。各平台的成员控制权、授权和生命周期限制仍然有效。当前已完成静态及离线检查，尚未进行三个平台中的真实团队或教学联调。
