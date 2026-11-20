# 投机解码与 EAGLE-3

> Phase 7 · Lesson 16 已经证明了数学：Leviathan rejection rule 精确保留 verifier 的分布。本课是从训练栈视角看 2026 年生产环境的 speculative decoding。EAGLE-3 把 draft model 从一个廉价的近似变成了一个专门打造的小网络，在 verifier 自己的 hidden states 上训练，随后加入一个 training-time test 循环，让它的训练分布与推理分布对齐。结果：端到端 3× 到 6.5× 加速，聊天场景下每 token 的接受率高于 0.9，没有任何分布上的让步。2026 年每一个生产推理栈都默认搭载它。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 7 · 16 (speculative decoding math), Phase 10 · 12 (inference optimization)
**Time:** ~75 分钟
## Learning Objectives

- 用一句话陈述 Leviathan 定理，并证明投机循环产出的样本与 verifier 的分布相同。
- 梳理从 vanilla spec-decoding（Leviathan 2023）到 EAGLE、EAGLE-2、EAGLE-3 的两年演进，并指出每一步消除了哪个确切的局限。
- 根据接受率 `α` 与 draft 对 verifier 的成本比 `c` 计算期望加速，并为每种情形选择最优 draft 长度 `N`。
- 从零实现完整的投机循环：draft、verify、从残差中拒绝采样、拒绝时回滚 KV cache、完全接受时发出 bonus token。

## 问题场景

在 H100 上，70B 模型的自回归解码大概每秒跑 35 个 token。GPU 远远没有跑满。天花板是内存带宽：每生成一个 token，都要从 HBM 加载 70B 的权重，做一步算术，产出一个浮点数。计算单元大部分时间都空着。

speculative decoding 把它变成一个你真正可以解决的吞吐问题。一个廉价的 draft 用 `N` 次小的前向传播提出 `N` 个 token。verifier 在 prefix 加上全部 `N` 个 draft 上跑一次。如果 verifier 在位置 `i` 的分布与 draft 一致（一种我们即将精确定义的统计意义上的“一致”），我们就接受；如果不一致，我们就拒绝，并从残差分布中采样一个修正。一次大模型前向最多产出 `N+1` 个被接受的 token，而不是一个。

真正重要的定理是 Leviathan、Kalman、Matias（ICML 2023）：输出分布与直接从 verifier 采样所得到的分布完全相同。不是近似。是完全相同。这正是 speculative decoding 在生产中可被接受的全部理由——它是一种纯粹的延迟优化，没有质量权衡。

Phase 7 · Lesson 16 给你的是数学。本课给你的是训练栈。一个好的 draft 带来的加速是廉价 draft 的两倍多。EAGLE、EAGLE-2 和 EAGLE-3（Li et al., 2024–2025）把“draft = 同一个模型的更小版本”变成了精确的工程学科。2026 年的生产推理服务器默认用 EAGLE-3。

## 核心概念

### 不变量：Leviathan rejection sampling

令 `p(t)` 为 draft 在给定某个 prefix 时对下一个 token 的分布，`q(t)` 为 verifier 的分布。采样一个 draft token `d ~ p`。以概率 `min(1, q(d) / p(d))` 接受。若被拒绝，则从残差分布 `(q - p)_+ / ||(q - p)_+||_1` 中采样。所得样本按 `q` 分布。无论 `p` 有多差，这一点都成立——它越差，你拒绝得越频繁，但输出依然精确。

把 `N` 次这样的调用首尾相接，用一次 verifier 在 `prefix + d_1 + ... + d_N` 上的前向传播来堆叠。verifier 同时返回 `q_1, q_2, ..., q_{N+1}`。从左往右走。在位置 `j` 遇到第一次拒绝时，从 `residual(q_j, p_j)` 采样并停止。如果全部接受，则从 `q_{N+1}` 再采样一个 bonus token。

### 什么决定了加速比

令 `α` 为每个 draft token 的期望接受率。令 `c = cost(draft) / cost(verifier)` 为成本比。每次 verifier 前向的期望接受 token 数为：

```
E[accepted] = (1 - α^(N+1)) / (1 - α)
```

每个被接受 token 的期望总墙钟时间是 `(N * c + 1) / E[accepted]`。对 `N` 最小化它，就得到最佳点。对 `α = 0.8, c = 0.05`：最优 `N` 大约在 5–7，加速 3.2×。对 `α = 0.95, c = 0.02`：最优 `N` 大约在 8–10，加速逼近 5×。

最大的杠杆是 `α`。从 `α = 0.6`（vanilla draft）提升到 `α = 0.9`（EAGLE-3），在固定 `N = 5` 下，每次 verifier 前向的期望接受 token 数从 2.2 变成 4.1。同一个 verifier，吞吐接近翻倍。

### 两年的演进

**Vanilla 投机解码（Leviathan, 2023）。** draft model 是同族中独立训练的较小 LLM。接线容易，`α ≈ 0.6`，加速最好也就 2× 左右。

**EAGLE-1（Li et al., 2024）。** draft 是一个极小的 transformer——通常只有一到两层——它以 verifier 最后一层的 hidden state 作为输入，直接预测下一个 token。因为 draft 看到的是 verifier 的特征表示，它的分布与 verifier 的接近得多。`α` 爬升到 0.7–0.8。

**EAGLE-2（Li et al., 2024）。** 加入动态 draft 树：不再提出 `N` 个 token 的单条序列，而是提出一棵小的候选树，用一次 verifier 前向（tree attention）给每个候选打分，然后走概率最高的那条路径。draft 长度按步自适应。每个被接受路径 token 的 `α` 升到 0.85 以上。

**EAGLE-3（Li et al., 2025, NeurIPS）。** 又有两处改动。第一，彻底去掉 feature-prediction loss——EAGLE-1/2 训练 draft 去匹配 verifier 的 hidden states，这限制了数据能带来多少收益。EAGLE-3 直接在 token 预测上训练。第二，training-time test（TTT）：在 draft 训练期间，把 draft 自己之前的预测在多个步上回灌为输入，与它在推理时的运行方式相同。这对齐了训练分布与测试分布，并阻止误差累积。实测加速：聊天场景最高 6.5×，在 H100 上 SGLang 中 batch 64 时吞吐提升 38%。

### KV cache rollback

校验会在一次传播中把 verifier 的 KV cache 扩展 `N` 个条目。如果拒绝发生在位置 `j`，那么位置 `j-1` 之后的 cache 内容就是错的。两种常见实现：写入一个 scratch buffer，接受时再提交（vLLM、TensorRT-LLM）；或者保留一份物理 KV cache 加一个逻辑长度，拒绝时截断。无论哪种，回滚成本都是每层每头的字节数，相对前向传播的成本可以忽略。

对于 EAGLE-2 的树搜索，verifier 用尊重树拓扑的非因果 mask 跑 attention。工程上琐碎烦人，但计算本身是一次带自定义 mask 的标准 flash-attention 调用。

### 2026 年的 draft 架构

| 策略 | draft 类型 | `α` | 加速比 | 训练成本 |
|----------|-----------|-----|---------|---------------|
| Vanilla | 独立的小型 LLM | 0.55-0.70 | 1.8-2.3× | 无（复用已有的小模型） |
| Medusa | 在 verifier 上加额外的 LM head | 0.65-0.75 | 2-3× | ~1B SFT tokens |
| EAGLE-1 | 在 hidden states 上的 1 层 transformer | 0.70-0.80 | 2.5-3× | ~60B tokens |
| EAGLE-2 | EAGLE-1 + 动态 draft 树 | 0.80-0.88 | 3-4× | ~60B tokens |
| EAGLE-3 | 多层特征融合 + TTT | 0.88-0.92 | 3.5-6.5× | ~60-200B tokens |
| Lookahead | 无 draft（Jacobi 迭代） | N/A | 1.3-1.6× | 无 |

2026 年的生产状况：只要有 EAGLE-3，vLLM 和 SGLang 就默认用它，否则用 EAGLE-2。TensorRT-LLM 对 Meta 和 NVIDIA 的公开模型有最快的 Medusa 路径。llama.cpp 为 CPU 部署提供 vanilla draft。

```figure
l5-spec-decode-eagle
```

## Build It

参见 `code/main.py`。这是完整的 Leviathan 投机循环，所有部件都在：draft-of-N、verifier 并行前向、逐位置拒绝、残差采样、bonus token、KV 回滚，以及对输出分布与直接从 `q` 采样一致的实证校验。

### 第 1 步：拒绝规则

```python
def accept(q_prob, p_prob, u):
    if p_prob <= 0:
        return True
    return u < min(1.0, q_prob / p_prob)
```

### 第 2 步：残差分布

```python
def residual(q, p):
    raw = [max(0.0, qi - pi) for qi, pi in zip(q, p)]
    s = sum(raw)
    if s == 0:
        return list(q)
    return [r / s for r in raw]
```

### 第 3 步：一次完整的投机步

`spec_step` 函数从 `p` draft 出 `N` 个 token，然后用一次并行的 `q` 评估校验全部。对每个 draft token 应用拒绝规则，在第一次拒绝时从残差中采样修正。如果全部接受，它从 `q_{N+1}` 发出一个 bonus token。

### 第 4 步：KV rollback 的簿记

模拟器为每个 worker 跟踪一个逻辑 `kv_length`。接受 `k` 个 draft 时，`kv_length += k`。在位置 `j` 拒绝时，cache 已经写过了 `j`，但逻辑长度被设为 `prefix_length + j + 1`——修正 token 的后一位。后续读取都截断到逻辑长度。

### 第 5 步：Leviathan 校验

跑 50,000 个投机步。统计被接受 token 的经验分布。与 50,000 个来自 `q` 的直接样本对比。卡方统计量应当远低于临界值。定理在实践中通过。

### 第 6 步：加速比 vs. α

通过以不同幅度把 `p` 从 `q` 扰动开来，扫描 draft 质量。测量 `α`，然后画出每次 verifier 调用的期望 token 数作为 `α` 与 `N` 的函数。代码会打印一张表，展示 EAGLE-3 级别的 draft 质量（`α ≈ 0.9`）如何解锁每次 verifier 调用 4–5 个 token。

## Use It

生产级的 `vllm serve`，配 EAGLE-3：

```bash
vllm serve meta-llama/Llama-3.3-70B-Instruct \
  --speculative-config '{
    "model": "yuhuili/EAGLE3-LLaMA3.3-Instruct-70B",
    "num_speculative_tokens": 5,
    "method": "eagle3"
  }'
```

在 H100 上用 EAGLE-3、batch 64 的 SGLang：按 EAGLE-3 论文，吞吐比 batch 64 的 vanilla 解码大约高 1.38×。

什么时候该用 speculative decoding：

- 任何交互式聊天负载，p50 延迟比峰值吞吐更重要。
- 代码生成与结构化输出（JSON、SQL）。`α` 高于 0.9，因为目标分布高度可预测。
- 长文生成（数千 token）。摊销后的加速会一直给你回报。

什么时候不该用：

- 非常小的模型（< 3B）。draft 并不比 verifier 便宜多少。
- 很小的 batch-1 CPU 部署。draft 模型的内存开销可能不划算。
- 温度很高的创造性采样，`α` 会崩掉。

## Ship It

本课产出 `outputs/skill-eagle3-tuner.md`。给定一个推理负载（模型、batch size、目标延迟、任务画像），它推荐一种 speculative-decoding 策略和调参参数（draft 家族、`N`、树深度、温度感知切换）。

## Exercises

1. 运行 `code/main.py`。确认 Leviathan 分布校验的卡方统计量在 50,000 个样本上保持在 95% 临界值以下。

2. 在 `α` 固定为 0.9、`c` 固定为 0.04 的情况下，把 `N` 从 1 扫到 10。画出每次 verifier 调用的期望 token 数与每个 token 的实际墙钟时间。找出使墙钟时间最小的 `N`。解释曲线的形状。

3. 修改代码以模拟 EAGLE-2 树搜索：每一步 draft 提出形状为 `[2, 2, 2]` 的树（八条候选路径）。verifier 跑一次，概率最高的被接受路径胜出。计算每个叶子的 `α` 以及每次 verifier 调用的总 token 数。与同等计算量下的线性链 spec-decoding 对比。

4. 为两条并发序列实现一个批处理的 KV 回滚模拟器。序列 A 的 draft 全部被接受；序列 B 在位置 2 被拒绝。说明正确的 `kv_length` 是按序列更新的，且没有工作被浪费。

5. 读 EAGLE-3 论文的第 4 节（Training-Time Test）。用两句话解释为什么没有 TTT 的朴素 draft 训练会遭遇 exposure bias，以及为什么在训练中把 draft 自己的预测回灌给它能修复这个问题。把它与 seq2seq 中的 scheduled-sampling 文献联系起来。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Leviathan rule | “min(1, q over p)” | 以概率 `min(1, q(d)/p(d))` 做伯努利接受/拒绝，在拒绝时从残差采样，从而精确保留 verifier 的分布 |
| Residual distribution | “(q minus p) plus, normalized” | `(q - p)_+` 在零处截断再归一化——拒绝时应当采样的正确分布 |
| Acceptance rate α | “draft 有多经常是对的” | 拒绝规则下每 token 伯努利成功的期望概率；支配全部加速数学 |
| EAGLE-1 | “hidden-state draft” | 以 verifier 最后一层 hidden state 为条件的极小 transformer draft（Li et al., 2024） |
| EAGLE-2 | “动态 draft 树” | EAGLE-1 加一棵候选续写树，用一次 verifier 传播中的 tree attention 打分 |
| EAGLE-3 | “training-time test” | 去掉 feature-prediction loss，直接在 token 预测上训练，并在训练中把 draft 自己的输出回灌给它 |
| Training-time test (TTT) | “exposure bias 修复” | 训练时让 draft 自回归地运行，使训练与测试的输入分布一致——scheduled sampling 的直接对应物 |
| KV rollback | “撤销被拒绝的 draft” | 在拒绝后把 verifier 的 KV cache 重置到已接受 prefix 长度的簿记 |
| Bonus token | “白捡的那个” | 当 `N` 个 draft 全部被接受时，从 `q_{N+1}` 额外采样一个，不额外花 verifier 成本 |
| Tree attention | “一次校验很多候选” | 带非因果 mask、尊重 draft 树拓扑的 attention；一次前向就为树中每个节点算出 `q_i` |

## Further Reading

- [Leviathan, Kalman, Matias — Fast Inference from Transformers via Speculative Decoding (arXiv:2211.17192, ICML 2023)](https://arxiv.org/abs/2211.17192) -- 奠基性论文与等价性定理
- [Chen et al. — Accelerating Large Language Model Decoding with Speculative Sampling (arXiv:2302.01318)](https://arxiv.org/abs/2302.01318) -- 同期独立提出，附一份简洁的证明
- [Li et al. — EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty (arXiv:2401.15077)](https://arxiv.org/abs/2401.15077) -- EAGLE-1，以 hidden state 为条件的 draft
- [Li et al. — EAGLE-2: Faster Inference of Language Models with Dynamic Draft Trees (arXiv:2406.16858)](https://arxiv.org/abs/2406.16858) -- 动态树搜索
- [Li et al. — EAGLE-3: Scaling up Inference Acceleration via Training-Time Test (arXiv:2503.01840, NeurIPS 2025)](https://arxiv.org/abs/2503.01840) -- 2026 年的生产默认方案
- [Cai et al. — Medusa: Multiple Decoding Heads (arXiv:2401.10774)](https://arxiv.org/abs/2401.10774) -- 另一种无 draft 方案
- [vLLM Speculative Decoding documentation](https://docs.vllm.ai/en/latest/features/spec_decode.html) -- 权威生产参考，所有策略都已接好
