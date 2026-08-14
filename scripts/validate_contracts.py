"""G0 契约校验：验证 Golden fixture、OpenAPI 边界和安全策略。"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "contracts" / "schemas"
FIXTURES = ROOT / "fixtures" / "golden"

FIXTURE_SCHEMAS = {
    "medication-due-event.json": "care-event.v1.json",
    "medication-context.json": "context-snapshot.v1.json",
    "reminder-intent.json": "action-intent.v1.json",
}
FORBIDDEN = {
    "database_write",
    "mqtt_publish",
    "ble_control",
    "gpio_control",
    "shell",
    "arbitrary_http",
    "mark_medication_taken",
    "change_dose",
    "trigger_sos",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def validate_fixtures() -> None:
    for fixture_name, schema_name in FIXTURE_SCHEMAS.items():
        fixture = load_json(FIXTURES / fixture_name)
        schema = load_json(SCHEMAS / schema_name)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(fixture), key=lambda item: list(item.path))
        assert not errors, f"{fixture_name} 不符合 {schema_name}: {errors}"


def validate_policy_and_skills() -> None:
    policy = load_json(ROOT / "policies" / "capability-matrix.yaml")
    assert policy["default_effect"] == "DENY"
    assert FORBIDDEN.issubset(set(policy["denied_capabilities"]))
    assert policy["subjects"]["MODEL_GATEWAY"] == ["generate_schema_response"]

    for manifest_path in (ROOT / "skills").glob("*.yaml"):
        manifest = load_json(manifest_path)
        required = {
            "skill_id", "version", "required_capability", "safety_level", "side_effects",
            "preconditions", "idempotency_strategy", "timeout_ms", "retry_policy",
            "compensation", "offline_supported", "allowed_callers", "audit_fields",
        }
        assert required.issubset(manifest), f"{manifest_path.name} 缺少 Skill Manifest 字段"
        assert manifest["required_capability"] not in FORBIDDEN
        assert "MODEL_GATEWAY" not in manifest["allowed_callers"]


def validate_openapi() -> None:
    spec = load_json(ROOT / "openapi" / "openapi.v1.json")
    assert spec["openapi"].startswith("3.1")
    paths = spec["paths"]
    assert "/internal/v1/events:batch" in paths
    assert "/internal/v1/model:generate" in paths
    assert "/v1/users/{id}/chat" in paths
    assert "/internal/v1/skills/{skill}:invoke" not in paths


if __name__ == "__main__":
    validate_fixtures()
    validate_policy_and_skills()
    validate_openapi()
    print("G0 契约校验通过：fixture、策略、Skill Manifest 与 OpenAPI 均符合基线。")
