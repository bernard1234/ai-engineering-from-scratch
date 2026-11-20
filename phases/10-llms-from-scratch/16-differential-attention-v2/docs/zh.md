# 差分注意力（V2）

> softmax attention 会在每一个不匹配的 token 上铺开一小部分概率。在 100k 个 token 上，这些噪声累积起来，把信号淹没。Differential Transformer（Ye et al., ICLR 2025）的解法是把 attention 算成两个 softmax 之差，减掉共享的噪声底。DIFF V2（Microsoft，2026 年 1 月）是生产栈的重写版本：解码延迟与基线 Transformer 持平，不需要自定义 kernel，与 FlashAttention 兼容。本课从头到尾走一遍 V1 到 V2，并给出一个可以在 stdlib Python 里跑的差分操作玩具实现。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 7 · 02 (self-attention), Phase 7 · 15 (attention variants), Phase 10 · 14 (architecture walkthrough)
**Time:** ~60 分钟
## Learning Objectives

- 精确陈述 softmax attention 为什么存在噪声底，以及它为什么随上下文长度增长。
- 推导 differential attention 公式，并解释为什么相减能抵消共享的噪声成分而保留信号。
- 梳理 V1 到 V2 的差异：什么变快了、什么变简单了、什么变稳定了，以及为什么每一处改动对生产级预训练都是必要的。
- 用纯 Python 从零实现 differential attention，并在一个合成的信号加噪声 query 上实证噪声抵消性质。

## 问题场景

标准 softmax attention 有一个数学性质，在规模上会变成运维上的头疼事。对一个 query `q`，attention 权重是 `softmax(qK^T / sqrt(d))`。softmax 永远无法产出精确的零——每个不匹配的 token 都会拿到一些正的质量。这份残余质量就是噪声，而且它随上下文长度增长。在 128k 个 token 时，即使每个不匹配的 token 只拿到 0.001% 的概率，127,999 个加起来也贡献了总量的约 12%。模型不得不学会绕开一个随上下文增长的噪声底。

经验上，这表现为 attention head 之间的相互干扰：长上下文 RAG 中编造的引用，100k token 检索任务上的 lost-in-the-middle 失败，以及 needle-in-haystack benchmark 超过 32k 后准确率的细微退化。Differential Transformer 论文（arXiv:2410.05258, ICLR 2025）测量了这个差距：DIFF Transformer 相比同等规模的基线，perplexity 更低、长上下文准确率更高、幻觉更少。

DIFF V1 有三个问题，让它进不了前沿预训练流水线。它的 value cache 在每个解码步都要加载两次；它需要自定义 CUDA kernel，破坏了 FlashAttention 兼容性；它的 per-head RMSNorm 在 70B 以上的规模上让长时间训练变得不稳定。DIFF V2（Microsoft unilm 博客，2026 年 1 月 20 日）把这三个问题都解决了。本课两个版本都走一遍，构建差分算子，并在一玩具 query 上测量噪声抵消。

## 核心概念

### softmax 的噪声底

对一个 query `q` 和 keys `K = [k_1, ..., k_N]`，attention 权重是：

```
w_i = exp(q . k_i / sqrt(d)) / sum_j exp(q . k_j / sqrt(d))
```

没有任何 `w_i` 会是零。如果 `k_i` 与 `q` 完全无关，分数 `q . k_i` 也不是 0——它在零附近波动，方差为 `||q||^2 / d`。经过 softmax 归一化后，每个无关 token 仍然向加权和贡献 `O(1/N)`。无关 token 的总贡献是 `O((N-1)/N) = O(1)`——不是一个小量。

模型想要的是类似硬 top-k 的东西：匹配 token 上高权重，其他地方权重接近零。softmax 太“平滑”，做不到这一点。

### 差分的思想

把每个 head 的 Q 和 K 投影各自拆成两份：Q = (Q_1, Q_2) 和 K = (K_1, K_2)。计算两张 attention map：

```
A_1 = softmax(Q_1 K_1^T / sqrt(d))
A_2 = softmax(Q_2 K_2^T / sqrt(d))
```

输出：

```
DiffAttn = (A_1 - lambda * A_2) V
```

相减会抵消两张 map 共享的那部分噪声分布。如果两张 map 在 127k 个无关 token 上的权重大致均匀（在随机初始化时它们确实如此），这些就会抵消。信号——少数真正相关 token 上的尖峰权重——只有在两张 map 中以相同幅度出现时才会被抵消，而模型一旦开始训练，这不会发生。

`lambda` 是每个 head 一个的可学习标量，参数化为 `lambda = exp(lambda_q1 dot lambda_k1) - exp(lambda_q2 dot lambda_k2) + lambda_init`。它可以为负。`lambda_init` 默认是一个小的正数，比如 0.8。

### 为什么这与头戴式降噪同构

想象两支有噪声的麦克风录同一个人的声音。两支都拾取到说话人，也都拾取到相关的背景噪声。把一支从另一支里减掉，共享的噪声就消失了。声音之所以活下来，是因为两路信号在相位或幅度上的差异足以阻止完全抵消。每个 head 的 `lambda` 学的正是这个平衡。

### V1 与 V2：差异在哪里

V1 让参数量与基线 Transformer 相等。为了每个 head 拿到两个 query，它把 head 维度减半。这损失了 head 的表达能力，更痛苦的是，它把每个 head 的 value cache 减半了。解码时每个步都要加载两次 value cache（每个 softmax 分支一次）。结果：尽管参数量匹配，解码却比基线慢。

V2 让 query head 数量翻倍，同时保持 KV head 不变（参数从 up-projection 里借）。head 维度与基线相同。相减之后，多出来的维度再投影回基线 Transformer 的 O_W 投影。三件事同时发生：

1. 解码速度与基线持平（KV cache 只加载一次）。
2. FlashAttention 原样运行（无需自定义 kernel）。
3. 解码时的算术强度上升（从 HBM 每加载一个字节做更多计算）。

V2 还去掉了 V1 用来稳定相减的 per-head RMSNorm。在 70B 级别的预训练规模上，那个 RMSNorm 让训练后期不稳定。V2 换成一个更简单的初始化方案，不加额外模块也能保持训练稳定。

### 什么时候该用它

| 负载类型 | 收益 |
|----------|---------|
| 长上下文 RAG（64k+） | attention map 更干净，编造的引用更少 |
| Needle-in-haystack benchmark | 超过 32k 后准确率显著提升 |
| 多文档问答 | 跨文档干扰更少 |
| 8k 的代码补全 | 边际收益，不值得改架构 |
| 短对话（< 4k） | 与基线基本无法区分 |

价值随上下文长度增长。在 4k token 时，噪声底小到标准 attention 就够用。到 128k 时，它正在伤害你。

### 与其他 2026 年旋钮如何叠加

| 特性 | 与 DIFF V2 兼容？ |
|---------|------------------------|
| GQA | 是（V2 增加的是 Q head，不是 KV head） |
| MLA (DeepSeek) | 原则上可以，尚无把它们结合的已发表论文 |
| MoE | 是（attention 与 MLP 块相互独立） |
| RoPE | 是（未改动） |
| YaRN / 长上下文缩放 | 是（正是 DIFF 帮助最大的地方） |
| FlashAttention | V2 中为是（V1 中为否） |
| 投机解码 | 是（attention 的改动对 spec-decode 循环不可见） |

```figure
differential-attention
```

## Build It

`code/main.py` 用纯 Python 实现 differential attention。一个结构已知的信号加噪声玩具 query，让你直接测量噪声抵消比。

### 第 1 步：标准 softmax attention

stdlib 矩阵运算：列表的列表、手写 matmul、减去最大值以保证数值稳定性的 softmax。

```python
def softmax(row):
    m = max(row)
    exps = [math.exp(x - m) for x in row]
    s = sum(exps)
    return [e / s for e in exps]
```

### 第 2 步：把 Q、K 拆成两半

V1 风格：把 head 维度减半。V2 风格：保持 head 维度，把 head 数量翻倍。玩具实现为了教学清晰采用 V1——数学完全相同，只是簿记不同。

### 第 3 步：两条 softmax 分支 + 相减

```python
A1 = [softmax([dot(q1, k) / scale for k in K1]) for q1 in Q1]
A2 = [softmax([dot(q2, k) / scale for k in K2]) for q2 in Q2]
diff_weights = [[a1 - lam * a2 for a1, a2 in zip(r1, r2)] for r1, r2 in zip(A1, A2)]
out = [[sum(w * v[j] for w, v in zip(row, V)) for j in range(d_v)] for row in diff_weights]
```

注意：输出权重可以为负。这没关系——value cache 仍然能处理带符号的贡献。随后的 V 投影会吸收符号。

### 第 4 步：噪声抵消测量

构建一条长度为 1024 的合成序列。把信号 token 放在已知位置，其余填满噪声。计算 (a) 标准 softmax attention 在信号位置上的权重，以及 (b) differential attention 的权重。测量各自的信噪比。DIFF attention 稳定地产出更高的信噪比，提升幅度为 3x-10x，取决于两条分支在训练中分化得有多开。

### 第 5 步：V1 与 V2 的参数核算

给定一个配置（hidden=4096, heads=32, d_head=128），打印：

- 基线 Transformer：Q、K、V 每个大小为 `hidden * hidden`，MLP 为 4 * hidden。
- DIFF V1：Q、K 每个大小为 `hidden * hidden`，V 大小为 `hidden * hidden`（不变），head 维度在内部减半。增加 per-head `lambda` 参数（O(heads * d_head)）。
- DIFF V2：Q 大小为 `2 * hidden * hidden`，K 大小为 `hidden * hidden`，V 大小为 `hidden * hidden`。多余维度在 O_W 之前投影回原大小。增加同样的 `lambda` 参数。

玩具会测量 V2 的额外参数成本（每个 attention 块大约 `hidden * hidden`）并打印出来。

## Use It

截至 2026 年 4 月，DIFF V2 还没有在每一个生产推理服务器中出货，但 vLLM 和 SGLang 的集成正在进行中。与此同时，这个模式出现在：

- Microsoft 内部的长上下文生产模型里。
- 若干针对 256k 以上上下文的开源模型训练中的研究性复现。
- 混合架构中，把 DIFF attention 与滑动窗口 attention 交替布置在不同层上。

2026 年你会在什么情况下用它：

- 从零训练一个瞄准 64k 以上有效上下文的新模型。从一开始就加入 differential attention；之后再重训代价很高。
- 微调一个长上下文模型，而 lost-in-the-middle 失败主导了你的评估。在 Q 投影上加 LoRA 可以近似 DIFF 结构。

什么情况下不用：

- 你已经在服务一个预训练的稠密模型，且长上下文性能稳定。重训成本在已有权重上很少能回本。
- 你的上下文永远在 16k 以下。噪声底可以忽略。

## Ship It

本课产出 `outputs/skill-diff-attention-integrator.md`。给定一个模型架构、目标上下文长度、幻觉画像和训练预算，它为一次新的预训练或 LoRA 微调产出加入 differential attention 的集成方案。

## Exercises

1. 运行 `code/main.py`。确认在合成 query 上，differential attention 报告的信噪比高于标准 softmax attention。改变噪声幅度，找出标准 attention 变得不可用的交叉点。

2. 为一个 7B 级模型（hidden=4096, heads=32, d_head=128, 32 层）计算从基线到 DIFF V1 以及从基线到 DIFF V2 的参数数量差。说明哪些组件增加了参数、哪些保持不变。

3. 读 DIFF V1 论文（arXiv:2410.05258）的第 3 节和 DIFF V2 Hugging Face 博客的第 2 节。用两句话解释为什么 V1 的 per-head RMSNorm 是必要的，以及为什么 V2 能去掉它而不引起训练发散。

4. 实现一个消融：用 `lambda = 0`（纯第一个 softmax）和 `lambda = 1`（完整相减）计算 differential attention。在合成 query 上，测量信噪比在整个扫描区间上的变化。找出使信噪比最大的 `lambda`。

5. 把玩具扩展到 GQA + DIFF V2。选 8 个 KV head 和 32 个 Q head。说明 KV cache 大小与同样 (8, 32) 配置的基线 GQA 模型一致。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Differential attention | “两个 softmax 互相减” | 把 Q、K 拆成两半，算两张 softmax map，用第一张减去第二张（按 lambda 缩放），再乘以 V |
| Noise floor | “softmax 的非零尾巴” | softmax 落在每个无关 token 上的 O(1/N) 权重，在长上下文上累加为 O(1) |
| lambda | “相减的尺度” | 每个 head 一个的可学习标量，参数化为 `exp(lq1.lk1) - exp(lq2.lk2) + lambda_init`；可以为负 |
| DIFF V1 | “ICLR 2025 那一版” | 原始 Differential Transformer；把 head 维度减半以保持参数量，需要自定义 kernel，解码更慢 |
| DIFF V2 | “2026 年 1 月的修复版” | 把 Q head 翻倍并保持 KV head 不变；解码速度与基线持平，且兼容 FlashAttention |
| Per-head RMSNorm | “V1 的稳定器” | V1 在相减之后施加的额外 norm；V2 去掉它以防止训练后期不稳定 |
| Signal-to-noise ratio | “有多少 attention 被浪费掉了” | 真信号位置上的权重与无关位置上平均权重之比 |
| Lost in the middle | “长上下文失败模式” | 一种经验现象：长上下文中部文档的检索准确率会下滑——DIFF attention 能减轻它 |
| Arithmetic intensity | “每加载一字节的 FLOPs” | V2 通过每次 KV 加载翻倍 query 数来在解码时提高的比值；对内存受限的解码很重要 |

## Further Reading

- [Ye et al. — Differential Transformer (arXiv:2410.05258, ICLR 2025)](https://arxiv.org/abs/2410.05258) -- 原始论文，含噪声抵消理论与长上下文消融
- [Microsoft unilm — Differential Transformer V2 (Hugging Face blog, January 2026)](https://huggingface.co/blog/microsoft/diff-attn-v2) -- 生产栈重写，解码与基线持平，兼容 FlashAttention
- [Understanding Differential Transformer Unchains Pretrained Self-Attentions (arXiv:2505.16333)](https://arxiv.org/abs/2505.16333) -- 理论分析：为什么相减能恢复预训练学到的 attention 结构
- [Shared DIFF Transformer (arXiv:2501.17900)](https://arxiv.org/html/2501.17900) -- 参数共享变体
- [Vaswani et al. — Attention Is All You Need (arXiv:1706.03762)](https://arxiv.org/abs/1706.03762) -- DIFF 在其之上做相减的基线 Transformer
- [Liu et al. — Lost in the Middle (arXiv:2307.03172)](https://arxiv.org/abs/2307.03172) -- DIFF attention 所针对的长上下文 benchmark
