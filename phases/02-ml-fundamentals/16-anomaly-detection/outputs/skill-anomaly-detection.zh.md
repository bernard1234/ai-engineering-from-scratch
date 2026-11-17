---
name: skill-anomaly-detection
description: 根据数据特性选择合适的异常检测方法
version: 1.0.0
phase: 2
lesson: 16
tags: [anomaly-detection, isolation-forest, lof, novelty]
---

# 异常检测方法选择指南

## 问题类型区分

| 类型 | 描述 | 方法 |
|------|------|------|
| Point anomalies | 单个数据点偏离其他点 | 最常见，任何方法都能处理 |
| Collective anomalies | 一个连续序列都异常 | 时间序列需特殊方法 |
| Contextual anomalies | 同一值在不同上下文是否异常不同 | 需要显式上下文特征 |

## 方法选择

| 数据特性 | 推荐方法 | 说明 |
|----------|----------|------|
| 小到中等数据集、未知簇 | Isolation Forest | 快、简单、自动给分数 |
| 已知正常类、找新类 | One-Class SVM | 拟合正常数据分布边界 |
| 局部异常、密度变化大 | LOF（Local Outlier Factor） | 基于局部密度偏差 |
| 低维可视化 | 3-sigma 或 IQR | 简单统计阈值 |
| 时序数据 | STL + 残差阈值 | 去趋势后检测残差异常 |

## 常见错误

- 用分类器做异常检测（需要标签，而你没有）
- 选污染率（contamination）时只靠猜测——先用 0.05–0.1 范围试
- 完全忽略数据漂移（训练时的正常模式可能随时间变了）
