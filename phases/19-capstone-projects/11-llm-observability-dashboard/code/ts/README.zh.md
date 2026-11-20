# LLM 可观测性仪表盘（TypeScript 骨架）

多文件 TypeScript 骨架，用于 LLM 可观测性仪表盘 capstone。
一个 Hono server 接收 OpenTelemetry GenAI span，将其保存在一个 10k 环形
缓冲区中，并渲染 p50/p95/p99 延迟与每个模型的成本。

## Layout

- `src/index.ts` — 入口点，播种合成 span，并可选地提供 HTTP 服务。
- `src/server.ts` — 用于 `/trace`、`/`、`/dashboard`、`/dashboard.json`、`/healthz` 的 Hono 路由。
- `src/spans.ts` — `RingBuffer` 与 `ObservabilityStore`（默认 10k span）。
- `src/rollup.ts` — `percentile` 与 `rollUpByModel`。
- `src/pricing.ts` — 2026 各模型价格与成本辅助函数。
- `src/types.ts` — 共享类型。
- `tests/*.test.ts` — 通过 `tsx` 运行的 `node --test` 风格测试。

## Install

```bash
npm install
```

## Run

```bash
npm start         # seeds 1200 synthetic spans and prints the rollup
npm run serve     # also serves the HTTP ingest + dashboard on PORT (default 8011)
```

## Verify

```bash
npm run typecheck
npm test
```

## Spec references

- 源课程：`phases/19-capstone-projects/11-llm-observability-dashboard/docs/en.md`
- [OpenTelemetry GenAI 语义约定](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
