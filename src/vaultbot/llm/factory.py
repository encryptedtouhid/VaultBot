"""LLM provider factory.

Creates LLM provider instances from configuration, routing to the
appropriate implementation based on provider name.
"""

from __future__ import annotations

from vaultbot.llm.base import LLMProvider

# Mapping of provider names to their implementations
_NATIVE_PROVIDERS = {"claude", "openai", "gemini"}
_COMPATIBLE_PROVIDERS = {
    "openrouter", "together", "groq", "mistral", "perplexity",
    "deepseek", "fireworks", "ollama", "vllm", "lmstudio",
    "xai", "bedrock_compat",
}


def create_provider(
    provider: str,
    *,
    api_key: str = "",
    model: str | None = None,
    base_url: str | None = None,
) -> LLMProvider:
    """Create an LLM provider instance by name.

    Parameters
    ----------
    provider:
        Provider name (e.g. ``claude``, ``openai``, ``gemini``, ``groq``,
        ``deepseek``, ``mistral``, ``ollama``, etc.).
    api_key:
        API key for the provider.
    model:
        Override the default model.
    base_url:
        Override the base URL (for compatible providers).

    Returns
    -------
    LLMProvider
        An instance satisfying the LLMProvider protocol.
    """
    name = provider.lower().strip()

    if name == "claude":
        from vaultbot.llm.claude import ClaudeProvider
        return ClaudeProvider(api_key=api_key)

    if name == "openai":
        from vaultbot.llm.openai_gpt import OpenAIProvider
        return OpenAIProvider(api_key=api_key)

    if name == "gemini":
        from vaultbot.llm.gemini import GeminiProvider
        return GeminiProvider(api_key=api_key, default_model=model or "gemini-2.0-flash")

    if name == "local":
        from vaultbot.llm.local import LocalProvider
        return LocalProvider(
            base_url=base_url or "http://localhost:11434/v1",
            default_model=model or "llama3.2",
            api_key=api_key or "not-needed",
        )

    if name in _COMPATIBLE_PROVIDERS:
        from vaultbot.llm.compatible import CompatibleProvider
        return CompatibleProvider.from_preset(name, api_key=api_key, model=model)

    # Fallback: treat as custom OpenAI-compatible endpoint
    if base_url:
        from vaultbot.llm.compatible import CompatibleProvider
        return CompatibleProvider(
            base_url=base_url,
            default_model=model or "default",
            api_key=api_key or "not-needed",
            provider_label=name,
        )

    available = sorted(_NATIVE_PROVIDERS | _COMPATIBLE_PROVIDERS | {"local"})
    raise ValueError(
        f"Unknown LLM provider '{provider}'. Available: {', '.join(available)}"
    )


def list_providers() -> list[str]:
    """Return a sorted list of all known provider names."""
    return sorted(_NATIVE_PROVIDERS | _COMPATIBLE_PROVIDERS | {"local"})
