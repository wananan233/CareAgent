"""G2.2 HTTP 聊天 API 的无网络单元测试。"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen

from carehub.g2 import ChatHttpApi, ChatService, InMemoryRateLimiter, StaticTokenAuthenticator, build_context_snapshot, serve_local
from carehub.core.service import CareCore
from carehub.simulators.devices import DeviceSimulator


def _snapshot(subject_id: str) -> dict:
    return build_context_snapshot(
        subject_id=subject_id,
        source_event_ids=["evt-api-test"],
        consent_scopes=["chat"],
        consent_expires_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        facts=[{"text": "模拟服药任务处于 DUE 状态。", "source_refs": ["evt-api-test"]}],
    )


def _api() -> ChatHttpApi:
    return ChatHttpApi(
        chat_service=ChatService(),
        authenticator=StaticTokenAuthenticator({"token-for-user": "user:synthetic-01"}),
        context_provider=_snapshot,
    )


def test_chat_api_returns_agent_response_for_authorized_subject() -> None:
    response = _api().handle(
        method="POST",
        path="/v1/users/synthetic-01/chat",
        headers={"Authorization": "Bearer token-for-user"},
        body=json.dumps({"message": "有什么提醒？"}).encode(),
    )

    assert response.status == 200
    assert response.body["schema_version"] == "AgentResponseV1"
    assert response.body["channel"] == "TERMINAL"


def test_chat_api_rejects_missing_token_and_subject_mismatch() -> None:
    missing_token = _api().handle(
        method="POST", path="/v1/users/synthetic-01/chat", headers={}, body=json.dumps({"message": "你好"}).encode()
    )
    mismatch = _api().handle(
        method="POST",
        path="/v1/users/another-user/chat",
        headers={"Authorization": "Bearer token-for-user"},
        body=json.dumps({"message": "你好"}).encode(),
    )

    assert (missing_token.status, missing_token.body["code"]) == (401, "UNAUTHORIZED")
    assert (mismatch.status, mismatch.body["code"]) == (403, "SUBJECT_MISMATCH")


def test_chat_api_rejects_invalid_json_and_extra_fields() -> None:
    invalid_json = _api().handle(
        method="POST",
        path="/v1/users/synthetic-01/chat",
        headers={"Authorization": "Bearer token-for-user"},
        body=b"not-json",
    )
    extra_field = _api().handle(
        method="POST",
        path="/v1/users/synthetic-01/chat",
        headers={"Authorization": "Bearer token-for-user"},
        body=json.dumps({"message": "你好", "unknown": []}).encode(),
    )

    assert (invalid_json.status, invalid_json.body["code"]) == (400, "INVALID_JSON")
    assert (extra_field.status, extra_field.body["code"]) == (400, "INVALID_REQUEST")


def test_chat_api_accepts_bounded_client_side_history() -> None:
    response = _api().handle(
        method="POST",
        path="/v1/users/synthetic-01/chat",
        headers={"Authorization": "Bearer token-for-user"},
        body=json.dumps({"message": "请继续", "history": [{"role": "user", "content": "第一句"}]}).encode(),
    )

    assert response.status == 200


def test_chat_api_rate_limits_each_authenticated_subject() -> None:
    api = ChatHttpApi(
        chat_service=ChatService(),
        authenticator=StaticTokenAuthenticator({"token-for-user": "user:synthetic-01"}),
        context_provider=_snapshot,
        rate_limiter=InMemoryRateLimiter(max_requests=2, window_seconds=60),
    )
    request = dict(
        method="POST",
        path="/v1/users/synthetic-01/chat",
        headers={"Authorization": "Bearer token-for-user"},
        body=json.dumps({"message": "你好"}).encode(),
    )

    assert api.handle(**request).status == 200
    assert api.handle(**request).status == 200
    limited = api.handle(**request)
    assert (limited.status, limited.body["code"], limited.body["retryable"]) == (429, "RATE_LIMITED", True)


def test_local_http_server_serves_authorized_chat_without_external_model() -> None:
    server = serve_local(_api(), port=0)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    port = server.server_address[1]
    request = Request(
        f"http://127.0.0.1:{port}/v1/users/synthetic-01/chat",
        data=json.dumps({"message": "有什么提醒？"}).encode(),
        headers={"Authorization": "Bearer token-for-user", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode())
    finally:
        thread.join(timeout=2)
        server.server_close()

    assert payload["schema_version"] == "AgentResponseV1"


def test_local_http_server_serves_web_page() -> None:
    server = serve_local(_api(), port=0)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_address[1]}/", timeout=2) as response:
            page = response.read().decode()
            csp = response.headers["Content-Security-Policy"]
    finally:
        thread.join(timeout=2)
        server.server_close()

    assert "CareHub G2.3" in page
    assert "default-src 'self'" in csp


def test_local_http_server_reads_g1_projection_from_request_thread(tmp_path) -> None:
    core = CareCore(tmp_path / "threaded-g1.db")
    core.ingest(DeviceSimulator().medication_due("morning", 1))
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    api = ChatHttpApi(
        chat_service=ChatService(),
        authenticator=StaticTokenAuthenticator({"token-for-user": "user:synthetic-01"}),
        context_provider=lambda subject_id: core.build_chat_context(
            subject_id=subject_id, consent_expires_at=expires_at
        ),
    )
    server = serve_local(api, port=0)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    port = server.server_address[1]
    request = Request(
        f"http://127.0.0.1:{port}/v1/users/synthetic-01/chat",
        data=json.dumps({"message": "有什么提醒？"}).encode(),
        headers={"Authorization": "Bearer token-for-user", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode())
    finally:
        thread.join(timeout=2)
        server.server_close()
        core.close()

    assert payload["schema_version"] == "AgentResponseV1"
