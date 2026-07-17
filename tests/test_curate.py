import json

import pytest
import yaml

from demiurge.curate import (
    admit,
    distill_failure,
    load_evals,
    load_record,
    record_verdict,
    retire,
    revise,
    run_evals,
    tenure_review,
)
from demiurge.delegate import delegate, record_delegation
from demiurge.delegate.ledger import LEDGER_FILENAME, ledger_path
from demiurge.mint import NeedStatement, mint


def _need(**overrides) -> NeedStatement:
    fields = {
        "id": "echo-archon",
        "title": "Echo Archon",
        "task": "Echo requests back for loop testing.",
        "why_persistent": "Recurring fixture exercising the full curation loop.",
        "capabilities": ["Echo a query back verbatim"],
    }
    fields.update(overrides)
    return NeedStatement.model_validate(fields)


def _fake_delegation(archon_dir, task_id: str, state: str = "TASK_STATE_COMPLETED", response="ok",
                     ledger_dir=None):
    entry = {
        "delegated_at": "2026-07-06T00:00:00+00:00",
        "request": f"request for {task_id}",
        "response": response,
        "state": state,
        "task_id": task_id,
        "duration_seconds": 0.1,
    }
    path = ledger_path(archon_dir, ledger_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(entry) + "\n")
    return entry


def test_status_transitions_are_validated(tmp_path):
    from demiurge.curate.record import set_status

    minted = mint(_need(), tmp_path)
    with pytest.raises(ValueError, match="invalid status"):
        set_status(minted.archon_dir, "bogus", "x", "y")


def test_admission_passes_against_the_echo_agent(tmp_path, echo_endpoint):
    minted = mint(_need(), tmp_path)
    report = admit(minted.archon_dir, echo_endpoint, timeout=30)
    assert report.passed
    record = load_record(minted.archon_dir)
    assert record["status"] == "admitted"
    assert record["history"][-1]["event"] == "admission-passed"
    assert (minted.archon_dir / "eval-report.json").is_file()


def test_admission_fails_closed_on_unmet_expectations(tmp_path, echo_endpoint):
    minted = mint(_need(id="picky-archon"), tmp_path)
    suite = load_evals(minted.archon_dir)
    suite.cases[0].expect_contains = ["the echo agent will never say this"]
    from demiurge.curate import save_evals

    save_evals(minted.archon_dir, suite)

    report = admit(minted.archon_dir, echo_endpoint, timeout=30)
    assert not report.passed
    record = load_record(minted.archon_dir)
    assert record["status"] == "specced"
    assert record["history"][-1]["event"] == "admission-failed"


def test_verdict_requires_a_real_task(tmp_path):
    minted = mint(_need(id="verdict-archon"), tmp_path)
    with pytest.raises(ValueError, match="no delegation with task_id"):
        record_verdict(minted.archon_dir, "ghost-task", "failure")


def test_tenure_heuristics(tmp_path):
    minted = mint(_need(id="tenure-archon"), tmp_path)
    # Not enough evidence -> keep
    _fake_delegation(minted.archon_dir, "t1")
    assert tenure_review(minted.archon_dir).recommendation == "keep"
    # A verdict overrides the transport heuristic
    _fake_delegation(minted.archon_dir, "t2")
    _fake_delegation(minted.archon_dir, "t3")
    record_verdict(minted.archon_dir, "t2", "failure", "wrong answer")
    report = tenure_review(minted.archon_dir)
    assert report.delegations == 3
    assert report.failures == 1
    assert report.recommendation == "revise"
    # Overwhelming failure -> retire (8 failures / 10 delegations = 80%)
    for task in ("t4", "t5", "t6", "t7", "t8", "t9", "t10"):
        _fake_delegation(minted.archon_dir, task, state="TASK_STATE_FAILED", response="")
    assert tenure_review(minted.archon_dir).recommendation == "retire"


def test_retire_ends_tenure_but_keeps_the_record(tmp_path):
    minted = mint(_need(id="old-archon"), tmp_path)
    retire(minted.archon_dir, "superseded")
    record = load_record(minted.archon_dir)
    assert record["status"] == "retired"
    assert (minted.archon_dir / "archon.agf.yaml").is_file()  # the record remains


def test_distill_turns_a_failure_into_a_regression_case(tmp_path):
    minted = mint(_need(id="distill-archon"), tmp_path)
    _fake_delegation(minted.archon_dir, "bad-task", response="wrong")
    case = distill_failure(
        minted.archon_dir, "bad-task", "must include the word echo", expect_contains=["echo"]
    )
    assert case.id == "field-failure-1"
    assert case.origin == "field-failure"
    suite = load_evals(minted.archon_dir)
    assert suite.cases[-1].id == "field-failure-1"
    assert suite.cases[-1].input["query"] == "request for bad-task"
    # a second distillation increments the index
    _fake_delegation(minted.archon_dir, "bad-task-2", response="also wrong")
    case2 = distill_failure(minted.archon_dir, "bad-task-2", "still broken")
    assert case2.id == "field-failure-2"


def test_revise_bumps_version_and_keeps_earned_evals(tmp_path):
    minted = mint(_need(id="revise-archon"), tmp_path)
    _fake_delegation(minted.archon_dir, "bad-task", response="wrong")
    distill_failure(minted.archon_dir, "bad-task", "regression", expect_contains=["echo"])

    revised = revise(_need(id="revise-archon", task="Echo better this time."), tmp_path)
    assert revised.spec.metadata.version == "0.2.0"
    record = load_record(minted.archon_dir)
    assert record["status"] == "specced"
    assert record["history"][-1]["event"] == "revised"
    suite = load_evals(minted.archon_dir)
    origins = [case.origin for case in suite.cases]
    assert "field-failure" in origins  # earned case survives revision
    spec = yaml.safe_load((minted.archon_dir / "archon.agf.yaml").read_text(encoding="utf-8"))
    assert spec["metadata"]["version"] == "0.2.0"
    assert "Echo better" in spec["metadata"]["description"]


def test_the_full_loop_end_to_end(tmp_path, echo_endpoint):
    """Phase 3 exit: admitted -> field failure -> distill -> revise -> re-admitted,
    passing the failure-derived eval."""
    minted = mint(_need(id="loop-archon"), tmp_path)

    # 1. eval-gated admission
    assert admit(minted.archon_dir, echo_endpoint, timeout=30).passed
    assert load_record(minted.archon_dir)["status"] == "admitted"

    # 2. real delegated work, recorded in the ledger
    result = delegate(echo_endpoint, "summarize the release notes", timeout=30)
    record_delegation(minted.archon_dir, "summarize the release notes", result)

    # 3. the field says the output was wrong
    record_verdict(minted.archon_dir, result.task_id, "failure", "echoed instead of summarizing")

    # 4. the failure is distilled into a regression eval the successor must pass
    case = distill_failure(
        minted.archon_dir,
        result.task_id,
        "must respond to the release-notes request",
        expect_contains=["release notes"],
    )
    assert case.origin == "field-failure"

    # 5. revise and re-enter through the gate — including the earned case
    revise(_need(id="loop-archon", task="Echo requests, including summaries."), tmp_path)
    assert load_record(minted.archon_dir)["status"] == "specced"
    report = admit(minted.archon_dir, echo_endpoint, timeout=30)
    assert report.passed, [result.checks for result in report.results if not result.passed]
    failure_results = [result for result in report.results if result.origin == "field-failure"]
    assert failure_results and all(result.passed for result in failure_results)
    assert load_record(minted.archon_dir)["status"] == "admitted"


def test_run_evals_writes_a_report(tmp_path, echo_endpoint):
    minted = mint(_need(id="report-archon"), tmp_path)
    report = run_evals(minted.archon_dir, echo_endpoint, timeout=30)
    on_disk = json.loads((minted.archon_dir / "eval-report.json").read_text(encoding="utf-8"))
    assert on_disk["passed"] == report.passed
    assert len(on_disk["results"]) == len(report.results)


# --- ledger_dir: the curate side must agree with the delegate side ------------------------------


def test_verdict_and_tenure_follow_the_ledger_dir(tmp_path):
    """A verdict must find the delegation it judges. If `delegate --ledger-dir` writes one place and
    `verdict` reads another, the chain breaks silently — the verdict raises 'no delegation with
    task_id' against a ledger that plainly has it."""
    minted = mint(_need(id="ledger-dir-archon"), tmp_path)
    state_dir = tmp_path / "runtime-state"
    _fake_delegation(minted.archon_dir, "task-1", ledger_dir=state_dir)

    # Reading the default location must NOT see it...
    with pytest.raises(ValueError, match="no delegation with task_id"):
        record_verdict(minted.archon_dir, "task-1", "success")

    # ...and reading through the override must.
    entry = record_verdict(minted.archon_dir, "task-1", "success", ledger_dir=state_dir)
    assert entry["outcome"] == "success"
    assert not (minted.archon_dir / LEDGER_FILENAME).exists()  # stable stays clean

    report = tenure_review(minted.archon_dir, ledger_dir=state_dir)
    assert report.archon_id == "ledger-dir-archon"   # identity still comes from archon_dir
    assert report.delegations == 1
    assert report.failures == 0


def test_distill_follows_the_ledger_dir(tmp_path):
    minted = mint(_need(id="distill-dir-archon"), tmp_path)
    state_dir = tmp_path / "runtime-state"
    _fake_delegation(minted.archon_dir, "task-2", state="TASK_STATE_FAILED", ledger_dir=state_dir)
    case = distill_failure(minted.archon_dir, "task-2", "broke", ledger_dir=state_dir)
    assert case.id
