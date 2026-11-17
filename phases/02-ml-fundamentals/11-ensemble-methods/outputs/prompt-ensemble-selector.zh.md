---
name: prompt-ensemble-selector
description: 根据数据特征选择合适的集成方法
phase: 2
lesson: 11
---

# 集成选择 Prompt

给定问题描述，推荐合适的集成方法。

## 决策检查

1. 你需要概率输出吗？→ 随机森林或 GBDT 都能给，GBDT 的概率更可靠
2. 有类别特征吗？→ CatBoost 自动处理，XGBoost/LightGBM 需要预先编码
3. 实时预测（< 10ms）？→ LightGBM + 小 max_depth 或 LinearSVC
4. 小数据集（< 1k）？→ Bagging + SVM / KNN，或干脆用单模型交叉验证
5. 有标签噪声？→ 随机森林比 GBDT 更鲁棒（Bootstrap 采样隔离噪声）
6. 要可解释性？→ XGBoost/LightGBM 的 SHAP 值；随机森林的特征重要性

## 推荐

用结构化方式给出：选哪个、为什么、关键超参数建议。
