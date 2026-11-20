---
name: provenance-check
description: 依据 California AB 2013 与 EU TDM opt-out 义务检查一个训练数据集。
version: 1.0.0
phase: 18
lesson: 27
tags: [data-provenance, ab-2013, tdm-opt-out, legitimate-interest, dpa]
---

给定一个部署所用的训练数据集，检查其是否符合 California AB 2013 与 EU TDM opt-out 的要求。

产出：

1. AB 2013 覆盖度。填写 12 个字段。标出任何缺失或仅有占位符的字段。注意：摘要一经发布即具约束力。
2. Opt-out 合规。该数据集是否尊重机器可读的 opt-out 信号（robots.txt、C2PA "No AI Training"、TDM.Reservation）？必须在采集前就部署过滤。
3. DPA 辖区映射。对数据主体所属的每个辖区，指出适用的 DPA 以及 2025 年在合法利益上的立场（Irish DPC、Cologne Higher Regional Court、Hamburg DPA、UK ICO、Brazilian ANPD）。
4. 不可逆性审计。如果数据集含 PII，已有何种 unlearning 或补救流程？应当承认没有任何流程能彻底补救训练数据。
5. 溯源源链完整性。从数据来源到训练流水线是否存在签名的链条？如果数据集是派生的（爬取 + 过滤），要记录其派生过程。

硬性拒绝：
- 任何引用 AB 2013 却不提供逐数据集 12 字段摘要的部署。
- 任何不尊重 robots.txt 或等效 opt-out 信号的部署。
- 任何假定可以从已训练权重中外科手术式移除数据的补救主张。

拒绝规则：
- 如果用户询问某个具体数据集是否"可以安全用于训练"，在没有逐辖区分析的情况下拒绝回答。
- 如果用户索要通用合规策略，拒绝——各辖区差异实质存在。

输出：一份一页纸的检查，填满五节内容，指出风险最高的合规缺口，并指出最紧迫的那一项补救。分别引用 California AB 2013 与 EU Copyright Directive 的 TDM 例外各一次。
