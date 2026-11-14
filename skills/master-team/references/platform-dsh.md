# DeepSeek Harness 适配

目标为deepseek-ai/deepseek-harness，实际接口随profile、插件和版本改变。来源见 [sources](sources.md)。

## 安装与发现

当前官方文件系统提供器扫描用户 `~/.dsh/skills/`、`~/.agents/skills/`，以及项目 `.dsh/skills/`、`.agents/skills/`；将完整目录放到其中的master-team子目录。`.skills/`只有被目标环境另行配置时才可使用。DSH预设/插件可覆盖技能目录，安装后核当前skills列表或skill工具能否发现并读取入口，不仅以文件存在判断生效。

核心入口只依赖name/description Markdown，不依赖agents/openai.yaml。团队模板合并到项目agent-team，项目规则入口按当前预设支持方式引用。

技能首次被实际读取并用于用户上手请求后，按[教学规则](onboarding.md)主动分步引导。若导入后尚未被发现/加载，使用[first_use](../assets/first_use.md)的自然语言入口；不把复制目录当成自动会话事件，也不自行注册插件hook。

## 子代理协作

当前官方委派工具默认名为subagent，可配置其他名称；控制提供器提供list_agents、send_message、wait_agent、interrupt_agent。可续接的本地Spawn/Fork子代理可在同一任务树继续收任务；外部执行后端可能只执行一次且不收后续消息。实际名称和参数以工具声明为准，这些能力不等于跨根会话独立持久聊天，因此默认parent_scoped。

若明确存在其他已验证且已授权的独立会话通道，才选择persistent；不能把workspace消息事件或内部服务文档直接当作用户可调用工具。当前没有子代理/通信工具时采用manual，不自动安装控制插件。

父子会话、共享root、隔离工作树和结果文件可见性分别核实。等待回报只视为对应工具语义，不自动等同于进程退出或Master验收；停止后仍核实际状态。

send_message成功仅说明收件箱接受，不返回对方的执行结果。wait_agent等待当前调用者的后续输入，不是等待某个目标变成done。interrupt_agent返回停止请求接受，也不证明已停止写入。若宿主明确要求在只剩等待时结束本轮、由完成通知继续唤起，则遵守其事件驱动方式，不用循环sleep替代，也不把结束本轮当成整个用户任务验收完成。

## 恢复与交接

记录宿主ID、父关系和实际工具；只在宿主支持时复用子代理ID。换根会话时，旧树的子代理管理权不能靠修改登记表转移。先由原父会话收尾或输出文件交接包，任何新建替代成员另遵守用户授权。
