---
name: llava-vibes-eval
description: 对 LLaVA 家族的 VLM 运行 10 条 prompt 的 vibes-eval，并生成人类可读的评分卡。
version: 1.0.0
phase: 12
lesson: 05
tags: [llava, vlm, vibes-eval, instruction-tuning]
---

给定一个 LLaVA 家族的 VLM（LLaVA-1.5、LLaVA-NeXT、LLaVA-OneVision 或社区 fork）以及一组测试图像，运行一套覆盖 captioning、VQA、推理、拒答和格式合规的 10 条 prompt 冒烟测试。产出一份评分卡，用于确认 projector 与 LLM 连接正确。

产出：

1. 十条 prompt 及预期行为描述：
   - 三条 captioning（简短、详细、创意）。
   - 三条 VQA（计数、颜色、物体是否存在）。
   - 两条推理（比较两个区域、因果关系）。
   - 两条拒答（私人个体、可识别 PII）。
2. 每条 prompt 的得分。pass / partial / fail，附一行理由。
3. 整体模式诊断。如果 captioning 通过但 VQA 失败，怀疑 stage 2 的数据配比。如果详细 captioning 出现幻觉，怀疑 ShareGPT4V 风格的数据不足。如果拒答失败，标记为安全数据缺口。
4. 分辨率检查。将一条需要 OCR 的 prompt 在 336x336 基础分辨率下跑一次，再用 AnyRes 跑一次，记录差异。低分辨率下失败是预期内的；高分辨率下失败则说明 AnyRes 配置有误。
5. 建议的后续动作。如果特定类别失败，调用方可以补充的三项具体训练数据。

硬性拒绝：
- 只按 benchmark 数字给 VLM 打分而不跑 vibes 套件。benchmark 可以被针对性地刷高；vibes 才能揭示真实的部署就绪度。
- 把幻觉与风格上的冗长混为一谈。要明确指出哪些物体是凭空捏造的，哪些只是描述得详尽。
- 在推理类 prompt 上不看推理链、只看最终答案就宣称通过。

拒答规则：
- 如果调用方要求对一个没有 API 访问权限的闭源 VLM（Gemini、Claude、GPT-5V）做 vibes-eval，拒绝——测试需要真实的推理输出。
- 如果目标用例是医学诊断或法律建议，拒绝——vibes-eval 不是认证，不得用于高风险领域。
- 如果未提供任何图像，拒绝——按定义这项测试必须以图像为依据。

输出：一份 10 行的评分卡（prompt、image、expected、actual、pass/partial/fail），一段整体模式诊断，以及一份三项后续清单。结尾用一段"接下来读什么"的文字，指向第 12.06 课（AnyRes）以处理分辨率相关失败，或第 12.07 课（消融实验）以调校数据配比。
