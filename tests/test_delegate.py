import socket
import threading
import time
import urllib.request

import pytest
import uvicorn
from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.types.a2a_pb2 import TaskState
from starlette.applications import Starlette

from demiurge.delegate import DelegationError, delegate, read_ledger, record_delegation


class EchoExecutor(AgentExecutor):
    """A minimal A2A agent: echoes the request text back as an artifact."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if not task:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        text = get_message_text(context.message)
        await updater.add_artifact(
            parts=[new_text_part(text=f"echo: {text}", media_type="text/plain")]
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED, message=new_text_message("done")
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def echo_endpoint():
    port = _free_port()
    endpoint = f"http://127.0.0.1:{port}"
    card = AgentCard(
        name="Echo",
        description="Echoes requests.",
        version="0.0.1",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(protocol_binding="JSONRPC", url=endpoint, protocol_version="1.0")
        ],
        skills=[AgentSkill(id="echo", name="Echo", description="Echoes.", tags=["test"])],
    )
    handler = DefaultRequestHandler(
        agent_executor=EchoExecutor(), task_store=InMemoryTaskStore(), agent_card=card
    )
    app = Starlette(routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, "/")])
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 30
    last_error = None
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"{endpoint}/.well-known/agent-card.json", timeout=1)
            break
        except OSError as error:
            last_error = error
            time.sleep(0.2)
    else:
        raise RuntimeError(f"echo server never came up: {last_error}")

    yield endpoint
    server.should_exit = True
    thread.join(timeout=10)


def test_delegate_round_trip_over_a2a(echo_endpoint):
    result = delegate(echo_endpoint, "ping", timeout=30)
    assert "echo: ping" in result.text
    assert result.completed, result.state
    assert result.duration_seconds >= 0


def test_delegation_is_recorded_in_the_ledger(tmp_path, echo_endpoint):
    archon_dir = tmp_path / "echo-archon"
    archon_dir.mkdir()
    result = delegate(echo_endpoint, "ledger me", timeout=30)
    entry = record_delegation(archon_dir, "ledger me", result)

    entries = read_ledger(archon_dir)
    assert entries == [entry]
    assert entries[0]["request"] == "ledger me"
    assert "echo: ledger me" in entries[0]["response"]
    assert entries[0]["state"] == "TASK_STATE_COMPLETED"


def test_ledger_of_unknown_archon_is_empty(tmp_path):
    assert read_ledger(tmp_path / "nope") == []


def test_unreachable_archon_raises_delegation_error():
    with pytest.raises(DelegationError, match="cannot reach archon"):
        delegate("http://127.0.0.1:9", "hello", timeout=2)
