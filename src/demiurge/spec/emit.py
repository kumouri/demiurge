"""Emit ArchonSpec models as .agf.yaml text."""

import yaml

from demiurge.spec.model import ArchonSpec


def to_yaml(spec: ArchonSpec) -> str:
    """Render the spec as YAML, preserving the document's field order."""
    return yaml.safe_dump(
        spec.to_document(),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )
