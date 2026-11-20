# 从 CLIP 到 BLIP-2 —— 以 Q-Former 作为模态桥

> CLIP 能对齐图像与文本，却无法生成描述、回答问题或进行对话。BLIP-2（Salesforce，2023）用一个小的可训练桥解决了这个问题：32 个可学习的 query 向量通过 cross-attention 汇聚冻结 ViT 的特征，然后直接插入冻结 LLM 的输入流。188M 参数的桥连起了 11B 的 LLM 与 ViT-g/14。直到 2026 年，所有基于 adapter 的 VLM——MiniGPT-4、InstructBLIP、LLaVA 的各位表亲——都是它的后裔。本课解读 Q-Former 的架构，解释它的两阶段训练，并构建一个把视觉 token 送入冻结文本解码器的玩具版本。

**Type:** Build
**Languages:** Python（标准库，cross-attention + 可学习 query 演示）
**Prerequisites:** Phase 12 · 02（CLIP）、Phase 7（Transformers）
**Time:** ~180 分钟

## Learning Objectives

- 解释为什么在冻结的视觉编码器与冻结的 LLM 之间放一个可训练的瓶颈，在成本和稳定性上都优于端到端微调。
- 实现一个 cross-attention 块，让一组固定的可学习 query 对外部图像特征做注意力。
- 梳理 BLIP-2 的两阶段预训练：先表征学习（ITC + ITM + ITG），再生成学习（在冻结解码器上使用 LM loss）。
- 比较 Q-Former 与 LLaVA 中更简单的 MLP projector，并论证各自在什么情况下更优。

## 问题场景

你有一个冻结的 ViT，每张图产生 256 个维度为 1408 的 patch token。你有一个冻结的 7B LLM，期望维度为 4096 的 token embedding。显而易见的桥——一层从 1408 到 4096 的线性层——可行，但把全部 256 个 patch token 喂进 LLM 的上下文，每张图就要多花 256 个 token。在一个 32 张图的 batch 上，仅视觉模态就吃掉 8192 个 token。

BLIP-2 要问的问题是：能否把 256 个 token 的图像表征压缩成远少的 token（比如 32 个），同时保留足够的信息，让 LLM 能描述图像、回答问题并对图像推理？以及，能否在不触碰冻结骨干网络的前提下训练这座桥，让训练成本只等于桥自身的参数？

答案是 Q-Former。32 个可学习的 "query" 向量通过 cross-attention 汇聚 ViT 的 patch token，产出一份 32 个 token 的视觉摘要供 LLM 使用。总共 188M 参数。在真正接触 LLM 之前，它已用对比、匹配和生成三类目标训练完毕。

## 核心概念

### 可学习 query

Q-Former 的核心技巧：不是让 LLM 的文本 token 去关注图像 patch，而是引入一组新的 32 个可学习 query 向量 `Q`，让它们去关注图像 patch。这些 query 是模型的参数——它们在训练中被学习，并且每张图都使用同样的这 32 个 query。

cross-attention 之后，每个 query 都持有一份图像的压缩摘要——"描述主体物体"、"描述背景"、"数一数物体"等等。query 并不会字面意义上专门对应语义标签；它们学到的是任何能让下游 loss 下降的编码方式。

### 架构

Q-Former 是一个小型 transformer（12 层，约 100M 参数），有两条路径：

1. Query 路径：32 个 query 向量先在彼此之间做 self-attention，再对冻结 ViT 的 patch token 做 cross-attention，最后过 FFN。
2. 文本路径：一个类 BERT 的文本编码器与 query 路径共享 self-attention 和 FFN 权重。文本路径关闭 cross-attention。

训练时两条路径都运行。query 与文本通过共享的 self-attention 交互，这意味着 query 可以在需要文本的任务（ITM、ITG）中以文本为条件。在向 VLM 交接的推理阶段，只有 query 流过，产出 32 个视觉 token。

### 两阶段训练

BLIP-2 分两阶段预训练：

Stage 1：表征学习（不涉及 LLM）。三个 loss：
- ITC（image-text contrastive）：在池化后的 query token 与文本 CLS token 之间做 CLIP 式对比。
- ITM（image-text matching）：二分类器——这对图文是否匹配？使用 hard negative 挖掘。
- ITG（image-grounded text generation）：在文本上接因果 LM head，以 query 为条件。迫使 query 编码可被文本生成的内容。

只有 Q-Former 参与训练。ViT 冻结。不涉及 LLM。

Stage 2：生成学习。接上一个冻结的 LLM（OPT-2.7B 或 Flan-T5-XL 等）。用一个小的线性层把 32 个 query 输出投影到 LLM 的 embedding 维度。把它们前置到文本 prompt 之前。只在拼接后的 prompt + image + caption 序列上以 LM loss 训练线性投影和 Q-Former。

Stage 2 之后，Q-Former + 投影层就是完整的视觉 adapter。推理时：image → ViT → Q-Former → linear proj → 前置到文本 → 冻结 LLM 输出。

### 参数量经济学

ViT-g/14（1.1B，冻结）+ OPT-6.7B（6.7B，冻结）+ Q-Former（188M，训练）的 BLIP-2 = 总量 8B，训练 188M。Q-Former 自身约占整套模型参数量的 2.4%。训练成本也反映了这一点：在少量 A100 上是几天，而端到端要数周。

质量：BLIP-2 在 zero-shot VQA 上追平甚至超过 Flamingo-80B，而体积小 50 倍。这座桥是管用的。

### InstructBLIP 与指令感知的 Q-Former

InstructBLIP（2023）给 Q-Former 增加了一个额外输入：指令文本本身。在 cross-attention 时，query 现在可以同时访问图像 patch 与指令。query 能按指令专门化（"数一数汽车"、"描述氛围"），而不是只学一份固定摘要。在留出任务上取得 benchmark 提升。

### MiniGPT-4 与只训投影层的路线

MiniGPT-4 保留了 Q-Former，但只训练输出线性投影层，其余一切冻结。便宜，但代价是质量——那些 query 是 BLIP-2 的，不是你的。适合快速迭代，不是最好的架构。

### LLaVA 为什么选了更简单的方案

LLaVA（2023，第 12.05 课）用一个朴素的 2 层 MLP 取代 Q-Former，把每个 ViT patch token 都投影到 LLM 空间——24x24 网格下每张图 576 个 token，全部喂给 LLM。压缩更差，但让 LLM 能对原始 patch 做注意力。这在当时颇具争议；到 2023 年末它成了主流，因为视觉指令数据（LLaVA-Instruct-150k）证明 MLP 可以被训练到保留足够信号。权衡在于：LLaVA 的上下文填得更快，但它能自然扩展到多图与视频。

到 2026 年，领域分化为两条路：在 token 预算敏感的场合（长视频、多图），Q-Former 存活下来；在以每个 token 的原始质量为先的场合，MLP projector 占主导。

### 门控 cross-attention：鼻祖 Flamingo

Flamingo（第 12.04 课）早于 BLIP-2，使用同样的 cross-attention 思路，但插在每一个冻结 LLM 层，而不是作为单一的桥。BLIP-2 证明了只压缩到输入层也依然有效。Gemini 与 Idefics 把两者结合：交错的输入 token，外加可选的 gated cross-attention 用于 in-context few-shot。

### 2026 年的后裔

- Q-Former：BLIP-2、InstructBLIP、MiniGPT-4，以及大多数出于 token 预算考虑的视频语言模型。
- Perceiver resampler：Flamingo 的变体（第 12.04 课）；Idefics 系列、Eagle、OmniMAE。
- MLP projector：LLaVA、LLaVA-NeXT、LLaVA-OneVision、Cambrian-1。
- Attention pool：VILA、PaliGemma。

四种都成立。决定性的问题是：你的约束在 token 预算上，还是在每个 token 的质量上。

```figure
modality-projection
```

## Use It

`code/main.py` 构建一个标准库实现的 Q-Former 风格 cross-attention：

1. 模拟 256 个图像 patch token（dim 128）。
2. 实例化 32 个可学习 query（dim 128）。
3. 执行 scaled-dot-product cross-attention（Q 来自 query，K/V 来自 patch）。
4. 通过线性层投影到 LLM 维度（512）。
5. 输出 32 个 LLM 可用的视觉 token。

全部数学都用纯 Python 实现（对向量做嵌套循环）。玩具级，但形状正确。它会打印 attention 权重矩阵，让你看到每个 query 从哪些 patch 上取到了信息。

## Ship It

本课产出 `outputs/skill-modality-bridge-picker.md`。给定目标 VLM 配置（视觉编码器 token 数、LLM 上下文预算、部署约束、质量目标），它会在 Q-Former、MLP 与 Perceiver resampler 之间给出推荐，并附简短理由和每种桥的参数估计。

## Exercises

1. 用 PyTorch 实现该 cross-attention 块。验证在 32 个 query 与 256 个 key/value 下，attention 权重矩阵为 32 x 256，且 softmax 后每行之和为 1。

2. 在 BLIP-2 stage 1 中，Q-Former 同时运行三个 loss：ITC、ITM、ITG。用伪代码写出三者各自的前向签名。哪一个需要文本编码器路径处于激活状态？

3. 比较参数量：Q-Former（12 层，768 hidden）与 2 层 MLP projector（1408 → 4096，两层）。在多大的 LLM 规模上，188M Q-Former 的成本能在训练效率上收回？

4. 阅读 BLIP-2 论文（arXiv:2301.12597）第 3.2 节关于 Q-Former 初始化的内容。解释为什么从 BERT-base 初始化（而非随机初始化）能加速收敛。

5. 对于一段 10 分钟、按 1 FPS 采样成 60 帧的视频，分别计算（Q-Former → 32 token/帧）与（MLP projector → 576 token/帧）的每帧 token 成本。哪一个能装进 128k token 的 LLM 上下文窗口？

## Key Terms

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Q-Former | "Query 式 transformer" | 小型 transformer，拥有 32 个可学习 query 向量，通过 cross-attention 汇聚冻结 ViT 的特征 |
| Learnable queries | "视觉的 soft prompt" | 一组固定参数，充当 cross-attention 的 query 侧；每个模型单独学习，跨所有输入共享 |
| Cross-attention | "Q 从这里来，K/V 从那里来" | query、key、value 来自不同来源的注意力；query 由此从 ViT patch 中取信息 |
| ITC | "Image-text contrastive" | 施加在 Q-Former 池化 query 与文本 CLS 之间的 CLIP 式 loss |
| ITM | "Image-text matching" | 在 hard negative 挖掘出的样本对上做二分类；迫使 query 区分细粒度不匹配 |
| ITG | "Image-grounded text generation" | 以 query 为条件生成文本的因果 LM loss；迫使 query 编码可被文本解码的内容 |
| Two-stage pretraining | "先表征再生成" | Stage 1 单独训练 Q-Former（ITC/ITM/ITG）；Stage 2 接上冻结 LLM，只训练投影层 + Q-Former |
| Frozen backbone | "不要微调" | 视觉编码器与 LLM 的权重固定；只有桥参与训练 |
| Projection head | "线性映射到 LLM 维度" | 把 Q-Former 输出映射到 LLM embedding 维度的最终线性层 |
| Perceiver resampler | "Flamingo 的版本" | 类似的可学习 query cross-attention，Flamingo 在每一层使用，而非作为单一桥 |

## Further Reading

- [Li et al. — BLIP-2 (arXiv:2301.12597)](https://arxiv.org/abs/2301.12597) — 核心论文。
- [Li et al. — BLIP (arXiv:2201.12086)](https://arxiv.org/abs/2201.12086) — 提出 ITC/ITM/ITG 三件套的前身。
- [Li et al. — ALBEF (arXiv:2107.07651)](https://arxiv.org/abs/2107.07651) — "align before fuse"——stage 1 训练的思想源头。
- [Dai et al. — InstructBLIP (arXiv:2305.06500)](https://arxiv.org/abs/2305.06500) — 指令感知的 Q-Former。
- [Zhu et al. — MiniGPT-4 (arXiv:2304.10592)](https://arxiv.org/abs/2304.10592) — 只训投影层的路线。
- [Jaegle et al. — Perceiver IO (arXiv:2107.14795)](https://arxiv.org/abs/2107.14795) — 可学习 query cross-attention 的通用架构。
