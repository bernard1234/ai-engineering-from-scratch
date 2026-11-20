---
name: societal-risk-review
description: 使用 CAIS 的 four-risk 框架以及 CAISI / SB-53 的监管背景，审查一个部署的 societal-scale risk 态势。
version: 1.0.0
phase: 15
lesson: 22
tags: [cais, caisi, four-risk-framework, organizational-risk, sb-53, societal-risk]
---

给定一个拟议中或运行中的 AI 部署，产出一份 societal-scale risk 审查：按 CAIS 的 four-risk 框架为部署打标签、盘点 organizational-risk 各子杠杆，并指明监管面。

产出：

1. **Four-risk 打标签。** 对四个类别（malicious use、AI races、organizational risks、rogue AIs）逐一说明该部署是否触及以及如何触及。一个部署可以触及多个类别；“不适用”必须用一句话给出理由。
2. **Organizational-risk 盘点。** 用四个子杠杆给部署打分：安全文化、审计严格度、多层防御、信息安全。任何被打为“缺失”的杠杆都是标记出来的缺口。
3. **监管面。** 指明适用的监管框架：EU AI Act（若在欧盟或服务欧盟用户）、California SB-53（若已签署且适用）、CAISI 自愿协议（若实验室已签署）。合规是部署的门槛，不是部署的加分项。
4. **外部评估态势。** 指明该部署或其基础模型经历过哪些外部评估（METR、CAISI、Apollo、Gray Swan 等）。对长时程自主部署而言，没有外部评估就是标记出来的缺口。
5. **结构性力量暴露。** 估计该组织承受多大的竞争性部署压力，以及这与 organizational-risk 杠杆如何权衡。竞争压力大的团队会最先降低审计的优先级；这是 CAIS 的发现。

硬性拒绝：
- 触及有害能力类别、却没有硬编码禁止层（第 17 课）的部署。
- 处于竞争竞赛条件下、却没有独立审计的部署。
- 没有外部能力评估的长时程自主部署。
- 没有 Article 14 HITL（第 15 课）的欧盟部署。
- 若 SB-53 已签署，却没有事件报告流程的加州部署。

拒绝规则：
- 如果用户说不出基础模型的外部评估机构，拒绝，要求先完成识别。仅凭自我评估是不够的。
- 如果用户把“我们有扩展政策”当作符合灾难性风险法规，拒绝，要求给出具体的监管面映射。
- 如果用户在竞争压力下、没有审计就提出部署，拒绝，并指出 CAIS 关于 organizational risk 的发现。

输出格式：

返回一份 societal risk 审查，包含：
- **Four-risk 行表**（类别、是否触及 y/n、性质）
- **Organizational-risk 记分卡**（安全文化 / 审计 / 防御 / 信息安全）
- **监管面**（适用框架及合规状态）
- **外部评估态势**（评估机构、范围、节奏）
- **结构性力量暴露**（低 / 中 / 高，附理由）
- **部署就绪度**（生产 / 预发 / 仅研究）
