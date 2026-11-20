# 多智能体软件团队（TypeScript 骨架）

多文件 TypeScript 骨架，用于多智能体软件团队 capstone。
Planner、coder 与 reviewer agent 共享一个工作区，并在一个
coordinator 下轮流切换。一个 worktree 桩通过 execFile 启动子进程，附带
拒绝清单（denylist）与 shell 元字符拒绝。

## Layout

- `src/index.ts` — 演示运行器。
- `src/agent.ts` — 基础 `Agent` 类，外加 `PlannerAgent`、`CoderAgent`、`ReviewerAgent`。
- `src/coordinator.ts` — 轮询循环与轮转跟踪。
- `src/workspace.ts` — 共享的内存文件系统与消息日志。
- `src/runtime.ts` — 带拒绝清单的 `child_process.execFile` worktree 桩。
- `src/types.ts` — 共享类型。
- `tests/*.test.ts` — 通过 `tsx` 运行的 `node --test` 风格测试。

## Install

```bash
npm install
```

## Run

```bash
npm start
```

## Verify

```bash
npm run typecheck
npm test
```

## Spec references

- 源课程：`phases/19-capstone-projects/10-multi-agent-software-team/docs/en.md`
- [MetaGPT](https://github.com/FoundationAgents/MetaGPT) 基于角色的多智能体框架。
