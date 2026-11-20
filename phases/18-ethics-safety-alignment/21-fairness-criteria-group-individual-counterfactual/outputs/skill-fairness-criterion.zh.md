---
name: fairness-criterion
description: 识别一项主张援引的是哪条公平性准则，并审计相关假设。
version: 1.0.0
phase: 18
lesson: 21
tags: [fairness, demographic-parity, equalized-odds, counterfactual-fairness, impossibility]
---

给定一个公平性主张或政策，识别它援引的是哪条准则、该主张依赖什么假设，以及不可能性定理对剩余准则意味着什么。

产出：

1. 准则识别。把主张标注为针对以下之一：demographic parity、equalized odds、conditional use accuracy equality、个体公平、反事实公平。含糊的主张必须在继续之前澄清。
2. 基率审计。部署中各群体的基率是多少？在基率不等时，Chouldechova / KMR 2017 不可能性适用：没有模型能同时满足三条群体准则。
3. 因果 DAG 依赖。如果主张是反事实公平，因果 DAG 是什么？反事实公平的合理性只与 DAG 的合理性相当。缺少 DAG 会使主张失效。
4. 相似度度量。如果主张是个体公平，相似度度量 d 是什么？该选择是任务特定的，是政策决策而非统计决策。
5. 干预合法性。如果主张使用反事实推理，是否涉及对受保护属性的干预？如果是，考虑回溯反事实（arXiv:2401.13935）以绕开法律问题。

硬性拒绝：
- 任何未识别准则的“公平”主张。
- 任何在基率不等时声称“所有公平准则都满足”、却不承认 Chouldechova / KMR 2017 的主张。
- 任何没有公开因果 DAG 的反事实公平主张。

拒绝规则：
- 如果用户问哪条公平性准则是“正确的”，拒绝排名，并说明这是政策选择。
- 如果用户问某个模型是否“公平”，拒绝二元主张；公平性是相对于准则而言的。

输出：一页审计，填写上述五个部分，在适用时标出不可能性，并点明该主张中隐含的政策选择。酌情各引用 Dwork et al. 2012、Kusner et al. 2017、Chouldechova 2017 一次。
