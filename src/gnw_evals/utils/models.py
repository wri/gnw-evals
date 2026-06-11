import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

_ANTHROPIC_MODEL = "claude-haiku-4-5"
_GEMINI_MODEL = "gemini-3.1-pro-preview"

_ANTHROPIC_PROVIDERS = frozenset({"anthropic", "haiku", "claude"})
_GEMINI_PROVIDERS = frozenset({"gemini", "google"})


def _resolve_judge_provider() -> str:
    return os.getenv("EVAL_JUDGE_LLM", "gemini").strip().lower()


@lru_cache(maxsize=1)
def _get_anthropic_judge_llm() -> BaseChatModel:
    return ChatAnthropic(
        model=_ANTHROPIC_MODEL,
        temperature=0,
        max_tokens=8_192,
    )


@lru_cache(maxsize=1)
def _get_gemini_judge_llm() -> BaseChatModel:
    return ChatGoogleGenerativeAI(
        model=_GEMINI_MODEL,
        temperature=0,
    )


def get_judge_llm() -> BaseChatModel:
    """Return the LLM used for eval judges (default: Gemini Pro)."""
    provider = _resolve_judge_provider()
    if provider in _ANTHROPIC_PROVIDERS:
        return _get_anthropic_judge_llm()
    if provider in _GEMINI_PROVIDERS:
        return _get_gemini_judge_llm()
    msg = f"Unknown EVAL_JUDGE_LLM={provider!r}. Use 'gemini' (default) or 'anthropic'."
    raise ValueError(msg)


def get_eval_judge_llm_label() -> str:
    """Return the LLM family and model used by eval judges in this repo."""
    provider = _resolve_judge_provider()
    if provider in _ANTHROPIC_PROVIDERS:
        return f"Anthropic / {_ANTHROPIC_MODEL}"
    return f"Google / {_GEMINI_MODEL}"
