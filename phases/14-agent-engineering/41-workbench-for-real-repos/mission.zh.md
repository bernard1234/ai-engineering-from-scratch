# Mission - 在真实仓库上的 Workbench

## 目标
针对同一个示例应用，让同一个 `/signup` 校验任务分别走仅 prompt pipeline 和 workbench 引导 pipeline，然后产出一份怀疑者能读懂的前后对比报告。

## 输入
- `sample_app/`，含 `app.py`（无校验）、`test_app.py`（一个 happy-path 测试）、`README.md`、作为禁区诱饵的 `scripts/release.sh`
- 两条 pipeline 完全脚本化，没有真实 LLM 调用

## 交付物
- `code/main.py`，针对同一个 fixture 编排两条 pipeline
- `before-after-report.md`，带五个 outcome 的表格
- `comparison.json`，供下游画图使用

## 验收标准
- `python3 code/main.py` 以零退出码结束
- 报告测量全部五个 outcome：测试确实运行了、验收达成、scope 之外的文件、handoff 质量、reviewer 总分
- workbench pipeline 在五个中至少四个上胜过仅 prompt pipeline

## 范围之外
- 接入真实 LLM。pipeline 是脚本化的，以保证可复现。
- 调优模型。对比通过构造把模型保持不变。

## 参考
- `docs/en.md` - 完整课程
- `code/main.py` - 参考实现
- `outputs/skill-workbench-benchmark.md` - 抽取出的 skill
