---
name: edge-target-picker
description: 根据设备、模型和延迟预算，选出 edge 推理目标（Apple ANE、Qualcomm Hexagon、WebGPU/WebLLM、NVIDIA Jetson）及匹配的量化格式。
version: 1.0.0
phase: 17
lesson: 12
tags: [edge, ane, hexagon, webgpu, webllm, jetson, core-ml, qnn, nvfp4]
---

给定部署平台（iOS、Android、浏览器、机器人/车载/edge 服务器）、模型以及延迟/显存预算，产出 edge 目标建议。

产出：

1. 目标。点名具体的 NPU/GPU（ANE、Hexagon、WebGPU、Jetson Orin Nano / AGX / Thor）。用平台和 2026 年的 runtime 覆盖情况说明理由。
2. 带宽上限。计算理论 decode 上限：bandwidth_GB_s / model_size_GB。与用户的 tok/s 需求对比。如果上限低于需求，拒绝或建议更小的模型 / 更紧的量化。
3. 量化格式。选 Q4 GGUF（浏览器/edge CPU）、Core ML INT4 + FP16（ANE）、QNN INT8/INT4（Hexagon）或 NVFP4 + FP8 KV（Jetson Thor / Edge-LLM）。
4. 转换流水线。点名确切的转换器（Core ML converter、Qualcomm AI Hub、WebLLM 用 MLC-LLM、TensorRT-LLM Edge compiler）。
5. Context 预算。说明在设备内存中与权重并存时的最大 context。对长 context 用例，指定 KV 量化（Q4 KV）或拒绝。
6. 降级方案。当设备无法胜任或 WebGPU 不可用（Firefox Android、旧版浏览器）时，指定具备相同 OpenAI 兼容接口的服务端 API 降级方案。

硬性拒绝：
- 承诺超过带宽上限的 tok/s。拒绝 —— 物理规律。
- 2026 年绕开 Core ML，用非 Core ML runtime 直接打 ANE。只有 Core ML 原生暴露 ANE。
- 假设每个浏览器都有 WebGPU。2026 年移动端覆盖约 70-75%；永远要写明降级方案。

拒绝规则：
- 如果模型 >6 GB 而目标是手机（4-8 GB RAM），拒绝 —— 先建议更小的模型或更激进的量化。
- 如果请求是在 iPhone 上用 7B 模型跑 128K context，拒绝 —— 不配 Q4 KV 加滑窗 attention，设备内存装不下。
- 如果部署要求在 Android 上通过 WebGPU 做长 context 流式输出，而用户又要求支持 Firefox，拒绝，并要求使用 Chrome 或服务端降级方案。

输出：一页方案，写明目标、上限、量化格式、转换器、context 预算、降级方案。最后给出一个指标：目标设备池中最差设备上的实测 tok/s。
