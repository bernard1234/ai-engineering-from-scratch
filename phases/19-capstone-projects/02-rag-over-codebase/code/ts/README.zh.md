# Capstone 19/02 — RAG over Codebase（TypeScript）

面向混合检索流水线的多文件 TypeScript 代码搜索 API，流水线详见
`../docs/en.md`。离线、确定性，六 chunk 的样例语料，
在 hono fetch handler 之后运行 node:http。

## 目录结构

```text
src/
  index.ts        entry point; boots node:http + self-probe + exits 0
  server.ts       hono routes (/healthz, /query) with zod-validated POST body
  retrieval.ts    runQuery + RRF merge over dense and BM25
  index_store.ts  FNV-1a hash embedder, cosine, field-weighted BM25
  corpus.ts       six-chunk sample (uploader / auth / client / catalog)
  types.ts        Chunk, RankedChunk, QueryResponse, anchor()
tests/
  index_store.test.ts
  retrieval.test.ts
  server.test.ts
```

## 运行

```bash
npm install
npm start                # boots api, probes three queries, exits 0
npm start -- --serve     # keep server up; ctrl-c to stop
npm test                 # node --test runner via tsx
npm run typecheck        # tsc --noEmit
```

非交互的 `npm start` 路径会断言 `/healthz` 返回 200，并断言
每个探测查询至少返回一条引用。路由：

- `GET /healthz` — 返回 `{ok, corpus}`。
- `GET /query?q=...` — 运行一次混合查询。
- `POST /query` — JSON `{q, topK?}`，由 zod 校验（`topK` 上限为 50）。
