# Show-o 与离散 diffusion 统一模型

> Transfusion 混合连续与离散两类表示。Show-o（Xie 等，2024 年 8 月）走的是相反方向：文本 token 用因果 next-token 预测，图像 token 用秉承 MaskGIT 精神的掩码离散 diffusion。两者共存于一个带混合 attention mask 的 transformer 中。其结果是：把 VQA、text-to-image、inpainting 以及混合模态生成统一到一个骨干上，每种模态一个 tokenizer，一种 loss 形式（把 next-token 扩展成掩码预测）。本节课梳理 Show-o 的设计——为什么掩码离散 diffusion 是一种并行的、少步数的图像生成器——并与 Transfusion、Emu3 做对比。

**Type:** 学习
**Languages:** Python（stdlib，掩码离散 diffusion 采样器）
**Prerequisites:** Phase 12 · 13（Transfusion）
**Time:** ~120 分钟

## Learning Objectives

- 解释掩码离散 diffusion：先均匀掩掉 token、再让 transformer 恢复它们的这一调度。
- 从速度和质量两方面比较并行图像解码（Show-o、MaskGIT）与自回归图像解码（Chameleon、Emu3）。
- 说出 Show-o 在一个 checkpoint 中处理的三个任务：T2I、VQA、图像 inpainting。
- 选择一种掩码调度（cosine、linear、truncated），并论述它对样本质量的影响。

## 问题场景

Transfusion 的双 loss 训练能用，但动态更难把握——连续 diffusion loss 与离散 NTP loss 处在不同的数值尺度上。平衡 loss 权重本身就是一次超参数搜索。这套架构有效，但复杂。

Show-o 的答案：让两种模态都保持离散（像 Chameleon 那样），但通过掩码离散 diffusion 并行生成图像，而非串行。训练目标因此变成单一的掩码 token 预测，它天然地推广了 next-token 预测。

## 核心概念

### 掩码离散 diffusion（MaskGIT）

Chang 等（2022）最初的 MaskGIT 技巧很优雅。从一张完全被掩码的图像出发（每个 token 都是特殊的 `<MASK>` id）。每一步并行预测所有被掩码的 token，然后保留置信度最高的 top-K 个预测，把其余重新掩码。经过约 8-16 次迭代，所有 token 都被填满。每步解掩多少 token 的调度需要调——cosine 调度效果很好。

训练很简单：从 [0, 1] 均匀采一个掩码比例，施加到图像的 VQ token 上，训练 transformer 恢复被掩码的那些。这正是 BERT 对文本做过的事，被扩展到图像生成。

### Show-o：一个 transformer，混合 mask

Show-o 把 MaskGIT 放进一个因果语言模型的 transformer 中。attention mask 是：

- 文本 token：因果（标准 LLM）。
- 图像 token：在图像块内完全双向（这样预测时被掩码的 token 能看到其他所有图像 token）。
- Text-to-image：文本能看到先前的图像，图像能看到先前的文本。

训练在以下三者之间交替：
1. 文本序列上的标准 NTP。
2. T2I 样本：文本 → 图像，图像 token 被掩码，使用掩码 token 预测 loss。
3. VQA 样本：图像 → 文本，文本 token 被掩码（其实就只是 NTP）。

统一的 loss 是对 `<MASK>` token 的交叉熵，它同时覆盖文本 NTP（只有最后一个 token 被“掩码”）与图像掩码 diffusion（随机子集被掩码）。

### 并行采样

Show-o 用约 16 步生成一张图像，而不是约 1000 步（逐 token 自回归）或约 20 步（diffusion）。每一步并行预测所有被掩码的 token，提交 top-K 个最自信的，然后重复。

对比：
- Chameleon / Emu3（基于 token 的自回归）：N_tokens 次前向传播，每张图通常 1024-4096 次。
- Transfusion（连续 diffusion）：约 20 步，每步一次完整 transformer pass。
- Show-o（掩码离散 diffusion）：约 16 步，每步一次完整 transformer pass。

在相近规模下，Show-o 比 Chameleon 快，步数大致与 Transfusion 相当，而单步成本更低（离散词表 logits 对连续 MSE loss）。

### 一个 checkpoint 中的多个任务

Show-o 在推理时支持四个任务，由 prompt 格式选择：

- 文本生成：标准的自回归文本输出。
- VQA：图像进，文本出。
- T2I：文本进，经掩码离散 diffusion 出图像。
- Inpainting：图像中部分 token 被掩码，将其填补。

Inpainting 能力是掩码预测训练自带的好处。掩住 VQ-token 网格的一块区域，把其余部分连同文本 prompt 一起输入，预测被掩码的 token。

### 掩码调度

每步解掩多少 token 的调度决定了质量。Show-o 推荐 cosine：

```
mask_ratio(t) = cos(pi * t / (2 * T))   # t = 0..T
```

第 0 步，全部 token 被掩码（比例 1.0）。第 T 步，没有 token 被掩码。Cosine 把权重集中在预测最有信息量的中间比例区间。linear 调度也能用，但更早进入平台期。

### Show-o2

Show-o2（2025 年的后续工作，arXiv 2506.15564）扩展了 Show-o：更大的 LLM 底座、更好的 tokenizer、改进的 mask 调度。架构模式相同。

### Show-o 所处的位置

在 2026 年的分类法中：

- 离散 token + NTP：Chameleon、Emu3。简单但推理慢。
- 离散 token + 掩码 diffusion：Show-o、MaskGIT、LlamaGen、Muse。并行采样，但仍受 tokenizer 的有损限制。
- 连续 + diffusion：Transfusion、MMDiT、DiT。质量最高，训练更复杂。
- 连续 + VLM 内的 flow matching：JanusFlow、InternVL-U。最新。

按任务来选：当你想用一个开源模型以合理速度同时获得 T2I + inpainting + VQA 时选 Show-o；当质量至上、且你能承受双 loss 那套接线时选 Transfusion。

```figure
masked-diffusion-unmask
```

## Use It

`code/main.py` 模拟 Show-o 的采样：

- 一个由 16 个 VQ token 组成的玩具网格。
- 一个模拟的“transformer”，基于 prompt 和当前未掩码的 token 预测 logits。
- 用 cosine 调度做 8 步的并行掩码采样。
- 打印中间状态（掩码模式的演变）和最终的 token。

运行它，观察 mask 一步一步消解。

## Ship It

本节课产出 `outputs/skill-unified-gen-model-picker.md`。给定一个既需要理解（VQA、captioning）又需要生成（T2I、inpainting）、且受开源权重约束的产品，它在 Show-o 家族、Transfusion/MMDiT 家族、Emu3 / Chameleon 家族之间做出选择，并给出具体的权衡。

## Exercises

1. 掩码离散 diffusion 用约 16 步采样。为什么不是 1 步？如果在第 0 步就解掩全部，会出什么问题？

2. 掩码 diffusion 让 inpainting 变得免费。提出一个（真实或假设的）产品用例，其中 Show-o 的 inpainting 胜过专用模型。

3. Cosine 调度与 linear 调度：画出 T=8 时每步解掩的 token 数量。哪一个更均衡？

4. 一张 512x512 的 Show-o 图像是 1024 个 token。在词表 K=16384 下，模型输出 1024 * log2(16384) = 14,336 比特（约 1.75 KiB）的数据。Stable Diffusion 输出 512*512*24 比特 = 6,291,456 比特（约 768 KiB）的原始像素。压缩比是多少，这样换来了什么质量？

5. 阅读 LlamaGen（arXiv:2406.06525）。LlamaGen 的类别条件自回归图像模型与 Show-o 的掩码方法有何不同？

## Key Terms

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Masked discrete diffusion | "MaskGIT-style" | 训练时预测被掩码的 token；推理时迭代地解掩置信度最高的预测 |
| Cosine schedule | "Unmask schedule" | 掩码比例随推理步数衰减的方式；把置信度的增长集中在中间区间 |
| Parallel decoding | "All tokens at once" | 每一步在一次前向传播中预测整条被掩码 token 序列，然后提交 top-K |
| Hybrid attention | "Causal + bidirectional" | 在文本 token 上因果、在图像块内双向的 mask |
| Inpainting | "Fill-in generation" | 以一张部分 token 被掩码的图像为条件，预测缺失的 token；是训练目标自带的 |
| Commitment rate | "Top-K per step" | 每轮迭代中宣告“完成”的 token 数量；控制推理速度与质量的权衡 |

## Further Reading

- [Xie et al. — Show-o (arXiv:2408.12528)](https://arxiv.org/abs/2408.12528)
- [Show-o2 (arXiv:2506.15564)](https://arxiv.org/abs/2506.15564)
- [Chang et al. — MaskGIT (arXiv:2202.04200)](https://arxiv.org/abs/2202.04200)
- [Sun et al. — LlamaGen (arXiv:2406.06525)](https://arxiv.org/abs/2406.06525)
- [Chang et al. — Muse (arXiv:2301.00704)](https://arxiv.org/abs/2301.00704)
