# CLIP 与对比式视觉-语言预训练

> OpenAI 的 CLIP（2021）证明了一个足够大的想法，足以支撑接下来的五年：只用嘈杂的网络图文对和一个对比损失，把图像编码器和文本编码器对齐到同一个向量空间。零监督标签。4 亿对数据。由此得到的 embedding 空间能做零样本分类、图文检索，并作为视觉塔接入每一个 2026 年的 VLM。SigLIP 2（2025）用 sigmoid 取代 softmax，以更低的成本超越了 CLIP。本课走通从 InfoNCE 到 sigmoid 成对损失的数学，并用 stdlib Python 构建训练步骤。

**Type:** Build
**Languages:** Python（stdlib，InfoNCE + sigmoid 损失实现）
**Prerequisites:** Phase 12 · 01（ViT patch）、Phase 7（Transformers）
**Time:** ~180 分钟

## Learning Objectives

- 从互信息推导 InfoNCE 损失，并实现一个数值稳定的向量化版本。
- 解释为什么 sigmoid 成对损失（SigLIP）能扩展到 batch 32768+，而不需要 softmax 所要求的 all-gather 开销。
- 通过构造文本模板（`a photo of a {class}`）并在余弦相似度上取 argmax，跑通零样本 ImageNet 分类。
- 说出 CLIP / SigLIP 预训练给你的四个杠杆：batch size、温度、prompt 模板、数据质量。

## 问题场景

CLIP 之前的视觉是监督式的。收集带标签的数据集（ImageNet：120 万张图像、1000 个类别），训练一个 CNN，发布。标签很贵，标签会偏向标注者能达成一致的东西，而且标签不经微调无法迁移到新任务。

网络上的图文对有一亿多对松散标注的数据是免费的。一张金毛寻回犬的图片带着 alt 文本"my dog Max in the park"，就携带了监督信号 —— 文本描述了图像。问题在于：你能把它变成有用的训练吗？

CLIP 的回答：把图文对当作一个匹配任务。给定一批 N 张图像和 N 条 caption，学习在 N-1 个干扰项中把每张图像与它自己的 caption 匹配起来。监督信号是"这两样东西属于一起；这 N-1 个不属于。"没有类别标签。没有人工标注。只有一个对比损失。

由此得到的 embedding 空间能做到超出 CLIP 训练目标的事情。ImageNet 零样本之所以有效，是因为"a photo of a cat"会嵌入到那些从未被显式标注为猫的猫的图片附近。这就是催生每一个 2026 年 VLM 的那次下注。

## 核心概念

### 双编码器

CLIP 有两个塔：

- 图像编码器 `f`：ViT 或 ResNet，为每张图像输出一个 D 维向量。
- 文本编码器 `g`：小型 transformer，为每条 caption 输出一个 D 维向量。

两个塔都把输出归一化为单位长度。因为两者都是单位范数，相似度就是 `cos(f(x), g(y)) = f(x)^T g(y)`。

对于一批 N 个（图像、caption）对，构造形状为 `(N, N)` 的相似度矩阵 `S`：

```
S[i, j] = cos(f(x_i), g(y_j)) / tau
```

其中 `tau` 是一个可学习的温度（CLIP 初始化为 0.07；在对数空间中学习）。

### InfoNCE 损失

CLIP 在行和列上使用对称的交叉熵：

```
loss_i2t = CE(S, labels=identity)     # each image's positive is its own caption
loss_t2i = CE(S^T, labels=identity)   # each caption's positive is its own image
loss = (loss_i2t + loss_t2i) / 2
```

这就是 InfoNCE。CE 中的 softmax 迫使每张图像与它自己的 caption 的匹配程度超过 batch 中任何其他 caption。所谓"负样本"就是 batch 中所有其他条目。更大的 batch = 更多负样本 = 更强的信号。CLIP 在 batch 32k 下训练；规模很重要。

### 温度系数

`tau` 控制 softmax 的锐度。低 tau → 分布更尖锐，有难负样本挖掘的效果。高 tau → 更平滑，所有样本都有贡献。CLIP 学习 log(1/tau)，并做裁剪以防止坍缩。SigLIP 2 固定初始 tau，改用学习到的偏置。

### 为什么 sigmoid 扩展性更好（SigLIP）

Softmax 需要整个相似度矩阵同步。在分布式训练中，你必须把每个 embedding all-gather 到每个 replica，然后做 softmax。这在通信上对世界规模是二次的。

SigLIP 用逐元素 sigmoid 取代 softmax：对每一对 `(i, j)`，损失是一次二分类 —— "这两者是不是匹配的那一对？"正类标签是对角线，其余全是负类。损失是：

```
L = -1/N sum over (i, j) [ y_ij log sigmoid(S[i,j]) + (1-y_ij) log sigmoid(-S[i,j]) ]
```

若 `i == j` 则 `y_ij = 1`，否则为 0。每一对的损失相互独立。不需要 all-gather。每块 GPU 计算自己的局部块并求和。SigLIP 2 能以低成本扩展到 batch 32k-512k，而在同样规模下 CLIP 需要按比例增加通信。

### 零样本分类

给定 N 个类别名，为每个类别构造一个文本模板：

```
"a photo of a {class}"
```

用文本编码器嵌入每个模板。用图像编码器嵌入你的图像。余弦相似度的 argmax 就是预测类别。不在目标类别上做任何训练。

Prompt 模板很重要。CLIP 原始论文每个类别用了 80 个模板（朴素的、艺术的、照片的、绘画的等）并对 embedding 取平均。ImageNet 提升 3 个点。现代用法通常只挑一两个模板。

### 线性探测与微调

零样本是一个基线。线性探测（在冻结的 CLIP 特征之上为目标类别训练一个线性层）在域内任务上胜过零样本。全量微调在域内胜过线性探测，但可能损害零样本迁移。三种方案，三种取舍。

### SigLIP 2：NaFlex 与稠密特征

SigLIP 2（2025）增加了：
- NaFlex：单个模型处理可变宽高比和分辨率。
- 更好的稠密特征，用于分割和深度估计，目标是作为 VLM 中的冻结骨干。
- 多语言：在 100+ 种语言上训练，而 CLIP 只支持英语。
- 10 亿参数规模，而 CLIP 止步于 4 亿。

在 2026 年的开放 VLM 中，SigLIP 2 SO400m/14 是默认视觉塔。对于特定的 LAION-2B 训练分布与你查询模式匹配的纯图文检索，CLIP 仍是默认选择。

### ALIGN, BASIC, OpenCLIP, EVA-CLIP

ALIGN（Google，2021）：与 CLIP 同样的想法，18 亿对的规模，90% 是嘈杂的。证明了嘈杂数据可以扩展。OpenCLIP（LAION）：在 LAION-400M / 2B 上对 CLIP 的开放复现，多种规模，是首选的开源 checkpoint。EVA-CLIP：从掩码图像建模初始化；是 VLM 的强骨干。BASIC：Google 的 CLIP+ALIGN 混合体。全是同一家族，不同的数据和调参。

### 零样本的天花板

CLIP 级模型在 ImageNet 零样本上大约封顶在 76%（CLIP-G、OpenCLIP-G）。再往上要么需要大得多的数据（SigLIP 2 达到 80%+），要么需要架构改动（监督头、更多参数）。这个 benchmark 正在饱和；真正的价值在于下游 VLM 所消费的那个 embedding 空间。

```figure
multimodal-fusion
```

## Use It

`code/main.py` 实现了：

1. 一个玩具双编码器（基于哈希的图像特征、文本字符特征），让你不用 numpy 也能看到 InfoNCE 的形状。
2. 纯 Python 的 InfoNCE 损失（通过 log-sum-exp 保证数值稳定）。
3. 用于对比的 sigmoid 成对损失。
4. 一个零样本分类例程：对一组文本 prompt 计算余弦相似度，argmax 作为预测。

运行它并观察损失曲线。绝对数值是玩具级的；形状与真实 CLIP 训练器输出的一致。

## Ship It

本课产出 `outputs/skill-clip-zero-shot.md`。给定一组图像（通过路径）和一个目标类别列表，它用 CLIP 模板构造文本 prompt，用声明的 checkpoint（例如 `openai/clip-vit-large-patch14`）嵌入两侧，并返回带相似度分数的 top-1 / top-5 预测。该 skill 拒绝就 prompt 列表之外的类别做出断言。

## Exercises

1. 为一批 4 个对亲手实现 InfoNCE。构造 4x4 相似度矩阵，跑 softmax，取出对角线，计算交叉熵。用这个手算结果验证你的 Python 实现。

2. SigLIP 在温度之外还使用一个偏置参数 `b`：`S'[i,j] = S[i,j]/tau + b`。当 batch 存在严重类别不平衡（每行负样本远多于正样本）时，`b` 起什么作用？阅读 SigLIP 第 3 节（arXiv:2303.15343）。

3. 构建一个猫 vs 狗零样本分类器。试两个 prompt 模板：`a photo of a {class}` 和 `a picture of a {class}`。在 100 张测试图像上测量准确率。模板集成是否胜过单个模板？

4. 计算 512 块 GPU、batch 32k 运行时，softmax InfoNCE 与 sigmoid 成对损失的通信成本。哪个是 O(N)，哪个是 O(N^2)？引用 SigLIP 第 4 节。

5. 阅读 OpenCLIP 缩放定律论文（arXiv:2212.07143，Cherti 等人）。从图表中复现他们关于数据缩放的结论：在固定模型规模下，ImageNet 零样本准确率与训练数据规模之间是怎样的对数线性关系？

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|------------------------|
| InfoNCE | "对比损失" | 对一个 batch 相似度矩阵做交叉熵；每个条目的正样本是它配对的条目，负样本是其余一切 |
| Sigmoid loss | "SigLIP 损失" | 逐对的二元交叉熵；没有 softmax，没有 all-gather，在分布式训练中廉价扩展 |
| Temperature | "tau" | 在 softmax/sigmoid 之前缩放 logits 的标量；控制分布的锐度 |
| Zero-shot | "免微调分类" | 用文本 prompt 构造类别 embedding 并按余弦相似度分类；不在目标类别上训练 |
| Prompt template | "a photo of a ..." | 围绕类别名的文本脚手架；会给零样本准确率带来 1-5 个点的影响 |
| Dual encoder | "双塔" | 一个图像编码器 + 一个文本编码器，输出位于共享的 D 维空间 |
| Hard negative | "难干扰项" | 与正样本足够相似、以致模型必须费力才能分开的负样本 |
| Linear probe | "冻结 + 一层" | 只在冻结特征之上训练一个线性分类器；用来衡量特征质量 |
| NaFlex | "原生灵活分辨率" | SigLIP 2 的能力：无需缩放即可接收任意宽高比和分辨率的图像 |
| Temperature scaling | "对数参数化 tau" | CLIP 把 `log(1/tau)` 参数化以使梯度行为良好；做裁剪以防止 tau 坍缩到接近零 |

## Further Reading

- [Radford et al. — Learning Transferable Visual Models From Natural Language Supervision (arXiv:2103.00020)](https://arxiv.org/abs/2103.00020) —— CLIP 论文。
- [Zhai et al. — Sigmoid Loss for Language Image Pre-Training (arXiv:2303.15343)](https://arxiv.org/abs/2303.15343) —— SigLIP。
- [Tschannen et al. — SigLIP 2 (arXiv:2502.14786)](https://arxiv.org/abs/2502.14786) —— 多语言 + NaFlex。
- [Jia et al. — ALIGN (arXiv:2102.05918)](https://arxiv.org/abs/2102.05918) —— 用嘈杂网络数据扩展。
- [Cherti et al. — Reproducible scaling laws for contrastive language-image learning (arXiv:2212.07143)](https://arxiv.org/abs/2212.07143) —— OpenCLIP 缩放定律。
