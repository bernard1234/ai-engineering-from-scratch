"""Toy ReWOO — Planner, Workers, Solver. Stdlib only.

Demonstrates the decoupled pattern from Xu et al. (arXiv:2305.18323):
  1. Planner emits a DAG of (tool, args) steps with references (#E1, #E2, ...).
  2. Workers run each step in topological order.
  3. Solver composes the final answer from question + plan + evidence.

Compare run_rewoo() vs run_react() at the bottom for token-use intuition.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class PlanStep:
    id: str
    tool: str
    args: dict[str, Any]


@dataclass
class Plan:
    steps: list[PlanStep]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., str]] = {}

    def register(self, name: str, fn: Callable[..., str]) -> None:
        self._tools[name] = fn

    def dispatch(self, name: str, args: dict[str, Any]) -> str:
        fn = self._tools.get(name)
        if fn is None:
            return f"error: unknown tool {name!r}"
        try:
            return fn(**args)
        except Exception as e:
            return f"error: {type(e).__name__}: {e}"


REFERENCE_RE = re.compile(r"#E(\d+)")


def resolve_references(value: Any, evidence: dict[str, str]) -> Any:
    if not isinstance(value, str):
        return value
    return REFERENCE_RE.sub(lambda m: evidence.get(f"E{m.group(1)}", m.group(0)),
                            value)


def topological(plan: Plan) -> list[PlanStep]:
    resolved: list[PlanStep] = []
    known: set[str] = set()
    pending = list(plan.steps)
    while pending:
        progress = False
        rest: list[PlanStep] = []
        for step in pending:
            refs = REFERENCE_RE.findall(str(step.args))
            if all(f"E{r}" in known for r in refs):
                resolved.append(step)
                known.add(step.id)
                progress = True
            else:
                rest.append(step)
        if not progress:
            raise RuntimeError("cyclic plan or unresolved reference")
        pending = rest
    return resolved


def run_workers(plan: Plan, tools: ToolRegistry) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for step in topological(plan):
        bound_args = {k: resolve_references(v, evidence) for k, v in step.args.items()}
        evidence[step.id] = tools.dispatch(step.tool, bound_args)
    return evidence


class ScriptedPlanner:
    def __init__(self, plan: Plan) -> None:
        self.plan = plan

    def plan_for(self, question: str) -> Plan:
        return self.plan


class ScriptedSolver:
    def __init__(self, answer_template: str) -> None:
        self.template = answer_template

    def solve(self, question: str, plan: Plan, evidence: dict[str, str]) -> str:
        return self.template.format(**evidence)


def needs_replan(evidence: dict[str, str]) -> bool:
    """任一 worker 返回了错误字符串，就需要修订计划。"""
    return any(v.startswith("error:") for v in evidence.values())


class ScriptedReplanner:
    """脚本化的 replanner（Plan-and-Execute 的增量部分）。

    真实的 replanner 会把「带错误的观察」重新喂给 planner 生成修订计划。
    这里用一条规则代替 LLM：把失败节点的工具替换成回退工具。
    足够演示循环结构，而非真实重规划。
    """

    def __init__(self, fallback_tool: str) -> None:
        self.fallback_tool = fallback_tool

    def replan(self, question: str, plan: Plan,
               evidence: dict[str, str]) -> Plan:
        failed = [s.id for s in plan.steps
                  if evidence.get(s.id, "").startswith("error:")]
        print(f"  [replanner] 失败节点 {failed}; "
              f"改用 {self.fallback_tool!r} 重试")
        return Plan(steps=[
            PlanStep(s.id,
                     self.fallback_tool if s.id in failed else s.tool,
                     s.args)
            for s in plan.steps
        ])


def fake_search(query: str) -> str:
    if "capital of france" in query.lower():
        return "Paris"
    if "population of paris" in query.lower():
        return "11.2 million metro"
    if "capital of germany" in query.lower():
        return "Berlin"
    return f"no result for {query!r}"


def rounded_million(text: str) -> str:
    m = re.search(r"([0-9]+\.?[0-9]*)", text)
    if not m:
        return "unknown"
    return f"{round(float(m.group(1)))} million"


@dataclass
class ReWOORun:
    question: str
    plan: Plan
    evidence: dict[str, str] = field(default_factory=dict)
    answer: str = ""
    planner_chars: int = 0
    worker_chars: int = 0
    solver_chars: int = 0
    rounds: int = 1


def run_rewoo(question: str, planner: ScriptedPlanner,
              tools: ToolRegistry, solver: ScriptedSolver) -> ReWOORun:
    plan = planner.plan_for(question)
    planner_chars = len(question) + sum(len(s.tool) + len(str(s.args))
                                        for s in plan.steps)
    evidence = run_workers(plan, tools)
    worker_chars = sum(len(str(s.args)) + len(v) for s, v in zip(plan.steps,
                                                                 evidence.values()))
    answer = solver.solve(question, plan, evidence)
    solver_chars = len(question) + worker_chars + len(answer)
    return ReWOORun(question=question, plan=plan, evidence=evidence,
                    answer=answer,
                    planner_chars=planner_chars, worker_chars=worker_chars,
                    solver_chars=solver_chars)


def run_plan_execute(question: str, planner: ScriptedPlanner,
                     tools: ToolRegistry, solver: ScriptedSolver,
                     replanner: ScriptedReplanner,
                     max_rounds: int = 3) -> ReWOORun:
    """ReWOO 加上 replanner：即 Plan-and-Execute。

    先跑计划；只要任一 worker 报错，就把 evidence 送回 replanner 生成
    修订计划再重跑。只有拿到无错误的 evidence（或重试预算耗尽）时才求解。
    """
    plan = planner.plan_for(question)
    rounds = 0
    evidence: dict[str, str] = {}
    for _ in range(max_rounds):
        rounds += 1
        evidence = run_workers(plan, tools)
        if not needs_replan(evidence):
            break
        plan = replanner.replan(question, plan, evidence)
    answer = solver.solve(question, plan, evidence)
    return ReWOORun(question=question, plan=plan, evidence=evidence,
                    answer=answer, rounds=rounds)


def run_react_mock(question: str, tools: ToolRegistry,
                   trajectory: list[tuple[str, dict[str, Any]]]) -> int:
    prompt_chars = len(question)
    total = 0
    history_chars = 0
    for name, args in trajectory:
        total += prompt_chars + history_chars + len(name) + len(str(args))
        obs = tools.dispatch(name, args)
        history_chars += len(name) + len(str(args)) + len(obs) + 40
    total += prompt_chars + history_chars
    return total


def main() -> None:
    print("=" * 70)
    print("REWOO — Planner, Workers, Solver (Phase 14, Lesson 02)")
    print("=" * 70)

    tools = ToolRegistry()
    tools.register("search", fake_search)
    tools.register("round_million", rounded_million)

    plan = Plan(steps=[
        PlanStep("E1", "search", {"query": "capital of France"}),
        PlanStep("E2", "search", {"query": "population of #E1"}),
        PlanStep("E3", "round_million", {"text": "#E2"}),
    ])
    planner = ScriptedPlanner(plan)
    solver = ScriptedSolver(
        "The capital of France is {E1}; rounded population is {E3}."
    )
    run = run_rewoo("What is the population of the capital of France, rounded?",
                    planner, tools, solver)

    print("\nPLAN")
    for step in run.plan.steps:
        print(f"  {step.id}: {step.tool}({step.args})")
    print("\nEVIDENCE")
    for k, v in run.evidence.items():
        print(f"  {k} -> {v}")
    print(f"\nFINAL: {run.answer}")

    react_chars = run_react_mock(
        run.question, tools,
        [("search", {"query": "capital of France"}),
         ("search", {"query": "population of Paris"}),
         ("round_million", {"text": "11.2 million metro"})])
    rewoo_chars = run.planner_chars + run.worker_chars + run.solver_chars
    print("\nTOKEN INTUITION (chars, approximate)")
    print(f"  react total  : {react_chars}")
    print(f"  rewoo total  : {rewoo_chars}")
    print(f"  ratio        : {react_chars / max(rewoo_chars, 1):.2f}x")
    print("\npaper claim: ~5x fewer tokens on HotpotQA. toy approximates the shape.")

    print("\n" + "=" * 70)
    print("PLAN-AND-EXECUTE — replanner triggers on worker error")
    print("=" * 70)

    # 首份计划在 E2 用了不存在的工具，触发 replanner 修订。
    bad_plan = Plan(steps=[
        PlanStep("E1", "search", {"query": "capital of France"}),
        PlanStep("E2", "lookup", {"query": "population of #E1"}),
        PlanStep("E3", "round_million", {"text": "#E2"}),
    ])
    pe_planner = ScriptedPlanner(bad_plan)
    replanner = ScriptedReplanner(fallback_tool="search")
    pe_run = run_plan_execute("What is the population of the capital of France?",
                              pe_planner, tools, solver, replanner)

    print(f"\nrounds needed : {pe_run.rounds}")
    print("final plan    :")
    for step in pe_run.plan.steps:
        print(f"  {step.id}: {step.tool}({step.args})")
    print("evidence      :")
    for k, v in pe_run.evidence.items():
        print(f"  {k} -> {v}")
    print(f"\nFINAL: {pe_run.answer}")


if __name__ == "__main__":
    main()
