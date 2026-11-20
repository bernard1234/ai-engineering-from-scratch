---
name: tokenizer-vs-adapter-picker
description: 为 VLM 项目在 Chameleon 风格 early fusion（共享词表 tokenizer）与 LLaVA 风格 late fusion（冻结 LLM 上的 adapter）之间做选择。
version: 1.0.0
phase: 12
lesson: 11
tags: [chameleon, early-fusion, vq-vae, late-fusion, adapter]
---

给定产品规格（只做理解，或理解+生成）、目标图像质量（社交帖文 / 杂志 / 印刷 / 广电）以及成本预算（训练 + 推理），推荐 Chameleon 家族或 LLaVA 家族，并给出具体的架构轮廓。

产出：

1. Verdict。early fusion（Chameleon / Emu3 / AnyGPT）还是 late fusion（LLaVA / BLIP-2 / Qwen-VL）家族。
2. Tokenizer pick（针对 early fusion 的判断）。VQ-VAE（Chameleon）、MAGVIT-v2、IBQ 或 SBER-MoVQGAN；引用预期的重建上限（PSNR）。
3. 训练稳定性方案。规模化的 early fusion 所需的 QK-Norm、dropout 位置、LayerNorm 顺序。
4. 成本估算。训练 GPU 小时数与每张图的推理延迟，对比 late fusion 备选方案。
5. 生成质量上限。用户可预期的 PSNR / FID 区间；产品的质量门槛用离散 token 能否达到，还是需要连续（Transfusion 风格）生成。
6. 迁移路径。如果用户规模增长、late fusion 成为限制（他们需要图像输出），迁移会是什么样子。

硬性拒绝：
- 给只做理解的产品推荐 Chameleon 风格。纯理解场景下 late fusion 更简单、更便宜、上限更高。
- 为生产级图像生成提出 K<4096 的 VQ-VAE。codebook 太小，伪影肉眼可见。
- 声称 early fusion 推理是免费的。VQ decoder 每张生成图增加 50-200ms，往往超过 LLM 输出时间。

拒绝规则：
- 如果用户想要前沿质量的图像生成（FID < 15、印刷级），拒绝离散 token，指向 Transfusion / Stable Diffusion 3 / MMDiT（课程 12.13）。
- 如果产品从不需要图像输出，拒绝 early fusion——复杂度不划算。
- 如果用户想接入现有的 Llama / Qwen LLM 权重，拒绝 early fusion——它需要从头预训练一个新模型。

输出：一页纸方案，包含判断、tokenizer 选择、稳定性清单、成本估算、质量上限、迁移路径。结尾附上 arXiv 2405.09818（Chameleon）与 2408.11039（Transfusion）供对比阅读。
