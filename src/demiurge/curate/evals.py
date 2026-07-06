"""The eval suite and the admission gate.

Judging is pluggable. The v1 ``BaselineJudge`` is deliberately deterministic:
a case passes when the delegated task completed, produced non-error text, and
contains every ``expect_contains`` substring. A case's natural-language
``expect`` is *advisory* under the baseline judge (recorded, not enforced) —
an LLM judge that enforces it is a strict upgrade, not a redesign.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field

from demiurge.curate.record import set_status
from demiurge.delegate.client import DelegationResult, delegate

EVALS_FILENAME = "evals.yaml"
EVAL_REPORT_FILENAME = "eval-report.json"

RUNTIME_ERROR_MARKER = "Archon runtime error:"


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    origin: str = "mint"  # "mint" | "field-failure"
    description: str = ""
    input: dict[str, Any]
    expect: str | None = None
    expect_contains: list[str] = Field(default_factory=list)

    def query_text(self) -> str:
        query = self.input.get("query")
        return query if isinstance(query, str) else json.dumps(self.input, ensure_ascii=False)


class EvalSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    archon: str
    suite_schema: str = Field(default="demiurge-evals/v1", alias="schema")
    cases: list[EvalCase] = Field(default_factory=list)


def load_evals(archon_dir: Path | str) -> EvalSuite:
    evals_path = Path(archon_dir) / EVALS_FILENAME
    if not evals_path.is_file():
        raise FileNotFoundError(f"no {EVALS_FILENAME} in {archon_dir} — mint the Archon first")
    return EvalSuite.model_validate(yaml.safe_load(evals_path.read_text(encoding="utf-8")))


def save_evals(archon_dir: Path | str, suite: EvalSuite) -> None:
    evals_path = Path(archon_dir) / EVALS_FILENAME
    document = suite.model_dump(by_alias=True, exclude_none=True)
    evals_path.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    origin: str
    passed: bool
    checks: list[str]
    response_text: str
    state: str
    judged_by: str


@dataclass(frozen=True)
class EvalReport:
    archon: str
    endpoint: str
    ran_at: str
    results: list[CaseResult]

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(result.passed for result in self.results)

    def to_document(self) -> dict[str, Any]:
        return {
            "archon": self.archon,
            "endpoint": self.endpoint,
            "ran_at": self.ran_at,
            "passed": self.passed,
            "results": [
                {
                    "case_id": result.case_id,
                    "origin": result.origin,
                    "passed": result.passed,
                    "checks": result.checks,
                    "state": result.state,
                    "judged_by": result.judged_by,
                    "response_text": result.response_text,
                }
                for result in self.results
            ],
        }


class Judge(Protocol):
    """Turns a case + delegation result into a verdict."""

    name: str

    def judge(self, case: EvalCase, result: DelegationResult) -> tuple[bool, list[str]]:
        """Return (passed, human-readable check messages)."""
        ...


class BaselineJudge:
    """Deterministic v1 judge: transport state + error marker + expect_contains."""

    name = "baseline"

    def judge(self, case: EvalCase, result: DelegationResult) -> tuple[bool, list[str]]:
        checks: list[str] = []
        passed = True
        if not result.completed:
            checks.append(f"FAIL task state is {result.state}, not TASK_STATE_COMPLETED")
            passed = False
        if not result.text.strip():
            checks.append("FAIL empty response")
            passed = False
        elif result.text.startswith(RUNTIME_ERROR_MARKER):
            checks.append("FAIL archon reported a runtime error")
            passed = False
        for needle in case.expect_contains:
            if needle.lower() in result.text.lower():
                checks.append(f"ok response contains {needle!r}")
            else:
                checks.append(f"FAIL response does not contain {needle!r}")
                passed = False
        if case.expect and not case.expect_contains:
            checks.append("note natural-language criteria not machine-checked by baseline judge")
        if passed:
            checks.insert(0, "ok completed with non-error text")
        return passed, checks


def run_evals(
    archon_dir: Path | str,
    endpoint: str,
    *,
    judge: Judge | None = None,
    timeout: float = 300.0,
) -> EvalReport:
    """Run the Archon's eval suite against a running deployment."""
    judge = judge or BaselineJudge()
    suite = load_evals(archon_dir)
    results: list[CaseResult] = []
    for case in suite.cases:
        result = delegate(endpoint, case.query_text(), timeout=timeout)
        passed, checks = judge.judge(case, result)
        results.append(
            CaseResult(
                case_id=case.id,
                origin=case.origin,
                passed=passed,
                checks=checks,
                response_text=result.text,
                state=result.state,
                judged_by=judge.name,
            )
        )
    report = EvalReport(
        archon=suite.archon,
        endpoint=endpoint,
        ran_at=datetime.now(UTC).isoformat(timespec="seconds"),
        results=results,
    )
    report_path = Path(archon_dir) / EVAL_REPORT_FILENAME
    report_path.write_text(
        json.dumps(report.to_document(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def admit(
    archon_dir: Path | str,
    endpoint: str,
    *,
    judge: Judge | None = None,
    timeout: float = 300.0,
) -> EvalReport:
    """The admission gate: run the suite; only a full pass enters the stable."""
    report = run_evals(archon_dir, endpoint, judge=judge, timeout=timeout)
    passed_count = sum(1 for result in report.results if result.passed)
    summary = f"{passed_count}/{len(report.results)} eval cases passed"
    if report.passed:
        set_status(archon_dir, "admitted", "admission-passed", summary)
    else:
        failed_ids = ", ".join(result.case_id for result in report.results if not result.passed)
        set_status(archon_dir, "specced", "admission-failed", f"{summary} (failed: {failed_ids})")
    return report
