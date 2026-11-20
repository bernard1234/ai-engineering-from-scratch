---
name: skill-tokenizer
description: 为 LLM 项目选择和构建 tokenizer
version: 1.0.0
phase: 10
lesson: 1
tags: [tokenizer, bpe, wordpiece, sentencepiece, llm, nlp]
---

# Tokenizer 的选择与实现

启动 LLM 项目时，用这个决策框架来选择 tokenizer。

## 各类 tokenizer 的适用场景

**Byte-level BPE（tiktoken）：** 你在 GPT 系列模型上构建或微调。你需要保证任意输入字节序列都能被处理。你不希望出现 unknown token。

**WordPiece（Hugging Face）：** 你使用 BERT 系列模型做分类、NER 或 embedding 任务。你需要 "##" 续接前缀，以服务依赖词边界信号的下游任务。

**SentencePiece（BPE 或 Unigram）：** 你从头训练。你需要与语言无关的 tokenization。你的数据包含 CJK 语言、泰语或其他没有空白词边界的文字系统。LLaMA、T5 和大多数多语言模型都用它。

## 词表大小指南

- 32K tokens：单语言模型的良好默认值，embedding 层保持较小
- 50K-64K tokens：更适合多语言或代码密集的模型
- 100K+ tokens：只有当你有海量训练数据且想要更短序列时才用

更大的词表意味着更短的序列（推理更便宜），但 embedding 矩阵参数更多。对于 100K 词表和 4096 维 embedding，仅 embedding 层就有 400M 参数。

## 重要的 pre-tokenization 规则

1. 在 BPE 之前按空白切分，防止跨词合并
2. 如果你想让模型学会算术，把数字逐位分开
3. 在 tokenization 之前做 Unicode 规范化（NFC），保证行为一致
4. 为你的用例添加特殊 token：`<pad>`、`<eos>`、`<bos>`、`<unk>`，以及任何任务专用标记

## tokenizer 行为的危险信号

- 目标语言的 fertility 高于 2.0：模型在浪费上下文窗口
- 常见领域词被切成 3 个及以上 token：用领域数据重新训练
- 数字的 tokenization 不一致：检查数字切分规则
- 词表很大但有很多只用一次的 token：减小词表

## 构建自定义 tokenizer —— 检查清单

1. 收集有代表性的训练数据（目标领域至少 1GB 文本）
2. 选择算法：通用场景用 BPE，多语言用 Unigram
3. 按上面的指南设置词表大小
4. 配置 pre-tokenization：空白切分、数字处理、标点
5. 添加特殊 token
6. 用 Hugging Face tokenizers 库训练（Rust 后端，快）
7. 验证：在所有目标语言的留出文本上检查 fertility
8. 测试边界情况：空字符串、超长输入、二进制数据、emoji、RTL 文本
9. 把 tokenizer 与模型 checkpoint 一起保存并做版本管理
