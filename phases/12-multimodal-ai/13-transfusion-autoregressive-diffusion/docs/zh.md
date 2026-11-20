# Transfusion：在同一个 Transformer 中做自回归文本 + 扩散图像

> Chameleon 和 Emu3 把全部赌注压在离散 token 上。它们能用，但量化瓶颈肉眼可见——图像质量的上限低于连续空间的 diffusion 模型。Transfusion（Meta，Zhou 等，2024 年 8 月）押了相反的一注：让图像保持连续，彻底去掉 VQ-VAE，用两个 loss 训练一个 transformer。文本 token 走 next-token 预测，图像 patch 走 flow matching / diffusion loss。两个目标优化同一套权重。支撑 Stable Diffusion 3 的架构（MMDiT）是它的近亲。本节课解读 Transfusion 的核心论点，构建一个玩具版双 loss 训练器，并追踪让一个 transformer 同时完成两项任务的 attention mask。

**Type:** 构建
**Languages:** Python（stdlib，在 MNIST 规模的玩具问题上实现双 loss 训练器）
**Prerequisites:** Phase 12 · 11（Chameleon）、Phase 8（Generative AI）
**Time:** ~180 分钟

## Learning Objectives

- 搭建一个在同一个骨干上同时运行两个 loss（文本 token 上的 NTP、图像 patch 上的 diffusion MSE）的 transformer。
- 解释为什么对图像 patch 使用双向 attention、对文本 token 使用因果 attention 是正确的 mask 选择。
- 从计算量、质量、代码复杂度三个方面比较 Transfusion 式（连续图像 + diffusion loss）与 Chameleon 式（离散图像 + NTP）。
- 说出 MMDiT 的贡献：每个 block 使用模态专属权重，在 residual stream 上做联合 attention。

## 问题场景

离散与连续图像 token 之争比 LLM 的历史还要久。连续表示（原始像素、VAE latent）能保留细节。离散 token（VQ 索引）契合 transformer 原生词表，但在量化那一步就丢掉了细节。

Chameleon / Emu3 选择离散：一个 loss、一套架构，但图像保真度被 tokenizer 质量封顶。

Diffusion 模型选择连续：图像质量极佳，但要与 LLM 分开成独立模型，噪声调度工程设计复杂，并且无法与文本生成干净地集成。

Transfusion 提出的问题是：能不能两者兼得？让图像保持连续，仍然只训练一个模型，用两个 loss 拼接进同一次梯度更新。

## 核心概念

### 双 loss 架构

一个 decoder-only transformer 处理这样一条序列，其中包含：

- 文本 token（离散，来自 BPE 词表）。
- 图像 patch（连续，把 16x16 的像素块经由线性 embedding 投影到 hidden dim——与 ViT encoder 的输入相同）。
- `<image>` 和 `</image>` 标签，标记连续 patch 所在的位置。

前向传播只跑一次。loss 按 token 选择两个 head 中的一个：

- 对文本 token：在词表 logits head 上做标准交叉熵。
- 对图像 patch：在连续 patch 上做 diffusion loss——预测添加到每个 patch 上的噪声。

梯度流经共享的 transformer 主体。两个 loss 同时改进共享权重。

### Attention mask：文本因果 + 图像双向

文本 token 必须是因果的——不能让文本 token 看到未来的文本，否则 teacher forcing 就失效了。然而图像 patch 代表的是同一张快照；在同一图像块内它们应当彼此双向可见。

mask 如下：

```
M[i, j] = 1 if:
  (i is text and j is text and j <= i)   # causal for text
  OR (i is image and j is image and same_image_block(i, j))   # bidirectional within image
  OR (i is text and j is image and j < i_image_end)   # text attends to previous images
  OR (i is image and j is text and j < i_image_start)   # image attends to preceding text
```

在训练和推理时，它被实现为块三角（block-triangular）mask。

### Transformer 内部的 diffusion loss

Diffusion loss 是标准的：给图像 patch 加噪，让模型去预测噪声（等价地，预测干净 patch）。Transfusion 的版本用 flow matching——预测从带噪指向干净的 velocity 场。

训练时：
1. 对每个图像 patch x0，采一个随机时间步 t。
2. 采噪声 ε，计算 xt = (1-t) * x0 + t * ε（flow matching 的线性插值）。
3. Transformer 预测 v_theta(xt, t)；loss = MSE(v_theta(xt, t), ε - x0)。
4. 与同一条序列上的文本 NTP loss 一起反向传播。

推理时，生成过程是：
- 文本 token：标准自回归采样。
- 图像 patch：以先前的文本 token 为条件的 diffusion 采样循环（通常 10-30 步）。

### MMDiT：Stable Diffusion 3 的变体

Stable Diffusion 3（Esser 等，2024 年 3 月）在差不多与 Transfusion 同一时间发布了 MMDiT（Multimodal Diffusion Transformer）。这两个架构是兄弟。

MMDiT 的关键差异：

- 每个 block 使用模态专属权重。每个 transformer block 对文本 token 和图像 patch 分别持有各自的 Q、K、V 和 MLP 权重。attention 是联合的（跨模态）；其余部分都是模态专属的。
- Rectified flow 训练。一种特定的 flow-matching 变体，采样方式已知，数学比 DDPM 更简单。
- 规模。MMDiT 是 SD3 的骨干（2B 和 8B 参数两个变体）。Transfusion 论文扩展到 7B。

两者都收敛到同一个核心理念：用一个 transformer 在文本上跑 NTP，在连续图像表示上跑 diffusion。

### 为什么这能胜过 Chameleon 式

在图像生成上，连续 diffusion 与离散 NTP 之间的质量差距是可测量的。Transfusion 论文报告：

- 在 7B 参数下，FID 比同等规模的 Chameleon 式模型好 3-5 个点。
- 不需要训练 tokenizer——图像 encoder 更简单（线性投影到 hidden，与 ViT 的输入层相同）。
- 与自回归图像 token 不同，推理时图像 patch 的去噪可以并行。

缺点：Transfusion 是双 loss 模型，训练动态更难把握。loss 权重需要调。NTP 与 diffusion 之间的调度不匹配，可能导致某个 head 占据主导。

### 下游沿革

Janus-Pro（12.15 课）通过解耦理解与生成所用的视觉 encoder 来改进 Transfusion 的思路——一个用 SigLIP，另一个用 VQ——同时共享 transformer 主体。Show-o（12.14 课）把 diffusion 换成离散 diffusion（掩码预测）。统一生成这一家族在 Transfusion 之后迅速分支。

2026 年能够输出图像的生产级 VLM——Gemini 3 Pro、GPT-5、Claude Opus 4.7 的图像生成路径——几乎可以肯定使用了该家族的某个后代。细节属于专有信息。

```figure
cfg-guidance-scale
```

## Use It

`code/main.py` 在一个微小的类 MNIST 问题上构建玩具版 Transfusion：

- 文本 caption 是描述某个数字（0-9）的短整数序列。
- 图像是 4x4 的字节网格。
- 一对共享权重的线性投影充当 transformer 的替身；文本上是 NTP loss，带噪 patch 上是 MSE loss。
- 训练循环交替两个 loss，attention mask 显式写出。
- 生成在一次前向传播中产出一个文本 caption 和一张 4x4 图像。

这个 transformer 是玩具。真正的产物是双 loss 的接线、attention mask 的构造以及推理循环。

## Ship It

本节课产出 `outputs/skill-two-loss-trainer-designer.md`。给定一个新的多模态训练任务（文本 + 图像、文本 + 音频、文本 + 视频），它设计双 loss 调度方案（loss 权重、mask 形状、共享还是模态专属 block），并标记实现风险。

## Exercises

1. 一个 Transfusion 式模型训练时 70% 是文本 token、30% 是图像 patch。图像 diffusion loss 的数值量级大约是文本 NTP loss 的 10 倍。什么样的 loss 权重能让它们平衡？

2. 为序列 `[T, T, <image>, P, P, P, P, </image>, T]` 实现块三角 mask。把每一项标为 0 或 1。

3. MMDiT 持有模态专属的 QKV 权重。与 Transfusion 的完全共享 transformer 相比，这增加了多少参数量开销？在 7B 参数下，值得吗？

4. 生成：给定一个文本 prompt，模型对 50 个 token 跑 NTP，然后遇到 `<image>`，接着在 256 个 patch 上跑 20 步去噪的 diffusion。总共需要多少次前向传播？

5. 阅读 SD3 论文第 3 节。描述 rectified flow，并说明为什么它比 DDPM 用更少的推理步数就能收敛。

## Key Terms

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Two-loss training | "NTP + diffusion" | 单个 transformer 在同一次梯度更新中同时优化文本 token 上的交叉熵与连续图像 patch 上的 MSE |
| Flow matching | "Rectified flow" | 一种 diffusion 变体，预测从噪声到干净数据的 velocity 场；数学比 DDPM 更简单 |
| MMDiT | "Multimodal DiT" | Stable Diffusion 3 的架构：联合 attention，模态专属的 MLP 与 norm |
| Block-triangular mask | "Causal text + bidirectional image" | 一种 attention mask，在文本上因果，但在图像区域内双向 |
| Continuous image representation | "No VQ" | 图像 patch 是实值向量，而非整数码本索引 |
| Velocity prediction | "v-parameterization" | 网络输出的是噪声与数据之间的 velocity 场，而不是噪声本身 |

## Further Reading

- [Zhou et al. — Transfusion (arXiv:2408.11039)](https://arxiv.org/abs/2408.11039)
- [Esser et al. — Stable Diffusion 3 / MMDiT (arXiv:2403.03206)](https://arxiv.org/abs/2403.03206)
- [Peebles & Xie — DiT (arXiv:2212.09748)](https://arxiv.org/abs/2212.09748)
- [Zhao et al. — MonoFormer (arXiv:2409.16280)](https://arxiv.org/abs/2409.16280)
- [Xie et al. — Show-o (arXiv:2408.12528)](https://arxiv.org/abs/2408.12528)
