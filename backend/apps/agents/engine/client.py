"""
OpenAI Client — Centralized, token-budgeted, retrying OpenAI API wrapper.
All agent LLM calls go through here.
"""
import json
import logging
import time
from typing import Any
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger("apps.agents")

_client = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


class LLMResponse:
    def __init__(self, content: str, parsed: dict, usage: dict, model: str, duration_ms: int):
        self.content = content
        self.parsed = parsed
        self.usage = usage
        self.model = model
        self.duration_ms = duration_ms
        self.prompt_tokens = usage.get("prompt_tokens", 0)
        self.completion_tokens = usage.get("completion_tokens", 0)
        self.total_tokens = usage.get("total_tokens", 0)


def call_llm(
    system_prompt: str,
    user_message: str,
    company,
    model: str = None,
    max_tokens: int = None,
    temperature: float = 0.3,
    response_schema: dict = None,
) -> LLMResponse:
    """
    Make a single LLM call with:
    - Automatic model selection (heavy vs light)
    - Company token budget enforcement
    - JSON output enforcement
    - Retry on transient errors
    - Token usage tracking
    """
    model = model or settings.OPENAI_MODEL_LIGHT
    max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS_DEFAULT

    # Check company token budget
    if not company.token_budget_remaining:
        raise BudgetExhaustedError(
            f"Company {company.name} has exhausted its daily token budget."
        )

    client = get_openai_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    # Enforce JSON output
    if response_schema:
        kwargs["response_format"] = {"type": "json_object"}

    start = time.time()
    last_error = None

    for attempt in range(3):
        try:
            response = client.chat.completions.create(**kwargs)
            break
        except Exception as e:
            last_error = e
            logger.warning("OpenAI call attempt %d failed: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(2 ** attempt)
    else:
        raise LLMCallError(f"OpenAI call failed after 3 attempts: {last_error}") from last_error

    duration_ms = int((time.time() - start) * 1000)
    content = response.choices[0].message.content or ""
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }

    # Deduct tokens from company budget
    company.consume_tokens(usage["total_tokens"])

    # Parse JSON
    parsed = {}
    if response_schema or content.strip().startswith("{"):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON content despite json_object mode.")

    logger.info(
        "LLM call | model=%s | tokens=%d | duration=%dms | company=%s",
        model,
        usage["total_tokens"],
        duration_ms,
        company.name,
    )

    return LLMResponse(
        content=content,
        parsed=parsed,
        usage=usage,
        model=model,
        duration_ms=duration_ms,
    )


class BudgetExhaustedError(Exception):
    pass


class LLMCallError(Exception):
    pass
