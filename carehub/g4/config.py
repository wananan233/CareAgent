"""显式选择 G4 Provider 的部署配置；密钥始终只由 Provider 从进程环境读取。"""
from __future__ import annotations

import os
from typing import Mapping

from .deepseek import DeepSeekProvider
from .gateway import FakeProvider, ModelGateway


def create_model_gateway_from_env(environ: Mapping[str, str] | None = None) -> ModelGateway:
    """创建受控网关。

    默认值永远是离线 FakeProvider。部署环境必须显式设置
    ``CAREHUB_MODEL_PROVIDER=deepseek`` 才会启用外部 Provider；API key 不会被
    本函数读取、记录或传给任一业务组件，而是在 DeepSeekProvider 发起请求时从
    该进程环境的 ``DEEPSEEK_API_KEY`` 读取。
    """
    env = os.environ if environ is None else environ
    provider_name = env.get("CAREHUB_MODEL_PROVIDER", "fake").strip().lower()
    if provider_name in {"", "fake"}:
        return ModelGateway(FakeProvider())
    if provider_name != "deepseek":
        raise ValueError("CAREHUB_MODEL_PROVIDER must be fake or deepseek")

    model = env.get("CAREHUB_DEEPSEEK_MODEL", "deepseek-v4-flash")
    base_url = env.get("CAREHUB_DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    try:
        timeout_seconds = float(env.get("CAREHUB_DEEPSEEK_TIMEOUT_SECONDS", "2"))
    except ValueError as error:
        raise ValueError("CAREHUB_DEEPSEEK_TIMEOUT_SECONDS must be a number") from error
    if timeout_seconds <= 0 or timeout_seconds > 10:
        raise ValueError("CAREHUB_DEEPSEEK_TIMEOUT_SECONDS must be within (0, 10]")
    return ModelGateway(DeepSeekProvider(model=model, base_url=base_url, timeout_seconds=timeout_seconds))
