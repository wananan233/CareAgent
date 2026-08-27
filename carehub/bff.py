"""C2 最小 BFF：双端通过同一受保护 REST 契约读取视图。"""
from __future__ import annotations

import uuid
import time
import json
from urllib.parse import unquote
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from threading import RLock
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from carehub.core.service import CareCore
from carehub.g3 import AuthContext, AuthorizedProjectionReader, ConsentLedger, ServerSidePDP
from carehub.sse import AuthorizedStateStream
from carehub.g4 import AgentOrchestrator, ModelGateway
from carehub.g4.capabilities import trend_context


@dataclass(frozen=True)
class BffResponse:
    status: int
    body: dict[str, Any]
    headers: dict[str, str]


def parse_path_segments(path: str) -> list[str]:
    """按路由 segment 单次解码，避免编码 ID 被当作另一主体或家庭。"""
    return [unquote(segment) for segment in path.strip("/").split("/") if segment]


class CareBff:
    """不向客户端暴露 EventStore、投影键或原始事件 payload。"""
    def __init__(self, *, core: CareCore, authenticator: Any, model_gateway: ModelGateway | None = None) -> None:
        self.core, self.authenticator = core, authenticator
        self._connection_lock = RLock()
        self.ledger = ConsentLedger(core.store)
        self.pdp = ServerSidePDP(core.store, self.ledger)
        self.views = AuthorizedProjectionReader(self.pdp, core.projections)
        self.stream = AuthorizedStateStream(self.pdp)
        # 默认网关仍是离线 FakeProvider；生产部署必须显式注入由 Linux
        # 进程环境构造的受控网关，BFF 从不读取或保存模型密钥。
        self.agent = AgentOrchestrator(core.store, self.pdp, gateway=model_gateway)

    def handle_request(self, *, method: str, path: str, headers: Mapping[str, str], body: Mapping[str, Any] | None = None) -> BffResponse:
        """按请求串行化共享 SQLite 连接的完整访问边界。"""
        with self._connection_lock:
            return self.handle(method=method, path=path, headers=headers, body=body)

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
        parts = parse_path_segments(path)
        if method == "GET" and len(parts) == 6 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] == "dashboard":
            household_id, subject_id = parts[2], parts[4]
            tasks = self.views.read(context=context, household_id=household_id, subject_id=subject_id, kind="tasks", purpose="view")
            alerts = self.views.read(context=context, household_id=household_id, subject_id=subject_id, kind="alerts", purpose="view")
            if tasks["reason_code"] != "ALLOW" or alerts["reason_code"] != "ALLOW": return self._error(403, "POLICY_DENIED", "当前身份无权访问该视图", correlation_id)
            consent = self.core.store.connection.execute(
                "SELECT scope, status, expires_at, version FROM consent_ledger WHERE tenant_id=? AND household_id=? AND owner=? AND grantee=? AND scope='view' AND purpose='view' AND classification='SENSITIVE' AND channel='TERMINAL' AND status='ACTIVE' ORDER BY version DESC LIMIT 1",
                (context.tenant_id, household_id, subject_id, context.actor_id),
            ).fetchone()
            if not consent: return self._error(403, "POLICY_DENIED", "当前身份无权访问该视图", correlation_id)
            return self._ok({"snapshot_id": self.core.projections.digest(), "server_time": datetime.now(timezone.utc).isoformat(), "last_updated_at": datetime.now(timezone.utc).isoformat(), "quality": "VALID", "source_refs": [{"type":"SIMULATOR","label":"CareHub 合成模拟器"}], "family_member": {"subject_id":subject_id,"household_id":household_id,"display_name":"已授权家庭成员","relationship":"家人"}, "consent":dict(consent), "allowed_actions": tasks["allowed_actions"]}, correlation_id)
        if method == "GET" and len(parse_path_segments(path)) == 6 and path.endswith("/stream"):
            parts = parse_path_segments(path)
            if parts[:2] == ["v1", "households"] and parts[3] == "subjects":
                return self._stream(context, parts[2], parts[4], headers.get("Last-Event-ID"), correlation_id)
        if method == "POST" and path == "/v1/consents":
            return self._grant_consent(context, body, correlation_id)
        if method == "POST" and path.startswith("/v1/consents/") and path.endswith(":activate"):
            return self._change_consent(context, path.removeprefix("/v1/consents/").removesuffix(":activate"), body, correlation_id, "activate")
        if method == "POST" and path.startswith("/v1/consents/") and path.endswith(":revoke"):
            return self._change_consent(context, path.removeprefix("/v1/consents/").removesuffix(":revoke"), body, correlation_id, "revoke")
        parts = parse_path_segments(path)
        if method == "POST" and len(parts) == 6 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] == "requests":
            return self._family_command(context, parts[2], parts[4], body, correlation_id)
        if method == "POST" and len(parts) == 6 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] == "read-only-qa":
            if not body or not isinstance(body.get("question"), str):
                return self._error(422, "INVALID_REQUEST", "问题必须是文本", correlation_id)
            return self._agent_response(context, parts[2], parts[4], "READ_ONLY_QA", correlation_id, question=body["question"])
        if method == "POST" and len(parts) == 7 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] == "consents" and parts[6].endswith(":revoke"):
            return self._revoke_subject_scope(context, parts[2], parts[4], parts[6].removesuffix(":revoke"), body, correlation_id)
        if method == "POST" and len(parts) == 7 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] == "consents" and parts[6].endswith(":relinquish"):
            return self._relinquish_scope(context, parts[2], parts[4], parts[6].removesuffix(":relinquish"), body, correlation_id)
        if method == "GET" and len(parts) == 6 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] in {"today-status", "report", "weekly-trend", "change-explanation"}:
            purpose = {"today-status": "TODAY_STATUS", "report": "DAILY_SUMMARY", "weekly-trend": "WEEKLY_TREND", "change-explanation": "CHANGE_EXPLANATION"}[parts[5]]
            return self._agent_response(context, parts[2], parts[4], purpose, correlation_id)
        if method == "GET" and len(parts) == 6 and parts[:2] == ["v1", "households"] and parts[3] == "subjects" and parts[5] in {"tasks", "alerts", "timeline"}:
            household_id, subject_id, kind = parts[2], parts[4], parts[5]
            body = self.views.read(context=context, household_id=household_id, subject_id=subject_id, kind=kind, purpose="view", resource_version=self.core.projections.digest())
            if body["reason_code"] != "ALLOW":
                return self._error(403, "POLICY_DENIED", "当前身份无权访问该视图", correlation_id)
            body.update({"snapshot_id": self.core.projections.digest(), "server_time": datetime.now(timezone.utc).isoformat(), "freshness": "CURRENT", "correlation_id": correlation_id})
            return self._ok(body, correlation_id, etag=body["snapshot_id"])
        return self._error(404, "NOT_FOUND", "接口不存在", correlation_id)

    def _agent_response(self, context: AuthContext, household_id: str, subject_id: str, purpose: str, correlation_id: str, question: str | None = None) -> BffResponse:
        """从已授权视图构造最小事实，再进入 purpose 受限的 G4 网关。"""
        timeline = self.views.read(context=context, household_id=household_id, subject_id=subject_id, kind="timeline", purpose="view")
        if timeline["reason_code"] != "ALLOW":
            return self._error(403, "POLICY_DENIED", "当前身份无权访问该视图", correlation_id)
        if purpose in {"WEEKLY_TREND", "CHANGE_EXPLANATION"}:
            capability = trend_context(timeline["items"])
        else:
            capability = {"facts": [{"text": f"{item.get('event_type', 'UNKNOWN')} 于 {item.get('occurred_at', 'UNKNOWN')} 记录。", "source_refs": [item["event_id"]]}
                                    for item in timeline["items"][:20] if item.get("event_id")], "unknowns": [], "why_it_matters": [], "suggested_safe_actions": []}
        context_data = {"facts": capability["facts"]}
        if question is not None:
            context_data["question"] = question
        result = self.agent.run(context=context, household_id=household_id, subject_id=subject_id,
                                purpose=purpose, minimal_context=context_data)
        return self._ok({"schema_version": "AgentResponseV1", "response_id": f"response-{uuid.uuid4()}",
                         "channel": "TERMINAL", **result, **{key: capability[key] for key in ("unknowns", "why_it_matters", "suggested_safe_actions")},
                         "correlation_id": correlation_id}, correlation_id)

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
        if action in {"ACKNOWLEDGE_TASK", "VIEW_ALERT", "ACKNOWLEDGE_ALERT"} and isinstance(body.get("resource_id"), str) and body["resource_id"]:
            result = {"request_id": f"request-{uuid.uuid4()}", "audit_time": datetime.now(timezone.utc).isoformat(), "alert_id": body["resource_id"], "status": "RECORDED"}
        elif action == "CREATE_CARE_REQUEST" and body.get("template") in {"SEND_CARE_NOTE", "REMINDER_PREFERENCE"}:
            result = {"request_id": f"care-{uuid.uuid4()}", "template": body["template"], "status": "RECORDED", "audit_time": datetime.now(timezone.utc).isoformat()}
        else:
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="FAILED")
            return self._error(422, "INVALID_REQUEST", "不支持的家属端命令", correlation_id)

        self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="SUCCEEDED")
        return self._ok(result, correlation_id)

    def _revoke_subject_scope(self, context: AuthContext, household_id: str, subject_id: str, scope: str, body: Mapping[str, Any] | None, correlation_id: str) -> BffResponse:
        """按主体和范围定位真实 consent_id；客户端不能猜测或伪造同意记录。"""
        if context.actor_id != subject_id:
            return self._error(403, "POLICY_DENIED", "当前身份无权撤销该主体授权", correlation_id)
        rows = self.core.store.connection.execute(
            "SELECT consent_id, version FROM consent_ledger WHERE tenant_id=? AND household_id=? AND owner=? AND scope=? AND status='ACTIVE' ORDER BY version DESC",
            (context.tenant_id, household_id, subject_id, scope),
        ).fetchall()
        if not rows:
            return self._error(404, "NOT_FOUND", "未找到可撤销的授权", correlation_id)
        accepted, error = self._command_meta(body, context, household_id, subject_id)
        if error: return error
        assert body is not None
        if not accepted: return self._ok({"status": self.core.store.command_status(body["idempotency_key"]) or "DUPLICATE", "correlation_id": correlation_id}, correlation_id)
        if any(row["version"] != body["expected_version"] for row in rows):
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="FAILED")
            return self._error(409, "VERSION_CONFLICT", "版本或状态已变更，请刷新后重试", correlation_id)
        try:
            changed = [self.ledger.revoke(row["consent_id"], actor=context.actor_id, expected_version=row["version"]) for row in rows]
        except (PermissionError, ValueError):
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="FAILED")
            return self._error(409, "VERSION_CONFLICT", "版本或状态已变更，请刷新后重试", correlation_id)
        self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="SUCCEEDED")
        return self._ok({"consent": changed[0], "correlation_id": correlation_id}, correlation_id)

    def _relinquish_scope(self, context: AuthContext, household_id: str, subject_id: str, scope: str, body: Mapping[str, Any] | None, correlation_id: str) -> BffResponse:
        row = self.core.store.connection.execute("SELECT consent_id, version FROM consent_ledger WHERE tenant_id=? AND household_id=? AND owner=? AND grantee=? AND scope=? AND status='ACTIVE' ORDER BY version DESC LIMIT 1", (context.tenant_id, household_id, subject_id, context.actor_id, scope)).fetchone()
        if not row: return self._error(403, "POLICY_DENIED", "当前身份无权放弃该授权", correlation_id)
        accepted, error = self._command_meta(body, context, household_id, subject_id)
        if error: return error
        assert body is not None
        if not accepted:
            return self._ok({"status": self.core.store.command_status(body["idempotency_key"]) or "DUPLICATE", "correlation_id": correlation_id}, correlation_id)
        if body["expected_version"] != row["version"]:
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="FAILED")
            return self._error(409, "VERSION_CONFLICT", "版本或状态已变更，请刷新后重试", correlation_id)
        try:
            changed = self.ledger.relinquish(row["consent_id"], actor=context.actor_id, expected_version=row["version"])
        except (PermissionError, ValueError):
            self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="FAILED")
            return self._error(409, "VERSION_CONFLICT", "版本或状态已变更，请刷新后重试", correlation_id)
        self.core.store.complete_command(idempotency_key=body["idempotency_key"], status="SUCCEEDED")
        return self._ok({"consent": changed, "correlation_id": correlation_id}, correlation_id)

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
        if not body or not isinstance(body.get("command_id"), str) or not body["command_id"] or not isinstance(body.get("idempotency_key"), str) or not body["idempotency_key"] or not isinstance(body.get("expected_version"), int) or body["expected_version"] < 1:
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


def make_bff_handler(bff: CareBff, *, allowed_origins: tuple[str, ...] = (), test_fault_status: int | None = None, test_delay_seconds: float = 0) -> type[BaseHTTPRequestHandler]:
    """开发/演示 HTTP 适配器；只为显式允许的浏览器 Origin 返回 CORS 头。"""
    class Handler(BaseHTTPRequestHandler):
        def _cors(self) -> None:
            origin = self.headers.get("Origin")
            if origin and origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Last-Event-ID")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Expose-Headers", "X-Correlation-Id")
                self.send_header("Vary", "Origin")
        def _write(self, response: BffResponse) -> None:
            is_sse = "_sse" in response.body
            raw = response.body["_sse"].encode() if is_sse else json.dumps(response.body, ensure_ascii=False).encode()
            self.send_response(response.status)
            self._cors()
            for key, value in response.headers.items(): self.send_header(key, value)
            self.send_header("Content-Type", response.headers.get("Content-Type", "application/json; charset=utf-8"))
            self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def do_GET(self) -> None:
            if self.path.endswith("/tasks") and test_fault_status:
                self._write(bff._error(test_fault_status, "UPSTREAM_UNAVAILABLE", "合成下游暂不可用", f"bff-{uuid.uuid4()}")); return
            if self.path.endswith("/tasks") and test_delay_seconds: time.sleep(test_delay_seconds)
            self._write(bff.handle_request(method="GET", path=self.path, headers=dict(self.headers.items())))
        def do_OPTIONS(self) -> None:
            if self.headers.get("Origin") not in allowed_origins:
                self.send_response(HTTPStatus.FORBIDDEN)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(HTTPStatus.NO_CONTENT)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()
        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                decoded = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
                if not isinstance(decoded, dict):
                    raise ValueError
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                self._write(bff._error(400, "INVALID_REQUEST", "请求正文必须是 JSON 对象", f"bff-{uuid.uuid4()}"))
                return
            self._write(bff.handle_request(method="POST", path=self.path, headers=dict(self.headers.items()), body=decoded))
        def log_message(self, format: str, *args: Any) -> None: del format, args
    return Handler


def serve_bff_local(bff: CareBff, *, port: int = 8081, allowed_origins: tuple[str, ...] = (), test_fault_status: int | None = None, test_delay_seconds: float = 0) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_bff_handler(bff, allowed_origins=allowed_origins, test_fault_status=test_fault_status, test_delay_seconds=test_delay_seconds))
