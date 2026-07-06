"""Reference adapter (ADR 0005): Claude Agent SDK runtime behind an a2a-sdk server.

The scaffold is a standalone uv project: the minted ``archon.agf.yaml`` plus a
generic ``server.py`` that loads and serves it. No per-Archon logic is
generated — the spec is the configuration.
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

_TEMPLATE_ROOT = "templates/claude_sdk"

# Demiurge-scoped Anthropic auth: if set, deployed Archons see it as
# ANTHROPIC_API_KEY so their runtime spend stays separable from other keys.
API_KEY_ENV = "ANTHROPIC_API_KEY_DEMIURGE"


class ClaudeAgentSdkAdapter:
    name = "claude-sdk"

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

        # Seed the runtime-owner MCP mapping: one example entry per grant.
        # The operator copies it to mcp-servers.json and fills in real
        # connection details (the Agent Format spec assigns them that job).
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
        env = os.environ.copy()
        if "ANTHROPIC_API_KEY" not in env and env.get(API_KEY_ENV):
            env["ANTHROPIC_API_KEY"] = env[API_KEY_ENV]
        with log_path.open("ab") as log:
            process = subprocess.Popen(
                command,
                cwd=scaffold_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
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
