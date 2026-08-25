"""C2 最小 BFF：双端通过同一受保护 REST 契约读取视图。"""
from __future__ import annotations

import uuid
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from carehub.core.service import CareCore
from carehub.g3 import AuthContext, AuthorizedProjectionReader, ConsentLedger, ServerSidePDP
from carehub.sse import AuthorizedStateStream
from carehub.g4 import AgentOrchestrator, ModelGateway


@dataclass(frozen=True)
class BffResponse:
    status: int
    body: dict[str, Any]
    headers: dict[str, str]


class CareBff:
    """不向客户端暴露 EventStore、投影键或原始事件 payload。"""
    def __init__(self, *, core: CareCore, authenticator: Any, model_gateway: ModelGateway | None = None) -> None:
        self.core, self.authenticator = core, authenticator
        self.ledger = ConsentLedger(core.store)
        self.pdp = ServerSidePDP(core.store, self.ledger)
        self.views = AuthorizedProjectionReader(self.pdp, core.projections)
        self.stream = AuthorizedStateStream(self.pdp)
        # 默认网关仍是离线 FakeProvider；生产部署必须显式注入由 Linux
        # 进程环境构造的受控网关，BFF 从不读取或保存模型密钥。
        self.agent = AgentOrchestrator(core.store, self.pdp, gateway=model_gateway)

    def handle(self, *, method: str, path: str, headers: Mapping[str, str], body: Mapping[str, Any] | None = None) -> BffResponse:
        correlation_id = f"bff-{uuid.uuid4()}"
        context = self.authenticator.authenticate_context(headers.get("Authorization"))
        if not context:
            return self._error(401, "UNAUTHORIZED", "请先完成身份验证", correlation_id)
        if method == "GET" and path == "/v1/me":
            rows = self.core.store.connection.execute("SELECT household_id, role FROM membership WHERE tenant_id=? AND principal_id=? ORDER BY household_id", (context.tenant_id, context.actor_id)).fetchall()
            return self._ok({"actor_id": context.actor_id, "households": [dict(row) for row in rows]}, correlation_id)
        if method == "GET" and path == "/v1/households":
            rows = self.core.store.connection.execute("SELECT h.household_id, h.display_name FROM household h JOIN membership m ON m.tenant_id=h.tenant_id AND m.household_id=h.household_id WHERE m.tenant_id=? AND m.principal_id=? ORDER BY h.household_id", (context.tenant_id, context.actor_id)).fetchall()
            return self._ok({"items": [dict(row) for row in rows]}, correlation_id)
        parts = path.strip("/").split("/")
        if method == "GET" and len(parts) == 6 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] == "dashboard":
            household_id, subject_id = parts[2], parts[4]
            tasks = self.views.read(context=context, household_id=household_id, subject_id=subject_id, kind="tasks", purpose="view")
            alerts = self.views.read(context=context, household_id=household_id, subject_id=subject_id, kind="alerts", purpose="view")
            if tasks["reason_code"] != "ALLOW" or alerts["reason_code"] != "ALLOW": return self._error(403, "POLICY_DENIED", "当前身份无权访问该视图", correlation_id)
            return self._ok({"snapshot_id": self.core.projections.digest(), "server_time": datetime.now(timezone.utc).isoformat(), "last_updated_at": datetime.now(timezone.utc).isoformat(), "quality": "VALID", "source_refs": [{"type":"SIMULATOR","label":"CareHub 合成模拟器"}], "family_member": {"subject_id":subject_id,"household_id":household_id,"display_name":"已授权家庭成员","relationship":"家人"}, "consent":{"scope":"view","status":"ACTIVE","expires_at":"2099-01-01T00:00:00+00:00","version":0}, "allowed_actions": tasks["allowed_actions"]}, correlation_id)
        if method == "GET" and len(path.strip("/").split("/")) == 6 and path.endswith("/stream"):
            parts = path.strip("/").split("/")
            if parts[:2] == ["v1", "households"] and parts[3] == "subjects":
                return self._stream(context, parts[2], parts[4], headers.get("Last-Event-ID"), correlation_id)
        if method == "POST" and path == "/v1/consents":
            return self._grant_consent(context, body, correlation_id)
        if method == "POST" and path.startswith("/v1/consents/") and path.endswith(":activate"):
            return self._change_consent(context, path.removeprefix("/v1/consents/").removesuffix(":activate"), body, correlation_id, "activate")
        if method == "POST" and path.startswith("/v1/consents/") and path.endswith(":revoke"):
            return self._change_consent(context, path.removeprefix("/v1/consents/").removesuffix(":revoke"), body, correlation_id, "revoke")
        parts = path.strip("/").split("/")
        if method == "POST" and len(parts) == 6 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] == "requests":
            return self._family_command(context, parts[2], parts[4], body, correlation_id)
        if method == "GET" and len(parts) == 6 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] == "report":
            household_id, subject_id = parts[2], parts[4]
            timeline = self.views.read(context=context, household_id=household_id, subject_id=subject_id, kind="timeline", purpose="view")
            if timeline["reason_code"] != "ALLOW": return self._error(403, "POLICY_DENIED", "当前身份无权访问该视图", correlation_id)
            facts = [{"text": f"{item.get('event_type', 'UNKNOWN')} 于 {item.get('occurred_at', 'UNKNOWN')} 记录。", "source_refs": [item["event_id"]]} for item in timeline["items"][:20] if item.get("event_id")]
            result = self.agent.run(context=context, household_id=household_id, subject_id=subject_id, purpose="DAILY_SUMMARY", minimal_context={"facts": facts})
            return self._ok({"schema_version": "AgentResponseV1", "response_id": f"response-{uuid.uuid4()}", "channel": "FAMILY", **result, "correlation_id": correlation_id}, correlation_id)
        if method == "GET" and len(parts) == 6 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] in {"tasks", "alerts", "timeline"}:
            household_id, subject_id, kind = parts[2], parts[4], parts[5]
            body = self.views.read(context=context, household_id=household_id, subject_id=subject_id, kind=kind, purpose="view", resource_version=self.core.projections.digest())
            if body["reason_code"] != "ALLOW":
                return self._error(403, "POLICY_DENIED", "当前身份无权访问该视图", correlation_id)
            body.update({"snapshot_id": self.core.projections.digest(), "server_time": datetime.now(timezone.utc).isoformat(), "freshness": "CURRENT", "correlation_id": correlation_id})
            return self._ok(body, correlation_id, etag=body["snapshot_id"])
        return self._error(404, "NOT_FOUND", "接口不存在", correlation_id)

    def _family_command(self, context: AuthContext, household_id: str, subject_id: str, body: Mapping[str, Any] | None, correlation_id: str) -> BffResponse:
        """家属端写操作唯一入口：先授权、幂等入站、仅返回最小回执。"""
        accepted, error = self._command_meta(body, context, household_id, subject_id)
        if error:
            return error
        assert body is not None
        if not accepted:
            return self._ok({"status": self.core.store.command_status(body["idempotency_key"]) or "DUPLICATE", "correlation_id": correlation_id}, correlation_id)
        view = self.views.read(context=context, household_id=household_id, subject_id=subject_id, kind="tasks", purpose="view")
        if view["reason_code"] != "ALLOW":
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="DENIED")
            return self._error(403, "POLICY_DENIED", "当前身份无权执行该操作", correlation_id)

        action = body.get("action")
        if action == "ACKNOWLEDGE_ALERT" and isinstance(body.get("resource_id"), str) and body["resource_id"]:
            result = {"request_id": f"request-{uuid.uuid4()}", "audit_time": datetime.now(timezone.utc).isoformat(), "alert_id": body["resource_id"], "status": "RECORDED"}
        elif action == "CREATE_CARE_REQUEST" and body.get("template") in {"SEND_CARE_NOTE", "REMINDER_PREFERENCE"}:
            result = {"request_id": f"care-{uuid.uuid4()}", "template": body["template"], "status": "RECORDED", "audit_time": datetime.now(timezone.utc).isoformat()}
        else:
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="FAILED")
            return self._error(422, "INVALID_REQUEST", "不支持的家属端命令", correlation_id)

        self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="SUCCEEDED")
        return self._ok(result, correlation_id)

    def publish_view_update(self, *, tenant_id: str, household_id: str, subject_id: str, view: str) -> int:
        return self.stream.publish(tenant_id=tenant_id, household_id=household_id, subject_id=subject_id, view=view, snapshot_id=self.core.projections.digest())

    def _stream(self, context: AuthContext, household_id: str, subject_id: str, last_event_id: str | None, correlation_id: str) -> BffResponse:
        try:
            last = int(last_event_id) if last_event_id else None
            if last is not None and last < 0: raise ValueError
        except ValueError:
            return self._error(400, "INVALID_REQUEST", "Last-Event-ID 无效", correlation_id)
        events = self.stream.read(context=context, household_id=household_id, subject_id=subject_id, last_event_id=last)
        if not events:
            return self._error(403, "POLICY_DENIED", "当前身份无权订阅该状态流", correlation_id)
        payload = "".join(self.stream.encode(event) for event in events)
        return BffResponse(200, {"_sse": payload}, {"X-Correlation-Id": correlation_id, "Cache-Control": "no-store", "Content-Type": "text/event-stream; charset=utf-8", "Connection": "keep-alive"})

    def _command_meta(self, body: Mapping[str, Any] | None, context: AuthContext, household_id: str, subject_id: str) -> tuple[bool, BffResponse | None]:
        if not body or not isinstance(body.get("command_id"), str) or not isinstance(body.get("idempotency_key"), str) or not isinstance(body.get("expected_version"), int):
            return False, self._error(422, "INVALID_COMMAND", "命令必须包含 command_id、idempotency_key 与 expected_version", f"bff-{uuid.uuid4()}")
        accepted = self.core.store.accept_command(command_id=body["command_id"], idempotency_key=body["idempotency_key"], expected_version=body["expected_version"], tenant_id=context.tenant_id, household_id=household_id, subject_id=subject_id)
        return accepted, None

    def _grant_consent(self, context: AuthContext, body: Mapping[str, Any] | None, correlation_id: str) -> BffResponse:
        if not body or body.get("owner") != context.actor_id:
            return self._error(403, "POLICY_DENIED", "当前身份无权授予该同意", correlation_id)
        accepted, error = self._command_meta(body, context, str(body.get("household_id", "")), context.actor_id)
        if error: return error
        if not accepted: return self._ok({"status": self.core.store.command_status(body["idempotency_key"]) or "DUPLICATE", "correlation_id": correlation_id}, correlation_id)
        try:
            consent = self.ledger.grant(owner=context.actor_id, grantee=str(body["grantee"]), household_id=str(body["household_id"]), scope=str(body["scope"]), purpose=str(body["purpose"]), classification=str(body.get("classification", "SENSITIVE")), channel=str(body.get("channel", "TERMINAL")), tenant_id=context.tenant_id, actor=context.actor_id, source="BFF")
        except (KeyError, ValueError):
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="FAILED")
            return self._error(422, "INVALID_REQUEST", "同意字段无效", correlation_id)
        self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="SUCCEEDED")
        return BffResponse(201, {"consent": consent, "correlation_id": correlation_id}, {"X-Correlation-Id": correlation_id, "Cache-Control": "no-store"})

    def _change_consent(self, context: AuthContext, consent_id: str, body: Mapping[str, Any] | None, correlation_id: str, action: str) -> BffResponse:
        try:
            current = self.ledger.get(consent_id)
        except KeyError:
            return self._error(404, "NOT_FOUND", "接口不存在", correlation_id)
        accepted, error = self._command_meta(body, context, current["household_id"], current["owner"])
        if error: return error
        if not accepted: return self._ok({"status": self.core.store.command_status(body["idempotency_key"]) or "DUPLICATE", "correlation_id": correlation_id}, correlation_id)
        try:
            changed = self.ledger.activate(consent_id, actor=context.actor_id, expected_version=body["expected_version"]) if action == "activate" else self.ledger.revoke(consent_id, actor=context.actor_id, expected_version=body["expected_version"])
        except PermissionError:
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="DENIED")
            return self._error(403, "POLICY_DENIED", "当前身份无权修改该同意", correlation_id)
        except ValueError:
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="FAILED")
            return self._error(409, "VERSION_CONFLICT", "版本或状态已变更，请刷新后重试", correlation_id)
        self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="SUCCEEDED")
        return self._ok({"consent": changed, "correlation_id": correlation_id}, correlation_id)

    @staticmethod
    def _ok(body: dict[str, Any], correlation_id: str, etag: str | None = None) -> BffResponse:
        headers = {"X-Correlation-Id": correlation_id, "Cache-Control": "no-store"}
        if etag:
            headers["ETag"] = f'"{etag}"'
        return BffResponse(200, body, headers)

    @staticmethod
    def _error(status: int, code: str, message: str, correlation_id: str) -> BffResponse:
        return BffResponse(status, {"code": code, "message": message, "retryable": status in {429, 503}, "correlation_id": correlation_id}, {"X-Correlation-Id": correlation_id, "Cache-Control": "no-store"})


def make_bff_handler(bff: CareBff) -> type[BaseHTTPRequestHandler]:
    """开发/演示 HTTP 适配器；业务与授权逻辑保留在 CareBff 中。"""
    class Handler(BaseHTTPRequestHandler):
        def _write(self, response: BffResponse) -> None:
            is_sse = "_sse" in response.body
            raw = response.body["_sse"].encode() if is_sse else json.dumps(response.body, ensure_ascii=False).encode()
            self.send_response(response.status)
            for key, value in response.headers.items(): self.send_header(key, value)
            self.send_header("Content-Type", response.headers.get("Content-Type", "application/json; charset=utf-8"))
            self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def do_GET(self) -> None: self._write(bff.handle(method="GET", path=self.path, headers=dict(self.headers.items())))
        def log_message(self, format: str, *args: Any) -> None: del format, args
    return Handler


def serve_bff_local(bff: CareBff, *, port: int = 8081) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_bff_handler(bff))
