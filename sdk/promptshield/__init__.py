"""
PromptShield SDK — protect any LLM call from prompt injection in 2 lines.

Usage:
    from promptshield import shield, InjectionDetected

    @shield
    def ask_gpt(user_message: str) -> str:
        # ... call OpenAI / Claude / Gemini here
        return response

    # Or with custom config:
    @shield(api_url="http://localhost:8000", api_key="secret", block=True, timeout=2.0)
    def ask_claude(user_message: str) -> str:
        ...
"""

import os
import functools
import inspect
import logging
from typing import Any, Callable, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_API_URL = os.getenv("PROMPTSHIELD_API_URL", "http://localhost:8000")
_DEFAULT_API_KEY = os.getenv("PROMPTSHIELD_API_KEY", "")
_DEFAULT_TIMEOUT = float(os.getenv("PROMPTSHIELD_TIMEOUT", "2.0"))
_DEFAULT_BLOCK = os.getenv("PROMPTSHIELD_BLOCK", "true").lower() != "false"


class InjectionDetected(Exception):
    """Raised by @shield when a prompt injection attack is detected (block=True)."""

    def __init__(self, message: str, event_id: str, category: str, severity: str, rule: str):
        super().__init__(message)
        self.event_id = event_id
        self.category = category
        self.severity = severity
        self.rule = rule

    def __repr__(self) -> str:
        return (
            f"InjectionDetected(event_id={self.event_id!r}, "
            f"category={self.category!r}, severity={self.severity!r}, rule={self.rule!r})"
        )


def _scan(prompt: str, api_url: str, api_key: str, timeout: float, app_id: Optional[str]) -> dict:
    """
    Call POST /scan synchronously.
    Returns the parsed JSON response.
    Raises httpx exceptions on network failure — caller handles fail-open logic.
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    payload: dict[str, Any] = {"prompt": prompt}
    if app_id:
        payload["app_id"] = app_id

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{api_url.rstrip('/')}/scan", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


def shield(
    func: Optional[Callable] = None,
    *,
    api_url: str = _DEFAULT_API_URL,
    api_key: str = _DEFAULT_API_KEY,
    timeout: float = _DEFAULT_TIMEOUT,
    block: bool = _DEFAULT_BLOCK,
    app_id: Optional[str] = None,
    prompt_arg: Optional[str] = None,
):
    """
    Decorator that scans the first string argument (or `prompt_arg` kwarg name)
    before passing it to the wrapped function.

    Parameters
    ----------
    api_url   : URL of the PromptShield API (default: PROMPTSHIELD_API_URL env var)
    api_key   : X-API-Key value (default: PROMPTSHIELD_API_KEY env var)
    timeout   : Hard timeout in seconds for the scan request (default: 2.0)
    block     : If True, raise InjectionDetected on BLOCK verdict.
                If False, log a warning but call the underlying function anyway.
    app_id    : Optional application identifier attached to scan events.
    prompt_arg: Name of the parameter holding the user message. Auto-detected
                if omitted (first str positional arg).
    """

    def decorator(fn: Callable) -> Callable:
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())

        def _get_prompt(args, kwargs) -> Optional[str]:
            # Explicit kwarg name takes priority
            if prompt_arg and prompt_arg in kwargs:
                return str(kwargs[prompt_arg])
            # Check positional args
            for i, val in enumerate(args):
                if isinstance(val, str):
                    return val
            # Check kwargs by position order
            for name in param_names:
                if name in kwargs and isinstance(kwargs[name], str):
                    return kwargs[name]
            return None

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            prompt = _get_prompt(args, kwargs)
            if prompt is None:
                # No string argument found — skip scan, call through
                return fn(*args, **kwargs)

            try:
                result = _scan(prompt, api_url, api_key, timeout, app_id)
                verdict = result.get("verdict", "ALLOW")

                if verdict == "BLOCK":
                    matched = result.get("matched_rule") or {}
                    msg = (
                        f"Prompt injection detected — "
                        f"category={result.get('category')}, "
                        f"severity={result.get('severity')}, "
                        f"rule={matched.get('rule_id', 'unknown')}"
                    )
                    logger.warning("PromptShield BLOCK | event_id=%s | %s", result.get("event_id"), msg)

                    if block:
                        raise InjectionDetected(
                            message=msg,
                            event_id=result.get("event_id", ""),
                            category=result.get("category", ""),
                            severity=result.get("severity", ""),
                            rule=matched.get("rule_id", ""),
                        )
                else:
                    logger.debug("PromptShield ALLOW | event_id=%s", result.get("event_id"))

            except InjectionDetected:
                raise
            except Exception as e:
                # Fail-open: network error, timeout, or unexpected exception
                logger.warning("PromptShield scan failed (fail-open): %s", e)

            return fn(*args, **kwargs)

        return wrapper

    # Support both @shield and @shield(...) usage
    if func is not None:
        return decorator(func)
    return decorator
