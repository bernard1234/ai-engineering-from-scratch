# Speculative Decoding 与 EAGLE

> 一个前沿 LLM 生成一个 token，需要对数十亿参数做一次完整的前向。这次前向的算力被严重超额配置：大多数时候，一个小得多的模型就能正确猜出接下来的 3-5 个 token，而大模型只需要*验证*这个猜测。猜对的时候，你用一次的代价拿到了 5 个 token。Speculative decoding（Leviathan 等 2023）让这件事变得精确，EAGLE-3（2025）把接受率推到每次验证约 4.5 个 token——在输出分布完全一致的前提下获得 4-5 倍加速。

**Type:** Build
**Languages:** Python (with numpy)
**Prerequisites:** Phase 10 Lesson 12 (Inference Optimization), Phase 10 Lesson 04 (Pre-training Mini-GPT)
**Time:** ~75 分钟

## 问题场景

70B 级模型在 H100 上的解码吞吐通常是 40-80 token/秒。每个 token 都需要一次完整的前向，从 HBM 读取全部模型权重。不改输出你就没法让模型变小。批大小受显存限制也没法再增大。你被卡住了——除非你能让模型在一次前向中输出不止一个 token。

自回归生成看起来本质上是串行的：`x_{t+1} = sample(p(· | x_{1:t}))`。但这里存在一个并发的机会。如果你有一个廉价的预测器说“接下来 4 个 token 大概是 [a, b, c, d]”，你就可以在**大模型的单次前向**中验证全部 5 个位置，并接受匹配的最长前缀。

Leviathan、Kalai、Matias（2023，"Fast Inference from Transformers via Speculative Decoding"）通过一个巧妙的接受/拒绝规则让这件事变得精确，同时保持目标模型的采样分布不变。相同的输出分布，快 2-4×。

## 核心概念

### 双模型设置

- **目标模型** `M_p`：你真正想从中采样的大、慢、高质量的模型。分布：`p(x)`。
- **草稿模型** `M_q`：一个小、快、质量较低的模型。分布：`q(x)`。小 5-30×。

每一步：

1. 草稿模型自回归地提出 `K` 个 token：`x_1, x_2, ..., x_K ~ q`。
2. 目标模型对全部 `K+1` 个位置并行跑**一次**前向，为每个被提出的 token 产出 `p(x_k)`。
3. 通过下面改进后的拒绝采样规则，从左到右逐个接受/拒绝。接受匹配的最长前缀。
4. 若有任何 token 被拒绝，就从修正后的分布中采样替代 token 并停止。否则从 `p(· | x_1...x_K)` 中采样一个奖励 token。

如果草稿与目标完全一致，你每次目标前向得到 K+1 个 token。如果草稿在第 1 个位置就错了，你只能得到 1 个 token。

### 精确性规则

Speculative decoding 在分布上**可证明等价于从 p 采样**。拒绝规则：

```
For each drafted token x_t:
    r ~ Uniform(0, 1)
    if r < p(x_t) / q(x_t):
        accept x_t
    else:
        sample replacement from residual: (p - q)+ / ||(p - q)+||_1
        stop
```

其中 `(p - q)+` 表示逐点差的正部。当草稿与目标一致（`p ≈ q`）时，接受率接近 1。当它们不一致时，残差分布的构造保证了整体采样仍然精确地服从 `p`。

**贪心情形。** 对 temperature=0 的采样，只需检查 `argmax(p) == x_t`。是则接受；否则输出 `argmax(p)` 并停止。

### 预期加速比

如果草稿模型在 token 级别的接受率是 `α`，每次目标前向预期的产出 token 数为：

```
E[tokens] = (1 - α^{K+1}) / (1 - α)        # K = draft length, α in [0, 1]
```

在 `α = 0.8, K = 4` 时：`(1 - 0.8^5)/(1 - 0.8) = 3.36` 个 token 每次前向。一次目标前向的成本大致是 `cost_q * K + cost_p`（K 个草稿步加一次目标验证）。若 `cost_p >> cost_q * K`，吞吐上的加速比就是 `3.36× / 1 = 3.36×`。

唯一真正的参数是 `α`，它完全取决于草稿与目标的对齐程度。一个好的草稿就是一切。

### 训练草稿：蒸馏

随机的小模型是很差的草稿。标准配方是从目标模型蒸馏：

1. 选一个小架构（70B 目标配 ~1B，7B 目标配 ~500M）。
2. 在大型文本语料上运行目标模型；保存它的下一 token 分布。
3. 用 KL 散度训练草稿，对齐目标的分布（而不是对齐真实 token）。

结果：编码任务上 `α` 通常为 0.6-0.8，自然语言聊天上为 0.7-0.85。生产中加速 2-3×。

### EAGLE：树状草稿 + 特征复用

Li、Wei、Zhang、Zhang（2024，"EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty"）观察到标准 speculative decoding 中的两处低效：

1. 草稿要做 K 个串行步，每步都是全栈的。但草稿本可以复用最近一次验证时目标的特征（hidden state）——目标已经算出了丰富的表示，而草稿却要从头重新推导。
2. 草稿输出一条线性链。如果草稿能输出一棵候选*树*（每个节点有多个猜测），目标的单次前向就能通过树形 attention mask 并行验证多条候选路径，并挑出被接受的最长分支。

EAGLE-1 的改动：
- 草稿输入 = 目标在位置 t 的最终 hidden state，而不是原始 token。
- 草稿架构 = 1 个 transformer decoder 层（而不是一个独立的小模型）。
- 输出 = 每层深度 K = 4-8 个候选组成的树，深度 4-6。

EAGLE-2（2024）加入动态树拓扑：在草稿不确定的地方树长得更宽，在它自信的地方保持窄。在不增加验证成本的前提下提高 `α_effective`。

EAGLE-3（Li 等 2025，"EAGLE-3: Scaling up Inference Acceleration of Large Language Models via Training-Time Test"）去掉了对固定顶层特征的依赖，用一种新的“测试时模拟”损失来训练草稿——草稿是在匹配目标测试时分布的输出上训练的，而不是在 teacher-forced 训练分布上。接受率从 0.75（EAGLE-2）升到 0.82（EAGLE-3），平均 tokens/verify 从 3.0 升到 4.5。

### 树形 attention 验证

当草稿输出一棵树时，目标模型用**树形 attention mask** 在一次前向中完成验证——这是一个编码了树拓扑而非纯线性结构的因果 mask。每个 token 只关注它在树中的祖先。验证这一遍仍然是一次前向、一次 matmul；拓扑 mask 只多花几个 KV 条目。

```
        root
       /    \
      a      b
     / \    / \
    c  d   e   f
```

如果 `a, b` 是竞争的首 token 候选，`c, d, e, f` 是次 token 候选，那么全部六个位置都在一次前向中验证完毕。输出是任一被接受路径上的最长前缀。

### 何时赢，何时不赢

**赢：**
- 文本可预测的聊天 / 补全（代码、常见英语、结构化输出）。`α` 很高。
- 解码时有闲置 GPU 算力的场景（memory-bound 阶段）。树状草稿用上了可用的 FLOPs。

**不赢 / 没有收益：**
- 高度随机的输出（高温下的创意写作）。`α` 会跌向 `1/|vocab|`。
- 并发度极高的批量服务——批处理已经填满了 FLOPs，树验证没有多少空间。
- 目标模型本身很小，草稿也没小多少。

生产环境通常报告：聊天场景 2-3× 墙钟加速，代码生成 3-5×，创意写作上接近于零。

```figure
speculative-decoding
```

## Build It

`code/main.py`：

- 一个参考实现 `speculative_decode(target, draft, prompt, K, temperature)`，实现精确的拒绝规则，并验证它保持了目标的分布（与朴素目标采样相比经验 KL < 0.01）。
- 一个 EAGLE 风格的树状草稿器，用 top-p 分支构建深度为 K 的树。
- 一个树形 attention mask 构建器，为验证器产出正确的因果模式。
- 一个接受率测试框架，在一个很小的 LM 上跑两者（从 GPT-2-medium 目标蒸馏出一个 GPT-2-small）。

```python
def speculative_step(p_target, q_draft, K, temperature=1.0):
    """One round of speculative decoding. Returns list of accepted tokens."""
    # 1. Draft K tokens
    draft_tokens = []
    q_probs = []
    state = draft_state_init()
    for _ in range(K):
        probs = softmax(q_draft(state) / temperature)
        t = np.random.choice(len(probs), p=probs)
        draft_tokens.append(t)
        q_probs.append(probs[t])
        state = draft_step(state, t)

    # 2. Target computes p at every drafted position + 1 extra
    p_probs_all = target_forward_batched(p_target, draft_tokens, temperature)

    # 3. Accept/reject left-to-right
    accepted = []
    for k, tok in enumerate(draft_tokens):
        r = np.random.uniform()
        if r < p_probs_all[k][tok] / q_probs[k]:
            accepted.append(tok)
        else:
            residual = np.maximum(p_probs_all[k] - q_probs[k], 0)
            residual /= residual.sum()
            accepted.append(np.random.choice(len(residual), p=residual))
            return accepted
    # 4. All K accepted → sample bonus token from target
    accepted.append(np.random.choice(len(p_probs_all[-1]), p=p_probs_all[-1]))
    return accepted
```

## Use It

- **vLLM** 和 **SGLang** 原生提供 speculative decoding。在 vLLM 中，给 `--speculative-config` 传一个包含 `method`、`model` 和 `num_speculative_tokens` 的 JSON 对象；EAGLE-3 是 `"method": "eagle3"`。
- **NVIDIA TensorRT-LLM** 原生支持 Medusa 与 EAGLE 树。
- **参考草稿模型**：`Qwen/Qwen3-0.6B`（为 Qwen3-32B 做草稿），`meta-llama/Llama-3.2-1B-Instruct`（为 Llama 3.x 70B 做草稿）。
- **Medusa 头**（Cai 等 2024，"Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads"）：不用草稿模型，而是给目标模型本身加上 K 个并行预测头。部署更简单，接受率略低于 EAGLE。

## Ship It

本课产出 `outputs/skill-speculative-tuning.md`——一个技能，它对目标模型的工作负载做剖析，并选择：草稿模型、K（草稿长度）、树宽、temperature，以及何时回退到普通解码。

## Exercises

1. 实现精确的拒绝规则并用实验验证它。通过 `speculative_decode` 和朴素目标采样各跑 10K 个样本；计算两个输出分布之间的 TV 距离。应当 < 0.01。

2. 推导加速比公式。给定固定的 `α` 和 `K`，画出每次目标前向的预期 token 数。为 α ∈ {0.5, 0.7, 0.9} 找出最优 K。

3. 训练一个微型草稿。拿一个 124M 的 GPT-2 目标，在 100M token 上用 KL 损失蒸馏出一个 30M 的 GPT-2 草稿。在留出文本上测量 `α`。预期：0.6-0.7。

4. 实现 EAGLE 风格的树状草稿。不是链，而是让草稿在每一深度输出 top-3 分支。构建树形 attention mask。验证目标接受了最长正确分支。

5. 测量失败模式。在 temperature=1.5（高随机性）下运行 speculative decode。显示 α 崩溃，且由于草稿开销，算法比普通解码更慢。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|-----------------|------------------------|
| Target model | “那个大模型” | 你希望从中采样的慢而高质量的模型（p 分布） |
| Draft model | “投机者” | 小而快的预测器（q 分布）；小 5-30 倍 |
| K / draft length | “前瞻长度” | 每次验证前向推测的 token 数 |
| α / acceptance rate | “命中率” | 草稿提议被接受的逐 token 概率 |
| Exact rejection rule | “接受测试” | 保持目标分布的 r < p/q 比较 |
| Residual distribution | “修正后的 p-q” | (p - q)+ / ||(p - q)+||_1，被拒绝时用来采样的分布 |
| Tree drafting | “分支投机” | 草稿输出一棵候选树，用树结构 attention mask 一次验证 |
| Tree attention mask | “拓扑 mask” | 编码树拓扑的因果 mask，使每个节点只关注自己的祖先 |
| Medusa heads | “并行头” | 目标模型自身上的 K 个额外预测头；不需要独立的草稿模型 |
| EAGLE feature reuse | “hidden state 草稿” | 草稿输入是目标的最后 hidden state 而非原始 token，从而缩小草稿 |
| Test-time simulation loss | “EAGLE-3 训练” | 在与目标测试时分布匹配的输出上训练草稿，而非 teacher forcing |

## Further Reading

- [Leviathan, Kalai, Matias, 2023 — "Fast Inference from Transformers via Speculative Decoding"](https://arxiv.org/abs/2211.17192) —— 精确拒绝规则与理论加速分析
- [Chen, Borgeaud, Irving et al., 2023 — "Accelerating Large Language Model Decoding with Speculative Sampling"](https://arxiv.org/abs/2302.01318) —— DeepMind 的并行 speculative-sampling 论文
- [Cai, Li, Geng, Wang, Wang, Zhu, Dao, 2024 — "Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads"](https://arxiv.org/abs/2401.10774) —— 替代草稿模型的并行头方案
- [Li, Wei, Zhang, Zhang, 2024 — "EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty"](https://arxiv.org/abs/2401.15077) —— 特征复用与树状草稿
- [Li et al., 2024 — "EAGLE-2: Faster Inference of Language Models with Dynamic Draft Trees"](https://arxiv.org/abs/2406.16858) —— 动态树拓扑
- [Li et al., 2025 — "EAGLE-3: Scaling up Inference Acceleration of Large Language Models via Training-Time Test"](https://arxiv.org/abs/2503.01840) —— 训练时与测试时分布的对齐
- [Fu, Haotian, Peng et al., 2024 — "Break the Sequential Dependency of LLM Inference Using Lookahead Decoding"](https://arxiv.org/abs/2402.02057) —— Jacobi/lookahead 解码，一种无需投机器的替代方案
