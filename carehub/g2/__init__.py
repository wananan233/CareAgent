"""G2 受控聊天组件：只读上下文和结构化回复。"""

from .chat import ChatService, ChatSession, DeepSeekGenerator, FakeLLM, build_context_snapshot
from .context import build_chat_context_from_g1
from .http_api import ChatHttpApi, InMemoryRateLimiter, StaticTokenAuthenticator, serve_local

__all__ = ["ChatHttpApi", "ChatService", "ChatSession", "DeepSeekGenerator", "FakeLLM", "InMemoryRateLimiter", "StaticTokenAuthenticator", "build_chat_context_from_g1", "build_context_snapshot", "serve_local"]
