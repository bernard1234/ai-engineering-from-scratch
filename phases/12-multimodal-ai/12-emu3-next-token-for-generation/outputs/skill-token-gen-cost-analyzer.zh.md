---
name: token-gen-cost-analyzer
description: 计算 Emu3 风格 next-token 生成的 token 数、推理延迟与质量上限，并在 Emu3 家族与扩散之间做选择。
version: 1.0.0
phase: 12
lesson: 12
tags: [emu3, next-token-prediction, video-gen, diffusion, cfg]
---

给定生成产品规格（图像或视频、目标分辨率、质量档位、吞吐要求），计算 Emu3 风格 next-token 生成的 token 数，估算推理成本，并在 Emu3 家族与扩散之间做选择。

产出：

1. Token 数。按所选 tokenizer 压缩率计算每张图像的 token 数（图像通常每维 8x）。对 3D VQ 计算每个视频的 token 数（典型为 4x4x4 时空 patch）。
2. 推理延迟。Emu3 家族为 token 数 / 吞吐（tokens-per-second）；扩散为 denoise-steps * step-time。引用具体的 A100 / H100 区间。
3. 质量上限。tokenizer 重建 PSNR（IBQ 类为 30-32 dB）、MJHQ-30K 上的预期 FID、视频的 FVD。
4. CFG 配置。每个任务推荐的 guidance 权重（gamma）；标准生成为 3.0，强 prompt 遵循为 5-7。
5. Pick。若产品需要统一的理解 + 生成，或任意模态的灵活性，选 Emu3 家族；若产品只做图像生成且延迟要求严格，选扩散（SDXL / SD3 / Flux）。

硬性拒绝：
- 声称 Emu3 推理比扩散快。并非如此；在数千个图像 token 上的自回归解码是长期存在的成本。
- 推荐 Emu3 家族却不指定 CFG 权重。没有它质量会崩塌。
- 为严格的 4K 图像生成提议 Emu3。2048+ 分辨率下的 token 数会撑爆 KV cache，并耗时数分钟。

拒绝规则：
- 如果延迟预算 <5s 每张图，拒绝 Emu3，推荐 SDXL 或 SD3。
- 如果产品必须生成图像、描述图像并对第三方图像做推理，推荐 Emu3 家族（统一损失正是重点）；扩散没有独立 VLM 就做不到。
- 如果用户想要宽松许可证的开源权重用于商业用途，拒绝 Emu3——先查其许可证；某些版本仅供研究使用。

输出：一页纸分析，包含 token 数、延迟估算、质量上限、CFG 配置，以及带理由的选择。结尾附上 arXiv 2409.18869（Emu3）与 2408.11039（Transfusion）作为替代方案。
