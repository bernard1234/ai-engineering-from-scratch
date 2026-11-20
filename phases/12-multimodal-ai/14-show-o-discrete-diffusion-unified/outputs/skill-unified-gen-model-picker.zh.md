---
name: unified-gen-model-picker
description: 为一个既需要多模态理解又需要生成、且使用开源权重的产品，在 Show-o / Transfusion / Emu3 / Janus-Pro 几个家族之间做出选择。
version: 1.0.0
phase: 12
lesson: 14
tags: [show-o, masked-diffusion, unified, t2i, inpainting]
---

给定一个需要统一理解 + 生成（VQA、captioning、T2I，可选 inpainting）、受开源权重约束并有延迟预算的产品，选出一个模型家族并给出参考配置。

产出：

1. 家族结论。Show-o（掩码离散 diffusion）、Transfusion / MMDiT（连续 diffusion）、Emu3 / Chameleon（自回归离散），或 Janus-Pro（解耦 encoder）。
2. 推理步数预算。Show-o 用 16 步，Transfusion 用 20 步，Emu3 用 1024+ 步。结合用户的延迟预算说明选择理由。
3. Inpainting 支持。Show-o 免费；Transfusion 需加一个 mask 通道；Emu3 需要单独微调。就此向用户提示。
4. Tokenizer 选择。对离散家族，推荐 IBQ / MAGVIT-v2 / SBER；对连续方案，推荐 SD3 的 VAE。
5. 训练稳定性。双 loss（Transfusion）需要调权重；Show-o 的单 loss 更干净。
6. 用户成长后的迁移路径。当质量成为瓶颈时，从 Show-o 迁到 Transfusion。

硬性拒绝：
- 在每张图推理延迟 <10s 的情况下提议 Emu3 / Chameleon。对约 1024 个 token 做自回归太慢。
- 声称 Show-o 在前沿图像质量上比肩 Transfusion。并非如此。tokenizer 是天花板。
- 给需要 VQA 的产品推荐 Stable Diffusion。SD 无法对图像进行推理。

拒绝规则：
- 如果用户要求每张图生成 <2s，拒绝 Show-o 并推荐 Stable Diffusion + 一个独立 VLM 负责理解。接受多模型的复杂度。
- 如果用户在开源权重下想要“一流质量”，拒绝 Show-o / Emu3 并推荐 Transfusion 家族（MMDiT）或 JanusFlow。
- 如果用户无法对某个 tokenizer 做出承诺（担心许可、质量天花板），拒绝纯离散家族并推荐 Transfusion。

输出：一页选型，包含家族结论、步数预算、inpainting 支持、tokenizer 建议、稳定性方案与迁移路径。结尾引用 arXiv 2408.12528（Show-o）、2408.11039（Transfusion）、2501.17811（Janus-Pro）。
