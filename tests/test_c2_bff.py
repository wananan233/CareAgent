from carehub.bff import CareBff
from carehub.core.service import CareCore
from carehub.g2 import StaticTokenAuthenticator
from carehub.g3 import ConsentLedger
from carehub.g4 import ModelGateway


def test_bff_me_households_and_authorized_views(tmp_path):
    core = CareCore(tmp_path / "bff.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    core.projections.tasks[("tenant:a", "user:alice", "home:a", "task:one")] = {"task_ref": "task:one", "status": "DUE", "evidence_state": "UNKNOWN", "raw": "hidden"}
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"))
    headers = {"Authorization": "Bearer alice"}
    assert bff.handle(method="GET", path="/v1/me", headers=headers).body["actor_id"] == "user:alice"
    assert bff.handle(method="GET", path="/v1/households", headers=headers).body["items"] == [{"household_id": "home:a", "display_name": "home:a"}]
    view = bff.handle(method="GET", path="/v1/households/home:a/subjects/user:alice/tasks", headers=headers)
    assert view.status == 200 and view.body["items"] == [{"task_ref": "task:one", "status": "DUE", "evidence_state": "UNKNOWN"}]
    assert view.headers["ETag"] and view.body["allowed_actions"]
    assert bff.handle(method="GET", path="/v1/households/home:b/subjects/user:alice/tasks", headers=headers).body["code"] == "POLICY_DENIED"
    bff.publish_view_update(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", view="tasks")
    stream = bff.handle(method="GET", path="/v1/households/home:a/subjects/user:alice/stream", headers=headers)
    assert stream.status == 200 and stream.headers["Content-Type"].startswith("text/event-stream") and "raw" not in stream.body["_sse"]
    core.close()


def test_bff_consent_commands_are_idempotent_and_versioned(tmp_path):
    core = CareCore(tmp_path / "commands.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a")); headers = {"Authorization": "Bearer alice"}
    grant = {"command_id": "cmd-1", "idempotency_key": "key-1", "expected_version": 1, "owner": "user:alice", "grantee": "user:bob", "household_id": "home:a", "scope": "view", "purpose": "view"}
    created = bff.handle(method="POST", path="/v1/consents", headers=headers, body=grant)
    assert created.status == 201 and created.body["consent"]["status"] == "GRANTED"
    assert bff.handle(method="POST", path="/v1/consents", headers=headers, body=grant).body["status"] == "SUCCEEDED"
    consent_id = created.body["consent"]["consent_id"]
    activate = bff.handle(method="POST", path=f"/v1/consents/{consent_id}:activate", headers=headers, body={"command_id": "cmd-2", "idempotency_key": "key-2", "expected_version": 1})
    assert activate.body["consent"]["status"] == "ACTIVE"
    conflict = bff.handle(method="POST", path=f"/v1/consents/{consent_id}:revoke", headers=headers, body={"command_id": "cmd-3", "idempotency_key": "key-3", "expected_version": 1})
    assert conflict.status == 409
    core.close()


def test_bff_report_uses_authorized_minimal_timeline_context(tmp_path):
    core = CareCore(tmp_path / "report.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    core.projections.timeline.append({"event_id": "evt-safe", "event_type": "MEDICATION_DUE", "occurred_at": "2026-08-22T09:00:00+00:00", "tenant_id": "tenant:a", "household_id": "home:a", "subject_id": "user:alice", "raw": "hidden"})
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"))
    response = bff.handle(method="GET", path="/v1/households/home:a/subjects/user:alice/report", headers={"Authorization": "Bearer alice"})
    assert response.status == 200 and response.body["fallback"] == "NONE"
    assert response.body["facts"][0]["source_refs"] == ["evt-safe"] and "raw" not in str(response.body)
    core.close()


def test_family_command_is_scoped_idempotent_and_returns_minimal_receipt(tmp_path):
    core = CareCore(tmp_path / "family-command.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"))
    headers = {"Authorization": "Bearer alice"}
    command = {"command_id": "command-1", "idempotency_key": "family-key-1", "expected_version": 1, "action": "ACKNOWLEDGE_ALERT", "resource_id": "alert:one"}
    path = "/v1/households/home:a/subjects/user:alice/requests"
    first = bff.handle(method="POST", path=path, headers=headers, body=command)
    assert first.status == 200 and first.body["status"] == "RECORDED" and first.body["alert_id"] == "alert:one"
    duplicate = bff.handle(method="POST", path=path, headers=headers, body=command)
    assert duplicate.status == 200 and duplicate.body["status"] == "SUCCEEDED"
    denied = bff.handle(method="POST", path="/v1/households/home:b/subjects/user:alice/requests", headers=headers, body={**command, "command_id": "command-2", "idempotency_key": "family-key-2"})
    assert denied.status == 403 and denied.body["code"] == "POLICY_DENIED"
    core.close()


def test_elder_terminal_commands_and_scope_revoke_use_the_same_bff_boundary(tmp_path):
    core = CareCore(tmp_path / "elder-command.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"))
    headers = {"Authorization": "Bearer alice"}
    receipt = bff.handle(method="POST", path="/v1/households/home:a/subjects/user:alice/requests", headers=headers, body={"command_id": "elder-ack", "idempotency_key": "elder-ack-key", "expected_version": 1, "action": "ACKNOWLEDGE_TASK", "resource_id": "task:one"})
    assert receipt.status == 200 and receipt.body["status"] == "RECORDED"
    consent = ConsentLedger(core.store).grant(owner="user:alice", grantee="user:alice", household_id="home:a", scope="timeline", purpose="view", tenant_id="tenant:a")
    consent = ConsentLedger(core.store).activate(consent["consent_id"], actor="user:alice", expected_version=1)
    revoked = bff.handle(method="POST", path="/v1/households/home:a/subjects/user:alice/consents/timeline:revoke", headers=headers, body={"command_id": "elder-revoke", "idempotency_key": "elder-revoke-key", "expected_version": consent["version"]})
    assert revoked.status == 200 and revoked.body["consent"]["status"] == "REVOKED"
    core.close()


def test_bff_accepts_an_explicitly_injected_model_gateway(tmp_path):
    class ControlledProvider:
        version = "controlled-provider.v1"

        def generate(self, *, purpose, facts):
            assert purpose == "DAILY_SUMMARY"
            assert facts == [{"text": "MEDICATION_DUE 于 2026-08-22T09:00:00+00:00 记录。", "source_refs": ["evt-safe"]}]
            return '{"message":"仅基于授权记录。","fact_indexes":[0]}'

    core = CareCore(tmp_path / "injected-model.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    core.projections.timeline.append({"event_id": "evt-safe", "event_type": "MEDICATION_DUE", "occurred_at": "2026-08-22T09:00:00+00:00", "tenant_id": "tenant:a", "household_id": "home:a", "subject_id": "user:alice"})
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"), model_gateway=ModelGateway(ControlledProvider()))
    response = bff.handle(method="GET", path="/v1/households/home:a/subjects/user:alice/report", headers={"Authorization": "Bearer alice"})
    assert response.status == 200
    assert response.body["generator_version"] == "controlled-provider.v1"
    assert response.body["message"] == "仅基于授权记录。"
    core.close()
