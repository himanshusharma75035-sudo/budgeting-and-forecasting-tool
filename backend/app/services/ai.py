"""Optional AI enrichment (disabled by default).

The core product is deterministic and offline. When AI is explicitly enabled
(``OPENFPA_AI_ENABLED=true`` + ``OPENFPA_ANTHROPIC_API_KEY`` + the ``[ai]`` extra), narratives can
be polished by Claude. Everything here degrades gracefully: if AI is off, the SDK is not installed,
or a call fails, the functions return ``None`` and callers fall back to the deterministic text — so
this module never breaks an offline install.
"""

from __future__ import annotations

from app.config import settings


def ai_available() -> bool:
    """True only if AI is enabled in settings and an API key is configured."""
    return settings.ai_enabled and bool(settings.anthropic_api_key)


def enrich_narrative(deterministic: str, *, instruction: str | None = None) -> str | None:
    """Return an LLM-polished narrative, or ``None`` if AI is unavailable or the call fails."""
    if not ai_available():
        return None
    try:
        import anthropic  # optional dependency, imported lazily
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = (
            "You are an FP&A analyst writing board commentary. Rewrite the variance commentary below "
            "as a concise, executive-ready paragraph (max 5 sentences). Keep every figure exactly as "
            "given — do not invent or recompute numbers.\n\n"
            f"{instruction or ''}\n\nCommentary:\n{deterministic}"
        )
        message = client.messages.create(
            model=settings.ai_model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        return text.strip() or None
    except Exception:  # network/SDK/runtime errors must never break the endpoint
        return None
