import json
from threading import Thread
from urllib.parse import quote
from urllib.request import Request, urlopen

from carehub.bff import CareBff, serve_bff_local
from carehub.core.service import CareCore
from carehub.g2 import StaticTokenAuthenticator
from carehub.g3 import ConsentLedger
from carehub.g4 import ModelGateway


def activate_view_consent(core, *, actor="user:alice", household_id="home:a"):
    consent = ConsentLedger(core.store).grant(owner="user:alice", grantee=actor, household_id=household_id, scope="view", purpose="view", tenant_id="tenant:a")
    active = ConsentLedger(core.store).activate(consent["consent_id"], actor="user:alice", expected_version=1)
    for purpose in ("TODAY_STATUS", "DAILY_SUMMARY"):
        agent = ConsentLedger(core.store).grant(owner="user:alice", grantee=actor, household_id=household_id, scope="agent_view", purpose=purpose, tenant_id="tenant:a")
        ConsentLedger(core.store).activate(agent["consent_id"], actor="user:alice", expected_version=1)
    stream = ConsentLedger(core.store).grant(owner="user:alice", grantee=actor, household_id=household_id, scope="view", purpose="stream", channel="SSE", tenant_id="tenant:a")
    ConsentLedger(core.store).activate(stream["consent_id"], actor="user:alice", expected_version=1)
    return active


def test_bff_me_households_and_authorized_views(tmp_path):
    core = CareCore(tmp_path / "bff.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    activate_view_consent(core)
    core.projections.tasks[("tenant:a", "user:alice", "home:a", "task:one")] = {"task_ref": "task:one", "status": "DUE", "evidence_state": "UNKNOWN", "raw": "hidden"}
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"))
    headers = {"Authorization": "Bearer alice"}
    assert bff.handle(method="GET", path="/v1/me", headers=headers).body["actor_id"] == "user:alice"
    assert bff.handle(method="GET", path="/v1/households", headers=headers).body["items"] == [{"household_id": "home:a", "display_name": "home:a"}]
    view = bff.handle(method="GET", path="/v1/households/home:a/subjects/user:alice/tasks", headers=headers)
    assert view.status == 200 and view.body["items"] == [{"task_ref": "task:one", "status": "DUE", "evidence_state": "UNKNOWN"}]
    encoded = bff.handle(method="GET", path=f"/v1/households/{quote('home:a', safe='')}/subjects/{quote('user:alice', safe='')}/tasks", headers=headers)
    assert encoded.status == 200 and encoded.body["items"] == view.body["items"]
    assert view.headers["ETag"] and view.body["allowed_actions"]
    assert bff.handle(method="GET", path=f"/v1/households/{quote('home:b', safe='')}/subjects/{quote('user:alice', safe='')}/tasks", headers=headers).body["code"] == "POLICY_DENIED"
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
    activate_view_consent(core)
    core.projections.timeline.append({"event_id": "evt-safe", "event_type": "MEDICATION_DUE", "occurred_at": "2026-08-22T09:00:00+00:00", "tenant_id": "tenant:a", "household_id": "home:a", "subject_id": "user:alice", "raw": "hidden"})
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"))
    response = bff.handle(method="GET", path="/v1/households/home:a/subjects/user:alice/report", headers={"Authorization": "Bearer alice"})
    assert response.status == 200 and response.body["fallback"] == "NONE"
    assert response.body["facts"][0]["source_refs"] == ["evt-safe"] and "raw" not in str(response.body)
    core.close()


def test_bff_today_status_and_report_use_separate_purpose_consents_and_agent_runs(tmp_path):
    class OfflineProvider:
        version = "offline-test.v1"
        def __init__(self): self.purposes = []
        def generate(self, *, purpose, facts):
            self.purposes.append(purpose)
            assert facts == [{"text": "MEDICATION_DUE 于 2026-08-22T09:00:00+00:00 记录。", "source_refs": ["evt-safe"]}]
            return '{"message":"仅基于授权记录。","fact_indexes":[0]}'

    core = CareCore(tmp_path / "today-status.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    activate_view_consent(core)
    core.projections.timeline.append({"event_id": "evt-safe", "event_type": "MEDICATION_DUE", "occurred_at": "2026-08-22T09:00:00+00:00", "tenant_id": "tenant:a", "household_id": "home:a", "subject_id": "user:alice", "raw": "hidden"})
    provider = OfflineProvider()
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"), model_gateway=ModelGateway(provider))
    headers = {"Authorization": "Bearer alice"}; root = "/v1/households/home:a/subjects/user:alice"
    today = bff.handle(method="GET", path=f"{root}/today-status", headers=headers)
    report = bff.handle(method="GET", path=f"{root}/report", headers=headers)
    assert [today.status, report.status] == [200, 200]
    assert provider.purposes == ["TODAY_STATUS", "DAILY_SUMMARY"]
    for response in (today, report):
        assert response.body["schema_version"] == "AgentResponseV1"
        assert response.body["channel"] == "TERMINAL"
        assert response.body["facts"] == [{"text": "MEDICATION_DUE 于 2026-08-22T09:00:00+00:00 记录。", "source_refs": ["evt-safe"]}]
        run = core.store.agent_run(response.body["agent_run_id"])
        assert run and run["status"] == "COMPLETED" and run["source_refs"] == ["evt-safe"]
        assert "raw" not in str(response.body) and "raw" not in str(run)
    core.close()


def test_bff_today_status_returns_controlled_fallback_and_agent_run_without_network(tmp_path):
    core = CareCore(tmp_path / "today-status-fallback.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    activate_view_consent(core)
    core.projections.timeline.append({"event_id": "evt-safe", "event_type": "MEDICATION_DUE", "occurred_at": "2026-08-22T09:00:00+00:00", "tenant_id": "tenant:a", "household_id": "home:a", "subject_id": "user:alice"})
    class OfflineFailure:
        version = "offline-failure.v1"
        def generate(self, **kwargs): raise OSError("network disabled")
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"), model_gateway=ModelGateway(OfflineFailure()))
    response = bff.handle(method="GET", path="/v1/households/home:a/subjects/user:alice/today-status", headers={"Authorization": "Bearer alice"})
    run = core.store.agent_run(response.body["agent_run_id"])
    assert response.status == 200
    assert response.body["fallback"] == "TEMPLATE_FALLBACK"
    assert response.body["facts"] == []
    assert run and run["status"] == "COMPLETED" and run["reason_code"] == "MODEL_UNAVAILABLE" and run["source_refs"] == ["evt-safe"]
    core.close()


def test_family_command_is_scoped_idempotent_and_returns_minimal_receipt(tmp_path):
    core = CareCore(tmp_path / "family-command.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    activate_view_consent(core)
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
    activate_view_consent(core)
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"))
    headers = {"Authorization": "Bearer alice"}
    receipt = bff.handle(method="POST", path="/v1/households/home:a/subjects/user:alice/requests", headers=headers, body={"command_id": "elder-ack", "idempotency_key": "elder-ack-key", "expected_version": 1, "action": "ACKNOWLEDGE_TASK", "resource_id": "task:one"})
    assert receipt.status == 200 and receipt.body["status"] == "RECORDED"
    consent = ConsentLedger(core.store).grant(owner="user:alice", grantee="user:alice", household_id="home:a", scope="timeline", purpose="view", tenant_id="tenant:a")
    consent = ConsentLedger(core.store).activate(consent["consent_id"], actor="user:alice", expected_version=1)
    revoked = bff.handle(method="POST", path="/v1/households/home:a/subjects/user:alice/consents/timeline:revoke", headers=headers, body={"command_id": "elder-revoke", "idempotency_key": "elder-revoke-key", "expected_version": consent["version"]})
    assert revoked.status == 200 and revoked.body["consent"]["status"] == "REVOKED"
    core.close()


def test_local_http_bff_forwards_json_post_commands(tmp_path):
    core = CareCore(tmp_path / "http-post.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    activate_view_consent(core)
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"))
    server = serve_bff_local(bff, port=0)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        payload = json.dumps({"command_id": "http-ack", "idempotency_key": "http-ack-key", "expected_version": 1, "action": "ACKNOWLEDGE_TASK", "resource_id": "task:one"}).encode()
        request = Request(f"http://127.0.0.1:{server.server_address[1]}/v1/households/home:a/subjects/user:alice/requests", data=payload, method="POST", headers={"Authorization": "Bearer alice", "Content-Type": "application/json"})
        with urlopen(request, timeout=3) as response:
            body = json.loads(response.read().decode())
        assert body["status"] == "RECORDED"
    finally:
        server.shutdown(); thread.join(timeout=3); server.server_close(); core.close()


def test_bff_accepts_an_explicitly_injected_model_gateway(tmp_path):
    class ControlledProvider:
        version = "controlled-provider.v1"

        def generate(self, *, purpose, facts):
            assert purpose == "DAILY_SUMMARY"
            assert facts == [{"text": "MEDICATION_DUE 于 2026-08-22T09:00:00+00:00 记录。", "source_refs": ["evt-safe"]}]
            return '{"message":"仅基于授权记录。","fact_indexes":[0]}'

    core = CareCore(tmp_path / "injected-model.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    activate_view_consent(core)
    core.projections.timeline.append({"event_id": "evt-safe", "event_type": "MEDICATION_DUE", "occurred_at": "2026-08-22T09:00:00+00:00", "tenant_id": "tenant:a", "household_id": "home:a", "subject_id": "user:alice"})
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a"), model_gateway=ModelGateway(ControlledProvider()))
    response = bff.handle(method="GET", path="/v1/households/home:a/subjects/user:alice/report", headers={"Authorization": "Bearer alice"})
    assert response.status == 200
    assert response.body["generator_version"] == "controlled-provider.v1"
    assert response.body["message"] == "仅基于授权记录。"
    core.close()


def test_self_revoke_immediately_denies_views_agent_and_stream(tmp_path):
    core = CareCore(tmp_path / "self-revoke.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    consent = activate_view_consent(core)
    core.projections.timeline.append({"event_id": "evt-safe", "event_type": "MEDICATION_DUE", "occurred_at": "2026-08-22T09:00:00+00:00", "tenant_id": "tenant:a", "household_id": "home:a", "subject_id": "user:alice"})
    bff = CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a")); headers = {"Authorization": "Bearer alice"}; root = "/v1/households/home:a/subjects/user:alice"
    assert bff.handle(method="GET", path=f"{root}/tasks", headers=headers).status == 200
    assert bff.handle(method="GET", path=f"{root}/report", headers=headers).status == 200
    revoked = bff.handle(method="POST", path=f"{root}/consents/view:revoke", headers=headers, body={"command_id": "revoke", "idempotency_key": "revoke-key", "expected_version": consent["version"]})
    assert revoked.status == 200 and revoked.body["consent"]["status"] == "REVOKED"
    assert [bff.handle(method="GET", path=f"{root}/{kind}", headers=headers).status for kind in ("dashboard", "tasks", "alerts", "timeline", "report", "stream")] == [403] * 6
    core.close()


def test_local_http_bff_cors_preflight_is_origin_restricted(tmp_path):
    core = CareCore(tmp_path / "cors.db")
    core.store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    server = serve_bff_local(CareBff(core=core, authenticator=StaticTokenAuthenticator({"alice": "user:alice"}, tenant_id="tenant:a")), port=0, allowed_origins=("http://127.0.0.1:5173",))
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        request = Request(f"http://127.0.0.1:{server.server_address[1]}/v1/households", method="OPTIONS", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Authorization, Content-Type"})
        with urlopen(request, timeout=3) as response:
            assert response.status == 204 and response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173" and "Authorization" in response.headers["Access-Control-Allow-Headers"]
    finally:
        server.shutdown(); thread.join(timeout=3); server.server_close(); core.close()
