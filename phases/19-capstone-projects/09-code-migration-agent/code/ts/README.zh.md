# 代码迁移 agent 看板（TypeScript 骨架）

面向代码迁移 agent capstone 看板层的多文件 TypeScript 骨架。
agent（Python）在 sandbox 中运行；本服务器
为操作者渲染进度。

## 布局

- `src/index.ts` — 入口，模拟 tick，并可选地提供 HTTP 服务。
- `src/server.ts` — 针对 `/`、`/dashboard`、`/migrations`、`/migrations/:id` 的 Hono 路由。
- `src/migrations.ts` — 按文件的状态机与种子数据。
- `src/cost.ts` — 轮数与美元预算的执行。
- `src/types.ts` — 共享类型。
- `tests/*.test.ts` — 通过 `tsx` 运行的 `node --test` 风格测试。

## 安装

```bash
npm install
```

## 运行

```bash
npm start         # offline: simulate 40 ticks and print rollup
npm run serve     # serve the HTML dashboard on PORT (default 8009)
```

## 验证

```bash
npm run typecheck
npm test
```

## 规范参考

- 源课程：`phases/19-capstone-projects/09-code-migration-agent/docs/en.md`
- Recipes：[OpenRewrite](https://docs.openrewrite.org)、libcst。
