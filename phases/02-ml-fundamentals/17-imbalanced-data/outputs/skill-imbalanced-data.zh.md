---
name: skill-imbalanced-data
description: 处理类别不平衡数据的策略选择
version: 1.0.0
phase: 2
lesson: 17
tags: [imbalanced-data, oversampling, undersampling, class-weight]
---

# 类别不平衡处理策略

## 第 1 步：确认不平衡程度

- < 5:1：通常不需要调整，用 F1/AUC 代替 Accuracy 即可
- 5:1 到 50:1：考虑 class_weight 或轻微重采样
- > 50:1：重采样或专门方法

## 第 2 步：选策略

| 策略 | 何时用 | 风险 |
|------|--------|------|
| class_weight="balanced" | 任何场景都能先试 | 可能改变决策边界 |
| 欠采样多数类 | 多数类极大 > 少数类 | 丢弃信息 |
| SMOTE 过采样少数类 | 少数类有一些样本（>20） | 可能生成噪声样本 |
| ADASYN 自适应过采样 | 少数类分布不均匀 | 同上 |
| SMOTE + Tomek Links | 过采样后清理边界 | 更干净但更慢 |

## 第 3 步：必须做的事

- 切分数据**之后**再重采样（防泄露！）
- 用分层交叉验证
- 评估少数类的精确率、召回率，不要只看 Accuracy
- 画 ROC 曲线和 Precision-Recall 曲线（PR 曲线在不平衡下更有信息量）

## 常见错误

- 切分前重采样（测试集信息泄露到训练集）
- 重采样后没调整决策阈值
- 用 Accuracy 汇报，掩盖少数类上的失败
