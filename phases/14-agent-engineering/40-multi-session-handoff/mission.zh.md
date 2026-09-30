# Mission - 跨会话交接

## 目标
在会话结束时从 workbench 产物生成 `handoff.md` 和 `handoff.json`，让下一个会话在第一分钟就进入状态。两种形式携带相同的七个字段；不一致时以 JSON 为准。

## 输入
- 来自前面几课的 `agent_state.json`、`verification_report.json`、`review_report.json`、`feedback_record.jsonl`
- 七个字段：summary、changed_files、commands_run、failed_attempts、open_risks、next_action、verdict_pointer

## 交付物
- 一个 `WorkbenchSnapshot` loader，捆绑四个产物
- `generate_handoff(snapshot) -> (markdown, payload)`
- 一个 feedback 过滤器，挑选最后 K 条记录加上每一条非零退出码
- 写在脚本旁的 `handoff.md` 和 `handoff.json`

## 验收标准
- `python3 code/main.py` 以零退出码结束
- 两个文件都携带全部七个字段，以及一个非空的 `next_action`
- 用相同输入重新运行脚本产生完全相同的 packet

## 范围之外
- Compaction 策略（Codex compact 端点、Claude Code 五阶段）。handoff 关闭会话；compaction 延长会话。
- PR 模板化。markdown 可以复用作 PR 正文，但本课止于文件本身。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-handoff-generator.md` - 抽取出的 skill