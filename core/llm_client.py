"""LLM access with a reproducibility cache.

Every response is stored in `cache/llm_cache.json`, keyed by a hash of
(model, effort, system prompt, user prompt, schema). Re-running the pipeline
returns the stored answer instead of calling the API, so results are reproducible
and the cache can be shipped with the submission.

Modes:
  live  - use cache, call the API on a miss (needs ANTHROPIC_API_KEY)
  cache - use cache only; a miss returns "unavailable" (no key needed)
  off   - never use AI (rule-only)
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import config


@dataclass
class LLMResult:
    data: dict | None
    status: str  # ok | refusal | error | unavailable | invalid_json
    model: str
    detail: str = ""
    from_cache: bool = False
    usage: dict = field(default_factory=dict)


class LLM(Protocol):
    model: str

    def complete_json(self, system: str, user: str, schema: dict, effort: str) -> LLMResult: ...


class AnthropicLLM:
    """Thin wrapper over the Anthropic Messages API with JSON-schema structured output."""

    def __init__(self, model: str = config.LLM_MODEL, use_fallback: bool = config.LLM_USE_REFUSAL_FALLBACK):
        import anthropic  # imported lazily so rule-only mode needs no SDK

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
        self.model = model
        self.use_fallback = use_fallback

    def complete_json(self, system: str, user: str, schema: dict, effort: str) -> LLMResult:
        a = self._anthropic
        kwargs = dict(
            model=self.model,
            max_tokens=config.LLM_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
        try:
            if self.use_fallback:
                resp = self.client.beta.messages.create(
                    **kwargs, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
            else:
                resp = self.client.messages.create(**kwargs)
        except a.AuthenticationError as e:
            raise LLMUnavailableError(f"Authentication failed: {e.message}") from e
        except a.PermissionDeniedError as e:
            raise LLMUnavailableError(f"Permission denied: {e.message}") from e
        except a.BadRequestError as e:
            return LLMResult(None, "error", self.model, f"Bad request: {e.message}")
        except a.RateLimitError as e:
            return LLMResult(None, "error", self.model, "Rate limited after SDK retries")
        except a.APIStatusError as e:
            return LLMResult(None, "error", self.model, f"API error {e.status_code}")
        except a.APIConnectionError:
            return LLMResult(None, "error", self.model, "Network error")

        served = getattr(resp, "model", self.model)
        usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
        if resp.stop_reason == "refusal":
            return LLMResult(None, "refusal", served, "Model declined the request")
        if resp.stop_reason == "max_tokens":
            return LLMResult(None, "error", served, "Response hit max_tokens")
        text = next((b.text for b in resp.content if b.type == "text"), None)
        try:
            data = json.loads(text) if text else None
        except json.JSONDecodeError:
            return LLMResult(None, "invalid_json", served, (text or "")[:200])
        if not isinstance(data, dict):
            return LLMResult(None, "invalid_json", served, "Top-level JSON is not an object")
        return LLMResult(data, "ok", served, usage=usage)


class LLMUnavailableError(Exception):
    """Credentials missing/invalid: stop calling the API for the rest of the run."""


@dataclass
class CachedLLM:
    """Wraps an LLM (or nothing) with the on-disk cache and usage accounting."""

    inner: LLM | None
    mode: str = "live"
    cache_path: Path = config.LLM_CACHE_FILE
    model: str = config.LLM_MODEL
    calls: int = 0
    cache_hits: int = 0
    misses_unavailable: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    disabled_reason: str | None = None
    _cache: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.inner is not None:
            self.model = self.inner.model
        if self.cache_path.exists():
            self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))

    @property
    def enabled(self) -> bool:
        return self.mode != "off"

    def _key(self, system: str, user: str, schema: dict, effort: str) -> str:
        blob = json.dumps({"model": self.model, "effort": effort, "system": system,
                           "user": user, "schema": schema}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def complete_json(self, system: str, user: str, schema: dict, effort: str) -> LLMResult:
        if self.mode == "off":
            return LLMResult(None, "unavailable", "RULE_ONLY", "AI disabled (rule-only mode)")
        key = self._key(system, user, schema, effort)
        if key in self._cache:
            entry = self._cache[key]
            self.cache_hits += 1
            return LLMResult(entry["data"], "ok", entry["model"], "cached", from_cache=True)
        if self.mode == "cache" or self.inner is None or self.disabled_reason:
            self.misses_unavailable += 1
            reason = self.disabled_reason or "No cached answer and live AI calls are off"
            return LLMResult(None, "unavailable", self.model, reason)
        try:
            result = self.inner.complete_json(system, user, schema, effort)
        except LLMUnavailableError as e:
            self.disabled_reason = str(e)
            self.misses_unavailable += 1
            return LLMResult(None, "unavailable", self.model, str(e))
        self.calls += 1
        if result.status == "ok":
            usage = result.usage
            self.input_tokens += usage.get("input_tokens", 0)
            self.output_tokens += usage.get("output_tokens", 0)
            self._cache[key] = {
                "model": result.model, "effort": effort, "data": result.data, "usage": usage,
                "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "user_prompt": user,
            }
        return result

    def save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._cache, indent=2, ensure_ascii=False, sort_keys=True),
                                   encoding="utf-8")

    def usage_summary(self) -> dict:
        return {"mode": self.mode, "model": self.model, "api_calls": self.calls,
                "cache_hits": self.cache_hits, "unavailable": self.misses_unavailable,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "disabled_reason": self.disabled_reason}


def build_llm(mode: str | None = None) -> CachedLLM:
    """Pick a mode: explicit, else live when a key is configured, else cache-only."""
    if mode is None:
        mode = "live" if os.environ.get("ANTHROPIC_API_KEY") else "cache"
    if mode not in {"live", "cache", "off"}:
        raise ValueError(f"Unknown LLM mode {mode!r}")
    inner = AnthropicLLM() if mode == "live" else None
    return CachedLLM(inner=inner, mode=mode)


def load_prompt(name: str) -> str:
    return (config.PROMPTS_DIR / name).read_text(encoding="utf-8").strip()
