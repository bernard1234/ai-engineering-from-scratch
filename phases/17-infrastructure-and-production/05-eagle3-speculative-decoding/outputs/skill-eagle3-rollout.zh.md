---
name: eagle3-rollout
description: 产出分阶段的 EAGLE-3 speculative decoding 上线计划，在发布前于真实流量上测量接受率 alpha。
version: 1.0.0
phase: 17
lesson: 05
tags: [speculative-decoding, eagle-3, vllm, alpha, production-rollout]
---

给定 target 模型、硬件（GPU 类型与数量）、流量描述（通用聊天 / 代码 / 垂直领域）、目标并发，以及当前基线指标（TTFT、ITL、吞吐），产出一份分阶段的 EAGLE-3 上线计划。

产出：

1. 基线测量计划。用哪个 benchmark（LLMPerf、GenAI-Perf 或生产影子流量）、哪种 prompt 分布、哪个并发点、记录哪些指标（TTFT 均值/P99、ITL 均值/P99、吞吐、并发）。
2. Draft head 选择。通用聊天用 ShareGPT 训练的 EAGLE-3。垂直领域流量（代码、医疗、法律）用领域训练的 EAGLE-3，或决定在上线前先训练一个。
3. 配置。确切的 vLLM `speculative_config` 字段（method、model、num_speculative_tokens）。对照部署所用 vLLM 版本的兼容性矩阵检查该组合（v0.18.0 把 speculative decoding 标记为与 chunked prefill 兼容）。
4. Alpha 门禁。生产并发下目标 alpha >= 0.55。测量流程：影子流量跑 24 小时，记录 vLLM 的 `spec_decode_metrics`，用被接受的 token 数除以请求的 draft 长度。任一 1 小时窗口内 alpha 低于 0.45 即触发熔断。
5. 尾部监控。画出 P99 ITL 差值（开启 spec 减关闭 spec）。如果差值为正，说明被拒 draft 的两趟模式在咬人。降低 K，或在该负载上关闭。
6. 盈亏平衡检查。在所报并发下，按当前验证开销计算盈亏平衡 alpha。只有当实测 alpha 至少高出盈亏平衡 0.1 时才上线。

硬性拒绝：
- 未在生产流量上测量 alpha 就上线。拒绝，并要求做 24 小时影子测量。
- 不说明实测 alpha 就宣称 2-3 倍加速。
- 为延迟并非约束的离线批处理任务启用 speculative decoding。
- 在 vLLM 0.15.0 及更早版本上把 speculative decoding 与 pipeline parallelism 组合。speculative decoding 文档将其列为不兼容。

拒绝规则：
- 如果流量以极短输出为主（均值 50 token 以下），拒绝。draft 开销占主导；直接上线裸 target。
- 如果硬件是消费级（RTX 4090 / 5090）且 batch size 始终低于 8，建议裸 target —— 验证开销的批摊薄需要该硬件供不出的并发。
- 如果用户想要在没有测量回路的情况下自动调 K，拒绝。K 由实测 alpha 加上验证开销决定；没有任何自动调参能替代测量。

输出：一页分阶段上线计划，列出基线 → 配置 → alpha 门禁 → 尾部监控 → 盈亏平衡确认。结尾用一段“接下来测什么”点出领域特定 EAGLE-3 训练、降低 K，或回退到裸 target，取决于诊断结果。
