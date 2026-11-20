# Chameleon 与 early fusion 的纯 token 多模态模型

> 到目前为止我们见过的每个 VLM 都把图像和文本分开处理。视觉 token 来自视觉编码器，流经 projector，然后在 LLM 内部与文本相遇。视觉词表和文本词表从不重叠。Chameleon（Meta，2024 年 5 月）提出的问题是：如果它们重叠会怎样？训练一个 VQ-VAE，把图像变成来自共享词表的离散 token 序列。于是每个多模态文档都变成一个序列——文本 token 与图像 token 交错排列，单一的自回归损失。副作用是：模型可以生成混合模态输出——在一次推理调用中交替输出文本和图像 token。本课解读 early fusion 的论点，并端到端搭建一个小型玩具版本。

**Type:** Build
**Languages:** Python（stdlib，VQ-VAE tokenizer + 交错解码器）
**Prerequisites:** Phase 12 · 05、Phase 8（Generative AI）
**Time:** ~180 分钟

## Learning Objectives

- 解释为什么共享词表 + 单一损失会改变模型能做到的事情。
- 描述 VQ-VAE 如何把图像 token 化成与 transformer 的 next-token 目标兼容的离散序列。
- 说出 Chameleon 的训练稳定性技巧：QK-Norm、dropout 位置、LayerNorm 顺序。
- 比较 Chameleon 与 BLIP-2 的 Q-Former 方案，并说明各自适用的场景。

## 问题场景

基于 adapter 的 VLM（LLaVA、BLIP-2、Qwen-VL）把文本和图像当作两种不同的东西。一个文本 token 走 `embed(text_token)`；一张图像走 `visual_encoder(image) → projector → ... pseudo_tokens`。模型有两条输入路径，在中间某处才汇合。

三个后果：

1. LLM 只能消费图像，不能输出图像。输出只有文本。
2. 混合模态文档（段落与图像交替，例如一篇文章）很别扭——你要么在模型外部解析多模态输入，要么把多次生成串起来。
3. 分布不匹配。视觉 token 和文本 token 位于隐空间的不同区域，会产生微妙的对齐问题。

Chameleon 否定了这个前提：图像不过是从共享词表中取出的一段离散 token 序列。用交错文档训练模型，一个损失、一个自回归解码器，你就免费获得了混合模态生成能力。

## 核心概念

### VQ-VAE 作为图像 tokenizer

tokenizer 是一个 vector-quantized variational autoencoder。架构如下：

- Encoder：CNN + ViT，把图像映射为空间特征图，例如 32x32 个 256 维特征。
- Codebook：一个学习得到的 K 个向量的词表（Chameleon 使用 8192），同样 256 维。
- Quantization：对每个空间特征，按 L2 距离查找最近的 codebook 条目。用整数索引替换连续特征。
- Decoder：CNN，把量化后的特征还原为像素。

训练：VAE 重建损失 + commitment 损失 + codebook 损失。codebook 索引构成了图像的离散字母表。

对 Chameleon 而言：一张图像变为 32*32 = 1024 个 token，取自大小为 8192 的词表。与文本 token（来自 LLM 的 BPE 词表，例如 32000）拼接。最终词表：40192。transformer 只看到一个序列、一个损失。

### 共享词表

Chameleon 的词表把文本 token、图像 token 和模态分隔符组合在一起。每个 token 只有唯一一个 ID。输入 embedding 层把每个 ID 映射为 D 维隐向量。输出投影把隐向量映射回词表 logits。Softmax 挑出下一个 token，无论它属于哪种模态。

分隔符很重要：`<image>` 和 `</image>` 标签括住图像 token 序列。在生成时，如果模型输出 `<image>`，下游软件就知道接下来的 1024 个 token 是 VQ 索引，应交给 decoder 渲染成像素。

### 混合模态生成

推理就是在共享词表上做 next-token prediction。示例 prompt："Draw a cat and describe it。" Chameleon 输出：

```
<image> 4821 1029 2891 ... (1024 image tokens) </image>
The cat is orange, sitting on a windowsill...
```

模型自主决定顺序——它可能先图后文、先文后图，或者交错输出。同一个 decoder，同一个损失。

对比之下，adapter 型 VLM 的生成只有文本。Chameleon 重新打开了"模型输出模态"这个问题。

### 训练稳定性——QK-Norm、dropout、LayerNorm 顺序

early fusion 训练在规模上是不稳定的。Chameleon 论文记录了三项技巧：

- QK-Norm。在 attention 内部对 query 和 key 投影做 LayerNorm，位于点积之前。防止深层处 logit 幅度爆炸。被多个 2024 年之后的大模型采用。
- Dropout 位置。在每个残差相加之后做 dropout，而不只是在 attention 和 MLP 之后。当图像 token 的梯度可能占据主导时，需要更多正则化。
- LayerNorm 顺序。残差分支上使用 Pre-LN（标准做法），并在最后一个 block 的 skip connection 上额外加一个 LN。稳定最后一层的梯度流动。

没有这些技巧，34B 参数的 Chameleon 训练在多个 checkpoint 处发散。有了它们，训练收敛。这套训练配方与架构本身同样重要。

### tokenizer 的重建上限

VQ-VAE 是有损的。在 8192 个 codebook 条目、每张 512x512 图像 1024 个 token 的设置下，重建 PSNR 上限约为 26-28 dB。这足以生成可辨认的图像，但明显差于连续空间扩散（Stable Diffusion 3 可达 32+ dB）。

tokenizer 就是瓶颈。更好的 tokenizer（MAGVIT-v2、IBQ、SBER-MoVQGAN）会抬高这个上限。Emu3（课程 12.12）仅凭更好的 tokenizer 就达到了 SDXL 质量的生成。

### Chameleon 与 BLIP-2 / LLaVA 对比

Chameleon（early fusion，共享词表）：
- 一个损失，一个 decoder。
- 生成混合模态输出。
- tokenizer 是质量上限。
- 昂贵：推理路径上每生成一张图都要跑 VQ-VAE decoder。

BLIP-2 / LLaVA（late fusion，分离的塔）：
- 视觉输入，仅文本输出。
- 复用预训练 LLM。
- 理解任务没有 tokenizer 瓶颈。
- 便宜：单次前向传播。

按任务选择。如果需要图像生成，选 Chameleon 家族。如果只需要理解，adapter-VLM 更简单，且能复用一个更大的预训练计算量。

### Fuyu 与 AnyGPT

Fuyu（Adept，2023）是相关方案：完全跳过独立的视觉编码器，把原始图像 patch 当作 token 一样喂进 LLM 的输入投影，不经过 tokenizer。比 Chameleon 简单，但失去了共享词表的输出生成能力。

AnyGPT（Zhan et al., 2024）把 Chameleon 扩展到四种模态：文本、图像、语音、音乐。每种模态都用同样的 VQ-VAE 技巧，共享同一个 transformer。任意模态到任意模态的生成。课程 12.16 有更多介绍。

```figure
vq-codebook
```

## Use It

`code/main.py` 端到端搭建一个小型 early fusion 模型：

- 一个微型 VQ-VAE 风格的量化器，把 8x8 patch 映射为 codebook 索引（K=16）。
- 一个共享词表：(文本 id 0..31) + (图像 id 32..47) + (分隔符 48, 49)。
- 一个玩具自回归 decoder（bigram 表），在合成的 caption + 图像 token 序列上训练。
- 采样循环，给定 prompt 后交替输出文本 + 图像 token。

代码故意把 transformer 保持得极小（bigram），以便你能端到端追踪信号流。

## Ship It

本课产出 `outputs/skill-tokenizer-vs-adapter-picker.md`。给定产品规格（只做理解 vs 理解 + 生成、所需图像质量、成本预算），它在 Chameleon 家族（early fusion）与 LLaVA 家族（late fusion）之间做选择，并用定量的经验规则给出理由。

## Exercises

1. Chameleon 使用 K=8192 个 codebook 条目、每张 512x512 图像 1024 个 token。估算相对 24 位 RGB 图像的压缩比。它是有损的吗？损失有多大？

2. 一张 4K 图像（3840x2160）在相同的 VQ-VAE 密度下会产生多少个图像 token？Chameleon 风格的模型能在一次推理调用中生成 4K 图像吗？首先崩掉的是什么——context、tokenizer 质量，还是 KV cache？

3. 用纯 Python 实现 QK-Norm。给定一个 64 维的 query 和 key，展示 LayerNorm 前后点积的变化。为什么在深层控制幅度很重要？

4. 阅读 Chameleon 第 2.3 节关于训练稳定性的内容。描述论文在 34B 规模上未使用 QK-Norm 时观察到的确切失败模式。这个"范数爆炸"的特征是什么？

5. 扩展玩具 decoder，使其能在只给文本 prompt 的情况下输出混合模态响应。在训练数据分布为 60% 先文本 / 40% 先图像的情况下，测量模型选择先图像 vs 先文本的频率。

## Key Terms

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Early fusion | "Unified tokens" | 图像被转换成离散 token，从第一步起就共享 transformer 的词表 |
| VQ-VAE | "Image tokenizer" | CNN + ViT + codebook，把图像映射为 transformer 可预测的整数索引 |
| Shared vocabulary | "One dictionary" | 单一 token ID 空间，覆盖文本 + 图像 + 模态分隔符 |
| QK-Norm | "Attention stabilizer" | 在点积之前对 query 和 key 施加 LayerNorm，防止范数爆炸 |
| Mixed-modality generation | "Text + image output" | 在一次推理中自主产出交错文本与图像 token 的推理过程 |
| Codebook size | "K entries" | VQ-VAE 可量化到的离散向量数量；在压缩率与保真度之间取舍 |
| Tokenizer ceiling | "Reconstruction limit" | 解码 VQ token 能达到的最佳 PSNR；它限定了模型的图像质量 |

## Further Reading

- [Chameleon Team — Chameleon: Mixed-Modal Early-Fusion Foundation Models (arXiv:2405.09818)](https://arxiv.org/abs/2405.09818)
- [Aghajanyan et al. — CM3 (arXiv:2201.07520)](https://arxiv.org/abs/2201.07520)
- [Yu et al. — CM3Leon (arXiv:2309.02591)](https://arxiv.org/abs/2309.02591)
- [Zhan et al. — AnyGPT (arXiv:2402.12226)](https://arxiv.org/abs/2402.12226)
- [Adept — Fuyu-8B blog (adept.ai)](https://www.adept.ai/blog/fuyu-8b)
