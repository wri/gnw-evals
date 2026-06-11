import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

_ANTHROPIC_MODEL = "claude-haiku-4-5"
_GEMINI_MODEL = "gemini-3.1-pro-preview"


def _use_anthropic_judge() -> bool:
    provider = os.getenv("EVAL_JUDGE_LLM", "gemini").strip().lower()
    if provider not in {"anthropic", "gemini"}:
        msg = f"Unknown EVAL_JUDGE_LLM={provider!r}. Use 'gemini' (default) or 'anthropic'."
        raise ValueError(msg)
    return provider == "anthropic"


@lru_cache(maxsize=1)
def get_judge_llm() -> BaseChatModel:
    """Return the LLM used for eval judges (default: Gemini Pro)."""
    if _use_anthropic_judge():
        return ChatAnthropic(model=_ANTHROPIC_MODEL, temperature=0, max_tokens=8_192)
    return ChatGoogleGenerativeAI(model=_GEMINI_MODEL, temperature=0)


def get_eval_judge_llm_label() -> str:
    """Return the LLM family and model used by eval judges in this repo."""
    if _use_anthropic_judge():
        return f"Anthropic / {_ANTHROPIC_MODEL}"
    return f"Google / {_GEMINI_MODEL}"
