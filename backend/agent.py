"""The Yale SOM course agent.

``main.py`` calls ``run_agent(message) -> {"reply": str, "tools_used": [...]}``.

Brain:  gpt-6-astra, reached through Portkey with PORTKEY_API_KEY.
Tools:  search_courses (local, over the catalog JSON)
        web_search     (OpenAI's native provider-side web search)
Every run is appended to ``output/audit_trail.json``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.capabilities import NativeTool
from pydantic_ai.messages import (
    NativeToolCallPart,
    NativeToolReturnPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import AgentResult, AuditEntry, AuditToolCall
from tools import WEB_SEARCH_TOOL, search_courses

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"

# The key may sit in this lecture folder or one level up (e.g. MGT409/.env).
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

MODEL_NAME = "gpt-6-astra"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# How much of a tool result to keep in the audit trail.
AUDIT_RESULT_CHARS = 400


def build_agent() -> Agent:
    """Create the agent. Raises if the Portkey key is missing."""
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "PORTKEY_API_KEY is not set. Put it in Lecture 7/.env or the parent "
            "folder's .env (see .env.example)."
        )

    model = OpenAIResponsesModel(
        MODEL_NAME,
        provider=OpenAIProvider(api_key=api_key, base_url=PORTKEY_BASE_URL),
    )
    return Agent(
        model,
        name="yale_som_course_agent",
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=[search_courses],
        capabilities=[NativeTool(WEB_SEARCH_TOOL)],
        output_type=str,
    )


_agent: Agent | None = None


def get_agent() -> Agent:
    """Build the agent once and reuse it across requests."""
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def _shorten(value: Any) -> str:
    """Render a tool result as a short string for the audit trail."""
    if value is None:
        return ""
    if isinstance(value, BaseModel):
        value = value.model_dump()
    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            value = str(value)
    value = " ".join(value.split())
    if len(value) > AUDIT_RESULT_CHARS:
        return value[:AUDIT_RESULT_CHARS] + f"… ({len(value)} chars total)"
    return value


def _as_args_dict(args: Any) -> dict[str, Any] | str:
    """Tool call args arrive as a dict or a JSON string, depending on the part."""
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            return args
        return parsed if isinstance(parsed, dict) else args
    return {}


def _read_run(result: Any) -> tuple[str, list[str], list[str], list[AuditToolCall]]:
    """Pull the reply, thoughts, tool names, and tool calls out of a finished run."""
    reply = (result.output or "").strip()
    thoughts: list[str] = []
    tools_used: list[str] = []
    calls: dict[str, AuditToolCall] = {}
    ordered: list[AuditToolCall] = []

    for message in result.all_messages():
        for part in getattr(message, "parts", []):
            if isinstance(part, ThinkingPart) and part.content:
                thoughts.append(_shorten(part.content))
            elif isinstance(part, (ToolCallPart, NativeToolCallPart)):
                if part.tool_name not in tools_used:
                    tools_used.append(part.tool_name)
                call = AuditToolCall(
                    tool=part.tool_name, args=_as_args_dict(part.args)
                )
                ordered.append(call)
                if part.tool_call_id:
                    calls[part.tool_call_id] = call
            elif isinstance(part, (ToolReturnPart, NativeToolReturnPart)):
                call = calls.get(part.tool_call_id)
                if call is not None:
                    call.result = _shorten(part.content)
            elif isinstance(part, TextPart) and not reply and part.content:
                reply = part.content.strip()

    return reply, thoughts, tools_used, ordered


def _stop_reason(result: Any, reply: str) -> str:
    """Best-effort description of why the loop ended."""
    finish = getattr(getattr(result, "response", None), "finish_reason", None)
    if finish:
        return f"model finished ({finish})"
    return "model returned a final answer" if reply else "run ended with no text output"


def append_audit(entry: AuditEntry) -> None:
    """Append one row to output/audit_trail.json, never wiping earlier rows."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    if AUDIT_PATH.exists():
        try:
            existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
            if isinstance(existing, list):
                rows = existing
        except json.JSONDecodeError:
            # Keep the unreadable file around rather than silently dropping history.
            AUDIT_PATH.replace(AUDIT_PATH.with_suffix(".corrupt.json"))

    rows.append(entry.model_dump())
    AUDIT_PATH.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def run_agent(message: str) -> dict:
    """Run one agent loop over the user's message and record it."""
    try:
        result = get_agent().run_sync(message)
    except Exception as exc:  # surfaced to the UI instead of a 500
        reply = f"The course agent hit an error: {exc}"
        append_audit(
            AuditEntry(
                user_message=message,
                reply=reply,
                stop_reason=f"error: {type(exc).__name__}",
            )
        )
        return AgentResult(reply=reply).model_dump()

    reply, thoughts, tools_used, tool_calls = _read_run(result)
    append_audit(
        AuditEntry(
            user_message=message,
            thoughts=thoughts,
            tool_calls=tool_calls,
            tools_used=tools_used,
            reply=reply,
            stop_reason=_stop_reason(result, reply),
        )
    )
    return AgentResult(reply=reply, tools_used=tools_used).model_dump()


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) or "Which courses does Uri Simonsohn teach?"
    answer = run_agent(question)
    print(answer["reply"])
    print("\ntools_used:", answer["tools_used"])
