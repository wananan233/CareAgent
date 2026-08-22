from scripts.validate_contracts import (
    validate_fixtures,
    validate_openapi,
    validate_policy_and_skills,
)
from pathlib import Path
import json
from jsonschema import Draft202012Validator


def test_golden_fixtures_match_contracts() -> None:
    validate_fixtures()


def test_policy_and_skill_boundaries() -> None:
    validate_policy_and_skills()


def test_openapi_does_not_expose_skill_execution() -> None:
    validate_openapi()


def test_g2_agent_and_task_contracts_are_valid_json_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("agent-run.v1.json", "care-task.v1.json"):
        with (root / "contracts" / "schemas" / name).open(encoding="utf-8") as source:
            Draft202012Validator.check_schema(json.load(source))
