"""G2 受控聊天组件：只读上下文和结构化回复。"""

from .chat import ChatService, ChatSession, DeepSeekGenerator, FakeLLM, GatewayResponseGenerator, build_context_snapshot
from .context import build_chat_context_from_g1
from .http_api import ChatHttpApi, InMemoryRateLimiter, SignedDemoAuthenticator, StaticTokenAuthenticator, serve_local
from .deterministic import ChannelMocks, DeterministicAgent, MockSkillExecutor, PolicyGateway
from .response import ResponseEngine

__all__ = ["ChannelMocks", "ChatHttpApi", "ChatService", "ChatSession", "DeepSeekGenerator", "DeterministicAgent", "FakeLLM", "GatewayResponseGenerator", "InMemoryRateLimiter", "MockSkillExecutor", "PolicyGateway", "ResponseEngine", "SignedDemoAuthenticator", "StaticTokenAuthenticator", "build_chat_context_from_g1", "build_context_snapshot", "serve_local"]
