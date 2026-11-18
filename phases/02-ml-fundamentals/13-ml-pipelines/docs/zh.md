# ML 流水线

> 模型不是产品。流水线才是。流水线是从原始数据到部署预测的一切，每一步都必须可复现。

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 2, Lesson 12 (超参数调优)
**Time:** ~120 minutes

## Learning Objectives

- 从零构建把填充、缩放、编码和模型训练串成一个可复现对象的 ML 流水线
- 识别数据泄露场景，解释流水线怎么通过只在训练数据上拟合转换器来预防它们
- 构建对数值和类别特征应用不同预处理的 ColumnTransformer
- 实现流水线序列化，演示同一个拟合好的流水线在训练和生产上产生相同结果

## 问题场景

你有一个 notebook，加载数据、用中位数填缺失值、缩放特征、训练模型、打印准确率。它能跑。你上线了。

一个月后，有人重训模型拿到了不同结果。中位数是在包含测试数据的完整数据集上算的（数据泄露）。缩放参数没保存，推理时用了不同统计量。特征工程代码在训练和部署之间复制粘贴过，两边不一样了。一个类别列在生产里多了个新值，编码器从没见过。

这些不是假设。它们是 ML 系统生产里最常见的翻车原因。流水线通过把每一步变换打包成一个有序的可复现对象来解决这些问题。

## 核心概念

### 流水线是什么

流水线是一个有序的数据变换序列，后面跟着一个模型。每一步把上一步的输出作为输入。整个流水线在训练数据上拟合一次。推理时，同一个拟合好的流水线变换新数据并产生预测。

（mermaid 图保留）

流水线保证：
- 变换只在训练数据上拟合（没有泄露）
- 推理时应用相同的变换
- 整个对象可以序列化成一个工件部署
- 交叉验证按折应用流水线，防止隐蔽泄露

### 数据泄露：沉默的杀手

数据泄露是测试集或未来数据的信息污染了训练。流水线能预防最常见的形式。

**泄露版（错）：** （代码逐字保留）

Scaler 看到了测试数据。均值和标准差包含了测试样本。这抬高了准确率估计。

**正确版：** （代码逐字保留）

用流水线，你不用想这些。流水线自动处理。

### sklearn Pipeline

sklearn 的 `Pipeline` 把转换器和评估器串起来。暴露 `.fit()`、`.predict()` 和 `.score()`，按顺序应用所有步骤。

（代码逐字保留）

调 `pipe.fit(X_train, y_train)` 时：
1. Scaler 在 X_train 上调用 `fit_transform`
2. Model 在缩放后的 X_train 上调用 `fit`

调 `pipe.predict(X_test)` 时：
1. Scaler 在 X_test 上调用 `transform`（不是 `fit_transform`）
2. Model 在缩放后的 X_test 上调用 `predict`

Scaler 在拟合期间从不看测试数据。这就是全部意义。

### ColumnTransformer：不同列不同流水线

真实数据集有需要不同预处理的数值列和类别列。`ColumnTransformer` 处理这个。

（代码逐字保留）

OneHotEncoder 里的 `handle_unknown="ignore"` 对生产至关重要。新类别出现时（模型从没见过的城市），它产生零向量而不是崩掉。

### 实验追踪

流水线让训练可复现，但你也需要追踪跨实验发生了什么：用了哪些超参数、哪个数据集版本、指标是什么、跑的是哪版代码。

**MLflow** 是最常见的开源方案：（代码逐字保留）

**Weights & Biases (wandb)** 用托管面板提供相同功能：（代码逐字保留）

### 模型版本管理

实验追踪之后，你需要管模型版本。哪个在生产？哪个在 staging？哪个是上周的？

MLflow 的 Model Registry 提供：
- **版本追踪**：每个保存的模型拿一个版本号
- **阶段转换**："Staging"、"Production"、"Archived"
- **审批流程**：模型必须明确提升才能进生产
- **回滚**：瞬间切回上一个版本

### 用 DVC 做数据版本管理

代码用 git 版本管理。数据也应该版本管理，但 git 处理不了大文件。DVC（Data Version Control）解决这个。

（DVC 命令保留）

DVC 把实际数据存在远程存储（S3、GCS、Azure），git 里留一个小 `.dvc` 文件记录哈希。当你 checkout 一个 git commit 时，`dvc checkout` 恢复当时用的精确数据。

这意味着每个 git commit 同时 pin 住代码和数据。完全可复现。

### 可复现实验

可复现实验需要四件事：

1. **固定随机种子**：给 numpy、random 和框架（torch、sklearn）设种子
2. **锁定依赖**：requirements.txt 或 poetry.lock 带精确版本
3. **版本化数据**：DVC 或类似
4. **配置文件**：所有超参数放在 config 里，不是硬编码

（代码逐字保留）

### 从 Notebook 到生产流水线

（mermaid 图保留）

典型演进：

1. **Notebook 探索**：快速实验、可视化、特征想法
2. **提取函数**：把预处理、特征工程、评估移进模块
3. **构建 Pipeline**：把变换串成 sklearn Pipeline 或自定义类
4. **配置管理**：把所有超参数移进 YAML/JSON config
5. **实验追踪**：加 MLflow 或 wandb 日志
6. **数据验证**：训练前检查 schema、分布和缺失值模式
7. **测试**：转换器的单元测试，完整流水线的集成测试
8. **部署**：序列化流水线，包装进 API（FastAPI、Flask），容器化

### 常见流水线错误

| 错误 | 为什么糟 | 修复 |
|------|----------|------|
| 切分之前在全数据上拟合 | 数据泄露 | 用 Pipeline 加 cross_val_score |
| 流水线之外做特征工程 | 训练和 serve 的变换不同 | 所有变换塞进 Pipeline |
| 不处理未知类别 | 生产上遇到新值就崩 | OneHotEncoder(handle_unknown="ignore") |
| 硬编码列名 | schema 变了就崩 | 用 config 里的列名列表 |
| 没有数据验证 | 坏数据上悄悄产生错预测 | 预测前加 schema 检查 |
| 训练/服务偏差 | 生产上模型看到不同特征 | 训练和 serve 用同一个 Pipeline 对象 |

```figure
f3-pipeline-flow
```

## Build It

`code/pipeline.py` 从零构建了完整的 ML 流水线：

### 第 1 步：自定义 Transformer

（代码逐字保留）

### 第 2 步：从零 Pipeline

（代码逐字保留）

### 第 3 步：带 Pipeline 的交叉验证

代码演示了带流水线的交叉验证怎么预防数据泄露：scaler 在每个折的训练数据上分别拟合。

### 第 4 步：用 sklearn 做完整生产流水线

一个带 `ColumnTransformer`、多条预处理路径和模型的完整流水线，用正确的交叉验证和实验日志训练。

## Ship It

本课产出：
- `outputs/prompt-ml-pipeline.md`——一个构建和调试 ML 流水线的 skill
- `code/pipeline.py`——从零到 sklearn 的完整流水线

## Exercises

1. 构建一个处理 3 个数值列和 2 个类别列的流水线。用 `ColumnTransformer` 对数值列应用中位数填充 + 缩放、对类别列用众数填充 + one-hot 编码。用 5 折交叉验证训练。
2. 刻意引入数据泄露：切分之前在完整数据集上拟合 scaler。对比交叉验证分数（泄露的）和流水线交叉验证分数（干净的）。差距多大？
3. 用 `joblib.dump` 序列化流水线。在另一个脚本里加载并跑预测。验证预测完全相同。
4. 在流水线里加一个自定义 transformer，为两个最重要的数值列创建二次多项式特征。它应该放在流水线的哪个位置？
5. 为流水线设置 MLflow 追踪。用不同超参数跑 5 次实验。用 MLflow UI（`mlflow ui`）对比 run 选最好模型。

## Key Terms

| 术语 | 人们常说 | 实际含义 |
|------|----------|----------|
| Pipeline | "变换 + 模型的链" | 一个有序的拟合好的转换器和模型序列，作为一个单元应用来防泄露 |
| Data leakage | "测试信息漏进训练" | 用训练集之外的信息构建模型，抬高性能估计 |
| ColumnTransformer | "每列不同预处理" | 对不同列子集应用不同流水线，合并结果 |
| 实验追踪 | "日志你的 run" | 为每次训练 run 记录参数、指标、工件和代码版本 |
| MLflow | "追踪和部署模型" | 用于实验追踪、模型注册和部署的开源平台 |
| DVC | "数据的 Git" | 大型数据文件的版本控制系统，git 里存哈希、远程存储里存数据 |
| 模型注册 | "模型版本目录" | 追踪模型版本并带阶段标签（staging、production、archived）的系统 |
| 训练/服务偏差 | "Notebook 里能跑" | 训练和推理期间数据处理方式不同，导致静默错误 |
| 可复现性 | "同样代码、同样结果" | 从同样的代码、数据和配置得到相同结果的能力 |

## Further Reading

- [scikit-learn Pipeline docs](https://scikit-learn.org/stable/modules/compose.html) — 官方 Pipeline 参考
- [MLflow documentation](https://mlflow.org/docs/latest/index.html) — 实验追踪和模型注册
- [DVC documentation](https://dvc.org/doc) — 数据版本管理
- [Sculley et al., Hidden Technical Debt in ML Systems (2015)](https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html) — ML 系统复杂度的里程碑论文
- [Google ML Best Practices: Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml) — 实用生产 ML 建议
