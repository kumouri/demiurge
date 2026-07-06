from types import SimpleNamespace

from demiurge.curate import ClaudeJudge, EvalCase, JudgeVerdict
from demiurge.delegate.client import DelegationResult


class StubClient:
    """Stands in for anthropic.Anthropic; returns a scripted verdict."""

    def __init__(self, verdict: JudgeVerdict | None = None, error: Exception | None = None):
        self.calls: list[dict] = []
        self._verdict = verdict
        self._error = error
        self.messages = SimpleNamespace(parse=self._parse)

    def _parse(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(parsed_output=self._verdict)


def _case(**overrides) -> EvalCase:
    fields = {
        "id": "c1",
        "input": {"query": "Summarize the release notes."},
        "expect": "A summary of the release notes, not an echo of the request.",
    }
    fields.update(overrides)
    return EvalCase.model_validate(fields)


def _result(text="Here is a summary: three bug fixes and one new feature.") -> DelegationResult:
    return DelegationResult(
        text=text, state="TASK_STATE_COMPLETED", task_id="t1", duration_seconds=1.0
    )


def test_passing_verdict_passes_the_case():
    stub = StubClient(verdict=JudgeVerdict(passed=True, reason="Genuinely summarizes."))
    passed, checks = ClaudeJudge(client=stub).judge(_case(), _result())
    assert passed
    assert any("ok claude judge" in check for check in checks)
    prompt = stub.calls[0]["messages"][0]["content"]
    assert "<expectation>" in prompt and "<response>" in prompt


def test_failing_verdict_fails_the_case():
    stub = StubClient(verdict=JudgeVerdict(passed=False, reason="It just echoed the request."))
    passed, checks = ClaudeJudge(client=stub).judge(
        _case(), _result("Summarize the release notes.")
    )
    assert not passed
    assert any("FAIL claude judge" in check for check in checks)


def test_baseline_failure_short_circuits_without_an_api_call():
    stub = StubClient(verdict=JudgeVerdict(passed=True, reason="unused"))
    result = DelegationResult(
        text="", state="TASK_STATE_FAILED", task_id="t1", duration_seconds=1.0
    )
    passed, checks = ClaudeJudge(client=stub).judge(_case(), result)
    assert not passed
    assert stub.calls == []  # no tokens spent on a case baseline already failed
    assert any("skip claude judgment" in check for check in checks)


def test_case_without_expect_needs_no_api_call():
    stub = StubClient(verdict=JudgeVerdict(passed=True, reason="unused"))
    passed, _ = ClaudeJudge(client=stub).judge(_case(expect=None), _result())
    assert passed
    assert stub.calls == []


def test_judge_errors_fail_closed():
    stub = StubClient(error=RuntimeError("api unreachable"))
    passed, checks = ClaudeJudge(client=stub).judge(_case(), _result())
    assert not passed
    assert any("FAIL claude judge error" in check for check in checks)
