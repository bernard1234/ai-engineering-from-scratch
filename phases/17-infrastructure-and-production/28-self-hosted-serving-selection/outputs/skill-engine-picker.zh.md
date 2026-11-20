---
name: engine-picker
description: 给定硬件、规模与工作负载，挑选一个自托管 LLM 引擎（llama.cpp、Ollama、TGI、vLLM、SGLang）。把 2026 年 TGI maintenance mode 作为迁移触发点。
version: 1.0.0
phase: 17
lesson: 28
tags: [self-hosted, vllm, sglang, llama-cpp, ollama, tgi, trt-llm, engine-selection]
---

给定硬件（CPU / Apple Silicon / AMD / NVIDIA Hopper / NVIDIA Blackwell）、规模（单用户 / 小团队 / 生产 / 企业）与工作负载（通用对话 / agent / RAG / 长上下文 / 代码），产出一个引擎推荐。

产出：

1. 引擎。点名具体的引擎。援引硬件第一、规模第二、工作负载第三的决策树。
2. 为什么不选替代方案。对每个替代引擎，说明它为何不是首选（TGI maintenance mode、AMD 排除 TRT-LLM、Ollama 仅限开发）。
3. 流水线。若是生产，点名流水线模式（dev Ollama → staging llama.cpp → prod vLLM/SGLang），并确认权重格式（GGUF 或 HF）能贯通流转。
4. 生产栈组合。在生产规模下，指向 Phase 17 · 18（production-stack）、· 17（分离式）、· 11（cache 感知路由）来组合。
5. TGI 迁移。如果现有引擎是 TGI，明确迁移计划与时间线 —— 不紧急，但应在 6 个月内启动。
6. 硬件陷阱。点出两个硬约束：仅 CPU → llama.cpp；AMD → 不能用 TRT-LLM。

硬性拒绝：
- 在 2026 年把新项目默认到 TGI。拒绝 —— maintenance mode。
- 在 > 1 个并发用户时用 Ollama 做共享生产。拒绝 —— 吞吐差距。
- 未确认仅限 NVIDIA 就建议 TRT-LLM。拒绝 —— AMD / 非 NVIDIA 是硬性阻断。

拒绝规则：
- 如果硬件是混合的（部分 AMD、部分 NVIDIA），要求按集群做引擎决策；不要强行单一引擎。
- 如果生产规模下工作负载是“未知/通用”，默认 vLLM，并计划在积累 3 个月流量数据后重新评估。
- 如果团队想要“没有 Blackwell 可用时的每 GPU 最快”并坚持仅用 Hopper，确认即可 —— TRT-LLM 或 vLLM 都可接受。

输出：一页纸的推荐，包含引擎、被排除的替代方案、流水线、生产栈组合、TGI 迁移姿态。结尾用单一的季度评审收尾：当工作负载形态发生实质变化时重新评估引擎选择。
