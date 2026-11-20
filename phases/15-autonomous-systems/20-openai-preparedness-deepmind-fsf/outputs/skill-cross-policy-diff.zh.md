---
name: cross-policy-diff
description: 针对一项具体能力，以 OpenAI Preparedness Framework v2、Anthropic RSP v3.0 和 DeepMind FSF v3 为参照，产出跨政策比较。
version: 1.0.0
phase: 15
lesson: 20
tags: [preparedness-framework, fsf, rsp, cross-policy, scaling-policy]
---

给定一项具体的前沿能力（例如“long-range autonomy”“autonomous replication and adaptation”“R&D automation”），产出一份跨政策 diff，展示三个框架各自如何分类该能力，以及会触发哪些缓解。

产出：

1. **OpenAI PF v2 分类。** Tracked 还是 Research。若为 Tracked，点名 Capabilities + Safeguards Report 的触发条件。若为 Research，注明政策措辞是“潜在”缓解。
2. **Anthropic RSP v3.0 分类。** 哪个阈值（ASL-3、AI R&D-4、硬编码禁令）？哪种缓解（肯定性论证、安全 + 部署）？确认该承诺落在 Anthropic 单方面层还是行业建议层。
3. **DeepMind FSF v3 分类。** 哪个领域（Cyber、Bio、ML R&D、CBRN）？哪个 CCL 或 Tracked Capability Level？是否援引了欺骗性对齐监控？
4. **趋同摘要。** 三份政策对该能力的严重性是否意见一致，还是存在实质分歧？哪种分类最严格，哪种最不严格？
5. **测量依赖。** 每个分类都依赖能力测量。说明该能力如何被测量，以及由哪个 eval provider（METR、Apollo、内部、第三方）负责这项测量。

硬性拒绝：
- 仅凭公告措辞相似、拿不出文档级证据就声称跨政策一致。
- 任何无法指向源文档具体条款的分类。
- 把“Research Category”（OpenAI）等同于“Tracked Category”——二者运营后果不同。

拒绝规则：
- 如果用户拿不出每项分类对应的源文档段落，拒绝，并要求先提供引用。
- 如果用户把政策的存在当作缓解已在实践中生效的证据，拒绝，并要求提供具体缓解确实触发的证据。
- 如果某项能力被声称已被某个框架“覆盖”，但该词并未出现在文档中，拒绝，并要求给出具体条款引用。

输出格式：

返回一份 diff 文档，包含：
- **能力定义**（一句话）
- **OpenAI PF v2 行**（分类、触发条件、源条款）
- **Anthropic RSP v3.0 行**（分类、触发条件、单方面 vs 建议）
- **DeepMind FSF v3 行**（领域、CCL / TCL、欺骗性对齐的涉及情况）
- **趋同摘要**（一致之处 + 实质分歧）
- **测量归属**（eval provider、eval 节奏）
- **给读者的建议**（最严格、最不严格，并给出理由）
