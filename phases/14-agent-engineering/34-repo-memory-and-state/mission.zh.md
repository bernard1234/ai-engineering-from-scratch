# Mission - Repo 记忆与持久 State

## 目标
为 `agent_state.json` 和 `task_board.json` 编写 JSON Schema，构建一个能加载、验证、变更并原子写入的 `StateManager`，并在两个 turn 间证明往返一致。

## 输入
- 来自 lesson 32 的三文件 workbench 结构
- 一个覆盖 required、type、enum、pattern 和 items 的纯 stdlib 验证器

## 交付物
- 代码旁的 `agent_state.schema.json` 和 `task_board.schema.json`
- 采用 temp-and-rename 写入的 `StateManager.load`、`StateManager.update`、`StateManager.commit`
- 一个在两个 turn 间变更 state 并干净重载的 demo run

## 验收标准
- `python3 code/main.py` 以零退出
- 一次坏写入（缺必需字段、坏 enum）被拒绝，而非持久化
- run 之后的 `workdir/agent_state.json` 能通过 schema 验证

## 范围之外
- SQLite 或外部存储后端。本地文件就是本课。
- LangGraph checkpointers、Letta memory blocks。同样的思路、不同的存储；此处范围之外。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-state-schema.md` - 提取出的 skill