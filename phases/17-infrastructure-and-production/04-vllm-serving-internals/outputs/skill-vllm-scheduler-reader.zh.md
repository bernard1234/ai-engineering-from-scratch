---
name: vllm-scheduler-reader
description: 通过读取调度器层面的旋钮诊断 vLLM 服务配置，识别 PagedAttention、continuous batching、chunked prefill 中哪一个是瓶颈。
version: 1.0.0
phase: 17
lesson: 04
tags: [vllm, paged-attention, continuous-batching, chunked-prefill, serving, scheduler]
---

给定一份 vLLM 服务配置（模型、dtype、硬件、`--gpu-memory-utilization`、`--max-num-batched-tokens`、`--enable-chunked-prefill`、`--speculative-config`、最大并发，以及观测到的指标集：TTFT 均值/P99、ITL 均值/P99、吞吐 tok/s），产出一份调度器层面的诊断。

产出：

1. 配置解读。对每个开关，说明它控制哪种调度器行为，以及 2026 年的默认值。标出任何被设为非默认值的开关，并说明原因。
2. 瓶颈识别。把瓶颈归类为以下之一：PagedAttention 供给不足（KV 块饥饿）、continuous batching 停滞（WAITING 队列增长）、chunked prefill 尺寸失当（TTFT 尾部尖峰）、decode 计算受限（ITL 下限），或 HBM 受限（装不下批次）。用上报的指标给出依据。
3. 调参建议。给出具体、有顺序的动作 —— 该翻哪个开关、该试哪个取值、该盯哪个指标。在没有先把调度器层面的调优做尽之前，不要建议“多上几块 GPU”。
4. 兼容性检查。对照配置中确切 vLLM 版本的兼容性矩阵，检查每一对已启用的特性。对 v0.18.0，矩阵把 speculative decoding 标记为与 chunked prefill 和 prefix caching 兼容。
5. 接下来读什么。视诊断结果指向 vLLM v0.18.0 发布说明、PagedAttention 论文或 Aleksa Gordic 的 V1 调度器讲解之一。

硬性拒绝：
- 缺少四项核心指标（TTFT、ITL、吞吐、并发）就做诊断。拒绝，并要求提供指标集。
- 未检查 speculative decoding 配置就建议 `--enable-chunked-prefill`。
- 把 `DCGM_FI_DEV_GPU_UTIL` 当作扩缩容信号。vLLM 会预分配 KV；占空比数字具有误导性。

拒绝规则：
- 如果 H100 上上报的吞吐低于 100 tok/s，瓶颈很可能不在 vLLM —— 检查客户端侧的 tokenizer、Python GIL 或请求级串行化。
- 如果 `--gpu-memory-utilization` 被设到 0.7 以下，拒绝继续调优 —— 操作者主动放弃了可用的 HBM，正确的修法是先抬高上限，再考虑翻动调度器开关。
- 如果操作者索要 speculative decoding + chunked prefill 的配方，回答前先对照其 vLLM 版本的兼容性矩阵检查该组合，并指向第 17 阶段 · 05 中的 EAGLE-3 了解 draft 方法。

输出：一页调度器诊断，列出开关、瓶颈、按序建议、兼容性说明和下一步阅读指引。结尾用一段“接下来测什么”点出 P99 ITL、块分配速率或 WAITING 队列深度三者之一，取决于识别出的瓶颈。
