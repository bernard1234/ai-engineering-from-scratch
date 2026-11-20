---
name: modality-bridge-picker
description: 在给定 token 预算、质量目标与训练算力的情况下，为 VLM 配置推荐 Q-Former、MLP projector 或 Perceiver resampler。
version: 1.0.0
phase: 12
lesson: 03
tags: [blip2, qformer, vlm, modality-bridge, architecture]
---

给定视觉编码器每张图的 token 数、LLM 的上下文预算、每个 prompt 的目标图像数以及训练算力预算，推荐应使用哪种模态桥，并用参数量与 token 经济学给出理由。

产出：

1. Token 预算审计。报告视觉编码器给出的每张图原始 token 数、每种桥方案下每张图的 token 数，以及在声明的每 prompt 图像数下占用的 LLM 上下文比例。
2. 桥方案对比。对 Q-Former（32 token，约 188M 参数）、MLP projector（全部 patch，约 20M 参数）与 Perceiver resampler（通过 N 层 cross-attention 得到 K 个可学习 query，规模可变）分别给出参数量、质量代理指标与训练成本量级。
3. 推荐。针对给定约束给出唯一的首选方案，并附一行理由。当约束互相矛盾（高质量 + 紧 token 预算 + 低训练算力）时必须明确指出。
4. 两阶段训练勾勒。若选中 Q-Former，概述 stage 1 的 ITC + ITM + ITG loss 与 stage 2 的 LM loss，并为每种给出一个代表性数据集（COCO、LAION、Visual Genome）。
5. 消融清单。调用方在锁定桥之前应运行的五个实验（query 数量、两阶段 vs 单阶段、projector 深度、冻结策略、微调子集）。

硬性拒绝：
- 任何忽略 token 预算的推荐。在 4k 上下文中处理 10 张图时，"用 MLP" 的每图 576 token 方案会失败。
- 声称 Q-Former 严格优于 MLP。在上下文不受限的单图高质量任务上，MLP 胜出。
- 把 Perceiver resampler 等同于 Q-Former。Flamingo 在每一 LLM 层应用它；BLIP-2 只应用一次。

拒答规则：
- 若调用方要一个能处理视频的桥，却不说明帧数与帧率，拒绝——视频桥与单图桥的差异在于规格，而不只是规模。
- 若范围内的 LLM 是与视觉塔从零联合训练的（early-fusion，Chameleon 式），拒绝——第 12.11 课单独讨论该情形。
- 若未说明训练算力，拒绝并询问调用方是能负担 BLIP-2 的 stage 2（约数百 A100 小时），还是只能做 projector-only 训练。

输出：一页纸的桥方案推荐，包含 token 计算、参数量、推荐架构、训练勾勒与消融清单。结尾用一段 "下一步该读什么" 指向第 12.04 课（Flamingo）了解 cross-attention everywhere、第 12.05 课（LLaVA）了解 MLP-only，或第 12.07 课（消融）了解数据与架构之间的权衡。
