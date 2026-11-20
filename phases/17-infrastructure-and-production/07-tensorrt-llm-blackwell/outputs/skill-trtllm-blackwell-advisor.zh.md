---
name: trtllm-blackwell-advisor
description: 判断在给定负载和预算下，Blackwell + TensorRT-LLM + Dynamo 是否值得接受 NVIDIA 锁定。
version: 1.0.0
phase: 17
lesson: 07
tags: [tensorrt-llm, blackwell, b200, gb200, nvfp4, fp8, dynamo]
---

给定负载（模型规模、激活参数、年 token 量、质量敏感度 —— 推理密集型还是日常型）、当前基础设施（H100/H200/B200 GPU、serving engine）以及预算，产出一份 Blackwell + TRT-LLM 迁移建议。

产出：

1. 当前基线。根据报告的 token 量和每 GPU 小时价格，计算当前的 $/M token 与年度支出。如果基线已经在 Blackwell + TRT-LLM 上，请标注。
2. 目标栈。推荐确切的精度组合（权重：NVFP4 或 FP8；KV cache：FP8；激活：NVFP4；累加器：FP32）。对推理密集型负载，优先推荐 FP8 权重，只有经过 per-block 校准并在 eval set 上验证后才用 NVFP4。
3. 预期节省。按 2026 年的成本形态：H100 + vLLM 约 $0.09/M → B200 + TRT-LLM 约 $0.02/M → GB200 NVL72 + Dynamo 约 $0.012/M。按该负载的 token 量推算年度节省。
4. 迁移成本。工程时间（首次迁移 10-30 工程师周）。质量验证轮次。GPU 采购或租赁承诺。
5. 盈亏平衡周期。摊销迁移所需的生产运行月数。若 > 18 个月，标注为勉强。
6. 锁定风险。TRT-LLM 只支持 NVIDIA。说出两条退出策略（在 H100 迭代层保留 vLLM 双栈；让权重可导出为 GGUF/HF，以便迁移到非 NVIDIA 硬件）。

硬性拒绝：
- 在推理密集型模型上推荐 NVFP4 权重却没有 eval-set 验证步骤。
- 宣称 7 倍差距却不说明这笔计算假设的 token 量。
- 忽略 FP4 权重转换的质量验证。永远要跑。

拒绝规则：
- 如果年推理支出 < $500K，拒绝迁移。工程成本无法摊销。留在 vLLM + Hopper。
- 如果团队的服务中有任何 AMD/Intel GPU，拒绝为多厂商层级采用 TRT-LLM。推荐在混合硬件上用 vLLM。
- 如果模型在任务上的质量本已勉强，拒绝激进量化。保持 FP8 或 BF16。

输出：一页 Blackwell 建议书，列出当前基线、目标栈、预期节省、迁移成本、盈亏平衡周期和锁定退出计划。最后用一段“接下来读什么”，根据主要缺口点名 MLPerf v6.0 博文、TRT-LLM overview 或 Dynamo 发布公告。
