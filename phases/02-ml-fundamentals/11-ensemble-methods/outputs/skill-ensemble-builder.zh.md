---
name: skill-ensemble-builder
description: 构建梯度提升集成并选择合适的超参数
version: 1.0.0
phase: 2
lesson: 11
tags: [ensemble, gradient-boosting, xgboost, lightgbm, stacking]
---

# 梯度提升构建指南

## 什么时候用

- 表格数据（结构化特征）
- 中等大数据集（1k–1000k 行）
- 需要可解释性（树模型天生可解释）

## 主流实现对比

| 库 | 特点 | 什么时候用 |
|----|------|------------|
| XGBoost | 最成熟、最常赢 Kaggle | 基线首选 |
| LightGBM | 直方图加速、快 | 大数据集、实时需求 |
| CatBoost | 自动处理类别、防泄露 | 有很多类别特征时 |

## 关键超参数

- n_estimators：树的数量。通常 100–500。配合早停。
- max_depth：单棵树深度。3–8 通常够用。越深越易过拟合。
- learning_rate（eta）：每棵树贡献权重。通常 0.01–0.1。越小需要越多树。
- subsample：样本采样比。0.7–1.0。引入随机性防过拟合。
- colsample_bytree：特征采样比。同上。

## 调参建议

1. 先小范围粗调 learning_rate + n_estimators
2. 然后调树深度和叶节点最小样本数
3. 再加正则化（lambda、alpha）
4. 用早停自动决定树数量

## 常见错误

- learning_rate 和 n_estimators 独立调（它们是乘法关系）
- max_depth 设太大（8+ 容易过拟合）
- 忘了 scale 特征（树不需要，但 stacking 里的线性模型需要）
- 在最终模型上用了验证集（需要把 train + val 合并再训）
