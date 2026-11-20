---
name: prompt-tokenizer-builder
description: 为 LLM 项目构建并调试生产级 tokenizer
version: 1.0.0
phase: 10
lesson: 2
tags: [tokenizer, bpe, byte-level, special-tokens, chat-template, multilingual]
---

# 生产级 Tokenizer 构建器

当你为 LLM 项目构建或调试 tokenizer 时，遵循此框架。

## 流水线检查清单

每个生产级 tokenizer 都需要这五个阶段。缺任何一步，你都会在生产中撞上边界情况。

1. **Normalize（规范化）** —— 应用 NFKC Unicode 规范化。它会折叠连字（"fi" -> "fi"），规范化全角字符，并统一空白。跳过这一步，同一个词就会因为你输入方式不同而得到不同的 token ID。

2. **Pre-Tokenize（预切分）** —— 在 BPE 之前把文本切成块。以英文为主的模型用 GPT-2 的正则模式。多语言模型用 SentencePiece 的原始字节方案。这个选择决定 BPE 能否跨词边界合并。

3. **BPE Merge（BPE 合并）** —— 对每个块内的字节序列应用学到的合并表。合并表就是 tokenizer 学到的全部知识。其余都只是管道工程。

4. **Special Token Injection（特殊 token 注入）** —— 在 BPE 运行之前精确匹配特殊 token。[BOS]、[EOS]、[PAD]、chat template 标记获得固定 ID。它们永远不参与合并。

5. **ID Mapping（ID 映射）** —— 把 token 字符串转成整数。模型只看到整数。

## 调试 tokenizer 问题

**症状：模型对 chat 输入输出乱码**
- 检查 chat template。每个模型的格式都不同。Llama 3 使用 `<|start_header_id|>` 标记。ChatGPT 使用 `<|im_start|>` 标记。模板错了，输入就落在训练分布之外。

**症状：非英文文本用了太多 token**
- 检查 fertility（每词 token 数）。高于 2.0 意味着 tokenizer 在该语言上浪费上下文窗口。解决方案：用更多多语言数据重新训练、增大词表，或改用 Unigram 的 SentencePiece。

**症状：数字和算术失败**
- 检查数字如何被 tokenize。"1234" 作为单个 token 意味着模型无法做数字级操作。在 pre-tokenization 时把数字逐位拆开。

**症状：代码 token 效率低**
- 检查缩进如何处理。GPT-2 的 tokenizer 在空格上浪费 token。Codex 和 StarCoder 使用特殊的缩进 token（4 个空格 = 1 个 token）。

## 词表大小决策

- 32K tokens：单语言、小模型、算力有限。embedding 层为 32K * d_model 参数。
- 50K-64K：多语言或代码密集。对大多数项目是良好平衡。
- 100K+（GPT-4、Llama 3）：只有拥有海量训练数据时才用。序列更短，但 embedding 参数为 100K * d_model。

对于 4096 维模型：32K 词表 = 131M embedding 参数。128K 词表 = 524M embedding 参数。仅 embedding 层就有 400M 参数。

## 速度要求

- 训练数据 tokenization：使用 Rust 后端库（tiktoken、HuggingFace tokenizers）。纯 Python 慢 10-100 倍。
- 推理 tokenization：延迟影响较小（单条序列），但仍应使用编译实现。
- 基准测试：tokenize 1GB 文本并测量 wall clock 时间。如果超过 60 秒，就换 Rust 后端。

## Chat Template 校验

部署任何 chat 模型之前，验证模板：

1. 用 tokenizer 编码一段已知对话
2. 解码回文本
3. 与模型文档中的期望格式逐字符比较
4. 注意：header token 之后的换行、内容之前的空格、回合结束标记
5. 测试边界情况：空的 system 消息、超长 user 消息、多个 assistant 回合

chat template 搞错是 chat 模型效果下降最常见的原因。
