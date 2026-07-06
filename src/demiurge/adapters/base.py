"""The adapter contract (ADR 0003): scaffold a runnable project, deploy it, tear it down."""

import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

WELL_KNOWN_CARD_PATHS = ("/.well-known/agent-card.json", "/.well-known/agent.json")


class DeployError(RuntimeError):
    """The Archon failed to come up healthy."""


@dataclass(frozen=True)
class ScaffoldResult:
    archon_id: str
    scaffold_dir: Path


@dataclass
class Deployment:
    """A running Archon process and how to reach it."""

    archon_id: str
    endpoint: str
    process: subprocess.Popen
    log_path: Path
    agent_card_url: str | None = None

    def is_healthy(self) -> bool:
        """True when the process is alive and its agent card is served."""
        if self.process.poll() is not None:
            return False
        for path in WELL_KNOWN_CARD_PATHS:
            try:
                with urllib.request.urlopen(f"{self.endpoint}{path}", timeout=2) as response:
                    if response.status == 200:
                        self.agent_card_url = f"{self.endpoint}{path}"
                        return True
            except (urllib.error.URLError, OSError, ValueError):
                continue
        return False

    def wait_healthy(self, timeout_seconds: float = 300.0, poll_seconds: float = 1.0) -> None:
        """Block until healthy; on failure or timeout, tear down and raise."""
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise DeployError(
                    f"archon '{self.archon_id}' exited with code {self.process.returncode} "
                    f"before becoming healthy — see {self.log_path}"
                )
            if self.is_healthy():
                return
            time.sleep(poll_seconds)
        self.teardown()
        raise DeployError(
            f"archon '{self.archon_id}' did not become healthy within {timeout_seconds:.0f}s "
            f"— see {self.log_path}"
        )

    def teardown(self) -> None:
        """Stop the Archon process (idempotent)."""
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)


@runtime_checkable
class RuntimeAdapter(Protocol):
    """What every runtime adapter provides."""

    name: str

    def scaffold(self, archon_dir: Path, out_dir: Path) -> ScaffoldResult:
        """Generate a runnable project for the Archon at ``archon_dir``."""
        ...

    def deploy(self, scaffold_dir: Path, *, port: int, timeout_seconds: float) -> Deployment:
        """Start the scaffolded Archon and block until it is A2A-addressable."""
        ...
