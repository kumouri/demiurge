"""Curation: the fused loop — eval-gated admission, outcome-based tenure, failure distillation."""

from demiurge.curate.distill import distill_failure, revise
from demiurge.curate.evals import (
    BaselineJudge,
    CaseResult,
    EvalCase,
    EvalReport,
    EvalSuite,
    admit,
    load_evals,
    run_evals,
    save_evals,
)
from demiurge.curate.outcomes import TenureReport, record_verdict, retire, tenure_review
from demiurge.curate.record import load_record, set_status

__all__ = [
    "BaselineJudge",
    "CaseResult",
    "EvalCase",
    "EvalReport",
    "EvalSuite",
    "TenureReport",
    "admit",
    "distill_failure",
    "load_evals",
    "load_record",
    "record_verdict",
    "retire",
    "revise",
    "run_evals",
    "save_evals",
    "set_status",
    "tenure_review",
]
