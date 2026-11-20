---
name: skill-inference-optimization
description: 诊断并优化 LLM 推理服务的吞吐、延迟和成本
version: 1.0.0
phase: 10
lesson: 12
tags: [inference, kv-cache, batching, speculative-decoding, vllm, optimization]
---

# LLM 推理优化模式

两个阶段：prefill（compute-bound，可并行）和 decode（memory-bound，串行）。
每一种优化都针对其中一个或两个阶段。

```
Request -> Prefill (process prompt) -> Decode (generate tokens) -> Response
              |                            |
         Compute-bound               Memory-bound
         Optimize: fusion,           Optimize: batching,
         prefix caching              quantization, speculation
```

## 决策框架

### 第 1 步：定位你的瓶颈

测量你的负载的 ops:byte 比值：

| ops:byte | 瓶颈类型 | 优化什么 |
|----------|-------|-----------------|
| < 50 | Memory | 量化 KV cache，增大 batch size |
| 50-200 | 过渡区 | 两者都重要，先从 batching 开始 |
| > 200 | Compute | kernel 融合、tensor parallelism、FP8 |

### 第 2 步：选择你的引擎

- **默认：** vLLM（模型支持最广、PagedAttention、OpenAI 兼容 API）
- **多轮对话 / 结构化输出：** SGLang（RadixAttention 前缀缓存、受约束解码）
- **最大化 NVIDIA 吞吐：** TensorRT-LLM（kernel 融合、H100 上的 FP8）

### 第 3 步：按顺序应用优化

1. **KV cache** —— 始终开启，没有副作用
2. **Continuous batching** —— 始终开启，没有副作用（vLLM/SGLang 默认就会做）
3. **前缀缓存（Prefix caching）** —— 如果有共享的 system prompt 就启用（大多数 chatbot 都有）
4. **Quantization** —— KV cache 的 INT8/FP8 能把显存降低 2-4 倍，质量损失极小
5. **Speculative decoding** —— 当延迟比吞吐更重要时加上
6. **Tensor parallelism** —— 模型装不进一张卡时跨 GPU 切分

## KV cache 显存公式

```
per_token = 2 * num_layers * num_kv_heads * head_dim * bytes_per_param
total = per_token * sequence_length * num_concurrent_users
```

常见模型的快速参考（BF16）：

| 模型 | 每 token | 100 用户 @ 4K |
|-------|-----------|----------------|
| Llama 3 8B | 32 KB | 12.5 GB |
| Llama 3 70B | 320 KB | 125 GB |
| Llama 3 405B | 504 KB | 197 GB |

## Speculative decoding 检查清单

- Draft 模型应比 target 模型小 5-10 倍（例如为 70B 配 8B 的 draft）
- 接受率 > 70% 才有明显的加速
- 在可预测的文本上效果最好（代码、结构化输出、自然语言）
- 在创意 / 采样密集的任务上效果最差（低 temperature 有帮助）
- 对大多数负载：EAGLE > draft-target > n-gram

## 常见错误

- 以 batch=1 运行 decode（memory-bound，GPU 计算 95% 空闲）
- 分配连续的 KV cache block（用 PagedAttention，浪费接近零）
- 当 80% 的请求共享同一个 system prompt 时却忽略前缀缓存
- 给模型权重分配过多显存，导致 KV cache 无内存可用
- 只测吞吐不测延迟（10s TTFT 下的高吞吐毫无意义）
- 在高 temperature 下使用 speculative decoding（接受率会掉到 50% 以下）

## 监控检查清单

- Time to first token（TTFT）：prefill 延迟，交互式场景目标 < 500ms
- Inter-token latency（ITL）：decode 速度，流式场景目标 < 50ms
- 吞吐（tokens/second）：所有并发用户的总和
- KV cache 利用率：已分配的 cache 中正在使用的百分比
- Batch 利用率：每次迭代中已填充的 batch 槽位百分比
- 队列深度：正在等待 batch 槽位的请求数
