# 任意分辨率视觉：Patch-n'-Pack 与 NaFlex

> 真实图像不是 224x224 的正方形。小票是 9:16，图表是 16:9，医学扫描可能是 4096x4096，手机截图是 9:19.5。2024 年之前 VLM 的答案是"把一切缩放到固定正方形"，而这恰恰丢掉了让 OCR、文档理解和高分辨率场景解析得以成立的信息。NaViT（Google，2023）证明可以把变分辨率的 patch 打包进同一个 transformer batch，并用块对角掩码隔离。Qwen2-VL 的 M-RoPE（2024）彻底去掉了绝对位置表。LLaVA-NeXT 的 AnyRes 把高分辨率图像切块成一张基础图 + 若干子图。SigLIP 2 的 NaFlex 变体（2025）如今是开源 VLM 的默认编码器，让单个 checkpoint 服务所有宽高比。本课端到端实现 patch-n'-pack。

**Type:** Build
**Languages:** Python（stdlib，patch 打包器 + 块对角掩码）
**Prerequisites:** Phase 12 · 01（ViT patch），Phase 12 · 05（LLaVA）
**Time:** ~120 分钟

## Learning Objectives

- 把一批变分辨率图像的 patch 打包进一条序列，并构建块对角注意力掩码。
- 针对给定任务，在 AnyRes 切块（LLaVA-NeXT）、NaFlex（SigLIP 2）和 M-RoPE（Qwen2-VL）之间做选择。
- 在不缩放的前提下，为 OCR、图表和摄影图像计算 token 预算。
- 说出 square-resize 的三种失败模式：文字被压扁、内容被裁掉、token 浪费在 padding 上。

## 问题场景

Transformer 期望的是一段序列。一个 batch 是一叠长度相同的序列。如果你的图像都是 224x224，那么每次都能得到 196 个 patch token，不需要 padding，完事。在 224 上训练，在 224 上推理，从此不必再考虑分辨率。

现实世界并不配合。文档是纵向的（8.5x11 英寸，约 2:3）。图表截图是横向的（16:9）。小票又高又窄（1:3）。医学影像以 2048x2048 或更大尺寸提供。手机截图是 1170x2532（0.46:1）。

2024 年之前的三种做法，以及它们各自为何失败：

1. 缩放到固定正方形（224x224 或 336x336）。拉伸会扭曲文字和人脸，降采样会毁掉图表标签和 OCR 内容。直到 LLaVA-1.5 之前这都是标准做法。
2. 裁剪成固定宽高比。你会丢掉图像的大部分，而且挑选裁剪位置本身就是个视觉问题。
3. 补边到最长边。修正了畸变，但对纵向图像来说，50% 以上的 token 都浪费在 padding 上，而且所有这些 pad token 都要付出二次方的注意力开销。

2024–2025 的答案是：让 transformer 直接吃图像原生分辨率下的 patch，再想办法把异构 batch 打包进一条序列而不浪费算力。

## 核心概念

### NaViT 与 patch-n'-pack

NaViT（Dehghani 等，2023）是证明这套做法在规模上可行的论文。想法很机械：

1. 对 batch 中每张图像，按选定的 patch 尺寸（比如 14）算出它在原生分辨率下的 patch 网格。
2. 把每张图像的 patch 展平为各自长度可变的序列。
3. 把 batch 中所有图像的 patch 拼接成一条长序列。
4. 构建块对角注意力掩码，使图像 A 的 patch 只在图像 A 内部做注意力。
5. 携带每个 patch 的位置信息（2D RoPE 或分数位置 embedding）。

一个包含三张图像的 batch——336x336（576 个 token）、224x224（256 个 token）和 448x336（768 个 token）——会变成一条 1600 token 的序列，配一张 1600x1600 的块对角掩码。没有 padding，没有浪费的算力，transformer 能处理任意宽高比。

NaViT 还在训练中引入了分数式 patch 丢弃——在整个 batch 上随机丢掉 50% 的 patch——既能正则化又能加速训练。SigLIP 2 继承了这一做法。

### AnyRes（LLaVA-NeXT）

LLaVA-NeXT 的 AnyRes 是更务实的替代方案。给定一张高分辨率图像和一个固定编码器（336 的 CLIP 或 SigLIP），对图像做切块：

1. 从预定义集合——(1x1)、(1x2)、(2x1)、(1x3)、(3x1)、(2x2) 等——中挑一个最贴合图像宽高比的网格布局。
2. 把整张图像按该网格切开，每一块成为一个 336x336 的裁剪。
3. 同时生成一张缩略图：将整张图像缩放到 336x336，作为全局上下文 token。
4. 用冻结的 336 编码器编码每一块，再把各块 token + 缩略图 token 拼接起来。

一张 672x672 图像在 2x2 网格加缩略图下：4 * 576 + 576 = 2880 个视觉 token。昂贵但有效——LLM 既看到局部细节，也看到全局上下文。

当你的编码器被冻结且只支持单一分辨率时，AnyRes 就是首选路线。它会让大图像的 token 数暴涨（一张 1344x1344 图像在 4x4 网格下是 9216 + 576 ≈ 9800 个 token，几乎塞满 8k 的 LLM 上下文）。

### M-RoPE（Qwen2-VL）

Qwen2-VL 提出了多模态旋转位置编码（Multimodal Rotary Position Embedding）。与 NaViT 的分数位置或 AnyRes 的切块加缩略图不同，每个 patch 携带一个 3D 位置（时间、高度、宽度）。query/key 的旋转可处理任意的 H、W 和时间长度。

M-RoPE 开箱即用地支持原生动态分辨率，无需重训。推理时你喂任意 HxW 的图像，patch embedder 产出 H/14 x W/14 个 token，每个 token 获得它的 (t=0, r=row, c=col) 位置，RoPE 用正确的频率旋转注意力，完事。Qwen2.5-VL 和 Qwen3-VL 延续了这套做法。InternVL3 的 V2PE 是同一思路，只是按模态做可变编码。

与 AnyRes 不同，M-RoPE 在原生分辨率下的 token 数是 O(H x W / P^2)——没有倍数级的切块开销。与 NaViT 不同，它每次前向仍然只接受一张图像。要跨分辨率批处理，仍需在其上叠加 patch-n'-pack。

### NaFlex（SigLIP 2）

NaFlex 是 SigLIP 2 checkpoint 的原生弹性（native-flex）模式。单个模型在推理时可服务多种序列长度（256、729、1024 个 token）。内部在训练时使用 NaViT 风格的 patch-n'-pack，并为每个 patch 使用绝对分数位置。卖点是：一个 checkpoint，推理时按任务挑选你的 token 预算。

语义任务（分类、检索）用 256 个 token。OCR 或图表理解用 1024 个 token。无需重训。

### 打包掩码

块对角掩码是大多数实现栽跟头的地方。对于一条长度为 `N_total` 的打包序列，覆盖长度为 `n_i` 的图像 `i=0..B-1`，形状为 `(N_total, N_total)` 的掩码 `M` 在两个下标都落在同一张图像的块内时取 1，否则取 0。你可以从一个累计长度列表构建它：

```
offsets = [0, n_0, n_0+n_1, ..., N_total]
M[i, j] = 1 iff there exists b where offsets[b] <= i < offsets[b+1] and offsets[b] <= j < offsets[b+1]
```

在 PyTorch 里用 `torch.block_diag` 或一次显式 gather 就是一行代码。FlashAttention 的变长路径（`cu_seqlens`）完全跳过掩码，直接用累计长度张量在序列内部做注意力——对典型 batch 来说比稠密掩码快约 10 倍。

### token 预算

按任务挑选策略：

- OCR / 文档：1024–4096 个 token。SigLIP 2 NaFlex 用 1024，或 AnyRes 3x3 + 缩略图。
- 图表和 UI：在 384–448 原生尺寸下 729–1024 个 token。Qwen2.5-VL 动态分辨率加上最大像素上限。
- 自然照片：256–576 个 token 就够了，下游 LLM 看到的信息已经足够。把 token 花在内容密度高的地方。
- 视频：空间池化后每帧 64–128 个 token，2–8 FPS。第 12.17 课会讲这个。

2026 年的生产规则：为每个任务设定一个最大像素上限，在该上限内按原生宽高比编码，打包 batch，并跳过 padding。Qwen2.5-VL 暴露了 `min_pixels` 和 `max_pixels`，正是为了这个旋钮。

```figure
mm-patch-n-pack
```

## Use It

`code/main.py` 为一批整数像素坐标的异构图像实现了 patch-n'-pack。它：

- 接收一组 (H, W) 图像尺寸。
- 按 patch 尺寸 14 计算每张图像的 patch 序列长度。
- 把它们打包成一条总长度为 `sum(n_i)` 的序列。
- 构建块对角注意力掩码（为清晰起见用稠密形式）。
- 比较打包方案与 square-resize、AnyRes 切块的成本。
- 为混合 batch（小票、图表、截图、照片）打印一张 token 预算表。

运行它。跑出来的数字，正是 2026 年每个开源 VLM 都采用 patch-n'-pack 的原因。

## Ship It

本课产出 `outputs/skill-resolution-budget-planner.md`。给定一个混合宽高比的工作负载（OCR、图表、照片、视频帧）和一个总 token 预算，它会挑出合适的策略（NaFlex、AnyRes、M-RoPE 或固定正方形），并输出一份逐请求的配置。当你在为某个产品给 VLM 做容量规划时，用这个 skill——它能避免那种悄悄发生的 10 倍 token 膨胀，那种膨胀会直接击穿延迟预算。

## Exercises

1. 一张小票是 600x1500（1:2.5）。在 patch 尺寸 14 下，原生分辨率有多少个 token？square-resize 到 336 之后有多少个？实践中哪种做法损失的 OCR 准确率更多？

2. 为长度为 256、576、729、1024 的四张图像组成的 batch 构建块对角掩码。验证注意力矩阵为 2585x2585，且非零元素恰好为 `256^2 + 576^2 + 729^2 + 1024^2` 个。

3. 对一张 patch 14 下的 1792x896 图像，比较：(a) 先 square-resize 到 336 再编码，(b) AnyRes 2x1 + 缩略图，(c) 原生分辨率下的 M-RoPE。哪种用的 token 最少？哪种保留的细节最多？

4. 实现分数式 patch 丢弃：给定一条打包序列，均匀随机丢弃 50% 的 token，并相应更新块对角掩码。测量掩码稀疏度的变化。

5. 阅读 Qwen2-VL 论文（arXiv:2409.12191）的第 3.2 节。用两句话描述 `min_pixels` 和 `max_pixels` 各控制什么，以及为什么两个边界都重要。

## Key Terms

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Patch-n'-pack | "NaViT 风格打包" | 把不同图像的变长 patch 序列拼接进同一个 batch 维度 |
| Block-diagonal mask | "打包掩码" | 限制每张图像的 patch 只对自身做注意力、而不对打包中的邻居做注意力的掩码 |
| AnyRes | "LLaVA-NeXT 切块" | 把高分辨率图像切成固定大小的网格块，再加一张全局缩略图；用固定编码器编码每一块 |
| NaFlex | "SigLIP 2 原生弹性" | 单个 SigLIP 2 checkpoint，推理时即可服务 256/729/1024 token 预算，无需重训 |
| M-RoPE | "多模态 RoPE" | 3D 旋转位置编码（时间、行、列），无需位置表即可处理任意 H、W、T |
| cu_seqlens | "FlashAttention 打包" | FlashAttention 变长路径用来替代稠密块对角掩码的累计长度张量 |
| min_pixels / max_pixels | "分辨率边界" | Qwen2.5-VL 的逐请求旋钮，用于给过小或过大的输入封顶 token 数 |
| Visual token budget | "每图多少个 token" | 每张图像输出的 patch token 的粗略数量，决定 LLM 的 prompt 预算与注意力开销 |

## Further Reading

- [Dehghani 等 — Patch n' Pack: NaViT（arXiv:2307.06304）](https://arxiv.org/abs/2307.06304)
- [Wang 等 — Qwen2-VL（arXiv:2409.12191）](https://arxiv.org/abs/2409.12191)
- [Laurençon 等 — What matters when building vision-language models?（Idefics2，arXiv:2405.02246）](https://arxiv.org/abs/2405.02246)
- [Tschannen 等 — SigLIP 2（arXiv:2502.14786）](https://arxiv.org/abs/2502.14786)
- [Qwen Team — Qwen2.5-VL Technical Report（arXiv:2502.13923）](https://arxiv.org/abs/2502.13923)
