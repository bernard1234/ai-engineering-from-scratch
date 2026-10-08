# Mission - 最小智能体工作台

## 目标
把三文件最小工作台（路由器、state、任务板）铺进一个全新的 `workdir/`，并证明一次智能体轮次能够读取 state、拉取任务、写进 scope，并持久化更新后的 state。

## 输入
- 课程代码旁边一个空的 `workdir/` 目录
- 对这三个文件的了解：`AGENTS.md`、`agent_state.json`、`task_board.json`

## 交付物
- `code/main.py`，创建这三个文件并跑一个轮次
- `workdir/AGENTS.md` 简短路由器，指向 state、board 和验证命令
- `workdir/agent_state.json`，带当前任务 id、已改动的文件、下一步动作
- `workdir/task_board.json`，带一份小 backlog 和状态

## 验收标准
- `python3 code/main.py` 在第一次和第二次运行都以零退出
- 第二次运行从第一次停下的地方接手，而非从零开始
- 脚本打印的 diff 展示该轮次改动的那个文件

## 范围之外
- Scope contracts、verification gates、reviewer agents。那些在后面的课里叠上去。
- 冗长、巨石式的 `AGENTS.md`。路由器有意保持简短。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-minimal-workbench.md` - 提取出的 skill