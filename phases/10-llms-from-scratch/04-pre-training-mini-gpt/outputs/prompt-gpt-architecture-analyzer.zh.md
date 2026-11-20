---
name: prompt-gpt-architecture-analyzer
description: 分析任意 GPT 风格 transformer 模型的架构选择
version: 1.0.0
phase: 10
lesson: 4
tags: [gpt, transformer, architecture, attention, kv-cache, scaling, pre-training]
---

# GPT 架构分析器

当你从技术报告、model card 或训练日志中评估一个 GPT 风格模型时，用这个框架拆解架构并识别设计权衡。

## 分析流程

### 1. 参数分配拆解

计算每个组件的精确参数数量：

- **Token embeddings**：vocab_size x embed_dim
- **Position embeddings**：max_seq_len x embed_dim
- **每个 block 的 attention**：4 x embed_dim x embed_dim（Q、K、V、输出投影）
- **每个 block 的 FFN**：2 x embed_dim x ff_dim + embed_dim + ff_dim（两个线性层 + 偏置）
- **每个 block 的 LayerNorm**：4 x embed_dim（两个 norm，每个含 scale + bias）
- **最终 LayerNorm**：2 x embed_dim
- **输出头**：vocab_size x embed_dim（若与 token embeddings 权重绑定则为 0）

如果有任何单个组件超过总参数的 40%，标记出来。小模型中 embedding 矩阵占主导。大模型中 attention 和 FFN 占主导。

### 2. Attention 设计分析

评估 attention 配置：

- **Head 维度**：embed_dim / num_heads。标准是 64（GPT-2）或 128（Llama 3）。低于 32 会限制单 head 的表达能力。高于 128 浪费算力，收益很小。
- **每层 head 数**：更多 head = 更多样的 attention 模式，但 KV cache 内存更多。
- **Grouped Query Attention（GQA）**：模型是否在多个 Q head 之间共享 K/V head？Llama 3 使用 GQA，32 个 Q head 配 8 个 KV head。这把 KV cache 减小到 1/4。
- **上下文长度**：最大 position embeddings。RoPE 允许外推到训练长度之外。绝对 position embeddings 做不到。

### 3. 内存预算

在模型最大上下文长度下做推理：

- **权重（FP16）**：total_params x 2 bytes
- **KV Cache（FP16）**：2 x num_layers x num_kv_heads x head_dim x max_seq_len x 2 bytes
- **Activations**：batch_size x seq_len x embed_dim x 2 bytes x num_layers（近似）

如果 KV cache 超过权重内存，标记出来。这发生在长上下文模型（128K+）上，说明模型在 decode 阶段受内存限制。

### 4. 算力画像

- **Prefill 每 token FLOPS**：约 2 x total_params（每个参数一次 matmul，前向传播）
- **Decode 每 token FLOPS**：与 prefill 相同，但只针对单个 token
- **Prefill 瓶颈**：算力受限（GPU TFLOPS）
- **Decode 瓶颈**：内存受限（GPU 内存带宽）
- **算术强度**：每访问一字节内存对应的 FLOPS。低于 100 = 内存受限。

### 5. Scaling 决策

对照已知的 scaling laws 评估：

- **Chinchilla 最优**：对于给定算力预算 C，最优模型规模 N 与 token 数 D 满足 N ~ D（大致等比例扩展）。一个 7B 模型需要约 140B tokens。
- **Llama 3 过训练**：Meta 在 15T tokens 上训练 Llama 3 8B（是 Chinchilla 最优的 100 倍）。用更多数据过训练小模型能换来更好的每 token 推理成本。
- **宽度 vs 深度**：在相同参数数量下，更深的模型（更多层）通常比更宽的模型（更大的 embed_dim）样本效率更高。

## 危险信号

- **FFN 比例不是 4x**：标准是 ff_dim = 4 x embed_dim。Llama 用 SwiGLU 时为 8/3 x embed_dim。偏离应有理由。
- **没有权重绑定**：除非 vocab_size 相对 embed_dim 非常大，否则输出头应与 token embeddings 共享权重。
- **13B 以上没有 GQA**：13B 以上不使用 grouped-query attention 的模型会有过大的 KV cache。
- **长上下文没有 RoPE**：绝对 position embeddings 无法外推到训练长度之外。目标 32K+ 上下文的模型应使用 rotary embeddings。
- **学习率相对模型规模过高**：更大的模型需要更低的峰值学习率。GPT-2 Small 用 6e-4。Llama 3 405B 用 8e-5。

## 输出格式

1. **参数表**：逐组件的参数数量及占比
2. **内存预算**：最大上下文长度下的权重、KV cache 和 activation 内存
3. **算力画像**：A100/H100 上的 prefill 与 decode 吞吐估算
4. **设计评估**：模型哪些地方做对了，哪些不标准
5. **Scaling 结论**：模型规模与其训练数据是否匹配
