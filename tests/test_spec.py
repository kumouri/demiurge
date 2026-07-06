import yaml

from demiurge.spec import (
    ArchonSpec,
    Interface,
    Metadata,
    react_policy,
    to_yaml,
    validate_document,
)


def _minimal_spec() -> ArchonSpec:
    return ArchonSpec(
        metadata=Metadata(
            id="test-archon",
            name="Test Archon",
            version="0.1.0",
            description="A test agent.",
        ),
        interface=Interface(
            input={"type": "object", "properties": {"query": {"type": "string"}}},
            output={"type": "object", "properties": {"response": {"type": "string"}}},
        ),
        execution_policy=react_policy("You are a test agent.", "claude-sonnet-5"),
    )


def test_minimal_spec_is_schema_valid():
    assert validate_document(_minimal_spec().to_document()) == []


def test_yaml_round_trip_preserves_document():
    spec = _minimal_spec()
    assert yaml.safe_load(to_yaml(spec)) == spec.to_document()


def test_unset_optional_sections_are_omitted():
    document = _minimal_spec().to_document()
    assert "constraints" not in document
    assert "action_space" not in document


def test_validation_reports_missing_required_sections():
    document = _minimal_spec().to_document()
    del document["metadata"]["id"]
    del document["execution_policy"]
    errors = validate_document(document)
    assert any("'id' is a required property" in error for error in errors)
    assert any("'execution_policy' is a required property" in error for error in errors)


def test_upstream_getting_started_example_is_valid():
    """The example from agentformat.org's getting-started docs must validate."""
    example = yaml.safe_load(UPSTREAM_EXAMPLE)
    assert validate_document(example) == []


UPSTREAM_EXAMPLE = """
schema_version: "1.0.0"
metadata:
  id: my-agent
  name: My Agent
  version: "1.0.0"
  description: "TODO: describe your agent"
  labels:
    team: "TODO"
    environment: "development"
interface:
  input:
    type: object
    properties:
      query:
        type: string
        description: "The user's input"
    required: [query]
  output:
    type: object
    properties:
      response:
        type: string
        description: "The agent's response"
    required: [response]
execution_policy:
  id: agf.react
  config:
    instructions: |
      TODO: write your agent's instructions.
    model: "gemini-2.0-flash"
    provider: "google"
    max_steps: 10
    tool_choice: auto
action_space:
  local_tools:
    - alias: example_tool
      description: "TODO: describe what this tool does"
constraints:
  budget:
    max_token_usage: 100000
    max_duration_seconds: 300
"""
