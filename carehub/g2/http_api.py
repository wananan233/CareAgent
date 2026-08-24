"""G2.2 本地只读聊天 HTTP API。"""

from __future__ import annotations

import json
import re
import uuid
import base64
import hashlib
import hmac
from collections import deque
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Mapping
from threading import Lock
from time import monotonic, time

from .chat import ChatService
from carehub.g3 import AuthContext, PolicyRequest, ServerSidePDP


CHAT_PATH = re.compile(r"^/v1/users/(?P<user_id>[a-zA-Z0-9_-]+)/chat$")
WEB_PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CareHub G2.3</title><style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;background:#f7f8fa;color:#18212f}h1{margin-bottom:.2rem}.hint{color:#536274}.settings{display:grid;grid-template-columns:1fr 2fr;gap:.6rem;margin:1rem 0}.settings input,textarea{font:inherit;padding:.65rem;border:1px solid #b9c2cf;border-radius:.4rem}.chat{background:white;border:1px solid #dce1e8;border-radius:.5rem;min-height:18rem;padding:1rem;display:flex;flex-direction:column;gap:.8rem}.item{white-space:pre-wrap;line-height:1.5}.you{color:#1d4ed8}.agent{color:#166534}.composer{display:flex;gap:.5rem;margin-top:1rem}textarea{flex:1;min-height:3rem}button{padding:.6rem 1rem;border:0;border-radius:.4rem;background:#2563eb;color:white;font:inherit;cursor:pointer}button:disabled{opacity:.6}
</style></head><body><h1>CareHub G2.3</h1><p class="hint">本地只读模拟器聊天。令牌和最近 3 轮历史仅存在当前页面内存，关闭页面即丢弃。</p>
<div class="settings"><input id="user" value="synthetic-01" aria-label="用户 ID"><input id="token" type="password" placeholder="输入 CAREHUB_API_TOKEN" aria-label="访问令牌"></div>
<main id="chat" class="chat" aria-live="polite"></main><form id="form" class="composer"><textarea id="message" placeholder="例如：我现在有什么提醒？" required maxlength="500"></textarea><button id="send">发送</button></form>
<script>
const history=[]; const chat=document.querySelector('#chat'); const form=document.querySelector('#form'); const message=document.querySelector('#message'); const send=document.querySelector('#send');
function add(role,text){const item=document.createElement('div');item.className='item '+role;item.textContent=(role==='you'?'你：':'CareHub：')+text;chat.append(item);chat.scrollTop=chat.scrollHeight;}
form.addEventListener('submit',async(event)=>{event.preventDefault();const text=message.value.trim(),token=document.querySelector('#token').value,user=document.querySelector('#user').value.trim();if(!text||!token||!user){add('agent','请填写用户 ID、访问令牌和消息。');return;}send.disabled=true;add('you',text);message.value='';try{const response=await fetch('/v1/users/'+encodeURIComponent(user)+'/chat',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify({message:text,history})});const payload=await response.json();if(!response.ok)throw new Error(payload.message||'请求失败');add('agent',payload.message);history.push({role:'user',content:text},{role:'assistant',content:payload.message});history.splice(0,Math.max(0,history.length-6));}catch(error){add('agent','请求未完成：'+error.message);}finally{send.disabled=false;message.focus();}});
</script></body></html>"""


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: dict[str, Any]


class StaticTokenAuthenticator:
    """测试和本地部署使用的令牌到主体映射；令牌本身不会写入日志。"""

    def __init__(self, token_subjects: Mapping[str, str | AuthContext], *, tenant_id: str = "tenant:synthetic") -> None:
        self._token_subjects = dict(token_subjects)
        self._tenant_id = tenant_id

    def authenticate(self, authorization: str | None) -> str | None:
        context = self.authenticate_context(authorization)
        return context.actor_id if context else None

    def authenticate_context(self, authorization: str | None) -> AuthContext | None:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization.removeprefix("Bearer ")
        identity = self._token_subjects.get(token)
        if isinstance(identity, AuthContext):
            return AuthContext(identity.actor_id, identity.tenant_id, token)
        return AuthContext(identity, self._tenant_id, token) if identity else None


class SignedDemoAuthenticator:
    """本地演示用 HMAC Bearer 令牌；密钥由部署注入，绝不写入仓库或审计。"""
    def __init__(self, signing_key: bytes, *, clock: Callable[[], float] = time) -> None:
        if len(signing_key) < 16:
            raise ValueError("演示签名密钥至少 16 字节")
        self._key, self._clock = signing_key, clock

    def issue(self, *, actor_id: str, tenant_id: str, ttl_seconds: int = 300) -> str:
        if ttl_seconds < 1 or not actor_id or not tenant_id:
            raise ValueError("令牌声明无效")
        payload = json.dumps({"actor_id": actor_id, "tenant_id": tenant_id, "exp": int(self._clock() + ttl_seconds)}, separators=(",", ":")).encode()
        body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
        signature = hmac.new(self._key, body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{signature}"

    def authenticate_context(self, authorization: str | None) -> AuthContext | None:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization.removeprefix("Bearer ")
        try:
            body, signature = token.split(".", 1)
            expected = hmac.new(self._key, body.encode(), hashlib.sha256).hexdigest()
            payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            if not hmac.compare_digest(signature, expected) or int(payload["exp"]) <= self._clock():
                return None
            return AuthContext(str(payload["actor_id"]), str(payload["tenant_id"]), "signed-demo")
        except (ValueError, KeyError, UnicodeDecodeError, json.JSONDecodeError):
            return None

    def authenticate(self, authorization: str | None) -> str | None:
        context = self.authenticate_context(authorization)
        return context.actor_id if context else None


class InMemoryRateLimiter:
    """按已认证主体限流；仅保存单调时间戳，不保存消息内容。"""

    def __init__(self, *, max_requests: int = 10, window_seconds: float = 60.0, clock: Callable[[], float] = monotonic) -> None:
        if max_requests < 1 or window_seconds <= 0:
            raise ValueError("限流参数必须为正数")
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._requests: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, subject_id: str) -> bool:
        now = self._clock()
        with self._lock:
            timestamps = self._requests.setdefault(subject_id, deque())
            while timestamps and timestamps[0] <= now - self._window_seconds:
                timestamps.popleft()
            if len(timestamps) >= self._max_requests:
                return False
            timestamps.append(now)
            return True


class ChatHttpApi:
    """无状态请求处理器；对话内容既不写入 EventStore，也不写入磁盘。"""

    def __init__(
        self,
        *,
        chat_service: ChatService,
        authenticator: StaticTokenAuthenticator,
        context_provider: Callable[[str], Mapping[str, Any]],
        rate_limiter: InMemoryRateLimiter | None = None,
        audit_recorder: Callable[[str, str, str], None] | None = None,
        pdp: ServerSidePDP | None = None,
    ) -> None:
        self._chat_service = chat_service
        self._authenticator = authenticator
        self._context_provider = context_provider
        self._rate_limiter = rate_limiter or InMemoryRateLimiter()
        self._audit_recorder = audit_recorder
        self._pdp = pdp

    def handle(self, *, method: str, path: str, headers: Mapping[str, str], body: bytes) -> ApiResponse:
        match = CHAT_PATH.fullmatch(path)
        if method != "POST" or not match:
            return self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "接口不存在", retryable=False)
        context = self._authenticator.authenticate_context(headers.get("Authorization"))
        if not context:
            return self._error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", "缺少或无效的访问令牌", retryable=False)
        requested_subject = f"user:{match.group('user_id')}"
        if not self._pdp and context.actor_id != requested_subject:
            return self._error(HTTPStatus.FORBIDDEN, "SUBJECT_MISMATCH", "令牌无权访问该用户", retryable=False)
        if not self._rate_limiter.allow(context.actor_id):
            return self._error(HTTPStatus.TOO_MANY_REQUESTS, "RATE_LIMITED", "请求过于频繁，请稍后重试", retryable=True)
        try:
            request = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error(HTTPStatus.BAD_REQUEST, "INVALID_JSON", "请求体必须是 JSON", retryable=False)
        if not isinstance(request, dict) or set(request) - {"message", "channel", "history"}:
            return self._error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "仅支持 message、可选 channel 和 history 字段", retryable=False)
        if self._pdp:
            scope = self._pdp.store.connection.execute(
                "SELECT household_id FROM subject WHERE tenant_id=? AND subject_id=?",
                (context.tenant_id, requested_subject),
            ).fetchone()
            if not scope:
                self._audit("DENY", "UNKNOWN_SCOPE", context.actor_id)
                return self._error(HTTPStatus.FORBIDDEN, "POLICY_DENIED", "无权访问该资源范围", retryable=False)
            decision = self._pdp.authorize(context, PolicyRequest(
                scope["household_id"], requested_subject, "read_authorized_view", "chat", "SENSITIVE",
                request.get("channel", "TERMINAL"), "chat",
            ))
            if not decision.allowed:
                self._audit("DENY", decision.reason, context.actor_id)
                return self._error(HTTPStatus.FORBIDDEN, "POLICY_DENIED", "授权策略拒绝访问", retryable=False)
        try:
            snapshot = self._context_provider(requested_subject)
            response = self._chat_service.respond(
                message=request.get("message"),
                context_snapshot=snapshot,
                channel=request.get("channel", "TERMINAL"),
                history=request.get("history", ()),
            )
        except ValueError as error:
            return self._error(HTTPStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", str(error), retryable=False)
        except RuntimeError:
            self._audit("DENY", "MODEL_UNAVAILABLE", context.actor_id)
            return self._error(HTTPStatus.BAD_GATEWAY, "MODEL_UNAVAILABLE", "模型服务暂不可用", retryable=True)
        except Exception:
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "本地服务处理失败", retryable=False)
        self._audit("ALLOW", "CHAT_RESPONSE", context.actor_id)
        return ApiResponse(status=HTTPStatus.OK, body=response)

    def _audit(self, decision: str, reason: str, subject_id: str) -> None:
        if self._audit_recorder:
            self._audit_recorder(decision, reason, f"chat:{subject_id}")

    @staticmethod
    def _error(status: HTTPStatus, code: str, message: str, *, retryable: bool) -> ApiResponse:
        return ApiResponse(
            status=status,
            body={
                "code": code,
                "message": message,
                "retryable": retryable,
                "correlation_id": f"http-{uuid.uuid4()}",
            },
        )


def make_handler(api: ChatHttpApi) -> type[BaseHTTPRequestHandler]:
    """生成不输出请求正文和 Authorization 的 HTTP Handler。"""

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, response: ApiResponse) -> None:
            self._send(response.status, json.dumps(response.body, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/":
                self._send(HTTPStatus.OK, WEB_PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/health":
                self._send_json(ApiResponse(status=HTTPStatus.OK, body={"status": "ok"}))
            else:
                self._send_json(api._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "接口不存在", retryable=False))

        def do_POST(self) -> None:  # noqa: N802
            content_length = self.headers.get("Content-Length")
            try:
                length = int(content_length or "0")
            except ValueError:
                length = -1
            if length < 0 or length > 16_384:
                response = api._error(HTTPStatus.BAD_REQUEST, "INVALID_BODY", "请求体大小无效", retryable=False)
            else:
                response = api.handle(
                    method="POST",
                    path=self.path,
                    headers={key: value for key, value in self.headers.items()},
                    body=self.rfile.read(length),
                )
            self._send_json(response)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    return Handler


def serve_local(api: ChatHttpApi, *, port: int = 8080) -> ThreadingHTTPServer:
    """创建仅绑定回环地址的服务，调用方负责 ``serve_forever``。"""
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(api))
