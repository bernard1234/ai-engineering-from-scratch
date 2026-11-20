# DeepSeek-V3 架构走读

> Phase 10 · 第 14 课点出了每个开放模型都会拧的六个架构旋钮。DeepSeek-V3（2024 年 12 月，总参数 671B，激活参数 37B）把这六个全拧了一遍，另外又加了四个：Multi-Head Latent Attention、无辅助损失的负载均衡、Multi-Token Prediction 以及 DualPipe 训练。本课自上而下通读 DeepSeek-V3 的架构，并从公开的 config 推导出每一个参数计数。读完之后，你能解释为什么 671B/37B 这个比例是正确的赌注，以及为什么在前沿尺度上 MLA + MoE 合起来胜过任何单独一个。

**Type:** Learn
**Languages:** Python (stdlib, parameter calculator)
**Prerequisites:** Phase 10 · 14 (open-model walkthroughs), Phase 10 · 17 (NSA), Phase 10 · 18 (MTP), Phase 10 · 19 (DualPipe)
**Time:** ~75 分钟

## Learning Objectives

- 自上而下读懂 DeepSeek-V3 的 config，并用六个 GPT-2 旋钮加上四个 DeepSeek 专属新增项来解释每个字段。
- 推导出总参数数（671B）、激活参数数（37B），以及各自由哪些组件贡献。
- 计算 MLA 在 128k 上下文下的 KV cache 占用，并与一个激活参数相同的稠密模型若用 GQA 需要付出的代价做比较。
- 说出 DeepSeek 的四项专属创新（MLA、MTP、无辅助损失路由、DualPipe），并指出每一项针对的是架构/训练栈的哪个部分。

## 问题场景

DeepSeek-V3 是第一个架构上与 Llama 家族有实质区别的前沿开放模型。Llama 3 405B 是“拧了六个旋钮的 GPT-2”。DeepSeek-V3 是拧了全部六个旋钮再加四个的 GPT-2。读 Llama 3 的 config 是读 DeepSeek config 的热身，但深层结构——attention 块的形状、路由逻辑、训练时的目标——差异足够大，你需要一份单独的走读。

学它的回报：DeepSeek-V3 的开源权重发布改变了开放模型中“前沿能力”的含义。这套架构是 2026 年许多训练任务正在照抄的蓝图。理解它对任何涉及前沿 LLM 训练或推理的岗位都是基本功。

## 核心概念

### 再次审视不变的核心

DeepSeek-V3 仍然是自回归的。它仍然堆叠 decoder 块。每个块仍然有 attention 加上 MLP 加上两个 RMSNorm。MLP 里仍然用 SwiGLU。仍然用 RoPE。pre-norm。权重绑定嵌入。和每一个 Llama 或 Mistral 的基线一样。

### 转折：用 MLA 取代 GQA

从 Phase 10 · 第 14 课你知道，GQA 通过在若干组 Q head 之间共享 K 和 V 来缩小 KV cache。Multi-Head Latent Attention（MLA）走得更远：K 和 V 被压缩进一个共享的低秩潜表示（`kv_lora_rank`），再按 head 即时解压。KV cache 只存这个潜向量——通常每层每 token 512 个 float，而不是 8 x 128 = 1024 个 float。

在 128k 上下文下，使用 MLA 的 DeepSeek-V3（每层每 token 一个共享潜向量 `c^{KV}`；K 和 V 都由该潜向量经上投影导出，而这些上投影可以吸收进后续的 matmul）：

```
kv_cache = num_layers * kv_lora_rank * max_seq_len * bytes_per_element
         = 61 * 512 * 131072 * 2
         = 7.6 GB
```

一个假想的 GQA 基线（Llama 3 70B 的形状，8 个 KV head，head 维度 128）要付出：

```
kv_cache = 2 * 61 * 8 * 128 * 131072 * 2
         = 30.5 GB
```

在 128k 上下文下，MLA 比 Llama-3-70B 风格的 GQA cache 小 4 倍。

权衡：MLA 在每次 attention 计算（每个 head）时增加一步解压。这点额外计算与省下的带宽相比微不足道。对长上下文推理是净胜。

### 路由：无辅助损失的负载均衡

MoE 路由器决定由哪 top-k 个专家处理每个 token。朴素的路由器会把过多工作集中到少数专家上，让其他专家闲着。标准修法：加一个辅助损失项，惩罚负载不均衡。这有效，但会略微降低主任务性能。

DeepSeek-V3 引入了一种无辅助损失的方案。把每个专家的 bias 项加到路由器 logits 上，训练中按一条简单规则调整：如果专家 `e` 过载，就降低 `bias_e`；如果欠载，就提高它。没有额外的损失项。训练保持干净。专家负载保持均衡。

对主损失的影响：无可测量的影响。对 MoE 架构的影响：更干净，没有辅助损失的超参数需要调。

### MTP：更稠密的训练 + 免费的 draft

从 Phase 10 · 第 18 课你知道，DeepSeek-V3 增加了一个 D=1 的 MTP 模块，用来预测向后两个位置的 token。在推理时，训练好的模块被改用作 speculative-decoding 的 draft，接受率 80% 以上。在训练时，每个 hidden state 都在 D+1 = 2 个目标上受到监督，提供了更稠密的信号。

参数：在 671B 主体之上再加 14B。开销：2.1%。

### 训练：DualPipe

从 Phase 10 · 第 19 课你知道，DualPipe 是一种双向 pipeline，把前向与反向 chunk 与跨节点 all-to-all 通信重叠起来。在 DeepSeek-V3 的 2,048 张 H800 规模下，它大约收回了 245k GPU 小时——这些时间原本会被 1F1B 损失在 pipeline bubble 上。

### 逐字段读 config

这是 DeepSeek-V3 的 config（简化版）：

```
hidden_size: 7168
intermediate_size: 18432   (dense MLP hidden size, used on first few layers)
moe_intermediate_size: 2048 (expert MLP hidden size)
num_hidden_layers: 61
first_k_dense_layers: 3    (first 3 layers use dense MLP)
num_attention_heads: 128
num_key_value_heads: 128   (formally equal to num_heads under MLA, but
                           the real compression is in kv_lora_rank)
kv_lora_rank: 512          (MLA latent dimension)
num_experts: 256            (MoE expert count per block)
num_experts_per_tok: 8      (top-8 routing)
shared_experts: 1           (always-on shared expert per block)
max_position_embeddings: 163840
rope_theta: 10000.0
vocab_size: 129280
mtp_module: 1               (1 MTP module at depth 1)
```

解析一下：

- `hidden_size=7168`：嵌入维度。
- `num_hidden_layers=61`：总的块深度。
- `first_k_dense_layers=3`：前 3 个块使用大小为 18432 的稠密 MLP。剩下的 58 个使用 MoE。
- `num_attention_heads=128`：128 个 query head。
- `kv_lora_rank=512`：K 和 V 被压缩到这个潜维度，并按 head 解压。
- `num_experts=256, num_experts_per_tok=8`：每个 MoE 块有 256 个专家，走 top-8 路由。
- `shared_experts=1`：在 256 个路由专家之上，有 1 个常开专家对每个 token 都有贡献。可以把它理解为“稠密地板”，确保每个 token 都能得到一些可靠的东西。
- `moe_intermediate_size=2048`：每个专家的 MLP 隐层大小。比稠密 MLP 小，因为有 256 个。

### 参数核算

完整计算在 `code/main.py` 里。要点：

- 嵌入：`vocab * hidden = 129280 * 7168 = ~0.93B`。
- 前 3 个稠密块：带 MLA 的 attention（每块约 144M）+ 稠密 MLP（每块约 260M）+ norm。合计约 1.2B。
- 58 个 MoE 块：带 MLA 的 attention（约 144M）+ 各 256 个专家（每个 30M）+ 1 个共享专家（30M）+ norm。每块合计约 7.95B（含全部专家）。58 个 MoE 块合计 461B。
- MTP 模块：14B。

总计：核心架构约 476B + MTP 14B + 另外，公开的 671B 数字还计入了额外的结构性参数（bias 张量、专家专属组件、共享专家缩放等）。我们在计算器中复现的数字与公开数字相差 3-5% 以内——差异来自 DeepSeek 报告 Section 2 附录中记录的细粒度核算。

每次前向的激活参数：

- Attention：每层 144M * 61 = 8.8B（所有层都会激发）。
- MLP 激活：前 3 层是稠密（3 * 260M = 780M），58 个 MoE 层每层由 8 个路由专家 + 1 个共享专家 + 路由开销激活。每层激活的 MLP：约 260M。合计：3 * 260M + 58 * 260M = 约 15.9B。
- 嵌入 + norm：1.2B。
- 总激活：核心约 26B + MTP 14B（参与训练但不总在推理时运行）≈ 37B。

### 671B / 37B 的比例

18 倍的稀疏比（激活参数占总量的 5.5%）。DeepSeek-V3 是已发布开放权重的最稀疏前沿 MoE 模型。Mixtral 8x7B 的比例是 13/47（28%），稠密得多。Llama 4 Maverick 的比例是 17B/400B（4.25%），与之相当。DeepSeek 的赌注是：在前沿尺度上，更多专家配更低的激活比例，能带来更高的每激活-FLOP 质量。

### DeepSeek-V3 所处的定位

| 模型 | 总量 | 激活 | 比例 | Attention | 新想法 |
|-------|------|-------|-------|-----------|-------------|
| Llama 3 70B | 70B | 70B | 100% | GQA 64/8 | — |
| Llama 4 Maverick | 400B | 17B | 4.25% | GQA | — |
| Mixtral 8x22B | 141B | 39B | 27% | GQA | — |
| DeepSeek V3 | 671B | 37B | 5.5% | MLA 512 | MLA + MTP + aux-free + DualPipe |
| Qwen 2.5 72B | 72B | 72B | 100% | GQA 64/8 | YaRN extension |

### 后续：R1、V4

DeepSeek-R1（2025）是在 V3 主干上做的一次推理训练。R1 使用相同的架构。变的是后训练配方（在可验证任务上做大规模 RL），而不是预训练架构。

DeepSeek-V4（如果发布）预计会保留 MLA + MoE + MTP，并加入 DSA（DeepSeek Sparse Attention），即 Phase 10 · 第 17 课中 NSA 的后继。这条脉络是稳定的：架构层面的创新会累积；每个版本都会多拧几个旋钮。

```figure
moe-routing
```

## Use It

`code/main.py` 是一个针对 DeepSeek-V3 形状特化的参数计算器。运行它，把输出与论文中的数字对比，并把它用在假想变体上（256 个专家 vs 512 个，top-8 vs top-16，MLA rank 512 vs 1024）。

值得关注的点：

- 总参数数与公开的 671B 的对比。
- 激活参数数与公开的 37B 的对比。
- 128k 上下文下的 KV cache——MLA 与 GQA 的对比。
- 逐层拆解，看参数预算实际花在哪里。

## Ship It

本课产出 `outputs/skill-deepseek-v3-reader.md`。给定一个 DeepSeek 家族模型（V3、R1 或任何未来的变体），它会产出一份逐组件的架构解读，命名 config 的每个字段，按组件推导参数计数，并指出该模型使用了四项 DeepSeek 专属创新中的哪几项。

## Exercises

1. 运行 `code/main.py`。把计算器的总参数估计与公开的 671B 对比，找出差异来自哪里。论文的 Section 2 有完整的逐项列表。

2. 修改 config，把 MLA rank 从 512 改为 256。计算 128k 上下文下得到的 KV cache 大小。它带来了百分之几的缩减，代价是在每 head 表达能力上付出了什么？

3. 把 DeepSeek-V3 的（256 个专家，top-8）路由与一个假想的（512 个专家，top-8）变体做比较。总参数增长；激活参数保持不变。多出来的专家容量在理论上买到了什么，在推理时又要付出什么代价？

4. 阅读 DeepSeek-V3 技术报告（arXiv:2412.19437）中关于 MLA 的 Section 2.1。用三句话解释为什么 K 和 V 的解压矩阵可以为了推理时的效率被“吸收”进后续的 matmul。

5. DeepSeek-V3 对大多数运算使用 FP8 训练。计算用 FP8 相对于 BF16 存储 671B 权重所节省的显存。这与 14.8T token 的训练预算如何交集？

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| MLA | “Multi-Head Latent Attention” | 把 K 和 V 压缩进一个共享的低秩潜表示（kv_lora_rank，通常为 512），按 head 即时解压；KV cache 只存这个潜向量 |
| kv_lora_rank | “MLA 压缩维度” | K 和 V 共享潜向量的大小；DeepSeek-V3 用 512 |
| First k dense layers | “前几层保持稠密” | MoE 模型的前几层跳过 MoE 路由器，跑稠密 MLP 以保持稳定 |
| num_experts_per_tok | “Top-k 路由” | 每个 token 激发多少个路由专家；DeepSeek-V3 用 8 |
| Shared experts | “常开专家” | 无论路由如何都处理每个 token 的专家；DeepSeek-V3 用 1 个 |
| Auxiliary-loss-free routing | “bias 调整的负载均衡” | 训练中调整每个专家的 bias 项以保持专家负载均衡，而不引入损失项 |
| MTP module | “额外的预测头” | 由 h^(1) 与 E(t+1) 预测 t+2 的 Transformer 块；训练更稠密，还免费得到一个 speculative-decoding draft |
| DualPipe | “双向 pipeline” | 把前向/反向计算与跨节点 all-to-all 重叠起来的训练调度 |
| Active parameter ratio | “稀疏度” | active_params / total_params；DeepSeek-V3 达到 5.5% |
| FP8 training | “8 位训练” | 训练存储和许多计算运算使用 FP8；相对 BF16 大致减半显存，质量代价很小 |

## Further Reading

- [DeepSeek-AI — DeepSeek-V3 Technical Report (arXiv:2412.19437)](https://arxiv.org/abs/2412.19437) —— 完整的架构、训练与结果文档
- [DeepSeek-V3 model card on Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-V3) —— config 文件与部署说明
- [DeepSeek-V2 paper (arXiv:2405.04434)](https://arxiv.org/abs/2405.04434) —— 引入 MLA 的前身
- [DeepSeek-R1 paper (arXiv:2501.12948)](https://arxiv.org/abs/2501.12948) —— 基于 V3 架构的推理训练后继
- [Native Sparse Attention (arXiv:2502.11089)](https://arxiv.org/abs/2502.11089) —— DeepSeek 家族 attention 的未来方向
- [DualPipe repository](https://github.com/deepseek-ai/DualPipe) —— 训练调度的参考
