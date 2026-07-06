import yaml

from demiurge.cli import main


def _write_need(tmp_path):
    need_file = tmp_path / "need.yaml"
    need_file.write_text(
        yaml.safe_dump(
            {
                "id": "cli-archon",
                "title": "CLI Archon",
                "task": "Exercise the CLI end to end.",
                "why_persistent": "Recurring test fixture for the mint command.",
                "capabilities": ["Respond to queries"],
            }
        ),
        encoding="utf-8",
    )
    return need_file


def test_mint_then_validate_round_trip(tmp_path, capsys):
    need_file = _write_need(tmp_path)
    stable = tmp_path / "stable"

    assert main(["mint", str(need_file), "--stable-dir", str(stable)]) == 0
    out = capsys.readouterr().out
    assert "minted archon 'cli-archon'" in out

    spec_file = stable / "cli-archon" / "archon.agf.yaml"
    assert main(["validate", str(spec_file)]) == 0
    assert "valid Agent Format 1.0.0" in capsys.readouterr().out


def test_mint_rejects_bad_need(tmp_path, capsys):
    need_file = tmp_path / "need.yaml"
    need_file.write_text("id: bad\n", encoding="utf-8")
    assert main(["mint", str(need_file), "--stable-dir", str(tmp_path / "stable")]) == 2
    assert "invalid need statement" in capsys.readouterr().err


def test_validate_reports_schema_violations(tmp_path, capsys):
    bad_file = tmp_path / "bad.agf.yaml"
    bad_file.write_text("schema_version: '1.0.0'\nmetadata:\n  id: x\n", encoding="utf-8")
    assert main(["validate", str(bad_file)]) == 1
    assert "schema violation" in capsys.readouterr().err
