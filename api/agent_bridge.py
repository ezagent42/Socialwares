"""
agent_bridge.py — Translation layer between the API layer and Agent logic.

ARCHITECTURE (RSCF mapping):
  Scope      = Room (task boundary, workspace isolation path)
  Flow       = AgentTask.status transitions (open → in_progress → submitted → completed)
  Commitment = The invoke() contract: AgentRequest in, AgentResponse out
  Role       = Future: agent/ module will define agent roles (placeholder only)

TODAY: Calls Anthropic SDK directly.
FUTURE: When agent/ module interface is defined, replace _call_anthropic() with
        agent.invoke(request). The AgentRequest / AgentResponse contract here is the
        stable interface that agent/ must implement.

INTERFACE CONTRACT (for agent/ module implementors):
  The agent/ module must expose:
    async def invoke(request: AgentRequest) -> AgentResponse

  AgentRequest fields:
    room_name       str           workspace/scope identifier
    workspace_path  str           absolute path for file operations
    prompt          str           user prompt for this turn
    task_id         str | None    existing task ID (None = new task)
    task_status     str | None    current Flow state
    history         list[dict]    prior [{role, content}] messages

  AgentResponse fields:
    content         str           agent reply text
    task_status     str           suggested next Flow state
    agent_id        str           model/agent identifier
    metadata        dict | None   optional extra data
"""

import os
from dataclasses import dataclass, field

from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
DEFAULT_MODEL = "claude-opus-4-6"


@dataclass
class AgentRequest:
    room_name: str
    workspace_path: str
    prompt: str
    task_id: str | None = None
    task_status: str | None = None
    history: list[dict] = field(default_factory=list)


@dataclass
class AgentResponse:
    content: str
    task_status: str
    agent_id: str = DEFAULT_MODEL
    metadata: dict | None = None


async def invoke(request: AgentRequest) -> AgentResponse:
    """Single entry point for all agent invocations.

    Today: calls Anthropic SDK directly.
    Future: route through agent/ module once interface is defined.
    """
    system_prompt = _build_system_prompt(request)
    messages = list(request.history) + [{"role": "user", "content": request.prompt}]

    response = await client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
    )

    content = response.content[0].text
    next_status = _infer_status_transition(request.task_status, content)

    return AgentResponse(
        content=content,
        task_status=next_status,
        agent_id=DEFAULT_MODEL,
    )

    # TODO: streaming SSE endpoint — use client.messages.stream() for responsive UI (Phase 2)


def _build_system_prompt(request: AgentRequest) -> str:
    return f"""You are an AI agent operating in the workspace: {request.room_name}
Workspace path: {request.workspace_path}
Current task status: {request.task_status or "none"}

Help the user accomplish tasks in this workspace. Follow the RSCF model:
- Your Scope is limited to the {request.room_name} workspace
- When you complete a task, say TASK_COMPLETE at the end of your response
- If you need more information, ask clearly before proceeding
"""


def _infer_status_transition(current: str | None, response_text: str) -> str:
    """Simple heuristic status transition. Replace with Flow state machine from agent/."""
    if "TASK_COMPLETE" in response_text:
        return "submitted"
    if current is None or current == "open":
        return "in_progress"
    return current
