"""Toy ReAct agent loop — stdlib only.

Implements the five ingredients from docs/en.md:
  1. message buffer
  2. tool registry
  3. stop condition
  4. turn budget
  5. observation formatter

ToyLLM is a scripted policy so the loop runs offline and deterministic. Swap
ToyLLM for a real provider client and the control flow is identical.
"""

from __future__ import annotations

import itertools
import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable


# Global id source so every tool call gets a unique correlation id even when
# the provider doesn't supply one (ToyLLM's script entries have no call_id).
_call_ids = itertools.count(1)


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    # Correlation key pairing this call with its result. Providers name it
    # `tool_use_id` (Anthropic), `call_id` (OpenAI), `toolUseId` (Bedrock).
    call_id: str | None = None


@dataclass
class Turn:
    kind: str
    content: str
    tool_call: ToolCall | None = None
    observation: str | None = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., str]] = {}

    def register(self, name: str, fn: Callable[..., str]) -> None:
        self._tools[name] = fn

    def names(self) -> list[str]:
        return sorted(self._tools)

    def dispatch(self, call: ToolCall) -> str:
        fn = self._tools.get(call.name)
        if fn is None:
            return f"error: unknown tool {call.name!r}"
        try:
            return fn(**call.args)
        except TypeError as e:
            return f"error: bad args for {call.name}: {e}"
        except Exception as e:
            return f"error: {type(e).__name__}: {e}"

    def dispatch_many(self, calls: list[ToolCall]) -> dict[str, str]:
        """Execute parallel calls and associate results by call_id.

        Parallel tools return out of order, so results are keyed by call_id
        instead of by position. We reverse the iteration here to exercise that
        path: the caller must look results up by id, never by list order.
        """
        results: dict[str, str] = {}
        for call in reversed(calls):
            results[call.call_id] = self.dispatch(call)
        return results


def calculator(expr: str) -> str:
    allowed = set("0123456789+-*/(). ")
    if not set(expr).issubset(allowed):
        return "error: illegal character in expr"
    try:
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"


class KVStore:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str:
        return self._store.get(key, f"missing:{key}")

    def set(self, key: str, value: str) -> str:
        self._store[key] = value
        return f"stored {key}"


class ToyLLM:
    """Scripted ReAct policy. Returns one assistant turn per call.

    Each script entry is either a 'turn' (a thought plus a list of parallel
    tool 'calls') or a 'finish' (the final answer). A 'turn' with an empty
    'calls' list is a direct answer: the loop stops with no tool dispatch.
    The loop runs through the script in order.

    To simulate 2026 CRITIC-style correction, an entry whose index is in
    ``malformed_at`` is emitted with a broken args payload (a list instead of
    a dict). The registry dispatch then returns an error observation, which the
    loop feeds back into the history; the next script entry models the LLM
    reading that error and retrying with correct args.
    """

    def __init__(self, script: list[dict[str, Any]],
                 malformed_at: set[int] | None = None) -> None:
        self.script = script
        self.cursor = 0
        self.malformed_at = malformed_at or set()

    def respond(self, history: list[Turn]) -> dict[str, Any]:
        if self.cursor >= len(self.script):
            return {"kind": "finish", "content": "no more actions"}
        entry = self.script[self.cursor]
        self.cursor += 1
        if self.cursor - 1 in self.malformed_at:
            entry = self._malform(entry)
        return entry

    @staticmethod
    def _malform(entry: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of entry whose calls carry a non-mapping args payload."""
        out = dict(entry)
        out["calls"] = [
            {"name": c["name"], "args": [c.get("args", {})]}
            for c in entry.get("calls", [])
        ]
        return out


RESPONSES_URL = "https://api.deepseek.com/responses"

class ResponsesLLM:
    """A stdlib client for the OpenAI Responses API (exercise 4).

    ToyLLM prompts the model for an inline `Thought:` string. The Responses API
    replaced that with native reasoning on a separate channel: the `output`
    array carries `reasoning` items alongside `function_call` items. This client
    splits the two apart and maps them back onto the loop's `{"thought",
    "calls"}` contract, so `AgentLoop` is untouched. The only difference is
    where the thought comes from — the reasoning channel (surfaced as a
    summary), not an inline string we prompted for.
    """

    def __init__(self, tools_schema: list[dict[str, Any]],
                 model: str = "deepseek-flash") -> None:
        self.tools_schema = tools_schema
        self.model = model
        self.api_key = (os.environ.get("DEEPSEEK_API_KEY")
                        or os.environ.get("OPENAI_API_KEY"))
        if self.api_key is not None and not self.api_key.isascii():
            raise ValueError(
                "API key contains non-ASCII characters (stray quote or BOM?). "
                "Re-set DEEPSEEK_API_KEY with a clean ASCII key.")

    def respond(self, history: list[Turn]) -> dict[str, Any]:
        if not self.api_key:
            return {"kind": "finish",
                    "content": "no OPENAI_API_KEY set — run the offline ToyLLM demo"}
        payload = {
            "model": self.model,
            "input": self._serialize_history(history),
            "tools": self.tools_schema,
        }
        request = urllib.request.Request(
            RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            print(f"[responses] HTTP {e.code} {e.reason}: {detail}")
            return {"kind": "finish", "content": f"API error {e.code}: {detail}"}
        return self._parse(body)

    @staticmethod
    def _serialize_history(history: list[Turn]) -> list[dict[str, Any]]:
        items = []
        for turn in history:
            if turn.kind == "user":
                items.append({"role": "user", "content": turn.content})
            elif turn.kind == "reasoning":
                # DeepSeek's thinking mode is stateless, so each request must
                # replay the previous turn's chain-of-thought. Skipping it makes
                # the API reject the call with "reasoning_text ... must be
                # passed back".
                items.append({
                    "type": "reasoning",
                    "content": [{"type": "reasoning_text", "text": turn.content}],
                })
            elif turn.kind == "action":
                # Replay the call and its result so the stateless API can
                # reconstruct the conversation.
                call = turn.tool_call
                name = call.name if call else turn.content
                args = json.dumps(call.args) if call and call.args else "{}"
                call_id = call.call_id if call and call.call_id else turn.content
                items.append({
                    "type": "function_call",
                    "call_id": call_id,
                    "name": name,
                    "arguments": args,
                })
                items.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": turn.observation or "",
                })
        return items

    @staticmethod
    def _parse(body: dict[str, Any]) -> dict[str, Any]:
        thought_parts: list[str] = []
        calls: list[dict[str, Any]] = []
        answer = ""
        for item in body.get("output", []):
            kind = item.get("type")
            if kind == "reasoning":
                # DeepSeek returns the chain-of-thought in plain text under
                # `content` (reasoning_text parts) with an empty `summary`;
                # OpenAI's encrypted form only exposes `summary`. Read both.
                content = item.get("content") or []
                thought_parts.append(
                    " ".join(s.get("text", "") for s in content
                             if isinstance(s, dict) and s.get("type") == "reasoning_text")
                )
                summary = item.get("summary") or []
                thought_parts.append(
                    " ".join(s.get("text", "") for s in summary if isinstance(s, dict))
                )
            elif kind == "function_call":
                try:
                    args = json.loads(item.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                calls.append({"name": item.get("name", ""), "args": args,
                              "call_id": item.get("call_id", "")})
            elif kind == "message":
                for block in item.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "output_text":
                        answer += block.get("text", "")
        thought = " ".join(p for p in thought_parts if p).strip()
        if calls:
            return {"kind": "turn", "reasoning": True, "thought": thought, "calls": calls}
        return {"kind": "turn", "thought": answer or thought, "calls": []}


@dataclass
class AgentLoop:
    llm: Any
    tools: ToolRegistry
    max_turns: int = 12
    max_tool_calls_per_turn: int = 3
    history: list[Turn] = field(default_factory=list)

    def run(self, user_message: str) -> str:
        self.history.append(Turn(kind="user", content=user_message))
        for step in range(self.max_turns):
            reply = self.llm.respond(self.history)
            if reply["kind"] == "finish":
                self.history.append(Turn(kind="final", content=reply["content"]))
                return reply["content"]
            thought = reply.get("thought", "")
            thought_kind = "reasoning" if reply.get("reasoning") else "thought"
            self.history.append(Turn(kind=thought_kind, content=thought))
            calls = reply.get("calls", [])
            if not calls:
                # No tool calls: the model answered directly. Stop here.
                self.history.append(Turn(kind="final", content=thought))
                return thought
            tool_calls = [
                ToolCall(name=e["name"], args=e.get("args", {}),
                         call_id=e.get("call_id") or f"call_{next(_call_ids)}")
                for e in calls[: self.max_tool_calls_per_turn]
            ]
            # Issue every call, then collect results keyed by call_id. Parallel
            # results can arrive in any order; each is matched to its call by the
            # correlation id, never by list position.
            results = self.tools.dispatch_many(tool_calls)
            for call in tool_calls:
                self.history.append(
                    Turn(kind="action", content=call.name,
                         tool_call=call, observation=results[call.call_id])
                )
            dropped = len(calls) - self.max_tool_calls_per_turn
            if dropped > 0:
                self.history.append(
                    Turn(kind="dropped",
                         content=f"{dropped} tool call(s) dropped "
                                 f"(max_tool_calls_per_turn={self.max_tool_calls_per_turn})")
                )
        self.history.append(Turn(kind="final",
                                 content="budget exhausted"))
        return "budget exhausted"


def pretty_trace(history: list[Turn]) -> None:
    for i, turn in enumerate(history):
        tag = f"[{i:02d} {turn.kind:>7}]"
        if turn.kind == "user":
            print(f"{tag} {turn.content}")
        elif turn.kind == "thought":
            print(f"{tag} {turn.content}")
        elif turn.kind == "reasoning":
            print(f"{tag} {turn.content}")
        elif turn.kind == "action":
            call = turn.tool_call
            assert call is not None
            print(f"{tag} {call.name}({call.args}) -> {turn.observation}")
        elif turn.kind == "dropped":
            print(f"{tag} {turn.content}")
        elif turn.kind == "final":
            print(f"{tag} {turn.content}")


def build_demo_agent() -> AgentLoop:
    tools = ToolRegistry()
    tools.register("calculator", calculator)
    kv = KVStore()
    tools.register("kv_get", kv.get)
    tools.register("kv_set", kv.set)

    script: list[dict[str, Any]] = [
        {"kind": "turn", "thought": "store the base price",
         "calls": [
             {"name": "kv_set", "args": {"key": "base", "value": "120"}},
         ]},
        {"kind": "turn", "thought": "compute the 15% tax",
         "calls": [
             {"name": "calculator", "args": {"expr": "120 * 0.15"}},
         ]},
        {"kind": "turn", "thought": "calculator errored; retry with a proper dict",
         "calls": [
             {"name": "calculator", "args": {"expr": "120 * 0.15"}},
         ]},
        {"kind": "turn", "thought": "store tax, compute total, and save a note",
         "calls": [
             {"name": "kv_set", "args": {"key": "tax", "value": "18.0"}},
             {"name": "calculator", "args": {"expr": "120 + 18.0"}},
             {"name": "kv_set", "args": {"key": "note", "value": "will be dropped"}},
         ]},
        {"kind": "turn", "thought": "the total including 15% tax is 138.0",
         "calls": []},
    ]
    # Index 1 is emitted with a malformed args payload, so its dispatch yields
    # an error observation; the following entry is the self-correction retry.
    return AgentLoop(llm=ToyLLM(script, malformed_at={1}), tools=tools,
                     max_turns=10, max_tool_calls_per_turn=2)


def build_responses_agent() -> AgentLoop:
    tools = ToolRegistry()
    tools.register("calculator", calculator)
    kv = KVStore()
    tools.register("kv_get", kv.get)
    tools.register("kv_set", kv.set)

    tools_schema = [
        {
            "type": "function",
            "name": "calculator",
            "description": "evaluate an arithmetic expression",
            "parameters": {
                "type": "object",
                "properties": {"expr": {"type": "string"}},
                "required": ["expr"],
            },
        },
        {
            "type": "function",
            "name": "kv_get",
            "description": "read a value from the key-value store",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
        },
        {
            "type": "function",
            "name": "kv_set",
            "description": "write a value to the key-value store",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}, "value": {"type": "string"}},
                "required": ["key", "value"],
            },
        },
    ]
    return AgentLoop(llm=ResponsesLLM(tools_schema=tools_schema), tools=tools,
                     max_turns=10, max_tool_calls_per_turn=2)


def main() -> None:
    print("=" * 70)
    print("REACT LOOP — Phase 14, Lesson 01")
    print("=" * 70)
    # Set DEEPSEEK_API_KEY in your environment (never hardcode keys).
    if os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        agent = build_responses_agent()
    else:
        print("(no OPENAI_API_KEY; running the offline ToyLLM demo)")
        agent = build_demo_agent()
    final = agent.run("What is 120 plus 15% tax, stored in kv?")
    print()
    pretty_trace(agent.history)
    print()
    print(f"final answer: {final}")
    print(f"turns used:   {len([t for t in agent.history if t.kind == 'action'])}")
    print(f"tools used:   {agent.tools.names()}")


if __name__ == "__main__":
    main()
