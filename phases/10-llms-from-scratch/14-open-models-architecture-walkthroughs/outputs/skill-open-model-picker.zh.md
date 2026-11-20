---
name: open-model-picker
description: 为给定的部署目标挑选开源 LLM 家族、quantization 和推理栈。
version: 1.0.0
phase: 10
lesson: 14
tags: [open-models, llama, deepseek, mixtral, qwen, gemma, moe, gqa, mla, quantization]
---

给定一个部署目标（GPU 类型、每卡 VRAM、GPU 数量、目标上下文长度、目标 p50/p99 延迟、峰值并发请求数）和一个任务画像（chat、code、reasoning、长上下文检索、tool use），推荐一个开源模型加服务栈，并对 Lesson 14 中的六个架构调节旋钮逐一给出明确理由。

产出：

1. 模型候选清单。三个候选，每个都要有总参数量、激活参数量（考虑 MoE）、架构标记（norm / activation / position / attention / MoE / context），以及它入选的单一理由。
2. 显存预算检查。对首选候选：BF16 下的权重显存和所选 quantization 下的权重显存；目标 batch size 在目标上下文下的 KV cache；activation 余量。如果权重 + KV cache + activation 超过可用 VRAM，就中止推荐。
3. Quantization 选择。GPTQ-4bit、AWQ-4bit、FP8 或 BF16。结合任务对准确率的敏感度论证（code / math / reasoning 任务在激进 quantization 下受到的损失比 chat 或检索更大）。
4. 推理栈。vLLM、TensorRT-LLM、SGLang 或 llama.cpp。结合以下方面论证：continuous batching 需求、speculative decoding 支持、quantization 格式兼容性，以及单节点 vs 多节点拓扑。
5. 吞吐合理性检查。基于 GPU 显存带宽（decode）和 TFLOPs（prefill）估算 prefill tokens/sec 和 decode tokens/sec。如果 decode 吞吐低于目标并发用户下限，拒绝该推荐。
6. 兜底方案。首选候选超出 VRAM 或吞吐预算时的第二选择。必须始终给出一个。

硬拒绝条件：
- 在单张 24GB 消费级 GPU 上运行 30B 以上的稠密模型，且没有 offloading 或激进 quantization。
- 在不支持 expert-parallel 的服务栈上运行 MoE 模型。
- 在不具备 GQA 或 MLA 的架构上跑长上下文（128k+）（KV cache 会爆炸）。
- 任何没有指明具体模型修订版本的推荐（例如 "Llama 3 8B Instruct v3.1" 而不是 "Llama 3"）。

输出：一页推荐，列出模型、quantization、技术栈，并为每个决策附上编号证据。最后用一段 "在以下情况下值得重新考虑……" 指出会推翻该选择的具体能力或部署参数。
