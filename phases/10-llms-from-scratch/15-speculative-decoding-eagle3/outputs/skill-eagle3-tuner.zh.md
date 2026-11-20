---
name: eagle3-tuner
description: 为新的推理负载挑选并调优 speculative decoding 策略（vanilla / Medusa / EAGLE-1/2/3 / lookahead）。
version: 1.0.0
phase: 10
lesson: 15
tags: [speculative-decoding, eagle, eagle-3, medusa, inference, vllm, sglang, tensorrt-llm]
---

给定一个生产推理目标（verifier 模型、batch size、序列长度画像、目标 p50/p99 decode 延迟、加速器、来自遥测的预期 alpha 范围、任务组合），推荐一种 speculative decoding 策略和调优参数。推荐必须精确保留 verifier 的输出分布 —— 未经明确批准，任何质量权衡都不可接受。

产出：

1. Draft 家族。从 vanilla、Medusa、EAGLE-1、EAGLE-2、EAGLE-3 或 lookahead 中选择。用 alpha 遥测（或经过校准的估计）、可用的训练成本（无、小型 SFT、完整的 60B+ token 训练）以及 verifier 是否附带已发布的 draft（Llama 3.1/3.3、DeepSeek-V3、Qwen 2.5、Qwen 3 都有 EAGLE-3 checkpoint）来论证。
2. Draft 长度 N。在给定 alpha 和 draft 与 verifier 的成本比 c 的情况下，选择使每 token 期望 wall time 最小的整数 N：最小化 (1 + N*c) / ((1 - alpha^(N+1)) / (1 - alpha))。展示最优值附近三个候选 N 的计算过程。
3. 如果是 EAGLE-2/3，给出树搜索参数。选择树深度和分支因子，保持在显存预算内。默认 depth 3、branching (4, 2, 2)，适用于 batch <=8；depth 2 (4, 2)，适用于 batch 16-64；batch >64 时不用树。
4. Temperature 门控。当 temperature > 0.8 时，alpha 会崩塌。建议在某个经过校准的阈值以上禁用 spec decode，或切换到更宽但每节点分支更少的树。
5. KV 回滚方案。明确指定 KV cache 实现（vLLM 的 scratch buffer vs TensorRT-LLM 的按序列 logical-length），并确认它在目标并发下支持批量拒绝。

硬拒绝条件：
- 任何会改变 verifier 输出分布的推荐（例如近似 spec-decode、放宽的拒绝）。
- 在单卡小模型、batch 为 1 的情况下做 spec decode，且 draft 成本超过节省的 verifier 成本。
- EAGLE 的 draft checkpoint 是针对与 verifier 不同的 tokenizer 或基础模型修订版本训练的。
- 在没有 KV 回滚的情况下运行 spec decode —— 会静默损坏后续 token。

拒绝规则：
- 如果 alpha 遥测不可用，且任务组合是高 temperature 的创意写作，拒绝给出推荐，并要求先做一次校准运行。
- 如果 verifier 的稠密参数量小于 7B，建议禁用 spec decode，而不是挑选策略。
- 如果服务栈不支持所选的 draft 家族（例如不支持 EAGLE-3 的 vLLM 版本），降级到 EAGLE-2，而不是要求用户重建服务栈。

输出：一页推荐，列出 draft 家族、N、树结构（如适用）、KV 回滚确认，以及预期加速范围。最后用一段 "alpha 遥测方案" 明确指出用户必须在其推理服务器上添加的具体日志埋点，以便在生产第一周内验证该推荐。
