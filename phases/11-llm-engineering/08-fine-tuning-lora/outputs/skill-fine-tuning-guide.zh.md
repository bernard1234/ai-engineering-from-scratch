---
name: skill-fine-tuning-guide
description: 判断何时以及如何用 LoRA 和 QLoRA 微调 LLM 的决策树
version: 1.0.0
phase: 11
lesson: 8
tags: [fine-tuning, lora, qlora, peft, llm-engineering]
---

# 微调决策指南

微调之前，按顺序先尝试这些手段：

```
1. Prompt engineering (minutes, $0)
2. Few-shot examples in prompt (minutes, $0)
3. RAG for knowledge retrieval (days, $10-100/month)
4. Fine-tuning with LoRA/QLoRA (days, $5-50 per experiment)
5. Full fine-tuning (weeks, $100-10,000 per run)
```

只有当前一步被可度量地证明不够用时，才进入下一步。

## 何时应该微调

- 模型需要一种 prompt 无法达成的、稳定的输出风格或格式
- 你在蒸馏一个更大的模型（用 8B 模型得到 GPT-4 的质量）
- 延迟很重要，而 few-shot 示例占用了太多 token
- 你需要模型可靠地遵循复杂的推理模式
- 你手上有 1,000+ 个高质量的、符合期望输入输出行为的样本

## 何时不该微调

- 配上合适的 prompt，模型已经能做到你想要的效果
- 你需要模型掌握事实知识（改用 RAG）
- 你的训练样本少于 500 个（很可能过拟合）
- 任务频繁变化（重新训练的成本太高）
- 你需要审计哪些数据影响了某个具体输出（微调是黑盒）

## 方法选择

| GPU VRAM | 7B 模型 | 13B 模型 | 70B 模型 |
|----------|----------|-----------|-----------|
| 16GB (T4) | QLoRA | 不可行 | 不可行 |
| 24GB (3090/4090) | QLoRA 或 LoRA | QLoRA | 不可行 |
| 40GB (A100) | LoRA 或 Full | QLoRA 或 LoRA | QLoRA |
| 80GB (A100/H100) | Full | LoRA 或 Full | QLoRA 或 LoRA |

## LoRA 配置清单

1. 从 r=16、alpha=32 开始（对大多数任务都是安全的默认值）
2. 先只对 q_proj 和 v_proj 做 target（最小可行的 LoRA）
3. QLoRA 用学习率 2e-4，LoRA fp16 用 5e-5
4. 设 lora_dropout=0.05
5. 训练 1-3 个 epoch（再多有过拟合风险）
6. 每 100 步在留出集上做一次 eval
7. 保存 checkpoint，按 eval loss 挑选最好的

## 常见错误

- 训练 epoch 太多（小数据集上第 2-3 个 epoch 之后就开始过拟合）
- 沿用全量微调的学习率（LoRA 需要更高的 LR）
- 忘记设置 pad token（Llama 系列模型上会导致 NaN loss）
- 没有冻结基础模型（这违背了 LoRA 的初衷）
- 只在训练数据上评估（始终留出 10-20% 做 eval）
- 跳过 prompt engineering 基线（去微调一个 prompt 已经能解决的问题）

## 质量验证

训练完成后，在 200+ 个留出样本上对比：
1. 最佳 prompt 下的基础模型（baseline）
2. 加 LoRA adapter 的基础模型（你的微调模型）
3. 相同 prompt 下的 GPT-4 或 Claude（上限）

如果 LoRA 模型赢不过加了 prompt 的基线，那么需要改进的是训练数据或配置，而不是加更多算力。

## Adapter 管理

- 多任务服务时把 adapter 分开保存（每次请求切换 adapter）
- 单任务部署时把 adapter 合并进基础权重
- 把 adapter 存到 Hugging Face Hub（10-100MB，易于版本管理和分享）
- 部署前测试合并后的模型输出与未合并的输出一致
- 用 TIES-Merging 或 DARE 把多个 adapter 合并成一个

## 调试训练

如果 loss 不下降：
1. 检查学习率（对 LoRA 而言可能太低，试试 2e-4）
2. 确认 LoRA 层确实在接收梯度
3. 确认基础模型的权重处于冻结状态
4. 检查数据格式（tokenizer 必须匹配模型期望的格式）

如果 loss 下降但 eval 质量很差：
1. 训练数据质量问题（garbage in, garbage out）
2. 过拟合（减少 epoch、增大 dropout、补充更多数据）
3. target module 选错（复杂任务要加上 MLP 层）
4. rank 太低（试试 r=32 或 r=64）
