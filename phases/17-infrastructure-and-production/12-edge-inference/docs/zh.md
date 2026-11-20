# Edge 推理 —— Apple Neural Engine、Qualcomm Hexagon、WebGPU/WebLLM、Jetson

> edge 的核心约束是显存带宽，不是算力。移动端 DRAM 在 50-90 GB/s，数据中心 HBM3 超过 2-3 TB/s —— 30-50 倍的差距。Decode 是 memory-bound 的，因此这个差距是决定性的。2026 年这块版图分成四支。Apple M4/A18 Neural Engine 峰值 38 TOPS，统一内存（没有 CPU↔NPU 拷贝）。Qualcomm Snapdragon X Elite / 8 Gen 4 Hexagon 达到 45 TOPS。WebGPU + WebLLM 在 M3 Max 上以约 41 tok/s 跑 Llama 3.1 8B（Q4），大约是原生的 70-80%；17.6k GitHub star，OpenAI 兼容 API，移动端覆盖约 70-75%。NVIDIA Jetson Orin Nano Super（8GB）能跑 Llama 3.2 3B / Phi-3；AGX Orin 通过 vLLM 以约 40 tok/s 跑 gpt-oss-20b；Jetson T4000（JetPack 7.1）是 AGX Orin 的 2 倍。TensorRT Edge-LLM 支持 EAGLE-3、NVFP4、chunked prefill —— 由 Bosch、ThunderSoft、MediaTek 在 CES 2026 上展示。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级带宽受限 decode 模拟器)
**Prerequisites:** 第 17 阶段，第 04 课（Serving Engine Internals），第 09 课（Production Quantization）
**Time:** ~60 分钟

## Learning Objectives

- 解释为什么移动端 LLM 推理是 memory-bandwidth-bound 的，而算力是次要的。
- 列举四个 edge 目标（Apple ANE、Qualcomm Hexagon、WebGPU/WebLLM、NVIDIA Jetson），并把每个匹配到一种用例。
- 说出 2026 年 WebGPU 的覆盖缺口（Firefox Android 正在追赶）以及 Safari iOS 26 的落地。
- 为每个目标选出量化格式（ANE 用 Core ML INT4 + FP16，Hexagon 用 QNN INT8/INT4，浏览器用 WebGPU Q4，Jetson Thor 用 NVFP4）。

## 问题场景

一个客户想要端侧聊天机器人：语音优先、默认隐私、可离线工作。在 MacBook Pro M3 Max 上，Llama 3.1 8B Q4 约 55 tok/s —— 可以。在 iPhone 16 Pro 上，同一个模型只有 3 tok/s —— 不行。在中端 Android（Snapdragon 8 Gen 3）上是 7 tok/s。在 Chrome Android v121+ 上通过 WebGPU 在浏览器里运行，视设备而定 4-8 tok/s。

吞吐的差异不是移植问题。它是带宽差距、量化格式，以及 NPU 能否从用户态访问这三者的乘积。2026 年的 edge 推理是四个不同的问题、四套不同的解法。

## 核心概念

### 带宽才是真正的天花板

Decode 每生成一个 token 都要读取全部权重。一个 Q4 的 7B 模型是 3.5 GB。以 50 GB/s 读取 3.5 GB 需要 70 ms —— 理论上限约 14 tok/s。在 90 GB/s（高端移动 DRAM）下上限变成约 25 tok/s。低于这个数字，再多算力也无济于事。

数据中心 HBM3 的 3 TB/s 在 1.2 ms 内读完同样的 3.5 GB —— 上限是 830 tok/s。同样的模型、同样的权重。不同的内存子系统。

### Apple Neural Engine（M4 / A18）

- 最高 38 TOPS。统一内存（CPU 和 ANE 共享同一内存池）—— 没有拷贝开销。
- 通过 Core ML + 编译后的 `.mlmodel` 模型访问，或通过 PyTorch 的 Metal Performance Shaders（MPS）访问。
- Llama.cpp 的 Metal 后端用的是 MPS，不是直接调用 ANE；要用原生 ANE 需要 Core ML 转换。
- 2026 年 iOS 应用最实用的路径：Core ML + INT4 权重 + FP16 激活。

### Qualcomm Hexagon（Snapdragon X Elite / 8 Gen 4）

- 最高 45 TOPS。在 SoC 内与 CPU、GPU 集成，但内存域独立。
- QNN（Qualcomm Neural Network）SDK 和 AI Hub 提供从 PyTorch/ONNX 的转换。
- Chat template、Llama 3.2、Phi-3 都在 AI Hub 上作为一等工件提供。

### Intel / AMD NPU（Lunar Lake、Ryzen AI 300）

- 40-50 TOPS。软件落后于 Apple/Qualcomm；OpenVINO 在进步但仍小众。
- 最适合 Windows ARM copilot 应用；在 AMD/Intel 桌面机上用于本地优先也很合适。

### WebGPU + WebLLM

- 通过 WebGPU compute shader 在浏览器中运行模型；无需安装。
- M3 Max 上 Llama 3.1 8B Q4 约 41 tok/s —— 同一后端下大约是原生的 70-80%。
- WebLLM 有 17.6k GitHub star；OpenAI 兼容的 JS API；Apache 2.0。
- 2026 年覆盖：Chrome Android v121+、Safari iOS 26 GA，Firefox Android 仍在追赶。整体移动端覆盖约 70-75%。

### NVIDIA Jetson 系列

- Orin Nano Super（8GB）：能跑 Llama 3.2 3B、Phi-3，tok/s 表现良好。
- AGX Orin：通过 vLLM 以约 40 tok/s 跑 gpt-oss-20b。
- Thor / T4000（JetPack 7.1）：性能是 AGX Orin 的 2 倍，支持 EAGLE-3 和 NVFP4。
- TensorRT Edge-LLM（2026）支持 EAGLE-3 speculative decoding、NVFP4 权重、chunked prefill —— 把数据中心的优化搬到了 edge。

### 按目标选量化

| 目标 | 格式 | 说明 |
|--------|--------|-------|
| Apple ANE | INT4 权重 + FP16 激活 | Core ML 转换路径 |
| Qualcomm Hexagon | QNN INT8 / INT4 | AI Hub 转换器 |
| WebGPU / WebLLM | Q4 MLC（q4f16_1） | 用 `mlc_llm convert_weight` + 编译后的 `.wasm`；不支持 GGUF |
| Jetson Orin Nano | Q4 GGUF 或 TRT-LLM INT4 | memory-bound |
| Jetson AGX / Thor | NVFP4 + FP8 KV | Edge-LLM 路径 |

### edge 上的长 context 陷阱

Llama 3.1 的 128K context 是数据中心特性。在 8 GB RAM 的手机上，4 GB 模型 + 32K token 的 2 GB KV cache + 系统开销 = OOM。除非接受激进的 KV 量化（Q4 KV），edge 部署要把 context 控制在 4K-8K。

### 语音是杀手级应用

语音 agent 对延迟敏感（首 token < 500 ms）。本地推理完全消除了网络延迟。再配上语音转文字（Whisper Turbo 的各个变体可在 edge 上运行），edge 推理就构成了生产级的语音回路。

### 应该记住的数字

- Apple M4 / A18 ANE：38 TOPS。
- Qualcomm Hexagon SD X Elite：45 TOPS。
- WebLLM M3 Max：Llama 3.1 8B Q4 上约 41 tok/s。
- AGX Orin：gpt-oss-20b 经 vLLM 约 40 tok/s。
- 数据中心与 edge 的带宽差距：30-50 倍。
- WebGPU 移动端覆盖：约 70-75%（Firefox Android 落后）。

```figure
edge-bandwidth-pipe
```

## Use It

`code/main.py` 用面向各 edge 目标的带宽受限数学计算理论 decode 吞吐上限。与实测 benchmark 对比，并突出显示带宽（而不是算力）成为瓶颈的地方。

## Ship It

本课产出 `outputs/skill-edge-target-picker.md`。给定平台（iOS/Android/浏览器/Jetson）、模型和延迟/显存预算，选出量化格式与转换流水线。

## Exercises

1. 运行 `code/main.py`。对一个 Q4 的 7B 模型、Snapdragon 8 Gen 3（带宽约 77 GB/s），计算 decode 上限。与实际观测的 6-8 tok/s 相比 —— runtime 高效吗？
2. Android 上的 WebGPU 需要 Chrome v121+。为旧浏览器设计降级方案 —— 通过同一个 OpenAI 兼容 API 走服务端。
3. 你的 iOS 应用需要 4K context 的流式输出。哪种模型/格式组合能让 iPhone 16 上的活跃内存保持在 4 GB 以内？
4. Jetson AGX Orin 以 40 tok/s 跑 gpt-oss-20b。Jetson Nano 只能装下 3B。如果你的产品两者都要覆盖，如何统一推理栈？
5. 论证“2026 年 WebLLM 是否已达到生产可用”。引用覆盖率、性能和 Firefox Android 的缺口。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| ANE | “Apple neural engine” | M 系列和 A 系列中的端侧 NPU；统一内存 |
| Hexagon | “Qualcomm NPU” | Snapdragon NPU；通过 QNN SDK 访问 |
| WebGPU | “browser GPU” | W3C 标准化的浏览器 GPU API；2026 年的 Chrome/Safari |
| WebLLM | “browser LLM runtime” | MLC-LLM 项目；Apache 2.0；OpenAI 兼容 JS |
| Jetson | “NVIDIA edge” | Orin Nano / AGX / Thor / T4000 系列 |
| TRT Edge-LLM | “edge TensorRT” | 2026 年 TensorRT-LLM 的 edge 移植；EAGLE-3 + NVFP4 |
| Unified memory | “shared pool” | CPU 与 NPU 看到同一块 RAM；无拷贝开销 |
| Bandwidth-bound | “memory limited” | Decode 受读取权重的字节/秒速率限制 |
| Core ML | “Apple conversion” | Apple 的 ANE 原生模型框架 |
| QNN | “Qualcomm stack” | Qualcomm Neural Network SDK |

## Further Reading

- [On-Device LLMs State of the Union 2026](https://v-chandra.github.io/on-device-llms/) —— 版图与 benchmark。
- [NVIDIA Jetson Edge AI](https://developer.nvidia.com/blog/getting-started-with-edge-ai-on-nvidia-jetson-llms-vlms-and-foundation-models-for-robotics/) —— Orin / AGX / Thor。
- [NVIDIA TensorRT Edge-LLM](https://developer.nvidia.com/blog/accelerating-llm-and-vlm-inference-for-automotive-and-robotics-with-nvidia-tensorrt-edge-llm/) —— 2026 年 edge 移植发布。
- [WebLLM (arXiv:2412.15803)](https://arxiv.org/html/2412.15803v2) —— 设计与 benchmark。
- [Apple Core ML](https://developer.apple.com/documentation/coreml) —— ANE 原生转换。
- [Qualcomm AI Hub](https://aihub.qualcomm.com/) —— 为 Hexagon 预转换的模型。
