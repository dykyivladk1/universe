import os
from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from universe import config

# key is what the UI/agents.json use, value is (provider, real model id).
# Old version probed every OpenAI model on startup which took forever,
# so now it's just a list. Add stuff here or via UNIVERSE_EXTRA_MODELS.
MODELS = {
    "gpt-5": ("openai", "gpt-5"),
    "gpt-5-mini": ("openai", "gpt-5-mini"),
    "gpt-4.1": ("openai", "gpt-4.1"),
    "gpt-4.1-mini": ("openai", "gpt-4.1-mini"),
    "gpt-4o": ("openai", "gpt-4o"),
    "o4-mini": ("openai", "o4-mini"),
    "claude-sonnet-4-5": ("anthropic", "claude-sonnet-4-5"),
    "claude-opus-4-1": ("anthropic", "claude-opus-4-1"),
    "claude-haiku-4-5": ("anthropic", "claude-haiku-4-5"),
}

# e.g. UNIVERSE_EXTRA_MODELS="openai:gpt-5.5,anthropic:claude-opus-4-6"
for item in os.getenv("UNIVERSE_EXTRA_MODELS", "").split(","):
    if ":" in item:
        provider, name = item.strip().split(":", 1)
        MODELS[name] = (provider, name)


def list_models():
    out = []
    for key, (provider, _) in MODELS.items():
        out.append({"key": key, "provider": provider})
    return out


@lru_cache(maxsize=32)
def get_llm(model_key, temperature=0.7):
    if model_key not in MODELS:
        raise ValueError(f"Unknown model: {model_key}")

    provider, name = MODELS[model_key]

    if provider == "openai":
        # reasoning models (o-series, gpt-5) don't accept temperature
        if name.startswith("o") or name.startswith("gpt-5"):
            return ChatOpenAI(model=name, api_key=config.OPENAI_API_KEY)
        return ChatOpenAI(model=name, temperature=temperature, api_key=config.OPENAI_API_KEY)

    if provider == "anthropic":
        return ChatAnthropic(
            model=name,
            temperature=temperature,
            max_tokens=4096,
            api_key=config.ANTHROPIC_API_KEY,
        )

    raise ValueError(f"Provider {provider} is not supported yet")
