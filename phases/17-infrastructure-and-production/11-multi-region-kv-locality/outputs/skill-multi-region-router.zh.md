---
name: multi-region-router
description: 设计一套具备 KV-cache 局部性、驻留边界、DR 清单和季度故障切换演练的多区域 LLM 路由方案。
version: 1.0.0
phase: 17
lesson: 11
tags: [multi-region, kv-cache, routing, dr, bedrock-cri, vllm-router, llm-d, gorgo]
---

给定范围内的区域、驻留边界、预期的 prefix-cache 多样性以及 TTFT SLA，产出多区域路由与 DR 方案。

产出：

1. Router 选择。选择 cache-aware router（vLLM Router、llm-d router）并描述 KV 事件通道。说明 prefix-hash 算法（例如 512 token 滚动）和打平规则（最小队列深度）。
2. 路由策略。是区域优先，还是 GORGO 式的全局最小化 prefill + RTT？用 prompt 长度分布说明理由 —— 长 prompt（>8K token）能从跨区域路由获益；短 prompt 不能。
3. 驻留分区。在任何优化之前：哪些请求因法律原因（GDPR、HIPAA）绑定到哪些区域。即使 TTFT 会改善，也禁止跨驻留区路由。
4. 商业 CRI 层。建议是否启用 Bedrock Cross-Region Inference 或 GKE Multi-Cluster Gateway 作为可用性层。明确说明这一层不是 TTFT 优化。
5. DR 清单。三文件最小集（HF 仓库 + 引擎配置 + 部署清单）。核对 tokenizer、量化配置、RoPE、chat template、LoRA adapter 均已包含。说明存储方式（S3 跨区域复制、多区域 GCS）。
6. 故障切换演练。季度节奏。谁执行、测量什么（RTO、RPO、cache 预热时间）。目标：30 分钟 RTO，对齐 2024 年 JPMorgan 的真实演练。

硬性拒绝：
- 为路由优化忽略驻留约束。拒绝 —— GDPR 违规比 TTFT 收益更重要。
- 宣称 Bedrock CRI “解决了”跨区域路由。拒绝 —— CRI 是可用性，不是 TTFT。
- 只备份权重。拒绝 —— 说出 32% DR 失败的统计，并要求三文件清单。

拒绝规则：
- 如果范围内只有一个区域，谢绝本方案 —— 单区域有不同的失效模式（第 17 阶段 · 03 有覆盖）。
- 如果驻留约束与 TTFT SLA 不相容（例如 EU 驻留迫使每个请求都在冷 prefix 上做 prefill，而 8K prompt 的 P99 TTFT 要求 < 100 ms），拒绝承诺该 SLA，并把产品需求上报。

输出：一页方案，写明 router、路由策略、驻留分区、CRI 层姿态、DR 清单、季度演练负责人。最后给出唯一需要告警的指标：跨区域 prefix-cache 命中率跌破方案规定的阈值。
