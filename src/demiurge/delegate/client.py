"""A2A delegation client: resolve the agent card, send one task, harvest the result."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.client.errors import A2AClientError
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest, TaskState


class DelegationError(RuntimeError):
    """The task could not be delivered to the Archon."""


@dataclass(frozen=True)
class DelegationResult:
    """What came back from one delegated task."""

    text: str
    state: str
    task_id: str | None
    duration_seconds: float

    @property
    def completed(self) -> bool:
        return self.state == "TASK_STATE_COMPLETED"


async def delegate_async(endpoint: str, text: str, *, timeout: float = 300.0) -> DelegationResult:
    """Send ``text`` as a task to the Archon at ``endpoint`` and await the outcome."""
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=endpoint)
            card = await resolver.get_agent_card()
    except (httpx.HTTPError, A2AClientError) as error:
        raise DelegationError(f"cannot reach archon at {endpoint}: {error}") from error

    client = await create_client(agent=card, client_config=ClientConfig(streaming=False))
    try:
        request = SendMessageRequest(message=new_text_message(text, role=Role.ROLE_USER))
        harvest = _Harvest()
        async for chunk in client.send_message(request):
            harvest.take(chunk)
    finally:
        await client.close()
    return DelegationResult(
        text=harvest.text(),
        state=harvest.state_name(),
        task_id=harvest.task_id,
        duration_seconds=round(time.monotonic() - started, 3),
    )


def delegate(endpoint: str, text: str, *, timeout: float = 300.0) -> DelegationResult:
    """Synchronous wrapper around :func:`delegate_async`."""
    return asyncio.run(delegate_async(endpoint, text, timeout=timeout))


class _Harvest:
    """Defensive accumulator over the shapes client.send_message may yield.

    Chunks arrive as StreamResponse protobufs whose oneof payload wraps a
    Task, a Message, or task update events (or as tuples/lists of those,
    depending on client version). We harvest only artifact text (plus plain
    agent-message text), the last task state, and the task id — never the
    request history or status chatter.
    """

    _ONEOF_FIELDS = ("task", "msg", "message", "status_update", "artifact_update")

    def __init__(self) -> None:
        self.task_id: str | None = None
        self._state: Any = None
        self._texts: list[str] = []

    def take(self, chunk: Any) -> None:
        if isinstance(chunk, tuple | list):
            for item in chunk:
                self.take(item)
            return
        if chunk is None:
            return
        if self._unwrap(chunk):
            return
        task_id = getattr(chunk, "id", None) or getattr(chunk, "task_id", None)
        if isinstance(task_id, str) and task_id:
            self.task_id = task_id
        status = getattr(chunk, "status", None)
        state = getattr(status, "state", None)
        if state is not None:
            self._state = state
        for artifact in getattr(chunk, "artifacts", ()) or ():
            for part in getattr(artifact, "parts", ()) or ():
                self._take_part(part)
        # TaskArtifactUpdateEvent carries a single .artifact
        for part in getattr(getattr(chunk, "artifact", None), "parts", ()) or ():
            self._take_part(part)
        # A plain agent Message (has role + parts) is response text too
        if getattr(chunk, "role", None) is not None:
            for part in getattr(chunk, "parts", ()) or ():
                self._take_part(part)

    def _unwrap(self, chunk: Any) -> bool:
        """Recurse into a response envelope's set oneof payload; True if unwrapped."""
        has_field = getattr(chunk, "HasField", None)
        if has_field is None:
            return False
        for field in self._ONEOF_FIELDS:
            try:
                if has_field(field):
                    self.take(getattr(chunk, field))
                    return True
            except ValueError:
                continue
        return False

    def _take_part(self, part: Any) -> None:
        text = getattr(part, "text", None)
        if isinstance(text, str) and text:
            self._texts.append(text)

    def text(self) -> str:
        return "\n".join(self._texts)

    def state_name(self) -> str:
        if self._state is None:
            return "TASK_STATE_UNSPECIFIED"
        try:
            return TaskState.Name(self._state)
        except (ValueError, TypeError):
            return str(self._state)
