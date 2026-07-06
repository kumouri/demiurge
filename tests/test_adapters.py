import ast
import subprocess
import sys
import tomllib

import pytest
import yaml

from demiurge.adapters import DeployError, Deployment, get_adapter
from demiurge.mint import NeedStatement, mint


def _minted_archon(tmp_path):
    need = NeedStatement.model_validate(
        {
            "id": "scaffold-target",
            "title": "Scaffold Target",
            "task": "Exercise the adapter layer.",
            "why_persistent": "Recurring test fixture for adapter scaffolding.",
            "capabilities": ["Respond to queries"],
        }
    )
    return mint(need, tmp_path / "stable")


def test_get_adapter_rejects_unknown_names():
    with pytest.raises(ValueError, match="unknown adapter 'nope'"):
        get_adapter("nope")


def test_scaffold_generates_a_runnable_project_layout(tmp_path):
    minted = _minted_archon(tmp_path)
    adapter = get_adapter("claude-sdk")
    result = adapter.scaffold(minted.archon_dir, tmp_path / "scaffolds")

    assert result.scaffold_dir == tmp_path / "scaffolds" / "scaffold-target"
    server_source = (result.scaffold_dir / "server.py").read_text(encoding="utf-8")
    ast.parse(server_source)  # generated server must be syntactically valid Python

    project = tomllib.loads((result.scaffold_dir / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["name"] == "scaffold-target-archon"
    assert any(dep.startswith("a2a-sdk") for dep in project["project"]["dependencies"])
    assert any(dep.startswith("claude-agent-sdk") for dep in project["project"]["dependencies"])

    spec = yaml.safe_load((result.scaffold_dir / "archon.agf.yaml").read_text(encoding="utf-8"))
    assert spec["metadata"]["id"] == "scaffold-target"
    assert "Scaffold Target" in (result.scaffold_dir / "README.md").read_text(encoding="utf-8")


def test_scaffold_requires_a_minted_spec(tmp_path):
    adapter = get_adapter("claude-sdk")
    with pytest.raises(FileNotFoundError, match="mint the Archon first"):
        adapter.scaffold(tmp_path / "missing-archon", tmp_path / "scaffolds")


def _fake_deployment(tmp_path, code: str) -> Deployment:
    log_path = tmp_path / "deploy.log"
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, "-c", code], stdout=log, stderr=subprocess.STDOUT
        )
    return Deployment(
        archon_id="fake",
        endpoint="http://127.0.0.1:1",  # nothing listens here
        process=process,
        log_path=log_path,
    )


def test_wait_healthy_raises_when_the_process_dies(tmp_path):
    deployment = _fake_deployment(tmp_path, "raise SystemExit(3)")
    deployment.process.wait(timeout=30)
    with pytest.raises(DeployError, match="exited with code 3"):
        deployment.wait_healthy(timeout_seconds=5, poll_seconds=0.1)


def test_wait_healthy_times_out_and_tears_down(tmp_path):
    deployment = _fake_deployment(tmp_path, "import time; time.sleep(60)")
    with pytest.raises(DeployError, match="did not become healthy"):
        deployment.wait_healthy(timeout_seconds=0.5, poll_seconds=0.1)
    assert deployment.process.poll() is not None  # torn down, not leaked


def test_teardown_is_idempotent(tmp_path):
    deployment = _fake_deployment(tmp_path, "import time; time.sleep(60)")
    deployment.teardown()
    deployment.teardown()
    assert deployment.process.poll() is not None
