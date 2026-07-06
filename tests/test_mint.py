import json

import pytest
import yaml
from pydantic import ValidationError

from demiurge.mint import MintError, NeedStatement, ToolGrant, mint
from demiurge.spec.validate import validate_document


def _need(**overrides) -> NeedStatement:
    fields = {
        "id": "changelog-scribe",
        "title": "Changelog Scribe",
        "task": "Draft release changelog entries from merged pull requests.",
        "why_persistent": "Recurs every release; accumulates style decisions worth curating.",
        "capabilities": [
            "Summarize a merged PR into a changelog line",
            "Group entries by Conventional Commit type",
        ],
        "tool_grants": [
            ToolGrant(
                alias="github",
                server_ref="github-mcp",
                allowed_tools=["list_pull_requests", "get_pull_request"],
            )
        ],
    }
    fields.update(overrides)
    return NeedStatement.model_validate(fields)


def test_mint_writes_all_four_artifacts(tmp_path):
    result = mint(_need(), tmp_path)
    assert result.spec_path.is_file()
    assert result.charter_path.is_file()
    assert result.evals_path.is_file()
    assert result.record_path.is_file()


def test_minted_spec_is_schema_valid_on_disk(tmp_path):
    result = mint(_need(), tmp_path)
    document = yaml.safe_load(result.spec_path.read_text(encoding="utf-8"))
    assert validate_document(document) == []
    assert document["metadata"]["id"] == "changelog-scribe"
    servers = document["action_space"]["mcp_servers"]
    assert servers[0]["alias"] == "github"
    assert servers[0]["allowed_tools"] == ["list_pull_requests", "get_pull_request"]


def test_record_starts_lifecycle_at_specced(tmp_path):
    result = mint(_need(), tmp_path)
    record = json.loads(result.record_path.read_text(encoding="utf-8"))
    assert record["status"] == "specced"
    assert record["archon_id"] == "changelog-scribe"
    assert record["need"]["why_persistent"]


def test_eval_seed_covers_smoke_plus_each_capability(tmp_path):
    result = mint(_need(), tmp_path)
    evals = yaml.safe_load(result.evals_path.read_text(encoding="utf-8"))
    case_ids = [case["id"] for case in evals["cases"]]
    assert case_ids == ["smoke-responds", "capability-1", "capability-2"]
    assert all(case["origin"] == "mint" for case in evals["cases"])


def test_charter_records_the_justification(tmp_path):
    result = mint(_need(), tmp_path)
    charter = result.charter_path.read_text(encoding="utf-8")
    assert "Why a persistent Archon" in charter
    assert "worth curating" in charter


def test_unjustified_need_is_refused():
    with pytest.raises(ValidationError, match="unjustified need does not get minted"):
        _need(why_persistent="   ")


def test_reminting_an_existing_archon_is_refused(tmp_path):
    mint(_need(), tmp_path)
    with pytest.raises(MintError, match="belong to curation"):
        mint(_need(), tmp_path)
