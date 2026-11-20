# 自托管 Serving 选择 —— 让引擎匹配硬件与规模

> 引擎选择是硬件、规模与生态的函数 —— 不是读一下排行榜。2026 年自托管推理由四个引擎主导：llama.cpp、Ollama、vLLM、SGLang，TGI 则在 maintenance mode 中落后。**llama.cpp** 在 CPU 上最快 —— 模型支持最广，对量化和线程有完全控制。**Ollama** 是开发笔记本上的一条命令安装，比 llama.cpp 慢约 15-30%（Go + CGo + HTTP 序列化），在类生产的负载下吞吐差 3 倍。**TGI 于 2025 年 12 月 11 日进入 maintenance mode** —— 只做 bug 修复，裸吞吐比 vLLM 慢约 10%，但历史上可观测性一流、HF 生态集成最好。这一 maintenance 状态使它成为有风险的长期押注 —— 新项目用 SGLang 或 vLLM 是更稳妥的默认。**vLLM** 是通用生产默认 —— v0.15.1（2026 年 2 月）加入 PyTorch 2.10、RTX Blackwell SM120、H200 优化。**SGLang** 是 agent 多轮 / 前缀密集的专家 —— 生产中 400,000+ GPU（xAI、LinkedIn、Cursor、Oracle、GCP、Azure、AWS）。硬件约束：CPU 优先 → llama.cpp。AMD / 非 NVIDIA → vLLM 是支持最好的路径（TRT-LLM 锁定在 NVIDIA）。2026 年的流水线模式：dev = Ollama，staging = llama.cpp，prod = vLLM 或 SGLang。各引擎采用不同的权重格式 —— llama.cpp 家族用 GGUF，GPU 引擎用 HF safetensors —— 所以两个阶段之间可能需要一次格式转换。

**Type:** Learn
**Languages:** Python (stdlib, 引擎决策树遍历器)
**Prerequisites:** 第 17 阶段所有涉及引擎的课程（04、06、07、09、18）
**Time:** ~45 分钟

## Learning Objectives

- 给定硬件（CPU / AMD / NVIDIA Hopper / Blackwell）、规模（1 用户 / 100 / 10,000）与工作负载（通用对话 / agent / 长上下文），挑选一个引擎。
- 说出 2026 年 TGI 的 maintenance-mode 状态（2025 年 12 月 11 日），以及为什么它让新项目偏向 vLLM 或 SGLang。
- 描述 dev/staging/prod 流水线，包括 GGUF 到 safetensors 的格式转换位于阶段之间的何处。
- 解释为什么“CPU 优先”指向 llama.cpp，而“AMD”排除 TRT-LLM。

## 问题场景

你的团队启动一个新的自托管 LLM 项目。一个工程师说 Ollama，另一个说 vLLM，第三个说“TGI 不是开箱即用吗？”三者在不同语境下都对。没有哪个对所有语境都对。

2026 年这棵选择树很重要：硬件第一，规模第二，工作负载第三。而 2025 年的一件具体事件 —— TGI 于 12 月 11 日进入 maintenance mode —— 改变了新项目的默认。

## 核心概念

### 五个引擎

| 引擎 | 最适合 | 备注 |
|--------|----------|-------|
| **llama.cpp** | CPU / 边缘 / 最少依赖 / 最广模型支持 | CPU 上最快，完全可控 |
| **Ollama** | 开发笔记本、单用户、一条命令安装 | 比 llama.cpp 慢 15-30%；生产吞吐差 3 倍 |
| **TGI** | HF 生态、受监管行业 | **2025 年 12 月 11 日进入 maintenance mode** |
| **vLLM** | 通用生产、100+ 用户 | 广泛的生产默认；v0.15.1 于 2026 年 2 月 |
| **SGLang** | Agent 多轮、前缀密集型工作负载 | 生产中 400,000+ GPU |

### 硬件优先的决策

**CPU 优先** → llama.cpp。Ollama 也行但更慢。在 CPU 上没有其他引擎能与之竞争。

**AMD GPU** → vLLM 是支持最好的路径（AMD ROCm 支持）。SGLang 也可用。TRT-LLM 锁定在 NVIDIA，所以出局。

**NVIDIA Hopper（H100 / H200）** → vLLM 或 SGLang 或 TRT-LLM。三者都是顶级。

**NVIDIA Blackwell（B200 / GB200）** → TRT-LLM 是吞吐领先者（Phase 17 · 07）。vLLM 与 SGLang 紧随其后。

**Apple Silicon（M 系列）** → llama.cpp（Metal）。Ollama 封装了它。

### 规模第二的决策

**1 用户 / 本地开发** → Ollama。一条命令，首 token 几秒内出。

**10-100 用户 / 小团队** → vLLM 单 GPU。

**100-10k 用户 / 生产** → vLLM production-stack（Phase 17 · 18）或 SGLang。

**10k+ 用户 / 企业** → vLLM production-stack + 分离式（Phase 17 · 17）+ LMCache（Phase 17 · 18）。

### 工作负载第三的决策

**通用对话 / Q&A** → vLLM 在广泛默认上胜出。

**Agent 多轮（工具、规划、记忆）** → SGLang 的 RadixAttention（Phase 17 · 06）占主导。

**前缀重度复用的 RAG** → SGLang。

**代码生成** → vLLM 就够好；SGLang 在 cache 上略好。

**长上下文（128K+）** → vLLM + chunked prefill；SGLang + 分层 KV。

### TGI 的 maintenance 陷阱

Hugging Face TGI 于 2025 年 12 月 11 日进入 maintenance mode —— 往后只做 bug 修复。历史上：顶级可观测性、一流的 HF 生态集成（model card、安全工具），裸吞吐略落后于 vLLM。

对 2026 年的新项目：默认避开 TGI。现有 TGI 部署可以继续，但最终应当迁移。SGLang 和 vLLM 是更稳妥的默认。

### 流水线模式

Dev（Ollama）→ staging（llama.cpp）→ prod（vLLM）。各引擎采用不同的权重格式 —— llama.cpp 家族用 GGUF，GPU 引擎用 HF safetensors —— 所以两个阶段之间可能需要一次格式转换。工程师在笔记本上快速迭代；staging 复刻生产的量化；prod 是 serving 目标。

### Ollama 的注意点

Ollama 适合开发。它不适合共享的生产：Go HTTP 序列化带来开销，并发管理比 vLLM 简单，OpenTelemetry 支持滞后。在它擅长之处用它 —— 单用户、一条命令 —— 共享场景改用 vLLM。

### 自托管 vs 托管是另一个决策

Phase 17 · 01（托管超大规模厂商）、· 02（推理平台）覆盖托管。本课假设你已经决定自托管。自托管的理由：数据驻留、自定义微调、规模化下的总成本自有、托管上没有的领域模型。

### 需要记住的数字

- TGI maintenance mode：2025 年 12 月 11 日。
- vLLM v0.15.1：2026 年 2 月；PyTorch 2.10；Blackwell SM120 支持。
- SGLang 生产足迹：400,000+ GPU。
- Ollama 相对 llama.cpp 的吞吐差距：慢 15-30%；生产负载下差 3 倍。

```figure
data-parallel
```

## Use It

`code/main.py` 是一个决策树遍历器：给定硬件 + 规模 + 工作负载，挑选引擎并解释原因。

## Ship It

本课产出 `outputs/skill-engine-picker.md`。给定约束，挑选引擎并写出迁移计划。

## Exercises

1. 用你的硬件 / 规模 / 工作负载运行 `code/main.py`。输出符合你的直觉吗？
2. 你的基础设施是 12 块 H100 和 8 块 MI300X AMD。选哪个引擎？为什么 TRT-LLM 出局？
3. 一个团队想在 2026 年继续用 TGI，因为“这是我们熟悉的”。论证迁移的理由。
4. 从 Ollama 开发到 vLLM 生产：量化、配置、可观测性上各有什么变化？
5. P99 前缀长度 8K、跨租户高复用的 RAG 产品。选一个引擎，并用 Phase 17 · 11 + 18 把它栈起来。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| llama.cpp | “CPU 那个” | 模型支持最广，CPU 上最快 |
| Ollama | “笔记本那个” | 一条命令安装，开发级吞吐 |
| TGI | “HF 的 serving” | 自 2025 年 12 月起 maintenance mode |
| vLLM | “默认那个” | 2026 年广泛的生产基线 |
| SGLang | “agent 那个” | 前缀密集、RadixAttention |
| TRT-LLM | “NVIDIA 锁定” | Blackwell 吞吐领先，仅限 NVIDIA |
| GGUF | “llama.cpp 格式” | 打包的 K-quant 变体 |
| Production-stack | “vLLM K8s” | Phase 17 · 18 参考部署 |
| Pipeline pattern | “dev→stage→prod” | Ollama → llama.cpp → vLLM；每个引擎权重格式不同 |

## Further Reading

- [AI Made Tools —— vLLM vs Ollama vs llama.cpp vs TGI 2026](https://www.aimadetools.com/blog/vllm-vs-ollama-vs-llamacpp-vs-tgi/)
- [Morph —— llama.cpp vs Ollama 2026](https://www.morphllm.com/comparisons/llama-cpp-vs-ollama)
- [n1n.ai —— 全面的 LLM 推理引擎对比](https://explore.n1n.ai/blog/llm-inference-engine-comparison-vllm-tgi-tensorrt-sglang-2026-03-13)
- [PremAI —— 2026 年 10 个最佳 vLLM 替代品](https://blog.premai.io/10-best-vllm-alternatives-for-llm-inference-in-production-2026/)
- [TGI maintenance 公告](https://github.com/huggingface/text-generation-inference) —— release notes。
- [vLLM v0.15.1 release notes](https://github.com/vllm-project/vllm/releases)
