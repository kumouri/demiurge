"""Second adapter (ADR 0006): Claude Code CLI runtime behind an a2a-sdk server.

Same scaffold shape as the claude-sdk reference adapter — a standalone uv
project whose generic ``server.py`` loads and serves the minted
``archon.agf.yaml`` — but delegated tasks execute by shelling out to the
``claude`` CLI (``claude -p``) instead of importing the Claude Agent SDK.

The point is the billing/auth model: the CLI bills the operator's logged-in
Claude **subscription** (or a ``claude setup-token`` OAuth token), never a
metered API key. ``deploy`` therefore *scrubs* ``ANTHROPIC_API_KEY`` from the
Archon's environment — the deliberate inversion of claude-sdk's
``ANTHROPIC_API_KEY_DEMIURGE`` passthrough.
"""

import json
import os
import shutil
import subprocess
from importlib.resources import files
from pathlib import Path
from string import Template

import yaml

from demiurge.adapters.base import DeployError, Deployment, ScaffoldResult
from demiurge.mint.pipeline import SPEC_FILENAME

_TEMPLATE_ROOT = "templates/claude_cli"

# The env var an unattended deployment uses for subscription auth (created
# once with `claude setup-token`). Passed through untouched; never required —
# an interactive `claude` login works too.
OAUTH_TOKEN_ENV = "CLAUDE_CODE_OAUTH_TOKEN"


def scrubbed_env() -> dict[str, str]:
    """Env for a claude-cli Archon: drop ANTHROPIC_API_KEY so the CLI always
    bills the subscription (login / CLAUDE_CODE_OAUTH_TOKEN), never the
    metered API."""
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    return env


class ClaudeCliAdapter:
    name = "claude-cli"

    def scaffold(self, archon_dir: Path, out_dir: Path) -> ScaffoldResult:
        archon_dir = Path(archon_dir)
        spec_path = archon_dir / SPEC_FILENAME
        if not spec_path.is_file():
            raise FileNotFoundError(f"no {SPEC_FILENAME} in {archon_dir} — mint the Archon first")
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        metadata = spec["metadata"]

        scaffold_dir = Path(out_dir) / metadata["id"]
        scaffold_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec_path, scaffold_dir / SPEC_FILENAME)
        (scaffold_dir / "server.py").write_text(_template("server.py"), encoding="utf-8")
        substitutions = {
            "archon_id": metadata["id"],
            "archon_name": metadata["name"],
            "archon_version": metadata["version"],
        }
        for template_name, out_name in (
            ("pyproject.toml.tmpl", "pyproject.toml"),
            ("README.md.tmpl", "README.md"),
        ):
            rendered = Template(_template(template_name)).substitute(substitutions)
            (scaffold_dir / out_name).write_text(rendered, encoding="utf-8")

        # Seed the runtime-owner MCP mapping — the identical operator contract
        # the claude-sdk scaffold uses (copy to mcp-servers.json, fill in real
        # connection details); server.py translates it into `--mcp-config`.
        grants = (spec.get("action_space") or {}).get("mcp_servers") or []
        if grants:
            example = {
                grant["alias"]: {
                    "server_ref": grant.get("server_ref"),
                    "command": "REPLACE-ME",
                    "args": [],
                    "env": {},
                }
                for grant in grants
            }
            (scaffold_dir / "mcp-servers.example.json").write_text(
                json.dumps(example, indent=2) + "\n", encoding="utf-8"
            )
        return ScaffoldResult(archon_id=metadata["id"], scaffold_dir=scaffold_dir)

    def deploy(
        self,
        scaffold_dir: Path,
        *,
        port: int = 9999,
        timeout_seconds: float = 300.0,
    ) -> Deployment:
        scaffold_dir = Path(scaffold_dir)
        uv = shutil.which("uv")
        if uv is None:
            raise DeployError("uv is required to deploy scaffolds but was not found on PATH")
        log_path = scaffold_dir / "deploy.log"
        command = [
            uv,
            "run",
            "--project",
            str(scaffold_dir),
            "python",
            "server.py",
            "--port",
            str(port),
        ]
        with log_path.open("ab") as log:
            process = subprocess.Popen(
                command,
                cwd=scaffold_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=scrubbed_env(),
            )
        deployment = Deployment(
            archon_id=scaffold_dir.name,
            endpoint=f"http://127.0.0.1:{port}",
            process=process,
            log_path=log_path,
        )
        deployment.wait_healthy(timeout_seconds=timeout_seconds)
        return deployment


def _template(name: str) -> str:
    return (
        files("demiurge.adapters").joinpath(f"{_TEMPLATE_ROOT}/{name}").read_text(encoding="utf-8")
    )
