# Mission - Scope Contract 与任务边界

## 目标
写一份每任务 `scope_contract.json` 和一个 glob 感知 checker，把 agent 的 diff 与 contract 比对，标记任何禁止或越界写入。

## 输入
- 一份带允许 glob、禁止 glob、验收命令、回滚段落、所需审批的任务描述
- 两个 demo run：一个留在 scope 内，一个越界

## 交付物
- `scope_contract.json` schema 验证器（JSON Schema 的子集，glob 数组）
- 一个从触碰文件加运行命令产出 `RunSummary` 的 diff 解析器
- `scope_check(contract, run) -> (violations, in_scope, off_scope)`
- 保存在脚本旁的 `scope_report.json`

## 验收标准
- `python3 code/main.py` 以零退出
- 在 scope 内的 run 报告零违规
- 越界的 run 报告确切的越界文件和各自原因

## 范围之外
- 时间预算、网络出口允许列表。本课交付文件 glob；练习提示扩展它。
- 接入 runtime interrupt。本课止步于 report。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-scope-contract.md` - 提取出的 skill