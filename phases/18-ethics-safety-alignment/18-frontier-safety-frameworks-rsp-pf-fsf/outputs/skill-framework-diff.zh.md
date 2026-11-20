---
name: framework-diff
description: 把一份新的安全框架或发布说明与 RSP v3.0、PF v2、FSF v3.0 作比较。
version: 1.0.0
phase: 18
lesson: 18
tags: [rsp, pf, fsf, frontier-safety, safety-case]
---

给定一份新的安全框架、政策或发布说明，沿着五个结构维度把它与 Anthropic RSP v3.0、OpenAI PF v2、DeepMind FSF v3.0 作比较。

产出：

1. 层级结构。框架是否定义了离散的能力阈值？是按领域划分（FSF 风格）还是全局统一（RSP 风格）？
2. CBRN 阈值。要求进行哪项 CBRN 评测？是否引用 WMDP（第 17 课）或等价物？是否包含诱导研究？
3. AI R&D 阈值。是否存在模型自主研究的阈值？门槛是"入门级研究员"（Anthropic AI R&D-2）还是"大幅加速扩容"（Anthropic AI R&D-4）？
4. 竞争者调整。框架是否允许在竞争对手未配备可比防护就发布时降低要求？酌情从竞赛动态或激励相容的角度来论述。
5. 安全案例结构。是否要求书面安全案例？它针对 monitoring、illegibility 还是 incapability？证据门槛是什么？

硬性拒绝：
- 任何没有按层级能力阈值的安全框架。
- 任何省略外部治理交叉引用（UK AISI、US CAISI、EU AI Office）的框架。
- 任何声称"我们与所有已发布框架对齐"却不给出具体阈值数字的框架。

拒绝规则：
- 如果用户问哪个框架"最好"，拒绝排名，并指向结构对齐。
- 如果用户要求给出数值阈值建议，拒绝——阈值因实验室而异，取决于其度量基础设施。

输出：针对三套框架的一页并排比较、被标记的差距，以及一条具体建议新增的阈值。分别各引用一次 RSP v3.0、PF v2、FSF v3.0。
