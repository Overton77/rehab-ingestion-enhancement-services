# events.py
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field


EventType = Literal[
    "agent_start",
    "agent_end",
    "llm_start",
    "llm_end",
    "tool_start",
    "tool_end",
    "handoff",
]


class AgentEvent(BaseModel):
    id: int
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    event_type: EventType

    # high-level metadata
    agent_name: Optional[str] = None
    session_name: Optional[str] = None

    # tool metadata (only for tool_* events)
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None

    # basic usage snapshot
    usage: Dict[str, int] = Field(default_factory=dict)

    # arbitrary extra info (output, error, etc.)
    details: Dict[str, Any] = Field(default_factory=dict)


class EventStore:
    def __init__(self) -> None:
        self._events: List[AgentEvent] = []
        self._lock = asyncio.Lock()
        self._next_id = 1

    async def add_event(self, event: AgentEvent) -> None:
        async with self._lock:
            event.id = self._next_id
            self._next_id += 1
            self._events.append(event)

    async def list_events(
        self,
        limit: int = 100,
        agent_name: Optional[str] = None,
        session_name: Optional[str] = None,
        event_type: Optional[EventType] = None,
    ) -> List[AgentEvent]:
        async with self._lock:
            events = list(self._events)

        if agent_name:
            events = [e for e in events if e.agent_name == agent_name]
        if session_name:
            events = [e for e in events if e.session_name == session_name]
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    async def get_event(self, event_id: int) -> Optional[AgentEvent]:
        async with self._lock:
            for e in self._events:
                if e.id == event_id:
                    return e
        return None


# single shared instance used by hooks + FastAPI
event_store = EventStore()
