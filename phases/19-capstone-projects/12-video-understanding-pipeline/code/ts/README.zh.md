# 第 12 课 - 视频理解流水线（TypeScript UI）

capstone 的 TypeScript 部分。Python 侧（`code/main.py`）负责
多向量索引与时间定位。本项目交付仪表盘那一半：一个覆盖四个流水线阶段
（chunk、embed、index、qa）的 Hono 应用。

## Layout

```text
src/
  index.ts     entry: demo (default) or HTTP server (--serve)
  server.ts    Hono routes (/, /jobs, /job/:id) + HTML index
  jobs.ts     JobStore + fixture seeder
  stages.ts    stage advance + overall status
  types.ts     Stage, StageState, Job
tests/
  stages.test.ts  job state transitions + store
```

## Run

```bash
npm install
npm run typecheck
npm test
npm start              # self-terminating demo
npm run serve          # HTTP server on :8123
```
