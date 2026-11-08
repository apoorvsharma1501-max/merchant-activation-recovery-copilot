"""A scripted stand-in for the Anthropic API so AI paths are tested without a key or cost."""
from __future__ import annotations

from collections.abc import Callable

from core.llm_client import CachedLLM, LLMResult


class FakeLLM:
    model = "fake-model"

    def __init__(self, responder: Callable[[str, str, dict], dict | LLMResult | None]):
        self.responder = responder
        self.prompts: list[str] = []

    def complete_json(self, system: str, user: str, schema: dict, effort: str) -> LLMResult:
        self.prompts.append(user)
        out = self.responder(system, user, schema)
        if isinstance(out, LLMResult):
            return out
        if out is None:
            return LLMResult(None, "invalid_json", self.model, "not json")
        return LLMResult(out, "ok", self.model, usage={"input_tokens": 10, "output_tokens": 5})


def cached(fake: FakeLLM, tmp_path) -> CachedLLM:
    return CachedLLM(inner=fake, mode="live", cache_path=tmp_path / "cache.json")


def diag(code, quote, sensitive=False, review=False, explanation="test"):
    return {"diagnosed_reason_code": code, "evidence_quote": quote, "explanation": explanation,
            "needs_human_review": review, "sensitive_case": sensitive}


def nudge(message, back=None):
    return {"message": message, "english_back_translation": back if back is not None else message}
