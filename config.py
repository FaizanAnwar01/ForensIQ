"""
ForensIQ – Configuration & API Key Management
===============================================
Loads environment variables from a `.env` file and exposes validated
settings to the rest of the application.

Supported LLM providers:
    • groq      – Groq (Llama, Mixtral, Gemma)  (default)
    • gemini    – Google Generative AI
    • openai    – OpenAI / GPT

Usage:
    from config import settings
    print(settings.provider)       # "groq"
    print(settings.api_key)        # "<your-key>"
    print(settings.model_name)     # "llama-3.3-70b-versatile"
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 1.  Load .env from project root
# ---------------------------------------------------------------------------
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)


# ---------------------------------------------------------------------------
# 2.  Provider ↔ defaults mapping
# ---------------------------------------------------------------------------
_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "groq": {
        "key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
    },
    "gemini": {
        "key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "default_model": "gemini-2.5-flash",
    },
    "openai": {
        "key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "default_model": "gpt-4o-mini",
    },
}

SUPPORTED_PROVIDERS = list(_PROVIDER_DEFAULTS.keys())


# ---------------------------------------------------------------------------
# 3.  Settings dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    """Immutable application settings resolved from the environment."""

    provider: str
    api_key: str
    model_name: str

    # -- LLM generation parameters (sensible defaults) ----------------------
    temperature: float = 0.2
    max_output_tokens: int = 8192

    def __post_init__(self) -> None:
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{self.provider}'. "
                f"Choose from {SUPPORTED_PROVIDERS}."
            )
        if not self.api_key or self.api_key.startswith("your-"):
            raise ValueError(
                f"Missing or placeholder API key for provider '{self.provider}'. "
                f"Set {_PROVIDER_DEFAULTS[self.provider]['key_env']} in your .env file."
            )


# ---------------------------------------------------------------------------
# 4.  Build settings singleton
# ---------------------------------------------------------------------------
def _load_settings() -> Settings:
    """Parse environment variables and return a validated Settings object."""
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()

    if provider not in _PROVIDER_DEFAULTS:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. "
            f"Supported: {SUPPORTED_PROVIDERS}"
        )

    defaults = _PROVIDER_DEFAULTS[provider]
    api_key = os.getenv(defaults["key_env"], "").strip()

    # Fallback: Google AI Studio names the key GOOGLE_API_KEY
    if not api_key and provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    model_name = os.getenv(defaults["model_env"], defaults["default_model"]).strip()

    return Settings(
        provider=provider,
        api_key=api_key,
        model_name=model_name,
    )


# Lazy singleton – imported as `from config import settings`
try:
    settings = _load_settings()
except ValueError as exc:
    # During import-time (e.g. IDE indexing) we don't want a crash.
    # The real validation happens when the app actually runs.
    settings = None  # type: ignore[assignment]
    _init_error = exc


def get_settings() -> Settings:
    """
    Return the global settings, raising a clear error if configuration
    is invalid.  Prefer this over the bare `settings` import when you
    need guaranteed validity.
    """
    if settings is None:
        raise _init_error  # type: ignore[name-defined]
    return settings
