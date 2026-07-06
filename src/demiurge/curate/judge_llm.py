"""The Claude judge: enforces natural-language ``expect`` criteria via the Claude API.

A strict upgrade over :class:`~demiurge.curate.evals.BaselineJudge`: baseline
checks (transport state, error marker, ``expect_contains``) still run first and
fail fast for free; only cases that pass them and carry an ``expect`` criterion
spend an API call. The verdict is a structured output — no response parsing.

Requires the optional ``anthropic`` dependency (``demiurge[judge]``) and
Anthropic auth: ``ANTHROPIC_API_KEY_DEMIURGE`` is preferred so Demiurge's
spend is separable; the SDK's normal resolution (``ANTHROPIC_API_KEY``, an
``ant auth login`` profile) is the fallback.
"""

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from demiurge.curate.evals import BaselineJudge, EvalCase
from demiurge.delegate.client import DelegationResult

DEFAULT_JUDGE_MODEL = "claude-opus-4-8"
API_KEY_ENV = "ANTHROPIC_API_KEY_DEMIURGE"

_SYSTEM_PROMPT = """You are the eval judge for Demiurge, a system that curates AI agents.

You are given an eval case's expectation, the request that was sent to an agent
(an "Archon"), and the agent's response. Decide whether the response satisfies
the expectation.

Rules:
- Judge only against the stated expectation. Do not invent additional requirements.
- Judge substance over style: a response that satisfies the expectation in
  different words still passes.
- An evasive, empty, or off-task response fails.
- Be strict but fair; when the response genuinely satisfies the expectation, pass it.
"""


class JudgeVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool = Field(description="Whether the response satisfies the expectation.")
    reason: str = Field(description="One or two sentences explaining the verdict.")


class ClaudeJudge:
    """Judges eval cases with baseline checks plus a Claude verdict on ``expect``."""

    name = "claude"

    def __init__(
        self,
        *,
        model: str = DEFAULT_JUDGE_MODEL,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._client = client if client is not None else _build_client(api_key)
        self._baseline = BaselineJudge()

    def judge(self, case: EvalCase, result: DelegationResult) -> tuple[bool, list[str]]:
        passed, checks = self._baseline.judge(case, result)
        # Baseline's advisory note doesn't apply here — the criteria ARE checked.
        checks = [c for c in checks if "not machine-checked" not in c]
        if not passed:
            checks.append("skip claude judgment — baseline checks already failed")
            return False, checks
        if not case.expect:
            return passed, checks
        try:
            verdict = self._ask(case, result)
        except Exception as error:  # fail closed: an unjudged case cannot admit an Archon
            checks.append(f"FAIL claude judge error ({type(error).__name__}): {error}")
            return False, checks
        marker = "ok" if verdict.passed else "FAIL"
        checks.append(f"{marker} claude judge ({self._model}): {verdict.reason}")
        return verdict.passed, checks

    def _ask(self, case: EvalCase, result: DelegationResult) -> JudgeVerdict:
        prompt = (
            f"<expectation>\n{case.expect}\n</expectation>\n\n"
            f"<request>\n{case.query_text()}\n</request>\n\n"
            f"<response>\n{result.text}\n</response>"
        )
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=JudgeVerdict,
        )
        verdict = response.parsed_output
        if verdict is None:
            raise ValueError("judge returned no parsable verdict")
        return verdict


def _build_client(api_key: str | None) -> Any:
    try:
        import anthropic
    except ImportError as error:
        raise ImportError(
            "the claude judge needs the 'anthropic' package — install demiurge[judge]"
        ) from error
    api_key = api_key or os.environ.get(API_KEY_ENV)
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    return anthropic.Anthropic()  # SDK default resolution (ANTHROPIC_API_KEY, profile)
