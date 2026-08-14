from scripts.validate_contracts import (
    validate_fixtures,
    validate_openapi,
    validate_policy_and_skills,
)


def test_golden_fixtures_match_contracts() -> None:
    validate_fixtures()


def test_policy_and_skill_boundaries() -> None:
    validate_policy_and_skills()


def test_openapi_does_not_expose_skill_execution() -> None:
    validate_openapi()
