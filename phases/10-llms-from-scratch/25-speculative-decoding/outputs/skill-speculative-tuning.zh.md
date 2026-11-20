---
name: speculative-tuning
description: 分析 decode 工作负载画像，为 speculative decoding 挑选 draft 模型、draft 长度 K、温度门控与回退策略。
version: 1.0.0
phase: 10
lesson: 25
tags: [speculative-decoding, draft-model, alpha, throughput, inference, decode-latency]
---

给定目标模型（规模、家族、tokenizer）、工作负载遥测（任务组合、prompt 与 decode 的 token 比例、p50/p99 decode 延迟、加速器与 HBM 余量、平均 batch size、采样温度分布）以及可用的 draft checkpoint，输出：

1. Draft 选择。从同家族小模型（Llama-70B 对应 Llama-3.2-1B）、在目标输出上训练的蒸馏 draft、在目标上外挂的 Medusa heads，或“不做 spec decode”（若没有任何 draft 的 FLOP 成本比在 30% 以内）中选择。逐字节确认 tokenizer 与目标匹配；tokenizer 不匹配则拒绝。
2. Draft 长度 K。取 E[tokens] / (1 + K x c) 的 Argmax，其中 c 是 draft 与目标的成本比。使用在 5_000 tokens 分布内数据上做校准运行测得的 alpha，展示 K 取 2、3、4、5、6 时的计算过程。对话默认 K=4，代码 K=6，高温创意写作 K=2。
3. 温度门控。设定一个温度阈值，高于此值即禁用 spec decode。默认 0.8；若校准显示 alpha 更早崩溃，则下调到 0.6。拒绝任何依赖逐请求检查、且增加超过 50 微秒的温度门控。
4. Tree 预算。如果服务栈支持 tree drafting，batch 小于 8 时选一个小的固定树（深度 2，分支 3-2）；batch 大于 32 时用扁平链。用字节数说明 verifier 的 KV scratch 大小，并确认它能装进 HBM 余量。
5. 回退策略。点名指标（对最近 1_000 次 verify 的滑动窗口 alpha）与阈值（alpha 低于 0.4），达到时服务器对该请求流回退到普通自回归 decode。包含该回退决策的按请求生命周期。

在 batch size 超过 verifier 受计算限制的临界点之后，拒绝 spec decode。超过该点后，speculator 本应吸收的未用 FLOPs 不复存在；吞吐会下降。对任何实测 alpha 低于 0.4 的任务家族拒绝 spec decode；draft 开销占主导，墙钟延迟会变差。拒绝对未经在留出的 1_000-token 样本上针对目标验证的 draft：未验证的 draft 是一种静默的 KL drift。

示例输入：“8xH100 上的 Llama-3.3-70B，对话工作负载，batch 16，p50 decode 28 ms，p99 60 ms，温度分布均值 0.4 / 最大值 1.2，校准显示对话 alpha 0.78，代码 alpha 0.61。”

示例输出：
- Draft：Llama-3.2-1B-Instruct。相同 tokenizer、相同家族，比值 c 约 0.03。
- K：4。E[tokens/verify] = 对话 3.4，代码 2.5。K=5 在对话上多 0.1 token，却多付 0.03 的 c；拒绝。
- 温度门控：0.8。高于 0.8 时，在校准集上 alpha 掉到 0.45 以下。
- Tree 预算：深度 2 分支 (3, 2)。batch 16 下 KV scratch 480 MB，装得下。
- 回退：最近 1_000 次 verify 的滑动窗口 alpha 低于 0.40 时，对该流禁用 spec decode 30 s，然后再次探测。
