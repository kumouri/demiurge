"""Validate documents against the vendored Agent Format JSON Schema.

The schema at ``schemas/agentformat-1.0.json`` is vendored verbatim from
https://agentformat.org/schema/1.0/agentformat-schema.json (fetched 2026-07-06)
so validation needs no network access. Re-vendor deliberately; never edit it.
"""

import json
from functools import cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator


class SpecValidationError(ValueError):
    """A document failed Agent Format schema validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("document violates the Agent Format schema:\n" + "\n".join(errors))


@cache
def _validator() -> Draft202012Validator:
    schema_text = (
        files("demiurge.spec").joinpath("schemas/agentformat-1.0.json").read_text(encoding="utf-8")
    )
    return Draft202012Validator(json.loads(schema_text))


def validate_document(doc: dict[str, Any]) -> list[str]:
    """Return schema-violation messages for ``doc`` (empty list = valid)."""
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(_validator().iter_errors(doc), key=lambda e: list(map(str, e.path)))
    ]


def assert_valid(doc: dict[str, Any]) -> None:
    """Raise :class:`SpecValidationError` if ``doc`` violates the schema."""
    errors = validate_document(doc)
    if errors:
        raise SpecValidationError(errors)
