---
name: skill-quantization
description: 根据硬件、质量和延迟约束，为 LLM 部署选择合适的 quantization 策略
version: 1.0.0
phase: 10
lesson: 11
tags: [quantization, inference, deployment, optimization, fp8, int4, int8, gptq, awq, gguf]
---

# Quantization 决策框架

部署语言模型时，用这套框架选择正确的数字格式、quantization 方法和质量验证策略。

## 输入要求

提供：
- **模型**（名称、参数量、原始精度）
- **目标硬件**（GPU 型号/VRAM、CPU、Apple Silicon、边缘设备）
- **延迟目标**（tokens/second、time to first token）
- **质量下限**（可接受的最大 perplexity 增幅、benchmark 差异）
- **服务模式**（batch size、最大上下文长度、并发用户数）

## 快速选择

| 你的情况 | 格式 | 方法 | 预期质量损失 |
|---------------|--------|--------|----------------------|
| H100 GPU，最大吞吐 | FP8 E4M3 | H100 原生 cast | < 0.1% |
| A100/A10，需要 2 倍吞吐 | INT8 | LLM.int8() 或 SmoothQuant | < 0.5% |
| 单张 24GB GPU，70B 模型 | INT4 | AWQ 或 GPTQ | 1-3% |
| MacBook / Apple Silicon | INT4 GGUF | 通过 llama.cpp 的 Q4_K_M | 1-2% |
| 移动端 / 边缘设备 | INT4 或 INT3 | QAT + 设备专用方案 | 2-5% |
| 最大压缩，允许一定损失 | INT2 | QuIP# 或 AQLM | 5-15% |
| 训练（混合精度） | BF16 + FP32 累加 | 框架原生支持 | 0% |

## 按组件选择精度

并非所有 tensor 都应得到同样的处理。

| 组件 | 安全下限 | 推荐 | 避免 |
|-----------|-------------|-------------|-------|
| FFN 权重 | INT4 | INT4（AWQ/GPTQ） | 未做 QAT 的 INT2 |
| Attention 权重 | INT4 | INT8 或 FP8 | INT2 |
| Embedding 层 | INT8 | FP16（保留原始精度） | INT4 |
| Output head | INT8 | FP16（保留原始精度） | INT4 |
| KV cache | FP8 | FP8 或 INT8 | 长上下文下的 INT4 |
| Attention logits | FP16 | FP16 或 BF16 | INT8 |
| Activation（推理时） | INT8 | FP8 或 INT8 | INT4 |

## 方法对比

### GPTQ
- **适用场景：** GPU 推理，你想要 Hugging Face 兼容的模型
- **校准数据：** 128 个样本，每个 2048 tokens
- **耗时：** 在 A100 上量化 70B 需要 30-60 分钟
- **工具：** `gptqmodel`、`exllama`、`exllamav2`
- **优势：** 经过充分测试，Hugging Face 上有庞大的模型库
- **劣势：** 应用速度比 AWQ 慢，在某些模型上质量略低于 AWQ

### AWQ
- **适用场景：** GPU 推理，你想要最佳的每 bit 质量
- **校准数据：** 128 个样本
- **耗时：** 在 A100 上量化 70B 需要 15-30 分钟
- **工具：** `llmcompressor`、`vLLM`（原生支持）
- **优势：** 最佳的 INT4 质量，应用快，与 vLLM 集成
- **劣势：** 模型库比 GPTQ 小

### GGUF
- **适用场景：** CPU 推理、Apple Silicon、llama.cpp 生态
- **变体：** Q2_K、Q3_K_S/M/L、Q4_K_S/M、Q5_K_S/M、Q6_K、Q8_0、F16
- **推荐默认值：** Q4_K_M（质量/体积的最佳平衡）
- **工具：** `llama.cpp`、`ollama`、`LM Studio`
- **优势：** 自包含文件、混合精度、庞大的生态
- **劣势：** 对 GPU 不是最优（为 CPU/Metal 设计）

### SmoothQuant
- **适用场景：** GPU 上的 INT8，需要同时量化权重和激活值
- **核心思路：** 通过 per-channel 缩放，把 quantization 难度从激活值迁移到权重
- **工具：** `smoothquant`、`TensorRT-LLM`
- **优势：** 实现 W8A8（权重和激活值都用 INT8），带来 2 倍加速
- **劣势：** 仅支持 INT8，无法扩展到 INT4

## 质量验证流程

quantization 之后，部署之前必须验证：

1. **Perplexity 测试。** 在 WikiText-2 或你的领域语料上计算。增幅 < 0.5 为优秀，0.5-1.0 为良好，> 2.0 就是问题。

2. **Benchmark 扫描。** 运行 MMLU（通用）、GSM8K（数学）、HumanEval（代码）。数学和代码对精度损失最敏感。

3. **输出对比。** 用原始模型和量化模型各生成 100 条回复。用 LLM-as-judge 计算胜率。目标：量化模型在 > 90% 的 prompt 上获胜或打平。

4. **延迟测量。** 在 batch size 1 和你的目标 batch size 下测量 tokens/second。确认加速足以抵消质量代价。

5. **长上下文测试。** 如果要服务长上下文（> 4K tokens），在你的最大上下文长度上测试。KV cache quantization 的误差会随序列长度累积。

## 显存预算计算器

```
Weight memory (GB) = parameters (B) * bits / 8 / 1.073741824
KV cache per token (MB) = 2 * num_layers * d_model * bits / 8 / 1048576
KV cache for context (GB) = kv_per_token * max_context_length / 1024
Activation memory (GB) ~ 1-4 GB (relatively constant, depends on batch size)
Total = weight_memory + kv_cache + activation_memory + overhead (10-20%)
```

Llama 3 70B、INT4、32K 上下文的示例：
- 权重：70B * 4 / 8 / 1.07 = 32.6 GB
- KV cache（FP16）：2 * 80 * 8192 * 16 / 8 / 1e9 * 32768 = ~40 GB
- KV cache（FP8）：~20 GB
- 使用 FP8 KV 的总计：~55 GB（能装进一张 80GB A100）

## 常见错误

| 错误 | 为什么会失败 | 修复方式 |
|---------|-------------|-----|
| 把 embedding 层量化到 INT4 | 第一层会把误差放大到整个模型 | Embedding 保持 FP16 或 INT8 |
| 对 INT4 使用 per-tensor 缩放 | 一行 outlier 就会毁掉所有行的精度 | 使用 per-channel 或 per-group 缩放 |
| 不做 GPTQ/AWQ 校准 | 没有代表性数据，scale factor 就是错的 | 使用来自你领域的 128 个样本 |
| 所有层用同一 bit-width | 第一层和最后一层更敏感 | 混合精度：首尾层用更高 bit |
| 在极长上下文下量化 KV cache | 误差随序列长度呈平方级累积 | KV cache 用 FP8，不要用 INT4 |
| 跳过质量验证 | 有些模型量化效果很差（尤其在边界上） | 始终运行 perplexity + 任务 eval |

## 部署配方

### 配方 1：vLLM 搭配 AWQ（GPU 服务器）
```
pip install vllm
vllm serve model-awq --quantization awq --dtype half --max-model-len 8192
```

### 配方 2：llama.cpp 搭配 GGUF（MacBook）
```
./llama-server -m model.Q4_K_M.gguf -c 4096 -ngl 99
```

### 配方 3：TensorRT-LLM 搭配 FP8（H100）
```
trtllm-build --model_dir model --output_dir engine --dtype float16 --use_fp8
```
