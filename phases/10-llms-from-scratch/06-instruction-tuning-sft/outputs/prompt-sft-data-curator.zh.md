---
name: prompt-sft-data-curator
description: 为监督微调设计并整理指令数据集
version: 1.0.0
phase: 10
lesson: 6
tags: [sft, instruction-tuning, fine-tuning, data-curation, alignment]
---

# SFT 数据策划师

当你为某一项特定能力（代码生成、数学、对话、安全）设计指令微调数据集时，用这个框架规划数据采集、定义质量标准并组织训练流水线。

## 输入要求

请提供：
- **目标能力**（例如 "Python code generation"、"medical Q&A"、"multi-turn conversation"）
- **基础模型**（例如 Llama 3 8B、Mistral 7B、Qwen 2.5 72B）
- **预算**（标注工时、合成生成的 API 成本）
- **格式偏好**（Alpaca、ShareGPT、ChatML）

## 第 1 步：数据集设计

### 规模指南

| 质量等级 | 所需样本数 | 预期结果 |
|--------------|----------------|------------------|
| 研究原型 | 1,000-5,000 | LIMA 级：如果样本由专家撰写，可与更大的数据集相媲美 |
| 生产 v1 | 10,000-50,000 | Stanford Alpaca 级：在常见任务上稳定遵循指令 |
| 生产 v2 | 50,000-200,000 | Vicuna/Llama 2 Chat 级：稳健的多轮能力与领域覆盖 |

质量永远胜于数量。1,000 个专家撰写的样本（LIMA，2023 年 5 月）就追平了在 50,000+ 样本上训练的模型。优先级：

1. **多样性** —— 覆盖目标能力的完整范围
2. **准确性** —— 每个回答必须在事实上正确
3. **清晰度** —— 回答应简洁且结构良好
4. **难度梯度** —— 包含简单、中等和困难样本

### 多样性检查清单

对于通用助手：
- 开放式问题（20%）
- 事实问答（20%）
- 创意写作（10%）
- 代码生成（15%）
- 推理与数学（15%）
- 摘要（10%）
- 带约束的指令遵循（10%）

针对领域专用模型调整百分比。编程助手可以分配 60% 给代码生成、20% 给代码解释。

## 第 2 步：数据格式

### Alpaca 格式（单轮）

```json
{
  "instruction": "Write a function that reverses a string in Python.",
  "input": "",
  "output": "def reverse_string(s):\n    return s[::-1]"
}
```

适用场景：单轮任务、简单的指令-回答对、快速原型。

### ShareGPT 格式（多轮）

```json
{
  "conversations": [
    {"from": "system", "value": "You are a Python expert."},
    {"from": "human", "value": "How do I reverse a string?"},
    {"from": "gpt", "value": "Use slicing: s[::-1]"},
    {"from": "human", "value": "What about for a list?"},
    {"from": "gpt", "value": "Same syntax works: my_list[::-1]"}
  ]
}
```

适用场景：对话式应用、多轮上下文很重要时。

### ChatML 格式（带特殊 token）

```
<|im_start|>system
You are a Python expert.<|im_end|>
<|im_start|>user
How do I reverse a string?<|im_end|>
<|im_start|>assistant
Use slicing: s[::-1]<|im_end|>
```

适用场景：目标模型原生使用 ChatML 时（Qwen、Yi）。

## 第 3 步：质量标准

### 单样本检查

1. **回答相关性**：回答是否真的回应了指令？
2. **事实准确性**：所有陈述是否可验证且正确？
3. **完整性**：回答是否充分处理了指令？
4. **简洁性**：同样的信息能否用更少的词表达？
5. **格式一致性**：回答是否遵循期望的风格？

### 危险信号（拒绝该样本）

- 回答自相矛盾
- 回答包含有害内容且未拒绝
- 回答编造事实或引用
- 指令含糊，而回答未做澄清
- 回答只是把指令换个说法复述一遍

### 数据集级检查

- 来自任何单一来源/模板的样本不超过 5%
- 至少 80% 的回答 token 是有意义的（不是填充内容）
- 平均回答长度为 50-200 tokens（避免过短或过长）
- System prompt 多样性：至少涵盖 10 个不同的 system prompt

## 第 4 步：训练配置

| 参数 | 推荐范围 | 说明 |
|-----------|------------------|-------|
| 学习率 | 1e-5 到 5e-5 | 大模型取低值（70B 用 1e-5，7B 用 5e-5） |
| Epochs | 1-3 | 监控验证 loss，一旦上升就停止 |
| Batch size | 32-128 | 受 GPU 限制时用 gradient accumulation 扩展 |
| Warmup | 总步数的 0-5% | 不如预训练时关键 |
| Weight decay | 0.0-0.1 | 短时间微调可选 |
| Loss masking | 仅回答 token | 屏蔽指令和 system prompt 的 token |
| 混入预训练数据 | 2-5% | 混入原始文本以防止灾难性遗忘 |

## 第 5 步：评估协议

训练后，在以下方面评估：

1. **指令遵循率**：模型给出相关且完整回答的测试 prompt 占比
2. **遗忘分数**：在留出的通用文本语料上的 perplexity，与基础模型对比
3. **格式合规率**：遵循期望 chat 格式的回答占比
4. **MT-Bench 或 AlpacaEval**：指令微调模型的标准 benchmark
5. **领域专用评估**：针对目标能力的自定义评估

### 警告信号

- 第 1 个 epoch 之后验证 loss 上升：你在过拟合，减少 epochs 或增加数据
- 遗忘分数上升 > 15%：学习率过高或 epochs 过多
- 模型逐字复现训练样本：严重过拟合，需要更多样化的数据
- 模型拒绝良性指令：在安全数据上训练过度，重新平衡数据集
