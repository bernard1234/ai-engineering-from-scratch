# 第 17 课 - 个人 AI 导师（TypeScript Web 应用）

本 capstone 的 TypeScript 部分。Python 侧交付 learner model 与
tutor policy；本项目暴露 Web 应用的接口面：一个课程 DAG
遍历器、一个 BKT 风格的 learner model，以及一个 FSRS-lite 间隔重复
调度器，承载于两个 HTTP 路由之后。

## 目录结构

```text
src/
  index.ts       entry: demo (default) or HTTP server (--serve)
  server.ts      Hono routes (GET /lesson/next, POST /lesson/:id/submit)
  curriculum.ts  DAG fixture + Kahn topo sort + next-lesson picker
  mastery.ts     MasteryStore (per-lesson BKT-ish update)
  repetition.ts  scheduleNextDue (interval doubling / halving, clamped)
  types.ts       Lesson, Mastery, Pick
tests/
  curriculum.test.ts  topo order, BKT update, FSRS scheduling
```

## 运行

```bash
npm install
npm run typecheck
npm test
npm start            # self-terminating curriculum walk
npm run serve        # HTTP server on :8090
```
