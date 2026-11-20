---
name: deepseek-v3-reader
description: 读取一个 DeepSeek 系列配置，产出逐组件的架构分析。
version: 1.0.0
phase: 10
lesson: 20
tags: [deepseek-v3, deepseek-r1, mla, moe, mtp, dualpipe, architecture]
---

给定一个 DeepSeek 系列模型（V3、R1 或任意衍生版本）及其配置（hidden_size、layers、num_experts、kv_lora_rank 等），产出一份架构分析，将模型按组件拆解，并指出它使用了哪些 DeepSeek 特有的创新。

产出：

1. 逐字段配置解读。对每个字段，指出它映射到的组件及其贡献的参数数量。格式：`field_name: value → interpretation → parameter contribution`。
2. 参数拆分。总参数、激活参数、激活比例。按 embedding、单层 attention、单层 MLP（dense 与 expert）、router、MTP 模块、LM head、RMSNorm 合计拆分。
3. 目标上下文下的 KV cache。报告 BF16 与 FP8 数值。包含在同一上下文与 hidden size 下与 Llama-3 风格 GQA(8/128) 基线的对比。
4. 创新点检查清单。对 MLA、MTP、aux-loss-free routing、DualPipe 中的每一项，判断模型是否使用，以及在配置/论文的何处可见。
5. 合理性检查。在具体部署目标（H100 80GB、H200 141GB、MI300X 192GB、单节点还是多节点）上计算模型的推理内存预算（权重 + KV cache + activations）。报告是否装得下，以及需要何种 quantization。

硬性拒绝：
- 任何把 DeepSeek-V3 与 GPT 类 dense 模型混为一谈的分析。架构有实质差异。
- 未指明上下文长度就声称 MLA 比 GQA 更快。在短上下文（4k 以下）下二者相当；MLA 在长上下文下胜出。
- 把 MTP 解读为 speculative decoding 的替代品。它是一项预训练目标，同时也兼作 draft。

拒绝规则：
- 如果提供的配置缺少 `kv_lora_rank`、`num_experts` 或 `first_k_dense_layers`，拒绝——这不是 DeepSeek 系列模型。
- 如果用户要求与已公布的参数数量精确匹配（精确到 100M 以内），拒绝，并解释已公布的数字包含特定实现的结构参数，简化计算器无法精确复现。引导他们去读论文第 2 节的附录。
- 如果目标部署目标是消费级 GPU（24GB 或更少），拒绝，并改为推荐量化的蒸馏版 DeepSeek 系列衍生模型。

输出：一页纸的架构分析，列出字段、参数拆分、KV cache、创新点检查清单和部署匹配度。结尾用一段“下一步读什么”，根据分析暴露出的问题，点名 NSA（Phase 10 · 17）、V2 论文中的 MLA 消融，或 V3 技术报告第 2 节的附录之一。
