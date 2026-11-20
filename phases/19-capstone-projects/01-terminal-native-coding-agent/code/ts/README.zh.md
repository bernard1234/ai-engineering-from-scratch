# Capstone 19/01 — 终端原生编码 agent（TypeScript）

面向 plan/act/observe 循环的多文件 TypeScript harness，循环定义见
`../docs/en.md`。离线、确定性、零网络调用。

## 目录结构

```text
src/
  index.ts     entry point; runs a scripted demo and the eval, then exits 0
  repl.ts      interactive command parser (run / eval / help / quit)
  harness.ts   the plan-act-observe loop, wired through the hook bus
  hooks.ts     eight-event hook bus plus a destructive-command guard
  model.ts     scripted offline LLM that drives the demo
  tools.ts     read_file + run_shell with zod-validated args
  plan.ts     PlanState (todo rewrite) + Budget (turn / token / dollar ceilings)
  eval.ts      tiny pass/fail counter across three offline tasks
  types.ts     shared shape definitions
tests/
  harness.test.ts
  tools.test.ts
```

## 运行

```bash
npm install
npm start                # runs the scripted demo + offline eval, exits 0
npm start -- --repl      # opens the interactive harness REPL
npm test                 # node --test runner via tsx
npm run typecheck        # tsc --noEmit
```

非交互的 `npm start` 路径会断言 eval 报告 `passed=3
failed=0`，且脚本化运行收敛到全部完成的计划。任何偏差
都会让这次运行失败。
