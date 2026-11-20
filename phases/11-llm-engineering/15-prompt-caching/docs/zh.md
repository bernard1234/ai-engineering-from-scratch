# Prompt Caching 与 Context Caching

> 你的 system prompt 有 4,000 token。你的 RAG context 有 20,000 token。你每个请求都把它们一起发出去。你也每次都为此付钱。Prompt caching 让 provider 在它那一侧把这个前缀保持温热，复用时只按正常费率的 10% 计费。用对了，它能把推理成本砍掉 50–90%，把首 token 延迟降低 40–85%。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 11 · 01 (Prompt Engineering), Phase 11 · 05 (Context Engineering), Phase 11 · 11 (Caching and Cost)
**Time:** ~60 分钟
## 问题场景

一个 coding agent 在对话的每一轮都向 Claude 发送同一份 15,000 token 的 system prompt。二十轮、每百万输入 token $3，光输入成本就是 $0.90——这还没算用户真正发的消息。再乘以每天 10,000 次对话，仅仅为了那段从不改变的文字，账单就到 $9,000/天。

你没法在不损伤质量的前提下压缩 prompt。你也没法不发送它——模型每一轮都需要它。唯一的出路是：不再为一个 provider 已经见过的前缀支付全价。

这条路就是 prompt caching。Anthropic 在 2024 年 8 月推出它（2025 年加了 1 小时扩展 TTL 的变体），OpenAI 在那年晚些时候实现了自动化，Google 随 Gemini 1.5 推出了显式 context caching，如今三家都在各自的前沿模型上把它作为一等功能提供。

## 核心概念

![Prompt caching：写一次，读得便宜](../assets/prompt-caching.svg)

**机制。** 当请求的前缀与某次近期请求的前缀匹配时，provider 直接复用上一次运行的 KV-cache，而不是重新编码这些 token。第一次你付一笔小的写入溢价，之后每次都享受大幅读取折扣。

**2026 年的三种 provider 风格。**

| Provider | API 风格 | 命中折扣 | 写入溢价 | 默认 TTL | 最小可缓存量 |
|---------|-----------|--------------|---------------|-------------|---------------|
| Anthropic | 在 content block 上显式打 `cache_control` 标记 | 输入按 10% 计费 | 加收 25% | 5 分钟（可延长到 1 小时） | 1,024 token（Sonnet/Opus），2,048（Haiku） |
| OpenAI | 自动前缀检测 | 输入按 50% 计费 | 无 | 最长 1 小时（尽力而为） | 1,024 token |
| Google（Gemini） | 显式 `CachedContent` API | 按存储计费；读取约为正常的 25% | 按 token·小时收存储费 | 用户设定（默认 1 小时） | 4,096 token（Flash），32,768（Pro） |

**不变式。** 三家都只缓存前缀。只要请求之间有任何一个 token 不同，从第一个不同 token 之后的内容全部未命中。把*稳定*的部分放顶部，*可变*的部分放底部。

### cache 友好的布局

```
[system prompt]          <-- cache this
[tool definitions]       <-- cache this
[few-shot examples]      <-- cache this
[retrieved documents]    <-- cache if reused, else don't
[conversation history]   <-- cache up to last turn
[current user message]   <-- never cache (different every time)
```

违反顺序——把用户消息放到 system prompt 上面，或者在 few-shot 之间穿插动态检索内容——cache 就永远不会命中。

### 盈亏平衡计算

Anthropic 的 25% 写入溢价意味着，一个缓存块至少要被读取两次才能净省钱。1 次写入 + 1 次读取平均下来是每次请求 0.675 倍成本（省 32%）；1 次写入 + 10 次读取平均是 0.205 倍（省 80%）。经验法则：只要预计在 TTL 内至少复用 3 次，就缓存它。

```figure
prompt-cache-hit
```

## Build It

### 第 1 步：用显式标记做 Anthropic prompt caching

```python
import anthropic

client = anthropic.Anthropic()

SYSTEM = [
    {
        "type": "text",
        "text": "You are a senior Python reviewer. Follow the rubric exactly.\n\n" + RUBRIC_15K_TOKENS,
        "cache_control": {"type": "ephemeral"},
    }
]

def review(code: str):
    return client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": code}],
    )
```

`cache_control` 标记告诉 Anthropic 把这个块存 5 分钟。在这个窗口内复用会命中；过期后复用会重新写入。

**响应中的 usage 字段：**

```python
response = review(code_a)
response.usage
# InputTokensUsage(
#     input_tokens=120,
#     cache_creation_input_tokens=15023,   # paid at 1.25x
#     cache_read_input_tokens=0,
#     output_tokens=340,
# )

response_b = review(code_b)
response_b.usage
# cache_creation_input_tokens=0
# cache_read_input_tokens=15023           # paid at 0.1x
```

在 CI 里检查这两个字段——如果 `cache_read_input_tokens` 在多次请求之间始终为零，说明你的 cache key 在漂移。

### 第 2 步：一小时的扩展 TTL

对于长时间运行的批处理任务，5 分钟默认值会在任务之间过期。设置 `ttl`：

```python
{"type": "text", "text": RUBRIC, "cache_control": {"type": "ephemeral", "ttl": "1h"}}
```

1 小时 TTL 的写入溢价翻倍（比基线高 50%，而不是 25%），但只要任何批处理复用该前缀超过 5 次，就很快回本。

### 第 3 步：OpenAI 自动 caching

OpenAI 什么也不用你配置。任何超过 1,024 token 且与近期请求匹配的前缀，都会自动获得 50% 折扣。

```python
from openai import OpenAI
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-5",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},   # long and stable
        {"role": "user", "content": user_msg},
    ],
)
resp.usage.prompt_tokens_details.cached_tokens  # the discounted portion
```

同样适用 cache 友好的布局规则。有两件事会破坏 OpenAI 的 cache，却不会影响 Anthropic：改动 `user` 字段（它被用作 cache key 的组成部分）和重排 tool。

### 第 4 步：Gemini 显式 context caching

Gemini 把 cache 当作一个由你创建并命名的一等对象：

```python
from google import genai
from google.genai import types

client = genai.Client()

cache = client.caches.create(
    model="gemini-3.8-flash",
    config=types.CreateCachedContentConfig(
        display_name="rubric-v3",
        system_instruction=RUBRIC,
        contents=[FEW_SHOT_EXAMPLES],
        ttl="3600s",
    ),
)

resp = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=["Review this code:\n" + code],
    config=types.GenerateContentConfig(cached_content=cache.name),
)
```

Gemini 在 cache 存活期间按 token·小时收存储费，读取约为正常输入费率的 25%。当你要在数天里跨多个 session 复用同一份巨型 prompt 时，这是正确的形态。

### 第 5 步：在生产中衡量命中率

见 `code/main.py` 里一个模拟的三 provider 记账器：它统计写入/读取/未命中次数，并计算每 1K 请求的混合成本。把目标命中率作为部署门禁——大多数生产环境的 Anthropic 配置在预热后应看到 >80% 的读取占比。

## 2026 年仍在出货的陷阱

- **顶部放动态时间戳。** 在 system prompt 顶部写 `"Current time: 2026-04-22 15:30:02"`。每个请求都未命中。把时间戳移到 cache breakpoint 下方。
- **tool 重排。** 以稳定顺序序列化 tool——部署之间 dict 重排一次，所有命中都废了。
- **自由文本的近似重复。** "You are helpful." 与 "You are a helpful assistant."——差一个字节就是完全未命中。
- **块太小。** Anthropic 强制 1,024 token 的下限（Haiku 为 2,048）。更小的块会静默地不缓存。
- **盲目的成本看板。** 把 "input tokens" 拆成 cached 与 uncached。否则流量下滑看起来像 cache 胜利。

## Use It

2026 年的 caching 栈：

| 场景 | 选择 |
|-----------|------|
| 有稳定 10k+ system prompt、多轮对话的 agent | Anthropic `cache_control`，5 分钟 TTL |
| 复用前缀 30 分钟以上的批处理任务 | Anthropic，`ttl: "1h"` |
| GPT-5 上的 serverless 端点，没有自建基础设施 | OpenAI 自动（只要让前缀稳定且够长） |
| 跨天复用庞大的代码/文档语料 | Gemini 显式 `CachedContent` |
| 跨 provider 的 fallback | 在各 provider 之间保持完全相同的可缓存前缀布局，这样任何一次命中都能生效 |

配合 semantic caching（Phase 11 · 11）处理用户消息层：prompt caching 处理*token 完全相同*的复用，semantic caching 处理*语义相同*的复用。

## Ship It

保存 `outputs/skill-prompt-caching-planner.md`：

```markdown
---
name: prompt-caching-planner
description: Design a cache-friendly prompt layout and pick the right provider caching mode.
version: 1.0.0
phase: 11
lesson: 15
tags: [llm-engineering, caching, cost]
---

Given a prompt (system + tools + few-shot + retrieval + history + user) and a usage profile (requests per hour, TTL needed, provider), output:

1. Layout. Reordered sections with a single cache breakpoint marked; explain which sections are stable, which are volatile.
2. Provider mode. Anthropic cache_control, OpenAI automatic, or Gemini CachedContent. Justify from TTL and reuse pattern.
3. Break-even. Expected reads per write within TTL; net cost vs no-cache with math.
4. Verification plan. CI assertion that cache_read_input_tokens > 0 on the second identical request; dashboard split by cached vs uncached tokens.
5. Failure modes. List the three most likely reasons the cache will miss in this setup (dynamic timestamp, tool reorder, near-duplicate text) and how you will prevent each.

Refuse to ship a cache plan that places a dynamic field above the breakpoint. Refuse to enable 1h TTL without a reuse count that makes the 2x write premium pay back.
```

## Exercises

1. **简单。** 拿一段 10 轮对话、带 5,000 token system prompt，对 Claude 跑一遍。先不加 `cache_control`，再加。报告各自的输入 token 账单。
2. **中等。** 写一个测试 harness：给定 prompt 模板和请求日志，计算每个 provider（Anthropic 5m、Anthropic 1h、OpenAI 自动、Gemini 显式）的预期命中率和美元节省。
3. **困难。** 构建一个布局优化器：给定一个 prompt 和一组标记为 `stable=True/False` 的字段，在不丢失信息的前提下重写 prompt，把唯一的 cache breakpoint 放在最 cache 友好的位置。在真实的 Anthropic 端点上验证。

## Key Terms

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Prompt caching | "让长 prompt 变便宜" | 为匹配的前缀复用 provider 侧的 KV-cache；重复输入 token 打 50-90% 折扣。 |
| `cache_control` | "Anthropic 的那个标记" | content block 的属性，声明"到这里为止的内容都可缓存"；`{"type": "ephemeral"}`。 |
| Cache write | "付溢价" | 第一个填充 cache 的请求；在 Anthropic 上按约 1.25 倍输入费率计费，OpenAI 上免费。 |
| Cache read | "那个折扣" | 后续匹配前缀的请求；按 10%（Anthropic）、50%（OpenAI）、约 25%（Gemini）计费。 |
| TTL | "它能活多久" | cache 保持温热的秒数；Anthropic 默认 5 分钟（可延长到 1 小时），OpenAI 尽力而为最长 1 小时，Gemini 由用户设定。 |
| Extended TTL | "Anthropic 的 1 小时 cache" | `{"type": "ephemeral", "ttl": "1h"}`；写入溢价翻倍，但对批处理复用值得。 |
| Prefix match | "我的 cache 为什么没命中" | 只有当从开头到 breakpoint 的每个 token 都字节一致时，cache 才命中。 |
| Context caching（Gemini） | "显式的那个" | Google 的具名、按存储计费的 cache 对象；最适合跨天复用大型语料。 |

## Further Reading

- [Anthropic — Prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)——`cache_control`、1h TTL、盈亏平衡表。
- [OpenAI — Prompt caching](https://platform.openai.com/docs/guides/prompt-caching)——自动前缀匹配。
- [Google — Context caching](https://ai.google.dev/gemini-api/docs/caching)——`CachedContent` API 与存储定价。
- [Anthropic engineering — Prompt caching for long-context workloads](https://www.anthropic.com/news/prompt-caching)——原始发布文章，附延迟数据。
- Phase 11 · 05（Context Engineering）——在哪里切分 prompt，才能让 cache 落位。
- Phase 11 · 11（Caching and Cost）——把 prompt caching 与用户消息层的 semantic cache 配对使用。
- [Pope et al., "Efficiently Scaling Transformer Inference" (2022)](https://arxiv.org/abs/2211.05102)——prompt caching 向用户暴露的 KV-cache 内存模型；解释了为什么重读缓存前缀比重算便宜约 10 倍。
- [Agrawal et al., "SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills" (2023)](https://arxiv.org/abs/2308.16369)——prefill 正是 prompt caching 抄近路的阶段；这篇论文解释了为什么 cache 命中时 TTFT 大幅下降而 TPOT 不受影响。
- [Leviathan et al., "Fast Inference from Transformers via Speculative Decoding" (2023)](https://arxiv.org/abs/2211.17192)——prompt caching 与推测解码、Flash Attention、MQA/GQA 并列，都是压弯推理成本曲线的杠杆；读这篇可以了解另外三个。
