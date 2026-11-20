# 多 token 预测（MTP）

> 从 GPT-2 到 Llama 3，每一个自回归 LLM 在每个位置只用一个 loss 训练：预测下一个 token。DeepSeek-V3 在每个位置加了第二个 loss：预测再下一个 token。多出来的 14B 参数（在 671B 的模型上）通过梯度流蒸馏回主模型，训练好的 MTP head 在推理时被改用作接受率 80%+ 的投机解码 drafter。1.8× 的生成吞吐是白捡的。本课构建 DeepSeek 技术报告中的顺序式 MTP 模块，计算 loss 与共享头的参数布局，并解释为什么 MTP 保住了因果链，而 Gloeckle et al. 最初的并行 MTP 破坏了它。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 10 · 04 (pre-training a mini GPT), Phase 10 · 15 (speculative decoding)
**Time:** ~60 分钟
## Learning Objectives

- 陈述 MTP 的训练目标，并推导跨预测深度的联合 loss。
- 解释 Gloeckle et al. 的并行 MTP head（2024）与 DeepSeek-V3 的顺序式 MTP 模块之间的区别，以及为什么顺序式设计保住了因果链。
- 计算在一次预训练中加入 MTP 模块的参数与内存开销。
- 从零实现一个 MTP 模块：共享 embedding、逐深度的 transformer 块、投影，以及共享输出头。

## 问题场景

下一个 token 预测是标准的 LLM 训练目标。每个 hidden state 都被监督去精确预测一件事：紧接在后面的那个 token。这是一个出奇弱的信号。序列中的大部分信息都超出一个 token 之外——结构、连贯性、事实性、算术链条。模型必须靠在数万亿 token 上累积大量单 token 信号来学会这些。

MTP 在问：如果每个 hidden state 都被监督去一次预测多个未来 token 会怎样？Gloeckle et al.（Meta, 2024）表明这有帮助。他们的实现是在 backbone 之上放若干个独立的输出头，每个预测一个不同的偏移。并行、简单，但各个头看到的是同一个 hidden state，没有任何层次化的精炼——而且预测之间不构成因果链，所以不能用它们做投机解码。

DeepSeek-V3（2024 年 12 月）把 MTP 重新设计成顺序式模块，在每个预测深度上都保住因果链。模型从 `h_i^(0)` 预测 `t+1`，然后从一个新的 hidden state `h_i^(1)` 预测 `t+2`，后者把 `h_i^(0)` 与 `E(t+1)` embedding 结合起来，依此类推。每个深度都是它自己的小 transformer 块。共享 embedding 和共享输出头让参数开销保持适度。在 DeepSeek-V3 的规模上，671B 主模型权重之上，MTP 模块合计 14B 额外参数。那 2% 的开销买到了更密集的训练信号，以及推理时现成的投机解码 draft。

本课从零构建一个 MTP 模块和 D 深度的 loss。数学很干净。实现是 150 行。

## 核心概念

### 顺序式 MTP 配方

DeepSeek-V3 在主模型之上加了 `D` 个 MTP 模块。每个模块 `k`（`k = 1..D`）预测深度 `k` 上的 token——也就是给定经过位置 `i` 的 prefix，预测 `t_{i+k}`。

模块 `k` 由以下部分组成：

- 一个 transformer 块 `T_k`，有自己的 attention 和 MLP。
- 一个投影矩阵 `M_k`，把上一深度的 hidden state 与下一深度 ground-truth token 的 embedding 结合起来。
- 共享 embedding `E`（与主模型相同）。
- 共享输出头 `Out`（与主模型相同）。

训练时，对经过位置 `i` 的 prefix，逐深度的 hidden state 为：

```
h_i^(0) = main model backbone at position i
h_i^(k) = T_k( M_k * concat(RMSNorm(h_i^(k-1)), RMSNorm(E(t_{i+k}))) )   for k >= 1
```

逐深度的预测为：

```
logits_{i+k} = Out(h_i^(k-1))   for k = 1..D
```

逐深度的 loss 是对 ground-truth `t_{i+k}` 的交叉熵：

```
L_k = CE(logits_{i+k}, t_{i+k})
```

跨深度的联合 loss：

```
L_MTP = (lambda / D) * sum_{k=1..D} L_k
```

`lambda` 是一个小的加权因子——DeepSeek-V3 在训练的前 10% 用 0.3，之后用 0.1。总训练 loss 是 `L_main + L_MTP`。

### 为什么是顺序式，而不是并行

Gloeckle 最初的并行 MTP 有 D 个输出头，每个直接施加在 `h_i^(0)` 上。每个头从同一个 backbone hidden state 预测 `t_{i+k}`。这样训练没问题，但各个预测之间不以彼此为条件。你没法用 `head_1` 的输出去帮助 `head_2`——这些头是并行触发的。

DeepSeek-V3 的顺序式设计从 `h_i^(k-1)` 加上真实的下一 token embedding `E(t_{i+k})` 构建 `h_i^(k)`。这保住了因果链：为了预测 `t_{i+k+1}`，深度 `k+1` 的模块看到的是 `t_{i+k}` 处的东西。这与自回归解码器消费自己输出的方式在结构上完全相同——使 MTP 模块可以直接用作投机解码的 drafter。

推理时：把 `h_i^(k-1)` 与 draft 出的 `t_{i+k}` 喂给模块 `k+1`，得到对 `t_{i+k+1}` 的预测。重复。这正好是一个 EAGLE 风格的 draft，用训练好的 MTP 模块作为 draft 网络。DeepSeek-V3 报告第一个 MTP 模块上接受率 80%+，加速约 1.8×。

### 参数核算

对一个 hidden 为 `h`、词表为 `V` 的模型：

- 主模型：数十亿参数，外加一个大小为 `V * h` 的输出头。
- 共享输出头：复用主模型的头。没有额外参数。
- 共享 embedding：复用主模型的 embedding。没有额外参数。
- 每个 MTP 模块：
  - 投影 `M_k`：`(2h) * h = 2h^2`。
  - Transformer 块 `T_k`：attention（MHA 为 `4h^2`）加 MLP（SwiGLU 在比例 8/3 下通常是 `8h^2`）。每块约 `12h^2`。

每个模块的额外参数合计：`~14h^2`。对 DeepSeek-V3 的 `h = 7168`、D = 1 个模块：纸面上 `~14 * 7168^2 = ~720M` 参数。DeepSeek-V3 报告的是 14B——差异主要来自 MTP 模块里的专家层同样是 MoE。

### 投机解码带来的回报

预训练期间，MTP 模块让训练慢大约 10%（更多前向计算、额外 loss）。回报有两方面：

1. 更密集的训练信号。每个 hidden state 看到 D+1 个监督目标。在 MMLU、GSM8K、MATH、HumanEval 上测得的效果：在 DeepSeek-V3 的消融中有一致的小幅度百分点提升。

2. 推理时免费的投机解码 draft。MTP 模块本来就被训练来预测接下来几个 token。改用作 draft 网络，它给出 80%+ 的接受率。在这个水平上，N=3 或 N=5 的 spec decoding 带来 1.8× 吞吐。这 10% 的训练成本在你第一次跑推理时就回本了。

### 与 EAGLE 的关系

EAGLE 在预训练之后单独训练一个小 draft model。MTP 把 draft 烤进预训练。两种方法收敛到相近的接受率，但走的是不同的流水线：

| 维度 | EAGLE-3 | MTP (DeepSeek-V3) |
|-----------|---------|------------------|
| 训练时机 | 预训练之后 | 预训练期间 |
| 与已有权重向后兼容 | 是 | 否（需要重新训练） |
| Draft 参数 | 1-2 层 transformer | 1 个 transformer 块 + 投影 |
| 接受率 | 0.88-0.92 | 深度 1 时 0.80+ |
| 加速之外的收益 | 仅投机解码 | 更密集的训练信号 + 加速 |

```figure
multi-token-predict
```

## Build It

`code/main.py` 端到端构建一个 MTP 模块：共享 embedding、投影、transformer 块、共享输出头。然后它在一条短的合成序列上计算逐深度的交叉熵 loss，并按组件打印参数数量。32 个 token 的玩具词表让数字保持可读。

### 第 1 步：共享 embedding 表

一张 `vocab_size x hidden` 表同时被主模型和每个深度上的每个 MTP 模块使用。不是第二份拷贝——就是同一个张量。

### 第 2 步：逐深度的组合

```python
def combine(prev_hidden, next_token_embed, M_k):
    # concat along feature dim, then project down to hidden
    concat = rms_norm(prev_hidden) + rms_norm(next_token_embed)  # vector addition stand-in
    projected = matvec(M_k, concat)
    return projected
```

真实的 DeepSeek-V3 把两个 RMSNorm 后的向量拼成 `[2h]`，用一个 `h x 2h` 矩阵投影。玩具为了 stdlib 的简洁用向量加法代替。

### 第 3 步：深度 k 的 transformer 块

自注意力加 MLP。在玩具里，一个单层线性 attention 块和一个 SwiGLU MLP 在不使用 numpy 的情况下让结构保持可见。

### 第 4 步：共享输出头

复用主模型的输出投影。在词表上得到 logits。

### 第 5 步：逐深度 loss

softmax(logits) 对偏移 `k` 处 ground-truth token 的交叉熵。用 `lambda / D` 缩放因子跨深度聚合。

### 第 6 步：参数核算

打印总参数数量、共享部分（embedding、头）数量，以及每个模块的额外数量。展示 MTP 额外参数与主模型规模之比。

## Use It

MTP 已集成进 DeepSeek-V3（2024 年 12 月）和 DeepSeek-R1 系列。推理时：

- DeepSeek 自己的服务栈开箱即把 MTP 模块用作投机解码器。
- 截至 2026 年 4 月，vLLM 和 SGLang 都有 DeepSeek-V3 MTP 的集成路径。
- AMD 的 ROCm SGLang 教程展示了一个具体的 MTP 投机解码配置，在 V3 checkpoint 上实测 1.8× 加速。

在什么情况下应该在新预训练任务里用 MTP：

- 你掌控完整的预训练流水线，并且想攒下更密集的训练信号。
- 你知道自己会大规模服务这个模型，想要免费的投机解码。
- 你的 hidden size 至少是 4096。在 1B 规模上，开销带来的伤害大于收益带来的帮助。

什么情况下不用：

- 微调一个已有的预训练稠密模型。MTP 模块并没有被训练。
- 需要干净基线做对比的研究模型。MTP 会改变架构。

## Ship It

本课产出 `outputs/skill-mtp-planner.md`。给定一次预训练任务的规格（模型规模、数据、算力），它返回一个集成 MTP 的方案：深度数量 D、`lambda` 调度、内存开销，以及推理时的投机解码接线。

## Exercises

1. 运行 `code/main.py`。证明逐深度 loss 随合成信号增强而单调下降。修改合成数据使用一个固定模式，验证深度 1 和深度 2 的 loss 都能收敛。

2. 为一个稠密 70B 模型（hidden 8192，80 层）计算 D=1 个 MTP 模块的参数开销。与 DeepSeek-V3 报告的 14B 开销对比。解释为什么 DeepSeek 的数字更高：MTP 的 transformer 块继承了同样的 MoE 结构，抬高了每个模块的参数数量。

3. 在玩具里实现 D=2：加第二个 MTP 模块，它接收 h^(1) 并预测 `t_{i+2}`。验证联合 loss 与参数核算与 DeepSeek 论文的等式 19-21 一致。

4. 把玩具切换成并行 MTP（Gloeckle 风格）：在主 hidden state 之上加 D 个输出头，每个预测不同的偏移。在相同的合成信号上测量逐深度 loss 与顺序式版本的对比。顺序式版本应当对 k > 1 产出更低的深度 k loss，因为它以中间预测为条件。

5. 把训练好的 MTP 模块用作 EAGLE 风格的 draft：推理时调用模块 k 提出 `t_{i+k}`。在一条留出序列上测量这些 draft token 相对主模型预测的接受率。如果在玩具上达到 50%+，你就复现了 MTP 作为 draft 的实证性质。

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| MTP module | “额外 loss 块” | 一个小 transformer 块加投影，用来预测主模型前方 `k` 个位置的 token |
| Prediction depth | “哪个偏移” | 整数 `k`，即模块 `k` 从经过位置 `i` 的 prefix 预测 `t_{i+k}` |
| Parallel MTP | “Gloeckle 风格” | D 个独立的头作用在同一个 backbone hidden state 上，没有条件链 |
| Sequential MTP | “DeepSeek-V3 风格” | 每个模块以上一深度的 hidden state 加下一 token 的 embedding 为条件；保住因果链 |
| Shared output head | “复用主头” | MTP 模块调用主模型的 LM head，而不是单独的 output projection |
| Shared embedding | “复用主表” | 同一个词表 embedding 表在各处使用；没有重复参数 |
| Projection matrix M_k | “组合 hidden + next-token” | 一个 `h x 2h` 线性层，把上一 hidden state 与目标 token 的 embedding 折叠成下一深度的输入 |
| Joint loss L_MTP | “平均后的额外 loss” | 逐深度交叉熵损失的算术平均，按 `lambda` 缩放 |
| Acceptance rate at depth 1 | “MTP draft 有多经常是对的” | D=1 的 MTP 模块 top-1 预测等于主模型 top-1 预测的比率；DeepSeek-V3 上为 80%+ |
| Lambda weighting | “额外 loss 的重要性” | 逐深度缩放因子；DeepSeek-V3 上训练初期 0.3，之后 0.1 |

## Further Reading

- [DeepSeek-AI — DeepSeek-V3 Technical Report (arXiv:2412.19437)](https://arxiv.org/abs/2412.19437) -- 完整的顺序式 MTP 描述（第 2.2 节），包括联合 loss 等式与推理时的 1.8× 加速
- [Gloeckle et al. — Better & Faster Large Language Models via Multi-token Prediction (arXiv:2404.19737)](https://arxiv.org/abs/2404.19737) -- 并行 MTP 基线，DeepSeek 的设计在此基础上改进
- [DeepSeek-V3 model card on Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-V3) -- 总计 685B（671B 主模型 + 14B MTP），部署说明
- [Leviathan et al. — Fast Inference from Transformers via Speculative Decoding (arXiv:2211.17192)](https://arxiv.org/abs/2211.17192) -- MTP 所嵌入的投机解码框架
- [Li et al. — EAGLE-3 (arXiv:2503.01840)](https://arxiv.org/abs/2503.01840) -- EAGLE 2025 年的 draft 架构，MTP 所竞争的对手
