# ML Pipelines

> 好的流水线把零散步骤组织成可复现的整体。

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 2 Lessons 8-12 (Feature Engineering through Tuning)
**Time:** ~45 minutes

## Learning Objectives

- 列出 ML 项目从数据到部署的完整流水线阶段
- 用 scikit-learn Pipeline / ColumnTransformer 构建可复现的预处理 + 训练流水线
- 说明为什么所有预处理步骤必须用训练集 fit 然后对两者 transform
- 讨论模型部署、版本管理和监控的要点

## 核心概念

### 完整流水线

```
获取数据 → 验证 → 预处理 → 特征工程 → 训练 → 评估 → 选择 → 部署 → 监控
```

### scikit-learn Pipeline

把多个步骤串起来，一个 fit 调用自动传递数据：

```python
pipe = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression()),
])
pipe.fit(X_train, y_train)
pipe.score(X_test, y_test)
```

ColumnTransformer：对不同列做不同预处理。

### 部署

- Flask/FastAPI 包 REST 端点
- 模型持久化：joblib.pickle / ONNX / TorchScript
- 版本管理：MLflow / DVC
- 推理服务：实时（< 100ms）或批量

### 监控

- 数据漂移：PSI（Population Stability Index）
- 性能退化：持续评估业务指标
- 反馈回路：线上预测 vs 真实结果的持续收集

## Build It

### Step 1: 从零预处理流水线（填充 + 缩放 + 编码）

### Step 2: scikit-learn Pipeline + ColumnTransformer

### Step 3: 用 FastAPI 做简单推理服务

## Use It

## Exercises

## Key Terms

## Further Reading
