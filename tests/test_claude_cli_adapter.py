"""The claude-cli adapter (ADR 0006): scaffold layout, CLI wiring, billing scrub."""

import ast
import importlib.util
import json
import tomllib
from pathlib import Path

import pytest
import yaml

from demiurge.adapters import get_adapter
from demiurge.adapters.claude_cli import scrubbed_env
from demiurge.mint import NeedStatement, mint


def _load_generated_server(scaffold_dir: Path):
    spec_module = importlib.util.spec_from_file_location(
        "generated_cli_server", scaffold_dir / "server.py"
    )
    server = importlib.util.module_from_spec(spec_module)
    spec_module.loader.exec_module(server)
    return server


def _minted_archon(tmp_path, **overrides):
    fields = {
        "id": "cli-target",
        "title": "CLI Target",
        "task": "Exercise the claude-cli adapter.",
        "why_persistent": "Recurring test fixture for CLI adapter scaffolding.",
        "capabilities": ["Respond to queries"],
    }
    fields.update(overrides)
    return mint(NeedStatement.model_validate(fields), tmp_path / "stable")


def test_scaffold_generates_a_runnable_project_layout(tmp_path):
    minted = _minted_archon(tmp_path)
    adapter = get_adapter("claude-cli")
    result = adapter.scaffold(minted.archon_dir, tmp_path / "scaffolds")

    assert result.scaffold_dir == tmp_path / "scaffolds" / "cli-target"
    server_source = (result.scaffold_dir / "server.py").read_text(encoding="utf-8")
    ast.parse(server_source)  # generated server must be syntactically valid Python

    project = tomllib.loads((result.scaffold_dir / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["name"] == "cli-target-archon"
    assert any(dep.startswith("a2a-sdk") for dep in project["project"]["dependencies"])
    # the CLI is a subprocess, not an import — the SDK dependency must be gone
    assert not any(dep.startswith("claude-agent-sdk") for dep in project["project"]["dependencies"])

    spec = yaml.safe_load((result.scaffold_dir / "archon.agf.yaml").read_text(encoding="utf-8"))
    assert spec["metadata"]["id"] == "cli-target"
    readme = (result.scaffold_dir / "README.md").read_text(encoding="utf-8")
    assert "CLI Target" in readme
    assert "subscription" in readme  # the billing model is the point — document it


def test_local_tools_flow_from_need_to_cli_allowed_tools(tmp_path):
    minted = _minted_archon(
        tmp_path,
        id="tooled-target",
        title="Tooled Target",
        local_tools=[
            {"alias": "shell", "name": "Bash(python *)"},
            {"alias": "WebSearch"},  # name defaults to the alias
        ],
        tool_grants=[
            {"alias": "notion", "server_ref": "notion-mcp", "allowed_tools": ["notion_search"]},
        ],
    )
    spec_doc = yaml.safe_load(minted.spec_path.read_text(encoding="utf-8"))
    local = spec_doc["action_space"]["local_tools"]
    assert [grant["alias"] for grant in local] == ["shell", "WebSearch"]

    adapter = get_adapter("claude-cli")
    result = adapter.scaffold(minted.archon_dir, tmp_path / "scaffolds")
    server = _load_generated_server(result.scaffold_dir)
    assert server.builtin_tools(spec_doc) == ["Bash(python *)", "WebSearch"]

    # MCP grants keep the claude-sdk operator contract, translated to CLI shape
    mapping_path = result.scaffold_dir / "mcp-servers.json"
    mapping_path.write_text(
        json.dumps({"notion": {"command": "npx", "args": ["-y", "notion-mcp"]}}),
        encoding="utf-8",
    )
    servers, allowed = server.mcp_options(spec_doc, config_path=mapping_path)
    assert servers == {"notion": {"command": "npx", "args": ["-y", "notion-mcp"]}}
    assert allowed == ["mcp__notion__notion_search"]

    cli_config = server.write_cli_mcp_config(servers, path=result.scaffold_dir / "cli.json")
    assert json.loads(cli_config.read_text(encoding="utf-8")) == {"mcpServers": servers}


def test_build_cli_command_composes_the_one_shot_invocation(tmp_path):
    minted = _minted_archon(tmp_path)
    adapter = get_adapter("claude-cli")
    result = adapter.scaffold(minted.archon_dir, tmp_path / "scaffolds")
    server = _load_generated_server(result.scaffold_dir)

    command = server.build_cli_command(
        cli_bin="claude",
        user_request="do the thing",
        instructions="You are a test Archon.",
        model="claude-sonnet-5",
        allowed_tools=["Bash", "mcp__notion__notion_search"],
        mcp_config_file=tmp_path / "cli.json",
        permission_mode=None,
    )
    assert command[:3] == ["claude", "-p", "do the thing"]
    assert command[command.index("--model") + 1] == "claude-sonnet-5"
    assert command[command.index("--allowedTools") + 1] == "Bash,mcp__notion__notion_search"
    assert "--strict-mcp-config" in command
    assert command[command.index("--append-system-prompt") + 1] == "You are a test Archon."

    bare = server.build_cli_command(
        cli_bin="claude",
        user_request="hi",
        instructions="x",
        model=None,
        allowed_tools=[],
        mcp_config_file=None,
        permission_mode=None,
    )
    for flag in ("--model", "--allowedTools", "--mcp-config", "--permission-mode"):
        assert flag not in bare


def test_deploy_time_model_override_beats_the_spec(tmp_path):
    # The deploy-time knob (any archon on any model; parallel instances on different models): a
    # --model passed at deploy overrides whatever the spec declared. Without it, the spec's model
    # still wins — so existing deployments are unchanged.
    minted = _minted_archon(tmp_path)
    adapter = get_adapter("claude-cli")
    result = adapter.scaffold(minted.archon_dir, tmp_path / "scaffolds")
    server = _load_generated_server(result.scaffold_dir)
    spec = yaml.safe_load((result.scaffold_dir / "archon.agf.yaml").read_text(encoding="utf-8"))
    spec["execution_policy"]["config"]["model"] = "claude-opus-4-8"

    assert server.ArchonExecutor(spec, "claude-fable-5")._model == "claude-fable-5"  # override wins
    assert server.ArchonExecutor(spec)._model == "claude-opus-4-8"  # else the spec's model


def test_env_scrub_drops_the_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-leak")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "subscription-token")
    env = scrubbed_env()
    assert "ANTHROPIC_API_KEY" not in env
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "subscription-token"


def test_scaffold_requires_a_minted_spec(tmp_path):
    adapter = get_adapter("claude-cli")
    with pytest.raises(FileNotFoundError, match="mint the Archon first"):
        adapter.scaffold(tmp_path / "missing-archon", tmp_path / "scaffolds")
