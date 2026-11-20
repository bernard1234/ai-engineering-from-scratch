# Emu3：面向图像与视频生成的 Next-Token Prediction

> BAAI 的 Emu3（Wang et al., 2024 年 9 月）是 2024 年本应终结"扩散 vs 自回归"之争的成果。一个单一的 Llama 风格 decoder-only transformer，仅用 next-token prediction 目标训练，覆盖文本 + VQ 图像 token + 3D VQ 视频 token 的统一词表，在图像生成上胜过 SDXL，在感知上胜过 LLaVA-1.6。没有 CLIP 损失。没有扩散 schedule。推理时使用 classifier-free guidance 以提升质量，但核心训练目标就是带 teacher forcing 的 next-token prediction。发表于 Nature。本课解读 Emu3 的论点——为什么"更好的 tokenizer 加上规模"就是你所需要的一切——并与扩散方法做对比。

**Type:** Learn
**Languages:** Python（stdlib，3D 视频 tokenizer 数学 + 自回归采样器骨架）
**Prerequisites:** Phase 12 · 11（Chameleon）
**Time:** ~120 分钟

## Learning Objectives

- 解释为什么 Emu3 的单一损失 next-token 目标能奏效，尽管长期以来的假设认为图像质量必须依赖扩散。
- 描述 3D 视频 tokenizer：时空 VQ codebook 长什么样，为什么 patch 要跨越时间。
- 在（训练算力、推理成本、质量上限）三个维度上比较 Emu3 与 Stable Diffusion XL。
- 说出同一个 Emu3 模型承担的三种角色：Emu3-Gen（图像生成）、Emu3-Chat（感知）、Emu3-Stage2（视频生成）。

## 问题场景

到 2024 年为止的普遍认知是：图像生成需要扩散。论据是：离散图像 token 丢失太多信息，无法重建细节，而自回归采样会在数千个 token 上累积误差。Stable Diffusion、DALL-E 3、Imagen、Midjourney 都使用某种形式的扩散。Chameleon（课程 12.11）在小规模上部分推翻了这一点，但在质量上未能匹敌 SDXL。

Emu3 正面攻击这个论点。其主张是：更好的视觉 tokenizer + 足够的规模 + next-token 损失 = 在同一个既能做感知的模型里实现胜过扩散的图像生成。

这一押注在发表时颇具争议。两年过去，开源统一生成家族（Emu3、Show-o、Janus-Pro、Transfusion）已成为研究的默认路径；生产级前沿模型似乎也采用了某种变体。

## 核心概念

### Emu3 的 tokenizer

关键成分是视觉 tokenizer。Emu3 训练了一个定制的 IBQ 类 tokenizer（Inverse Bottleneck Quantizer，SBER-MoVQGAN 家族），每个 token 对应 8x8 的分辨率压缩。一张 512x512 图像在 codebook 大小为 32768 时变为 64x64 = 4096 个 token。

这比 Chameleon 在 K=8192 时每张 512x512 用 1024 个 token 要多，但每个 token 更便宜（更小的 codebook 查找、更简单的 codec）。关键指标是：重建 PSNR 达 30.5 dB，与 Stable Diffusion 连续隐空间的 32 dB 相当。

对视频而言：一个 3D VQ tokenizer 将时空 patch（4x4x4 像素）编码为一个整数。一个 8 FPS 的 4 秒片段有 32 帧；在 256x256 下，空间 4 倍、时间 4 倍压缩，token 数为 (256/4) * (256/4) * (32/4) = 64 * 64 * 8 = 32,768 个 token。

tokenizer 质量就是上限。Emu3 的贡献有一部分就是"我们训练了一个非常好的 tokenizer"。

### 单一损失训练

Emu3 使用一个目标：在覆盖文本 token、2D 图像 token 和 3D 视频 token 的共享词表上做 next-token prediction。训练时权重会按模态特定的系数相乘以平衡贡献，但损失函数完全相同。

在以下混合数据上训练：
- 图像生成：`<text caption> <image> image_tokens </image>`
- 图像感知：`<image> image_tokens </image> <question> text_tokens`
- 视频生成：`<text caption> <video> video_tokens </video>`
- 视频感知：类似。
- 纯文本：标准 NTP。

模型从数据分布中学会何时输出图像 token、何时输出文本 token。生成能力从模型在 `<image>` 标签之后预测图像 token 中涌现出来。

### classifier-free guidance 与 temperature

自回归图像生成在推理时使用 classifier-free guidance（CFG）会好很多。Emu3 使用了它：生成两次，一次用完整 caption，一次用空 caption，按 guidance 权重（典型值 3.0-7.0）混合 logits。这正是扩散使用的同一个 CFG 技巧，被借用到自回归设定中。

temperature 也很重要：过高会产生伪影；过低会导致模式坍塌。Emu3 推荐 temperature 为 1.0（感知）、0.8（图像生成）。

### 三种角色，一个模型

Emu3 以三个功能上不同的 API 发布，但底层只有一套权重：

- Emu3-Gen。图像生成。输入文本，输出图像 token。
- Emu3-Chat。VQA 与 captioning。输入图像（token），输出文本。
- Emu3-Stage2。视频生成与视频 VQA。输入文本或视频，输出文本或视频。

没有任务特定的 head。只有不同的 prompt 模板。同一个 checkpoint。

### 基准测试

来自 Emu3 论文（2024 年 9 月）：

- 图像生成：在 MJHQ-30K FID 上胜过 SDXL（5.4 vs 5.6），GenEval overall 持平（0.54 vs 0.55——统计上打平），Deep-Eval 综合指标相当。
- 图像感知：在 VQAv2 上胜过 LLaVA-1.6（75.1 vs 72.4），在 MMMU 上大致持平。
- 视频生成：4 秒片段质量在 FVD 上与 Sora 时代有公开基准的模型具竞争力。

这些数字并非处处取胜——Emu3 在这里让一分、在那里补一分——但"next-token prediction 就是你所需要的一切"这一主张在各模态上是站得住脚的。

### 算力成本

Emu3 用 7B 参数模型在约 3000 亿个多模态 token 上训练。GPU 小时大致与 Llama-2-7B 预训练相当（A100 级硅片上的 2k-4k GPU-years）。Stable Diffusion 3 这类扩散模型的训练预算相近，但需要独立的文本编码器和更复杂的流水线。

推理时，Emu3 每张图比 SDXL 慢：4096 个图像 token 以 30 tok/s 计约需 2 分钟生成一张 512x512，而 SDXL 只需 2-5 秒。投机解码与 KV-cache 优化缩小了差距但未消除。自回归图像生成是计算密集型的；这是长期存在的取舍。

### 为什么重要

Emu3 深层的贡献是概念性的。如果 next-token prediction 能扩展到在图像生成上匹敌扩散，那么统一模型路径（一个损失、一个骨干、任意模态）就是可行的。未来的模型不再需要独立的文本编码器、独立的扩散 scheduler、独立的 VAE。一个 transformer、每种模态一个 tokenizer、规模。

Show-o、Janus-Pro 和 InternVL-U 都基于这一论点构建或提出挑战。截至 2025 年，中国实验室（BAAI、DeepSeek）在这一方向上的发表比美国实验室更激进。

```figure
l5-emu3-next-token
```

## Use It

`code/main.py` 搭建了两个玩具组件：

- 一个 2D 与 3D VQ tokenizer 计数计算器：给定（resolution、patch、clip_length、FPS），计算图像与视频的 token 数。
- 一个带 classifier-free guidance 与 temperature 的自回归图像 token 采样器。

CFG 的实现与 Emu3 的配方一致——用 guidance 权重混合条件 logits 与无条件 logits。

## Ship It

本课产出 `outputs/skill-token-gen-cost-analyzer.md`。给定生成产品规格（图像或视频、目标分辨率、质量档位、延迟预算），它计算 token 数、推理成本，并在 Emu3 家族与扩散之间做选择。

## Exercises

1. Emu3 在 8x8 压缩下每张 512x512 图像产生 4096 个 token。计算 1024x1024 和 2048x2048 的对应值。推理延迟会怎样变化？

2. 阅读 Emu3 第 3.3 节关于视频 tokenizer 的内容。描述 3D VQ patch 的形状，以及为什么是 4x4x4 而不是 8x8x1。

3. classifier-free guidance 权重 5.0 vs 3.0：视觉上有什么效果？追踪 `code/main.py` 中的数学。

4. 计算 Emu3-7B 在 300B token 上的训练 FLOPs，并与 Stable Diffusion 3 比较。哪个训练更贵？

5. Emu3 在 FID 上胜过 SDXL，但在 VQAv2 上对专用 VLM 未能胜过。解释为什么统一损失方案在不同基准上相对专家模型表现出不同的强项。

## Key Terms

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Next-token prediction | "NTP" | 标准自回归损失：给定 token[0..i] 预测 token[i+1]；任何模态只要 token 化就适用 |
| IBQ tokenizer | "Inverse bottleneck quantizer" | 一类 VQ-VAE，codebook 更大（32768+），重建效果好于 Chameleon |
| 3D VQ | "Spatiotemporal quantizer" | 以（时间、行、列）索引的 codebook；一个 token 覆盖 4x4x4 像素立方体 |
| Classifier-free guidance | "CFG" | 用权重 gamma 混合条件与无条件 logits；在推理时提升图像质量 |
| Unified vocabulary | "Shared tokens" | 文本 + 图像 + 视频都取自同一个整数空间；模型预测下一个出现的模态 |
| MJHQ-30K | "Image gen benchmark" | 含 30k prompt 的 Midjourney 质量基准；Emu3 在此报告 FID |

## Further Reading

- [Wang et al. — Emu3: Next-Token Prediction is All You Need (arXiv:2409.18869)](https://arxiv.org/abs/2409.18869)
- [Sun et al. — Emu: Generative Pretraining in Multimodality (arXiv:2307.05222)](https://arxiv.org/abs/2307.05222)
- [Liu et al. — LWM (arXiv:2402.08268)](https://arxiv.org/abs/2402.08268)
- [Yu et al. — MAGVIT-v2 (arXiv:2310.05737)](https://arxiv.org/abs/2310.05737)
- [Tian et al. — VAR (arXiv:2404.02905)](https://arxiv.org/abs/2404.02905)
