# 视觉 Transformer 与 patch-token 基础原语

> 在做任何多模态之前，图像必须先变成 transformer 能"吃"下去的 token 序列。2020 年的 ViT 论文用 16x16 像素的 patch、一次线性投影和一个位置嵌入回答了这个问题。五年之后，每一个 2026 年的前沿模型（Claude Opus 4.7 原生 2576px、Gemini 3.1 Pro、Qwen3.5-Omni）仍然从这里出发 —— 编码器从 ViT 换成了 DINOv2 再到 SigLIP 2，register token 被加入进来，位置方案变成了 2D-RoPE，但这个原语本身没有变。本课从头到尾拆解 patch-token 流水线，并用 stdlib Python 把它实现出来，好让 Phase 12 的其余部分对"视觉 token"有一个具体的心智模型。

**Type:** Learn
**Languages:** Python（stdlib，patch tokenizer + 几何计算器）
**Prerequisites:** Phase 7（Transformers）、Phase 4（计算机视觉）
**Time:** ~120 分钟

## Learning Objectives

- 把一张 HxWx3 的图像转换成带正确位置编码的 patch token 序列。
- 计算给定（patch size、分辨率、hidden dim、depth）的 ViT 的序列长度、参数量和 FLOPs。
- 说出让 ViT 从 2020 年的研究走向 2026 年生产环境的三大升级：自监督预训练（DINO / MAE）、register token，以及原生分辨率打包。
- 在下游任务中于 CLS 池化、mean 池化和 register token 之间做出选择。

## 问题场景

Transformer 处理的是向量序列。文本本来就是序列（字节或 token）。图像则是带三个颜色通道的 2D 像素网格 —— 不是序列。如果把每个像素都展平，一张 224x224 的 RGB 图像会变成 150,528 个 token，这个长度的自注意力根本无从谈起（对序列长度是二次复杂度）。

2020 年之前的做法是在前面接一个 CNN 特征提取器：ResNet 产生一个 7x7 的 2048 维特征图，把这 49 个 token 喂给 transformer。这可行，但继承了 CNN 的偏置（平移等变性、局部感受野），也丢掉了 transformer 对规模的胃口。

Dosovitskiy 等人（2020）提出了一个直白的问题：如果跳过 CNN 会怎样？把图像切成固定大小的 patch（比如 16x16 像素），把每个 patch 线性投影成一个向量，加上位置嵌入，再把序列喂给一个朴素的 transformer。这在当时是异端 —— 不用卷积做视觉。但有足够的数据（JFT-300M，之后是 LAION），它在 ImageNet 上击败了 ResNet，并持续提升。

到 2026 年，ViT 这个原语是不容置疑的基础。每一个开放权重 VLM 的视觉塔都是它的某个后代（DINOv2、SigLIP 2、CLIP、EVA、InternViT）。问题不再是"我们该不该用 patch？"，而是"用什么 patch size、什么分辨率调度、什么预训练目标、什么位置编码。"

## 核心概念

### patch 作为 token

给定一张形状为 `(H, W, 3)` 的图像 `x` 和一个 patch size `P`，你把图像切成 `(H/P) x (W/P)` 个互不重叠的 patch 组成的网格。每个 patch 是一个 `P x P x 3` 的像素立方体。把每个立方体展平成 `3 P^2` 的向量。应用一个形状为 `(3 P^2, D)` 的共享线性投影 `W_E`，把每个 patch 映射到模型的隐藏维度 `D`。

对于 ViT-B/16 的经典配置：
- 分辨率 224，patch size 16 → 网格 14x14 → 196 个 patch token。
- 每个 patch 是 `16 x 16 x 3 = 768` 个像素值，被投影到 `D = 768`。
- 加入一个可学习的 `[CLS]` token → 序列长度为 197。

patch 投影在数学上等同于一个 kernel size 为 `P`、stride 为 `P`、输出通道数为 `D` 的 2D 卷积。生产代码实际上就是这么实现的 —— `nn.Conv2d(3, D, kernel_size=P, stride=P)`。"线性投影"的表述是概念层面的；卷积核的表述是效率层面的。

### 位置嵌入

patch 本身没有内在顺序 —— transformer 把它们看成一个袋子。早期的 ViT 加了一个可学习的 1D 位置嵌入（每个位置一个 768 维向量，共 197 个）。这可行，但把模型绑死在训练分辨率上：推理时如果改变网格，就必须对位置表做插值。

现代视觉骨干使用 2D-RoPE（Qwen2-VL 的 M-RoPE、SigLIP 2 的默认方案）或因子化的 2D 位置。2D-RoPE 根据 patch 的（行、列）索引来旋转 query 和 key 向量，于是模型从旋转角度推断相对的 2D 位置。没有位置表。模型在推理时能处理任意网格尺寸。

### CLS token、池化输出与 register token

图像级表示是什么？三种选择并存：

1. `[CLS]` token。在 patch 序列前面加上一个可学习向量。经过所有 transformer block 之后，CLS token 的隐藏状态就是图像表示。继承自 BERT。原始 ViT 和 CLIP 使用。
2. Mean 池化。对 patch token 的输出隐藏状态取平均。SigLIP、DINOv2 以及大多数现代 VLM 使用。
3. Register token。Darcet 等人（2023）观察到，没有显式 sink token 训练出来的 ViT 会发展出高范数的"伪影"patch，它们劫持了自注意力。加入 4–16 个可学习的 register token 可以吸收这份负载，并提升稠密预测质量（分割、深度）。DINOv2 和 SigLIP 2 都自带 register。

这个选择对下游任务很重要。CLS 对分类没问题。对于把 patch token 喂进 LLM 的 VLM，你完全跳过池化 —— 每个 patch 都成为一个 LLM 输入 token。register 在交接前被丢弃（它们是脚手架，不是内容）。

### 预训练：监督、对比、掩码、自蒸馏

2020 年的 ViT 是在 JFT-300M 上做监督分类预训练的。它很快被以下方法取代：

- CLIP（2021）：在 4 亿对数据上做对比式图文训练。见课程 12.02。
- MAE（2021，He 等人）：掩掉 75% 的 patch，重建像素。自监督，可作用于纯图像。
- DINO（2021）/ DINOv2（2023）：学生-教师自蒸馏，不用标签，不用 caption。2023 年的 DINOv2 ViT-g/14 是最强的纯视觉骨干，也是"稠密特征"用例的默认选择。
- SigLIP / SigLIP 2（2023、2025）：用 sigmoid 损失、并用 NaFlex 支持原生宽高比的 CLIP。2026 年开放 VLM（Qwen、Idefics2、LLaVA-OneVision）中占主导地位的视觉塔。

你选择的预训练方式决定了这个骨干适合做什么：CLIP/SigLIP 适合与文本做语义匹配，DINOv2 适合稠密视觉特征，MAE 适合作为下游微调的起点。

### 缩放定律

ViT 缩放（Zhai 等人 2022）确立了一点：ViT 的质量在模型规模、数据规模和计算量上遵循可预测的规律。在固定计算量下：
- 更大的模型 + 更多的数据 → 更好的质量。
- Patch size 是调节序列长度与保真度之间权衡的杠杆。Patch 14（DINOv2/SigLIP SO400m 常用）比 patch 16 给出更多 token；对 OCR 和稠密任务更好，对速度更差。
- 分辨率是另一个大杠杆。从 224 到 384 再到 512 几乎总是有帮助，代价是 FLOPs 的二次增长。

ViT-g/14（10 亿参数，patch 14，分辨率 224 → 256 个 token）和 SigLIP SO400m/14（4 亿参数，patch 14）是 2026 年开放 VLM 的两台主力编码器。

### ViT 的参数量

完整计算放在 `code/main.py` 里。对于 224 输入的 ViT-B/16：

```
patch_embed = 3 * 16 * 16 * 768 + 768  =  591k
cls + pos    = 768 + 197 * 768          =  152k
block        = 4 * 768^2 (QKVO) + 2 * 4 * 768^2 (MLP) + 2 * 2*768 (LN)
             = 12 * 768^2 + 3k          =  7.1M
12 blocks    = 85M
final LN    = 1.5k
total       ≈ 86M
```

在你加载 checkpoint 之前，先这样粗略估算每个 ViT。骨干大小决定了任何下游 VLM 的显存下限。

### 2026 年生产配置

2026 年大多数开放 VLM 自带的编码器是原生分辨率（NaFlex）下的 SigLIP 2 SO400m/14。它有：
- 4 亿参数。
- Patch size 14，默认分辨率 384 → 每张图 729 个 patch token。
- 图像级任务用 mean 池化；VQA 时全部 729 个 patch 流入 LLM。
- 4 个 register token，在交给 LLM 前丢弃。
- 带图像级缩放的 2D-RoPE，支持原生宽高比。

这个配置里的每一个决定都能追溯到你读得到的一篇论文。

```figure
image-patch-tokens
```

## Use It

`code/main.py` 是一个 patch tokenizer 和几何计算器。它接收（图像 H、W、patch P、hidden D、depth L）并报告：

- 打 patch 之后的网格形状和序列长度。
- 一张合成的 8x8 像素玩具图像的 token 序列（走一遍展平 + 投影的路径）。
- 按 patch embed、position embed、transformer block 和 head 拆解的参数量。
- 目标分辨率下每次前向的 FLOPs。
- 一张横跨 ViT-B/16 @ 224、ViT-L/14 @ 336、DINOv2 ViT-g/14 @ 224、SigLIP SO400m/14 @ 384 的对比表。

运行它。把参数量与已发表的数字对上。调整 patch size 和分辨率，感受 token 数量的代价。

## Ship It

本课产出 `outputs/skill-patch-geometry-reader.md`。给定一个 ViT 配置（patch size、分辨率、hidden dim、depth），它产出一份带论证的 token 数、参数量和显存估算。每当你为 VLM 挑选视觉骨干时都用上这个 skill —— 它能避免"token 爆炸把我 LLM 的上下文塞满了"这类意外。

## Exercises

1. 计算 Qwen2.5-VL 在原生 1280x720 输入、patch size 14 下的 patch-token 序列长度。与只用 CLS 的表示相比如何？

2. 一帧 1080p 画面（1920x1080）在 patch 14 下会产生多少 token？在 30 FPS、5 分钟视频下，视觉 token 总数是多少？哪种做法最省成本：池化、帧采样，还是 token 合并？

3. 用纯 Python 实现 patch token 上的 mean 池化。验证对 DINOv2 输出 196 个 token 做 mean 池化，与请求池化嵌入时模型 `forward` 返回的结果是否一致。

4. 阅读《Vision Transformers Need Registers》第 3 节（arXiv:2309.16588）。用两句话描述 register 吸收了哪些伪影，以及为什么这对下游稠密预测很重要。

5. 修改 `code/main.py` 以支持 patch-n'-pack：给定一组不同分辨率的图像，产出一个打包后的单一序列以及块对角注意力掩码。等你学到课程 12.06 时再验证。

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|------------------------|
| Patch | "16x16 像素方块" | 输入图像中固定大小、互不重叠的区域；变成一个 token |
| Patch embedding | "线性投影" | 一个共享的学习矩阵（或 stride=P 的 Conv2d），把展平后的 patch 像素映射为 D 维向量 |
| CLS token | "类别 token" | 前置的可学习向量，其最终隐藏状态表示整张图像；在 2026 年是可选项 |
| Register token | "Sink token" | 额外的可学习 token，用来吸收 ViT 在预训练过程中发展出的高范数注意力伪影 |
| Position embedding | "位置信息" | 逐位置的向量或旋转，使序列具备顺序感知；2D-RoPE 是现代默认方案 |
| Grid | "Patch 网格" | 给定分辨率和 patch size 下的 (H/P) x (W/P) 二维 patch 数组 |
| NaFlex | "原生灵活分辨率" | SigLIP 2 的特性：单个模型无需重训练即可服务多种宽高比和分辨率 |
| Backbone | "视觉塔" | 预训练的图像编码器，其 patch-token 输出在 VLM 中喂给 LLM |
| Pooling | "图像级摘要" | 把 patch token 转成一个向量的策略：CLS、mean、attention 池化或基于 register |
| Patch 14 vs 16 | "更细 vs 更粗的网格" | Patch 14 每张图产生更多 token，对 OCR 保真度更高、更慢；patch 16 是经典默认 |

## Further Reading

- [Dosovitskiy et al. — An Image is Worth 16x16 Words (arXiv:2010.11929)](https://arxiv.org/abs/2010.11929) —— 原始 ViT 论文。
- [He et al. — Masked Autoencoders Are Scalable Vision Learners (arXiv:2111.06377)](https://arxiv.org/abs/2111.06377) —— MAE，自监督预训练。
- [Oquab et al. — DINOv2 (arXiv:2304.07193)](https://arxiv.org/abs/2304.07193) —— 大规模自蒸馏，无需标签。
- [Darcet et al. — Vision Transformers Need Registers (arXiv:2309.16588)](https://arxiv.org/abs/2309.16588) —— register token 与伪影分析。
- [Tschannen et al. — SigLIP 2 (arXiv:2502.14786)](https://arxiv.org/abs/2502.14786) —— 2026 年的默认视觉塔。
- [Zhai et al. — Scaling Vision Transformers (arXiv:2106.04560)](https://arxiv.org/abs/2106.04560) —— 经验的缩放定律。
