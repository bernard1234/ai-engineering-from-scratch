# Capstone 05 — 自主研究 Agent（AI-Scientist 类）

> Sakana 的 AI-Scientist-v2 发表了完整论文。Agent Laboratory 跑通了实验。Allen AI 公开了 trace。2026 年的形态是在实验之上做 plan-execute-verify 树搜索、预算化成本、沙箱化代码执行、带视觉反馈的 LaTeX 写作器，以及自动化的 NeurIPS 风格评审团。本 capstone 要求你构建一个这样的系统，在每篇论文 $30 的成本内端到端跑通，并通过 Sakana 记录过的 sandbox 逃逸红队测试。

**Type:** Capstone
**Languages:** Python（agent 与 sandbox）、LaTeX（输出）
**Prerequisites:** 第 2 阶段（ML）、第 3 阶段（deep learning）、第 7 阶段（transformers）、第 10 阶段（LLMs from scratch）、第 14 阶段（agents）、第 15 阶段（autonomous）、第 16 阶段（multi-agent）、第 18 阶段（safety）
**Phases exercised:** P0 · P2 · P3 · P7 · P10 · P14 · P15 · P16 · P18
**Time:** 40 小时

## 问题场景

自主研究 agent 在 2026 年跨过了一道门槛。Sakana AI 的 AI-Scientist-v2 在 Nature 上发表，其生成的论文通过了 workshop 同行评审。ShinkaEvolve（ICLR 2026）把这条路线扩展到假设进化。AMD 的 Agent Laboratory 交付了可复现的 trace。这些 agent 并不神奇——它们是一个在候选实验树上运行的 plan-execute-verify 循环，配有成本上限、种子绑定的 sandbox 和自动评审。功夫在于循环、预算和安全叙事。

你通过在一个窄领域（例如对 100M 参数 transformer 做 attention 稀疏性消融）针对一个种子想法实现一个这样的循环来学习它。价值不在于第一次运行就发现新东西，而在于基础设施：树搜索、实验 sandbox、写作-评审循环、红队报告。Sakana 团队记录过 sandbox 逃逸失败；你的 agent 必须通过同样的红队。

## 核心概念

该 agent 是一个 best-first 树搜索。节点是实验规格：(hypothesis, config, code, expected outcome)。expand 步骤用小的改动（换 optimizer、调 batch size、消融某个组件）提出子节点。每个子节点都在一个全新的 sandbox 中运行，并带有硬性资源上限。结果回流到一个评分函数，按（novelty × quality × remaining budget）对节点排序。树持续生长直到预算耗尽，然后写出最佳分支。

写作器是多模态的。它生成 LaTeX 草稿，编译它，渲染图，再把渲染出的 PDF 送回 Claude Opus 4.7 的视觉模式，对版式、图的清晰度和论断-证据对齐进行批判。一个由五个 LLM 评审组成的评审团给出 NeurIPS 风格的评分（novelty、rigor、clarity、reproducibility、impact）；如果平均分低于阈值，论文带着批判意见退回写作器。

安全是承重的。每个实验都在 E2B 或 Daytona sandbox 中运行，无网络出口、墙钟时间受限、资源上限被钉死。agent 的代码生成步骤要经过一个策略层，拦截那些会逃出 sandbox 的 syscall。红队报告复现 Sakana 记录过的攻击面（fork bomb、文件系统逃逸、LLM 编写的网络调用）。

## 架构

```
seed idea + domain
      |
      v
  literature search (Semantic Scholar + OpenAlex + FAISS cache)
      |
      v
  LangGraph plan-execute-verify tree
      |
      v
  +--- expand node ----+      per-node sandbox
  |                    |      (E2B / Daytona)
  v                    v      resource caps
  child_1           child_k   no network egress
  |                    |      deterministic seeds
  v                    v
  run experiment       run experiment
  |                    |
  v                    v
  score nodes by (novelty, quality, budget)
      |
      v
  best branch -> LaTeX writer
      |
      v
  compile + vision critique (Opus 4.7 vision)
      |
      v
  reviewer ensemble (5 LLM judges, NeurIPS rubric)
      |
      v
  paper.pdf + review.md + trace.json
```

## 技术栈

- 编排：LangGraph，带 checkpointing 与人工审批关卡
- 树搜索：在实验节点上自定义 best-first（Sakana v2 风格的 AB-MCTS）
- Sandbox：每个实验一个 E2B，Docker-in-Docker 兜底；通过 cgroups 施加资源上限
- 文献：Semantic Scholar Graph API + OpenAlex + 摘要的本地 FAISS 缓存
- 写作器：LaTeX 模板 + Claude Opus 4.7（视觉模式）做图批判与版式
- 评审：5 个评审组成的评审团（Opus 4.7、GPT-5.4、Gemini 3 Pro、DeepSeek R1、Qwen3-Max），加权聚合
- 实验框架：物理实验用 PyTorch 2.5，W&B 做日志
- 可观测性：Langfuse 做 agent trace，每篇论文 $30 硬预算

```figure
ce-experiment-tree
```

## Build It

1. **种子与领域界定。** 取一个种子想法（例如“研究 sub-1B transformer 的 attention map 中的稀疏模式”）。定义搜索空间：模型、数据集、算力预算。

2. **文献梳理。** 向 Semantic Scholar + OpenAlex 查询 50 篇被引最多的相关论文；把摘要缓存到本地；生成 1 页的领域摘要。

3. **树的脚手架。** 用种子假设初始化根节点。实现 `expand(node) -> children`，采用小改动提议（每个子节点只改一项配置）。实现 `score(node)`，作为 novelty × quality × budget 的加权项。

4. **Sandbox 封装。** 每个实验运行 `docker run --network=none --memory=8g --cpus=2 --pids-limit=256 --read-only`（或等价的 E2B 策略）。种子被写入 sandbox；输出以只读方式挂载回来。

5. **Plan-execute-verify 循环。** `plan` 提出子节点。`execute` 运行 sandbox，捕获日志与指标。`verify` 对指标跑单元检查（loss 是否下降？消融是否隔离了效应？）。失败的节点会在树上存下失败原因。

6. **写作器。** 预算耗尽后，选出最佳分支。用 matplotlib 渲染图。在上下文中带上分支 trace，通过 Claude Opus 4.7 生成 LaTeX 草稿。编译。把编译后的 PDF 送回 Opus 4.7 视觉模式做批判。迭代。

7. **评审团。** 五个评审用 NeurIPS 风格评分表对草稿就（novelty、rigor、clarity、reproducibility、impact）打分。若均值 < 4.0/5，带着批判意见退回写作器。3 次重写后硬性停止。

8. **红队。** 构建或集成一组针对 sandbox 的对抗任务：fork bomb、网络外泄尝试、文件系统逃逸、LLM 编写的 shell 元字符。确认全部被拦截。写出结论。

9. **可复现性。** 每篇论文都随附其树搜索 trace JSON、种子、W&B 运行链接、sandbox 配置，以及一份端到端复现它的 README。

## Use It

```
$ ai-scientist run --seed "attention sparsity in sub-1B transformers" --budget 30
[lit]    50 papers, digest in 12s
[tree]   expanded 8 nodes, budget 12/30
[exec]   node #3 sparsity=top-8, loss=2.83 (best so far)
[exec]   node #6 sparsity=top-4, loss=3.12 (worse)
[exec]   ...
[tree]   chose branch rooted at node #3 (novelty 0.62, quality 0.81)
[write]  LaTeX draft v1 complete
[vision] critique: figure 2 legend too small, claim-evidence ok
[write]  draft v2 after 3 edits
[review] mean 4.2/5 (novelty 3.9, rigor 4.3, clarity 4.1, repro 4.5, impact 4.2)
[done]   paper.pdf + review.md + trace.json     $28.40 spent
```

## Ship It

`outputs/skill-ai-scientist.md` 是交付物。给定一个种子想法 + 一个领域 + $30 预算，它跑完整条流水线，产出一篇可评审的论文外加一个可复现性包。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | 论文质量 | 对照已发表的 workshop 论文做盲评评分表评审 |
| 20 | 实验严谨性 | baseline、种子、消融；每个论断都由结果表中的某个单元格支撑 |
| 20 | 成本与算力纪律 | 强制 $30/篇上限，Langfuse 追踪 |
| 20 | 安全性 | sandbox 红队通过；网络策略与 kill-switch 已验证 |
| 15 | 可复现性 | 使用相同种子的一键重跑可复现该论文 |
| **100** | | |

## Exercises

1. 在同一领域针对三个不同的种子想法运行流水线。比较树搜索的哪些部分发生重叠。找出重复浪费的算力。

2. 在执行实验前，为预估成本超过 $5 的节点加一个人工审批关卡。测量总成本下降了多少。

3. 把评审团换成单一评审。在一组留出的已知劣质论文上测量误接受率。

4. 引入一个网络外泄红队测试：让 agent 写出试图 `curl` 外部地址的代码。确认 `--network=none` 策略将其拦截。记录这次尝试。

5. 把你的树搜索与一个平坦随机 baseline（相同预算，无扩展策略）比较。报告 novelty × quality 的增益。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Tree search | “AB-MCTS 风格扩展” | 在实验节点上的 best-first 探索，按 novelty×quality×budget 打分 |
| Sandbox | “实验隔离” | 无网络、CPU/内存受限、种子钉死、输入只读的容器 |
| Vision critique | “先渲染再读取” | 把论文编译成 PDF，再将 PDF 回灌给 VLM 做版式与论断-证据批判 |
| Reviewer ensemble | “自动同行评审” | 多个 LLM 评审用 NeurIPS 评分表给论文打分；加权聚合结果决定流水线是否过关 |
| Novelty score | “这是新的吗？” | 一种启发式，惩罚与 50 篇文献缓存的接近程度 |
| Cost ceiling | “$ 预算” | 每篇论文总花费的硬上限；Langfuse 计数器 + 运行前估算 |
| Red team | “sandbox 逃逸审计” | 若策略有误就会逃出 sandbox 的对抗任务 |

## Further Reading

- [Sakana AI-Scientist-v2 仓库](https://github.com/SakanaAI/AI-Scientist-v2) — 参考性的生产级研究 agent
- [Sakana AI-Scientist-v1 论文（arXiv:2408.06292）](https://arxiv.org/abs/2408.06292) — 最初的方法论
- [ShinkaEvolve（Sakana ICLR 2026）](https://sakana.ai) — 进化式扩展
- [Agent Laboratory（AMD）](https://github.com/SamuelSchmidgall/AgentLaboratory) — 多角色研究实验室框架
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/) — 参考编排层
- [Semantic Scholar Graph API](https://api.semanticscholar.org/) — 文献检索
- [E2B sandbox](https://e2b.dev) — 参考实验隔离方案
- [NeurIPS 评审指南](https://neurips.cc/Conferences/2026/ReviewerGuidelines) — 评审团所编码的评分表
