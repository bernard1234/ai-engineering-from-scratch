---
name: prompt-alignment-method-selector
description: 为你的用例选择正确的对齐方法（SFT、RLHF、DPO、KTO、ORPO、SimPO）
version: 1.0.0
phase: 10
lesson: 8
tags: [alignment, dpo, rlhf, kto, orpo, simpo, preference-optimization, fine-tuning]
---

# 对齐方法选择器

当你为语言模型选择对齐方法时，用这个框架评估你的数据、算力和质量要求，然后选出最贴合你约束的方法。

## 输入要求

请提供：
- **基础模型**（例如 Llama 3 8B、Mistral 7B、Qwen 2.5 72B）
- **起点**（基础模型，还是已经做过 SFT？）
- **可用数据**（指令对、偏好对、非成对评分，或没有）
- **算力预算**（GPU 小时数、GPU 数量）
- **质量目标**（够做原型、可与开源模型竞争、state-of-the-art）
- **时间线**（天、周、月）

## 决策矩阵

### 快速选择

| 你的情况 | 推荐方法 | 原因 |
|---------------|-------------------|-----|
| 没有偏好数据，只有指令对 | 只做 SFT | 没有偏好信号就无法对齐 |
| 少于 5,000 组偏好对，算力有限 | DPO | 流水线更简单，小数据下表现良好 |
| 非成对反馈（只有 thumbs up/down） | KTO | 唯一不需要成对比较就能工作的方法 |
| 想在单次训练中完成对齐 | ORPO | 合并 SFT + 对齐，不需要 reference model |
| 内存受限（装不下 reference model） | SimPO | 不需要 reference model |
| 大规模、多目标对齐 | RLHF（PPO） | 独立的 reward model 能捕捉复杂偏好 |
| 使用在线数据迭代对齐 | RLHF（PPO） | 可以在循环中生成、评分、重训 |
| RLHF 之后的精修 | DPO | 在目标偏好上微调 RLHF 模型 |

### 详细对比

| 方法 | 数据要求 | 内存中模型数 | 训练循环数 | 稳定性 | 最佳规模 |
|--------|-----------------|-----------------|----------------|-----------|------------|
| SFT | 指令对（10K+） | 1 | 1 | 高 | 任意 |
| RLHF | 偏好对（20K+） | 3-4 | 3 | 低 | 大规模（70B+） |
| DPO | 偏好对（5K+） | 2 | 2（SFT + DPO） | 高 | 小到中等（7B-70B） |
| KTO | 非成对评分（5K+） | 2 | 2（SFT + KTO） | 高 | 任意 |
| ORPO | 偏好对（10K+） | 1 | 1 | 高 | 小到中等 |
| SimPO | 偏好对（5K+） | 1 | 2（SFT + SimPO） | 高 | 小到中等 |

## 各方法专属配置

### SFT

- **何时停止**：1-3 个 epoch 之后，或验证 loss 不再下降时
- **关键超参数**：学习率（1e-5 到 5e-5，模型越大越低）
- **关键细节**：在 loss 中屏蔽指令 token
- **坑点**：超过 3 个 epoch 会导致记忆化；混入 2-5% 预训练数据

### RLHF（PPO）

- **何时使用**：你有 20K+ 组比较对，需要多目标对齐，或想做迭代式在线学习
- **关键超参数**：KL 系数（0.01-0.05）、PPO clip 比例（0.1-0.3）、学习率（5e-6 到 3e-5）
- **关键细节**：reward model 应 >= policy model 规模
- **坑点**：PPO 不稳定；持续监控 KL 散度和 reward 曲线

### DPO

- **何时使用**：你有偏好对，且想要比 RLHF 更简单的流水线
- **关键超参数**：Beta（0.1-0.5；越低允许偏离 reference 越多）
- **关键细节**：reference model 必须是 SFT checkpoint 的冻结副本
- **坑点**：对 beta 非常敏感；在 [0.05, 0.1, 0.2, 0.5] 上做 sweep

### KTO

- **何时使用**：你只有 "good" 或 "bad" 标签，没有成对比较
- **关键超参数**：Beta（与 DPO 相同）、损失厌恶乘数（对 bad 回答取 1.5 倍）
- **关键细节**：需要大致平衡的 good/bad 样本（40-60% 的划分）
- **坑点**：没有成对信息时梯度信号更弱；可能比 DPO 需要更多数据

### ORPO

- **何时使用**：你想完全跳过 SFT，直接从基础模型走到对齐模型
- **关键超参数**：Lambda（偏好项与 SFT 项的权重）
- **关键细节**：同一个数据集里既需要指令标签又需要偏好对
- **坑点**：组合目标很难平衡；如果 SFT loss 占主导，对齐效果会很弱

### SimPO

- **何时使用**：内存受限，装不下 reference model 的环境
- **关键超参数**：Beta、gamma（长度归一化指数）
- **关键细节**：长度归一化防止模型偏好简短回答
- **坑点**：没有 reference model 作锚点，模型可能漂移得更远；需仔细监控

## 流水线模板

### 模板 1：快速原型（1-2 天）

```
Base Model -> SFT (1 epoch, 10K examples) -> DPO (3 epochs, 5K pairs)
```

算力：7B 模型在 A100 上约 4 GPU-hours
质量：稳定的指令遵循，基础的偏好对齐

### 模板 2：生产质量（1-2 周）

```
Base Model -> SFT (2 epochs, 50K examples) -> DPO (5 epochs, 20K pairs) -> Eval -> Iterate
```

算力：7B 约 40 GPU-hours，70B 约 200 GPU-hours
质量：可与开源 RLHF 模型竞争

### 模板 3：State-of-the-Art（1-3 个月）

```
Base Model -> SFT (2 epochs, 100K+ examples) -> RLHF (PPO, 50K+ pairs) -> DPO (targeted refinement) -> Eval -> Iterate
```

算力：70B 约 500+ GPU-hours
质量：接近前沿模型的对齐水平

### 模板 4：最少数据（1-2 天）

```
Base Model -> SFT (1 epoch, 5K examples) -> KTO (unpaired thumbs up/down from users)
```

算力：7B 约 2 GPU-hours
质量：数据采集开销极小的前提下，优于只做 SFT

## 评估协议

对齐之后，在以下维度评估：

1. **偏好胜率**：由人工评审在 200+ 个测试 prompt 上比较对齐模型与 SFT 模型。目标：> 60% 胜率。
2. **Benchmark 保持**：MMLU、HumanEval 或领域专用 benchmark。相对 SFT 基线下降不应 > 5%。
3. **MT-Bench 或 AlpacaEval**：标准对齐质量 benchmark。与已发布的基线比较。
4. **安全评估**：针对对抗 prompt、jailbreak 和有害请求类别进行测试。
5. **回答多样性**：测量 100 个 prompt 上回答的熵。熵低 = 模式崩溃。

## 常见失败模式

| 症状 | 原因 | 方法专属修复 |
|---------|-------|-------------------|
| 回答冗长、注水 | Reward model / 隐式 reward 偏好长度 | DPO：提高 beta。RLHF：加长度惩罚。SimPO：调整 gamma。 |
| 模型对一切都表示赞同 | 偏好数据偏差导致的谄媚 | 加入正确回答与用户意见相左的偏好对 |
| 拒绝良性请求 | 在安全数据上对齐过度 | 降低安全样本比例，增加良性-拒绝配对 |
| 输出与 SFT 几乎一样 | Beta 过高（DPO/KTO）或 KL 系数过高（PPO） | 降低 beta / KL 系数；模型没在学 |
| 训练 loss 震荡 | 学习率过高或数据不足 | 把 lr 降低 2-3 倍；增加偏好数据 |
