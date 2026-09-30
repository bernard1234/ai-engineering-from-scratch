# Mission - Agent 的初始化脚本

## 目标
构建 `init_agent.py`，探测 runtime、依赖、测试命令、环境变量和 state 新鲜度，然后写出 `init_report.json`，并在 block 级 probe 失败时大声停机。

## 输入
- 一个带 `requirements.txt`（或等价物）、一条测试命令、以及来自 lesson 34 的 workbench state 文件的 repo
- 本课的 probe 表（runtime、deps、paths、env、state 新鲜度、last-known-good 提交）

## 交付物
- `init_agent.py`，每个 probe 一个函数，返回 `(name, status, detail)`
- 带完整 probe set 和一个时间戳的 `init_report.json`
- 任何 block 级 probe 失败时非零退出

## 验收标准
- `python3 code/main.py` 在 happy path 上以零退出
- 连续运行两次除时间戳外是 no-op
- 一个模拟的缺失环境变量 probe 出现在 report 中并翻转退出码

## 范围之外
- 自动安装缺失依赖。脚本停机并呈报；人类来修。
- 从 probe 调用 LLM。probe 保持确定性管道。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-init-script.md` - 提取出的 skill