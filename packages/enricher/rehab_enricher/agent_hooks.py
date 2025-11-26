# hooks.py
from typing import Any, Optional, cast

from agents import Agent, RunContextWrapper, RunHooks, Tool, Usage
from agents.items import ModelResponse, TResponseInputItem
from agents.tool_context import ToolContext

from .runner_events import AgentEvent, event_store


class RehabRunHooks(RunHooks):
    """
    Global run hooks for the rehab enrichment workflows.
    Logs all major lifecycle events into the shared EventStore.
    """

    def __init__(self) -> None:
        self.event_counter = 0

    def _usage_to_dict(self, usage: Usage) -> dict:
        return {
            "requests": usage.requests,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        }

    def _session_name_from_context(self, context: RunContextWrapper[Any]) -> Optional[str]:
        # If you add session_name to your context object, it will be picked up here.
        # e.g. context.context.session_name = "rehab_run_123"
        return getattr(context.context, "session_name", None)

    async def _log_event(
        self,
        event_type: str,
        context: RunContextWrapper[Any],
        agent: Optional[Agent[Any]] = None,
        extra: dict | None = None,
    ) -> None:
        self.event_counter += 1
        usage_dict = self._usage_to_dict(context.usage)
        session_name = self._session_name_from_context(context)

        event = AgentEvent(
            id=0,  # filled by store
            event_type=event_type,  # type: ignore[arg-type]
            agent_name=agent.name if agent else None,
            session_name=session_name,
            usage=usage_dict,
            details=extra or {},
        )
        await event_store.add_event(event)

    # ---- Agent lifecycle ----

    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        await self._log_event("agent_start", context, agent)

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        await self._log_event(
            "agent_end",
            context,
            agent,
            extra={"output_preview": str(output)[:500]},
        )

    # ---- LLM lifecycle ----

    async def on_llm_start(
        self,
        context: RunContextWrapper,
        agent: Agent,
        system_prompt: Optional[str],
        input_items: list[TResponseInputItem],
    ) -> None:
        await self._log_event(
            "llm_start",
            context,
            agent,
            extra={"system_prompt_preview": (system_prompt or "")[:500]},
        )

    async def on_llm_end(
        self,
        context: RunContextWrapper,
        agent: Agent,
        response: ModelResponse,
    ) -> None:
        await self._log_event(
            "llm_end",
            context,
            agent,
            extra={"response_preview": str(response)[:500]},
        )

    # ---- Tool lifecycle (local tools only) ----

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        tool_context = cast(ToolContext[Any], context)
        await self._log_event(
            "tool_start",
            tool_context,
            agent,
            extra={
                "tool_name": tool.name,
                "tool_call_id": tool_context.tool_call_id,
                "tool_arguments": tool_context.tool_arguments,
            },
        )

    async def on_tool_end(
        self,
        context: RunContextWrapper,
        agent: Agent,
        tool: Tool,
        result: str,
    ) -> None:
        tool_context = cast(ToolContext[Any], context)
        await self._log_event(
            "tool_end",
            tool_context,
            agent,
            extra={
                "tool_name": tool.name,
                "tool_call_id": tool_context.tool_call_id,
                "tool_arguments": tool_context.tool_arguments,
                "result_preview": result[:500],
            },
        )

    # ---- Handoffs between agents ----

    async def on_handoff(
        self,
        context: RunContextWrapper,
        from_agent: Agent,
        to_agent: Agent,
    ) -> None:
        await self._log_event(
            "handoff",
            context,
            from_agent,
            extra={"to_agent": to_agent.name},
        )
