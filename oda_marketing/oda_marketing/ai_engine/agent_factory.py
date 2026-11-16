# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

"""Builds Pydantic AI models from the dict returned by key_manager.get_llm_config().

Never logs or embeds secrets in exceptions. Unsupported, mock or unknown providers raise
LLMConfigError so callers can record an explicit failure instead of a fake result.
"""

OPENAI_STYLE_PROVIDERS = ("APIM Gateway", "OpenAI")
REQUEST_TIMEOUT_SECONDS = 60
MAX_RETRIES = 2


class LLMConfigError(Exception):
    """The LLM configuration is missing, unsupported or unusable."""


def _require(cfg, key, provider):
    value = (cfg.get(key) or "").strip() if isinstance(cfg.get(key), str) else cfg.get(key)
    if not value:
        raise LLMConfigError(f"LLM config for provider '{provider}' is missing '{key}'.")
    return value


def normalize_anthropic_base_url(endpoint):
    """Stored value is like https://api.anthropic.com/v1; the SDK adds /v1 itself (verify)."""
    base = (endpoint or "").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return base


def normalize_openai_base_url(endpoint):
    """Accept an API base URL or the full chat-completions route configured in Env Variable."""
    base = (endpoint or "").strip().rstrip("/")
    suffix = "/chat/completions"
    if base.lower().endswith(suffix):
        base = base[: -len(suffix)].rstrip("/")
    return base


def build_openai_client(cfg):
    """AsyncOpenAI client. api_key -> Authorization: Bearer; APIM also gets the api-key header."""
    from openai import AsyncOpenAI

    provider = cfg.get("provider")
    api_key = _require(cfg, "api_key", provider)
    endpoint = _require(cfg, "endpoint", provider)
    return AsyncOpenAI(
        api_key=api_key,
        base_url=normalize_openai_base_url(endpoint),
        default_headers={"api-key": api_key},
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=MAX_RETRIES,
    )


def build_anthropic_client(cfg):
    """Create an Anthropic client with the app's required authorization headers."""
    from anthropic import AsyncAnthropic

    provider = cfg.get("provider")
    api_key = _require(cfg, "api_key", provider)
    endpoint = _require(cfg, "endpoint", provider)
    return AsyncAnthropic(
        api_key=api_key,
        base_url=normalize_anthropic_base_url(endpoint),
        default_headers={
            "Authorization": f"Bearer {api_key}",
            "api-key": api_key,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=MAX_RETRIES,
    )


def build_model(cfg):
    """Return a Pydantic AI Model for the configured provider, or raise LLMConfigError."""
    provider = cfg.get("provider")
    model_name = _require(cfg, "model", provider)

    if provider in ("Mock Agent", "Custom"):
        raise LLMConfigError(f"Provider '{provider}' has no live LLM; configure a real provider.")

    if provider in OPENAI_STYLE_PROVIDERS:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=build_openai_client(cfg)))

    if provider == "Anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(
            model_name,
            provider=AnthropicProvider(anthropic_client=build_anthropic_client(cfg)),
        )

    if provider == "Google Gemini":
        raise LLMConfigError(
            "Google Gemini is not installed (the 'google' extra conflicts with Frappe's google-auth pin). "
            "Use an OpenAI-compatible endpoint with provider 'OpenAI'."
        )

    raise LLMConfigError(f"Unknown LLM provider: {provider!r}")


def build_model_settings(temperature=0.2, max_tokens=None):
    """Plain dict accepted as model_settings (keys verified against ModelSettings in 2.66)."""
    settings = {"temperature": temperature, "timeout": REQUEST_TIMEOUT_SECONDS}
    if max_tokens:
        settings["max_tokens"] = max_tokens
    return settings
