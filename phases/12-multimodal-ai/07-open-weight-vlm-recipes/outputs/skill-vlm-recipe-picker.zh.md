---
name: vlm-recipe-picker
description: 为开放权重 VLM 挑选一套配方（编码器、连接器、LLM、数据配比、分辨率调度），每个选择都附带消融表引用。
version: 1.0.0
phase: 12
lesson: 07
tags: [vlm, mm1, idefics2, molmo, cambrian, prismatic, ablation]
---

给定任务组合（OCR、图表、UI agent、推理、grounding）、算力预算（LLM 参数量、训练 GPU 小时，或推理延迟目标），以及部署约束（边缘、云端、端侧），输出一份完整的开放权重 VLM 配方，并附引用。

产出：

1. 编码器选择。默认 SigLIP 2 SO400m/14；若任务组合中包含 grounding/分割，则拼接 DINOv2 ViT-g/14；引用 MM1 表 3 与 Cambrian-1 的视觉编码器对比。
2. 连接器选择。默认 2 层 MLP，除非受 token 限制（此时用 32 query 的 Q-Former）；引用 Prismatic VLMs 的连接器消融，其差异小于 1 分。
3. LLM 选择。按预算决定：低于 10B 用 Qwen2.5-7B，高于 30B 用 Llama-3.1-70B 或 Qwen2.5-72B。指出 70B 之后 MMMU 进入平台期。
4. 数据配比。默认 PixMo + ShareGPT4V + Cauldron；引用 Molmo 的详细人类描述结果（同等 token 数下比蒸馏高 2-3 分 MMMU）。
5. 分辨率调度。默认动态（256-1280），并先做 stage-1 的固定 384 对齐预训练；引用 Idefics2 的分辨率消融（AnyRes 带来 3-5 分 DocVQA 提升）以及 Qwen2.5-VL 的动态 M-RoPE。
6. 训练阶段。Stage 1 仅投影器，Stage 2 全量微调，Stage 3 任务特定。

必须拒绝：
- 把 CLIP ViT-L/14 推荐为默认编码器，却不提示它在新项目中已被 SigLIP 2 取代。
- 暗示 Q-Former 相对 MLP 能带来质量提升。它是 token 预算的杠杆，不是质量的杠杆。
- 在存在人类描述替代方案时，提议把合成的 GPT-4V 描述作为主要训练数据。请引用 Molmo。
- 声称连接器架构解释了实际上来自 token 数的方差。

拒绝规则：
- 如果用户想要 1-3B 的 VLM 做推理密集型任务，拒绝，并建议更大的 LLM；推理能力的天花板由 LLM 决定。
- 如果用户无力承担详细人类描述数据，明确标出预期的 2-3 分 MMMU 上限，并提供尽力而为的蒸馏回退方案。
- 如果任务组合包含 4K+ 文档图像且部署为冻结编码器，拒绝 AnyRes，改为推荐原生分辨率 + M-RoPE 的编码器，如 Qwen2.5-VL。

输出：一份单页配方卡，含每个轴的选择、消融引用（arXiv ID）、训练阶段计划以及预期 benchmark 区间。结尾列出接下来要读的三篇消融论文：arXiv 2403.09611 (MM1)、2405.02246 (Idefics2)、2409.17146 (Molmo)。
