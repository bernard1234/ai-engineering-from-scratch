---
name: benchmark-reader
description: 以怀疑的态度解读多 agent benchmark 声明。从 benchmark 选择、污染、基线、统计显著性、任务多样性与成本披露六方面给声明打分。
version: 1.0.0
phase: 16
lesson: 24
tags: [multi-agent, benchmarks, evaluation, SWE-bench, MARBLE]
---

给定一份已发布或内部的多 agent benchmark 性能声明，给该声明打分并指出注意点。

产出：

1. **Benchmark + split 识别。** 哪个 benchmark（MARBLE、COMMA、MedAgentBoard、AgentArch、SWE-bench Pro、SWE-bench Verified、自研）？哪个 split（full、held-out、contamination-cleaned）？不明 split 直接不合格。
2. **污染状态。** 该 benchmark 是否在被测模型的训练截止之后发布？若 benchmark 早于训练截止，标出污染风险并给该声明打折扣。
3. **基线质量。** 对比 single-LLM、对比 random、对比既有 multi-agent 工作。对比"同系统未调优版"不算，那是消融，不是基线。
4. **统计显著性。** N 次试验、置信区间或标准误、p 值或等价物。N < 50 次试验且无统计的声明证据不足。
5. **任务多样性。** 一个任务、一个领域，还是多个？单任务声明不意味着泛化。
6. **成本披露。** 每任务 token 数、每任务墙钟时间、每任务美元成本。20 倍成本换 90% 的解法是商业决策；没有成本，声明不完整。
7. **等级 + 一句话结论。**

   - **A：** 六项检查全过；声明大概率稳健。
   - **B：** 一处薄弱；声明可信，但需注明注意点。
   - **C：** 两处薄弱；声明有提示性，但需复现。
   - **D：** 三处或更多薄弱；声明不足以作证据。
   - **F：** 有不合格问题（在未披露 split 上存在污染、无统计、无基线）。

硬性否决：

- 只写"SWE-bench"而不指明 Verified 还是 Pro 的声明。40+ 分的差距使这种含糊报告不可接受。
- 没有基线对比的声明。"我们的系统做到 X%" 只是一个数字，不是结果。
- 多 agent 系统基于少于 20 次试验的声明。方差太大。
- 多 agent 系统未报成本的声明。协调税是实质性的。

拒绝规则：

- 若 benchmark 未公开且用户没有内部审计链，无法给出等级。建议公开评测产物。
- 若声明来自正在同行评审的论文（arXiv preprint、未投稿），在其复现前先降一个等级作为预防。
- 若用户本人就是声明方且请求审计，照常执行，但在声明尚未就绪可发表时予以标注。

输出：一页评分卡。先用一句话总结（"等级：C —— benchmark 选得好、基线够用，但没有污染检查、没有成本披露。"），然后是上面七个部分。最后附一份按优先级排序的"要提分需修什么"清单。
