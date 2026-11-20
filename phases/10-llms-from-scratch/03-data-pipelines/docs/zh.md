# 预训练的数据流水线

> 模型是一面镜子。你喂它什么，它就反射什么。喂它垃圾，它就用完美的流畅度反射垃圾。

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 10, Lessons 01-02 (分词器、从零构建分词器)
**Time:** ~90 分钟
## Learning Objectives

- 构建流式数据流水线，对 TB 级文本做分词、分块、打乱和批处理，而不必全部载入内存
- 实现真实预训练流水线中使用的数据质量过滤器（去重、语言识别、内容过滤）
- 创建定长训练序列，配好 attention mask 和文档边界处理
- 剖析流水线吞吐，确保 dataloader 跟得上 GPU 训练速度

## 问题场景

你有分词器了。现在你需要数据。

不是一份数据集。不是一个 CSV 文件。是 TB 级的文本——清洗过、去重过、按质量过滤过、分词成定长序列，并以足够快的速度以随机批次供给，让你的 8 卡 GPU 集群从不等待下一个 batch。

大多数人以为训练 LLM 的关键是模型架构。不是。Llama 3 用了 15.6 万亿 token。GPT-3 用了 3000 亿。DeepSeek-V2 用了 8.1 万亿。这三者的架构大体相同：堆叠的 transformer 块，带 attention 和前馈层。输出质量的差异压倒性地来自数据。

DeepMind 的 Chinchilla 论文把这一点讲清楚了。给定算力预算，模型参数与训练 token 之间存在一个最优比例。Chinchilla 表明 2022 年的大多数模型都严重训练不足——相对于它们见到的数据量，参数太多了。一个 700 亿参数、在 1.4 万亿 token 上训练的模型（Chinchilla 最优）胜过一个 2800 亿参数、只在 3000 亿 token 上训练的模型（Gopher）。

你的数据流水线决定了你的模型学到的是语言，还是噪声。

## 核心概念

### 数据从哪来

每个大语言模型都在混合来源上训练。确切配比对多数实验室来说是严守的秘密，但我们知道的足够理解这些类别。

| 来源 | 规模 | 质量 | 使用者 |
|--------|------|---------|---------|
| Common Crawl | 约 250 TB 原始数据 | 低（需要重度过滤） | GPT-3、Llama、多数开源模型 |
| Wikipedia | 约 20 GB | 高 | 每个主流 LLM |
| GitHub 代码 | 约 1 TB+ | 中（大量重复、死代码） | StarCoder、CodeLlama、DeepSeek-Coder |
| 书籍（BookCorpus、Pile） | 约 100 GB | 高 | GPT-2、GPT-3、早期模型 |
| 学术论文（arXiv、S2ORC） | 约 100 GB | STEM 领域高 | Llama、Galactica |
| StackOverflow、Reddit | 约 100 GB | 中 | Llama、Falcon |
| 精选网页（C4、RefinedWeb） | 约 5 TB | 中高（已预过滤） | T5、Falcon |

Llama 3 公开了它的数据配比：约 50% 网页数据、25% 代码、13% 书籍与学术论文、8% 数学数据、4% 多语言网页数据。总计 15.6 万亿 token，原始文本超过 5 TB。

比例和总量同样重要。网页数据太多，模型就变成一只 Reddit 鹦鹉。代码太少，它不会编程。数学太少，它在推理上失败。把配比调对是训练 LLM 最难的部分之一，而且没有公式——需要实验和评估。

### 数据清洗

原始网页数据很脏。一份典型的 Common Crawl 转储包含：

- HTML 标签和 JavaScript
- 模板化的页眉、页脚、导航菜单
- 重复页面（完全相同和近乎重复）
- 机器生成的垃圾内容
- 个人可识别信息（PII）
- 低质量文本（关键词堆砌、SEO 垃圾）
- 被当作文本编码的非文本内容

清洗不是可选项。它决定了模型是生成连贯的段落，还是输出夹杂着商品列表的 HTML 标签。

```mermaid
graph TD
    A[原始文本] --> B[剥离 HTML]
    B --> C[语言识别]
    C --> D[质量过滤]
    D --> E[去重]
    E --> F[移除 PII]
    F --> G[干净文本]

    style A fill:#1a1a2e,stroke:#e94560,color:#fff
    style B fill:#1a1a2e,stroke:#e94560,color:#fff
    style C fill:#1a1a2e,stroke:#e94560,color:#fff
    style D fill:#1a1a2e,stroke:#e94560,color:#fff
    style E fill:#1a1a2e,stroke:#e94560,color:#fff
    style F fill:#1a1a2e,stroke:#e94560,color:#fff
    style G fill:#1a1a2e,stroke:#e94560,color:#fff
```

每一步消除一类噪声：

**剥离 HTML：** 移除所有标记。只保留可见的文本内容。`trafilatura` 或 `readability` 这类库会抽取文章正文，同时丢弃导航、广告和模板内容。

**语言识别：** 用 fastText 的语言识别模型（lid.176.bin）给每篇文档分类。过滤到你的目标语言。一篇被判为英文但置信度低于 0.8 的文档，很可能不是干净的英文。

**质量过滤：** 这里开始有意思了。RefinedWeb（Falcon 背后的数据集）使用基于困惑度的过滤器：在 Wikipedia 上训练一个小语言模型，然后给每篇文档打分。困惑度高意味着文档不像 Wikipedia——很可能是垃圾邮件、关键词列表或机器生成内容。困惑度超过阈值的文档会被移除。

**去重：** 影响最大的单个清洗步骤。Common Crawl 中包含海量重复页面——法律声明、cookie 提示、服务条款。在重复数据上训练会浪费算力，还可能让模型记住并逐字复述特定段落。

**移除 PII：** 姓名、邮箱地址、电话号码、社会安全号码。结构化 PII 用基于正则的检测，上下文中的姓名用 NER 模型。

### 用 MinHash 去重

精确去重很简单：对每篇文档做哈希，删掉重复的。但近重复才是真正的问题。同一篇新闻稿的两份副本，周围广告略有不同，就是近重复。内容 95% 相同，但逐字节比较时不同。

MinHash + 局部敏感哈希（LSH）能高效解决这个问题。

```mermaid
graph LR
    A[文档] --> B[Shingling]
    B --> C[MinHash 签名]
    C --> D[LSH 分桶]
    D --> E[候选对]
    E --> F[Jaccard 相似度]
    F --> G[去重后的集合]

    style A fill:#1a1a2e,stroke:#e94560,color:#fff
    style B fill:#1a1a2e,stroke:#e94560,color:#fff
    style C fill:#1a1a2e,stroke:#e94560,color:#fff
    style D fill:#1a1a2e,stroke:#e94560,color:#fff
    style E fill:#1a1a2e,stroke:#e94560,color:#fff
    style F fill:#1a1a2e,stroke:#e94560,color:#fff
    style G fill:#1a1a2e,stroke:#e94560,color:#fff
```

思路：

1. **Shingling：** 把每篇文档转换成一组 n-gram（例如词或字符的 5-gram）。"the quick brown fox" 用 3 词 shingle 就变成 {"the quick brown", "quick brown fox"}。

2. **MinHash：** 对每篇文档的 shingle 集合计算 k 个哈希值。每个哈希值是在不同哈希函数下所有 shingle 的最小哈希。这就造出一个定长 "签名"，近似任意两篇文档之间的 Jaccard 相似度。

3. **LSH：** 按 MinHash 签名的分段把文档分组到桶里。同一个桶里的文档是近重复候选。这样就避免了两两比较——你只比较候选对。

4. **验证：** 对每个候选对计算精确的 Jaccard 相似度。相似度超过阈值（通常是 0.8）就删掉一份副本。

Llama 团队报告称通过去重移除了约 38% 的网页数据。这不是个小数字。Common Crawl 里有超过三分之一是重复或近重复内容。

### 序列打包

你的模型期望定长输入序列。你的文档是变长的。有的 50 个 token。有的 50,000 个 token。

朴素做法：把每篇文档填充到最大序列长度。这会在毫无学习贡献的 padding token 上浪费大量算力。

更好的做法：把多篇文档打包进一条序列，用序列结束 token 分隔。一条 2048 token 的序列里可能装着三篇短文档，中间用 [EOS] token 隔开。

```mermaid
graph TD
    subgraph Naive Packing
        A1["文档 A（200 token）"] --> P1["[PAD] x 1848"]
        A2["文档 B（500 token）"] --> P2["[PAD] x 1548"]
        A3["文档 C（100 token）"] --> P3["[PAD] x 1948"]
    end

    subgraph Efficient Packing
        B1["文档 A（200） | 文档 B（500） | 文档 C（100） | 文档 D（400） | 文档 E（848）"]
    end

    style A1 fill:#1a1a2e,stroke:#e94560,color:#fff
    style A2 fill:#1a1a2e,stroke:#e94560,color:#fff
    style A3 fill:#1a1a2e,stroke:#e94560,color:#fff
    style P1 fill:#333,stroke:#666,color:#999
    style P2 fill:#333,stroke:#666,color:#999
    style P3 fill:#333,stroke:#666,color:#999
    style B1 fill:#1a1a2e,stroke:#16c784,color:#fff
```

attention mask 必须设置正确。在同一条打包序列里，文档 A 的 token 不应该 attend 到文档 B 的 token。这需要块对角（block-diagonal）的 attention mask。

长文档会被截断，或在序列边界处切块。切点很关键：从句子中间切，会迫使模型看到不完整的想法。有些流水线会尽量把切点对齐到段落或句子边界。

### Chinchilla 缩放定律

对于固定的算力预算 C（以 FLOPs 计），最优模型规模 N 和数据集规模 D 满足：

```
N_opt ~ C^0.5
D_opt ~ C^0.5
```

在实践中，这意味着你应该让模型规模和数据集规模大致等比例增长。参数多 10 倍的模型，要达到同样的 loss，大约需要多 10 倍的训练 token。

| 模型 | 参数量 | 训练 token 数 | Chinchilla 最优？ |
|-------|-----------|----------------|-------------------|
| GPT-3 | 175B | 300B | 否（训练不足 3-4 倍） |
| Chinchilla | 70B | 1.4T | 是（设计如此） |
| Llama 2 | 70B | 2T | 过度训练（有意为之） |
| Llama 3 | 70B | 15T | 严重过度训练 |

Llama 3 有意违反了 Chinchilla 定律。Meta 发现，在更多数据上过度训练——远超算力最优比例——能产出推理更好的模型。额外的训练成本只付一次，但更小的模型在服务上是永久更便宜的。这有时被称为 "推理最优" 缩放路线，自 2024 年以来已成为行业标准。

```figure
l5-data-pipeline
```

## Build It

### 第 1 步：文本清洗

剥离 HTML、归一化空白、移除非文本内容。我们用一个公共领域文本（Project Gutenberg）作为小语料。

```python
import re

def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^\x20-\x7E\n]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()

def quality_filter(text, min_words=50, max_ratio_caps=0.3, max_ratio_special=0.1):
    words = text.split()
    if len(words) < min_words:
        return False
    caps_ratio = sum(1 for w in words if w.isupper()) / len(words)
    if caps_ratio > max_ratio_caps:
        return False
    special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
    if special_chars / max(len(text), 1) > max_ratio_special:
        return False
    return True
```

质量过滤器能抓住 SEO 垃圾（全大写）、机器生成的噪声（特殊字符比例高）和占位页（太短）。仅这三项检查就能从网页抓取结果里清掉惊人数量的垃圾。

### 第 2 步：MinHash 去重

从零实现 MinHash。不需要外部库——只用 `hashlib`。

```python
import hashlib
from collections import defaultdict

def get_shingles(text, k=5):
    words = text.lower().split()
    if len(words) < k:
        return set()
    return {" ".join(words[i:i+k]) for i in range(len(words) - k + 1)}

def minhash_signature(shingles, num_hashes=128):
    signature = []
    for i in range(num_hashes):
        min_hash = float("inf")
        for shingle in shingles:
            h = int(hashlib.sha256(f"{i}:{shingle}".encode()).hexdigest(), 16)
            min_hash = min(min_hash, h)
        signature.append(min_hash)
    return signature

def lsh_buckets(signature, bands=16):
    rows_per_band = len(signature) // bands
    buckets = []
    for b in range(bands):
        start = b * rows_per_band
        band_data = tuple(signature[start:start + rows_per_band])
        bucket_hash = hashlib.md5(str(band_data).encode()).hexdigest()
        buckets.append((b, bucket_hash))
    return buckets

def deduplicate(documents, threshold=0.8, num_hashes=128, bands=16):
    signatures = []
    shingle_sets = []
    for doc in documents:
        shingles = get_shingles(doc)
        shingle_sets.append(shingles)
        signatures.append(minhash_signature(shingles, num_hashes))

    bucket_map = defaultdict(list)
    for doc_idx, sig in enumerate(signatures):
        for band_id, bucket_hash in lsh_buckets(sig, bands):
            bucket_map[(band_id, bucket_hash)].append(doc_idx)

    duplicate_pairs = set()
    for bucket_docs in bucket_map.values():
        if len(bucket_docs) < 2:
            continue
        for i in range(len(bucket_docs)):
            for j in range(i + 1, len(bucket_docs)):
                duplicate_pairs.add((bucket_docs[i], bucket_docs[j]))

    removed = set()
    for i, j in duplicate_pairs:
        if i in removed or j in removed:
            continue
        s1, s2 = shingle_sets[i], shingle_sets[j]
        if not s1 or not s2:
            continue
        jaccard = len(s1 & s2) / len(s1 | s2)
        if jaccard >= threshold:
            removed.add(j)

    return [doc for idx, doc in enumerate(documents) if idx not in removed], len(removed)
```

`num_hashes=128` 和 `bands=16` 这两个参数控制精确率与召回率的权衡。哈希越多，相似度估计越准。分段越多，召回越高（抓到更多重复），但误报也更多。这些取值对典型网页文本表现良好。

### 第 3 步：分词并打包序列

把干净、去重后的文本分词，再打包成定长序列用于训练。

```python
def tokenize_corpus(documents, tokenizer):
    all_tokens = []
    for doc in documents:
        tokens = tokenizer.encode(doc)
        all_tokens.extend(tokens)
        all_tokens.append(tokenizer.eos_id)
    return all_tokens

def pack_sequences(token_ids, seq_length, pad_id=0):
    sequences = []
    attention_masks = []
    for i in range(0, len(token_ids), seq_length):
        seq = token_ids[i:i + seq_length]
        mask = [1] * len(seq)
        if len(seq) < seq_length:
            pad_count = seq_length - len(seq)
            seq = seq + [pad_id] * pad_count
            mask = mask + [0] * pad_count
        sequences.append(seq)
        attention_masks.append(mask)
    return sequences, attention_masks
```

### 第 4 步：训练用的 DataLoader

产出随机化的打包序列批次。这就是训练循环所消费的东西。

```python
import random

class PreTrainingDataLoader:
    def __init__(self, sequences, attention_masks, batch_size, shuffle=True):
        self.sequences = sequences
        self.attention_masks = attention_masks
        self.batch_size = batch_size
        self.shuffle = shuffle

    def __len__(self):
        return (len(self.sequences) + self.batch_size - 1) // self.batch_size

    def __iter__(self):
        indices = list(range(len(self.sequences)))
        if self.shuffle:
            random.shuffle(indices)
        for start in range(0, len(indices), self.batch_size):
            batch_idx = indices[start:start + self.batch_size]
            batch_seqs = [self.sequences[i] for i in batch_idx]
            batch_masks = [self.attention_masks[i] for i in batch_idx]
            yield batch_seqs, batch_masks
```

### 第 5 步：数据集统计

计算那些真正重要的数字：总 token 数、唯一 token 数、压缩比、文档长度分布。

```python
from collections import Counter

def compute_statistics(documents, token_ids, sequences, tokenizer_vocab_size):
    total_chars = sum(len(d) for d in documents)
    total_tokens = len(token_ids)
    unique_tokens = len(set(token_ids))
    compression_ratio = total_chars / total_tokens

    doc_lengths = [len(d.split()) for d in documents]
    avg_doc_length = sum(doc_lengths) / max(len(doc_lengths), 1)
    max_doc_length = max(doc_lengths) if doc_lengths else 0
    min_doc_length = min(doc_lengths) if doc_lengths else 0

    token_counts = Counter(token_ids)
    top_tokens = token_counts.most_common(10)

    non_pad_tokens = sum(sum(1 for t in seq if t != 0) for seq in sequences)
    total_positions = sum(len(seq) for seq in sequences)
    utilization = non_pad_tokens / max(total_positions, 1)

    stats = {
        "total_documents": len(documents),
        "total_characters": total_chars,
        "total_tokens": total_tokens,
        "unique_tokens": unique_tokens,
        "vocab_utilization": unique_tokens / tokenizer_vocab_size,
        "compression_ratio": compression_ratio,
        "avg_doc_length_words": avg_doc_length,
        "max_doc_length_words": max_doc_length,
        "min_doc_length_words": min_doc_length,
        "num_sequences": len(sequences),
        "sequence_utilization": utilization,
        "top_10_tokens": top_tokens,
    }
    return stats
```

压缩比告诉你分词器在这个语料上有多高效。英文文本通常压缩到每个 token 约 3-4 个字符。如果看到每个 token 只有 1.5 个字符，说明你的分词器切得太碎了。如果看到 8 个以上，它学到了非常领域特定的合并。

序列利用率告诉你打包序列里有多少是真实数据、多少是 padding。低于 90% 意味着打包效率不行——你在 padding token 上浪费算力。

## Use It

### 与 HuggingFace Datasets 对比

用 HuggingFace 的 datasets 库加载同一份语料，比较流水线速度。

```python
from datasets import load_dataset
from transformers import AutoTokenizer

ds = load_dataset("wikitext", "wikitext-2-raw-v1", split="train")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3-8B")

import time

start = time.time()
tokenized = ds.map(
    lambda x: tokenizer(x["text"], truncation=True, max_length=2048),
    batched=True,
    num_proc=4,
)
hf_time = time.time() - start
total_tokens = sum(len(t) for t in tokenized["input_ids"])
print(f"HuggingFace: {total_tokens:,} tokens in {hf_time:.2f}s ({total_tokens/hf_time:,.0f} tokens/sec)")
```

HuggingFace 流水线底层用 Rust 分词器，并在 4 个核上并行处理。你的纯 Python 流水线会慢 10-50 倍。这个差距就是生产团队使用编译型分词器的原因。算法是一样的。差的是实现语言。

## Ship It

本课产出一个用于验证和调试 LLM 训练流水线数据质量的 prompt。见 `outputs/prompt-data-quality-checker.md`。

## Exercises

1. **简单：** 用简单启发式（字符集分析）给清洗流水线加上语言识别。只保留英文文档，并测量有多少文档被移除。
2. **中等：** 在 MinHash 近重复去重之外，用 SHA-256 哈希实现精确去重。在一个网页抓取语料上比较两种方法各自抓到的重复数量。
3. **困难：** 构建一个基于困惑度的质量过滤器。在 Wikipedia 文本上训练一个小 bigram 语言模型，按困惑度给每篇文档打分，移除最差的 20%。比较在过滤后数据与未过滤数据上训练的模型输出质量。

## Key Terms

| 术语 | 人们常说 | 实际含义 |
|------|----------------|----------------------|
| Common Crawl | "整个互联网" | 每月爬取网页的非营利组织——约 250TB 原始数据，多数 LLM 训练数据的起点 |
| MinHash | "某种哈希戏法" | 用定长签名估计集合间 Jaccard 相似度的技术——让大规模近重复检测成为可能 |
| LSH | "Locality-Sensitive Hashing" | 把相似条目分到同一个桶的方法——把两两比较从 O(n^2) 降到接近线性 |
| Sequence packing | "把文档拼起来" | 用正确的 attention mask 把多篇文档装进定长序列——消除 padding 浪费 |
| Chinchilla scaling | "拿更多数据训练" | 在固定算力预算下，最优性能要求模型规模和训练 token 大致等比扩展 |
| Fertility | "每个词的 token 数" | 每个词的平均 token 数——GPT-4 里英文是 1.3，非拉丁文字更高 |
| Data mixing | "选择训练数据" | 代码与文本、数学、多语言数据的比例——没有公式，需要实验 |
| Perplexity filter | "质量打分" | 用小语言模型给文档打分——困惑度高说明文本不像干净的参考数据 |
| Deduplication | "删掉副本" | 消除完全相同和近重复的文档——通常能删掉 30-40% 的原始网页数据 |
| Attention mask | "该看哪些 token" | 一个二值掩码，阻止打包序列中跨文档边界的 attention |

## Further Reading

- [Hoffmann et al., 2022 -- Training Compute-Optimal Large Language Models (Chinchilla)](https://arxiv.org/abs/2203.15556) —— 改变了我们对数据规模认知的论文
- [Penedo et al., 2023 -- The RefinedWeb Dataset for Falcon LLM](https://arxiv.org/abs/2306.01116) —— 如何把 Common Crawl 过滤到高质量
- [Touvron et al., 2023 -- Llama 2: Open Foundation and Fine-Tuned Chat Models](https://arxiv.org/abs/2307.09288) —— Llama 2 的数据流水线细节
- [Lee et al., 2022 -- Deduplicating Training Data Makes Language Models Better](https://arxiv.org/abs/2107.06499) —— 为什么去重比你想象的更重要
- [Broder, 1997 -- On the Resemblance and Containment of Documents](https://ieeexplore.ieee.org/document/666900) —— MinHash 的原始论文
- [Meta, 2024 -- Llama 3 Technical Report](https://arxiv.org/abs/2407.21783) —— 15.6T token、数据混合比例、过滤流水线
