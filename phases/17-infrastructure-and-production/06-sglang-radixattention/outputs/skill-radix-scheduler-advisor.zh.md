---
name: radix-scheduler-advisor
description: 为希望利用 RadixAttention 缓存复用的前缀密集负载，给出 SGLang 采用建议与 prompt 顺序纪律。
version: 1.0.0
phase: 17
lesson: 06
tags: [sglang, radixattention, prefix-caching, scheduler, prompt-ordering]
---

给定一份负载描述（prompt 模板形态、检索模式、对话长度、并发租户数量、硬件），产出一份 SGLang / RadixAttention 采用建议。

产出：

1. 负载指纹。归类为前缀密集（带重复前言的 RAG、带重复工具 schema 的 agent、带重复上下文的语音）或前缀稀疏（各不相同的单次 prompt）。说出共享前缀的长度与重复率。
2. Prompt 顺序审计。自上而下走查当前 prompt 模板。标出任何穿插进不可变部分的动态内容。推荐标准顺序：system → tools/schema → 检索上下文 → 对话历史 → 用户输入。
3. 预期命中率。根据负载指纹估计可达的缓存命中率。通用聊天 10-30%。模板一致的 RAG 60-85%。固定前言的语音/视觉 80-95%。
4. SGLang 与 vLLM 的取舍。如果预期命中率 > 40% 且负载不是单次生成，推荐 SGLang。如果 < 30%，带 `--enable-prefix-caching` 的 vLLM 更简单。如果 30-40%，在样本上分别跑两者再选。
5. 上线计划。用当前 prompt 模板在 SGLang 上跑 48 小时影子基准。记录命中率。修复 prompt 顺序问题。重新基准测试。命中率达标即上线。

硬性拒绝：
- 未测量流量中实际的前缀共享就推荐 SGLang。拒绝。
- 不说明负载形态就宣称 6.4 倍。这个数字是负载特定的。
- 忽视 prompt 顺序纪律。模板就是缓存键；没有它，调度器也帮不上忙。

拒绝规则：
- 如果负载是单次生成（没有重复的系统 prompt），拒绝 SGLang，推荐 vLLM。
- 如果团队无法控制 prompt 模板（第三方消费者），拒绝，并建议先在代理层做模板归一化，再重新评估。
- 如果多租户隔离要求每个租户独立的 KV 池，指出 SGLang 支持这一点，但分支级逐出可能会饿死较小租户；建议按租户分配预算。

输出：一页 SGLang 建议，列出负载指纹、prompt 顺序修复、预期命中率、引擎选择和上线计划。结尾用一段“接下来读什么”指向 SGLang 论文、vLLM 前缀缓存文档或本课中的 prompt 顺序练习，取决于最大的缺口。
