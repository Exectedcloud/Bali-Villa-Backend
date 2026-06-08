import hashlib

import deepl
from django.conf import settings
from django.core.cache import cache

_translator = None


def _get_translator() -> deepl.Translator:
    global _translator
    if _translator is None:
        _translator = deepl.Translator(settings.DEEPL_API_KEY)
    return _translator


def translate(text: str, target_lang: str, source_lang: str = None) -> str:
    """Translate text via DeepL. Results cached by content hash for 30 days.

    target_lang: 'ZH' for Chinese Simplified, 'EN-US' for English.
    Returns original text on any error (empty key, network failure, quota).
    """
    if not text or not text.strip():
        return ""

    cache_key = f"tx:{hashlib.sha1(f'{text}|{target_lang}'.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        result = _get_translator().translate_text(
            text,
            target_lang=target_lang,
            source_lang=source_lang,
        )
        cache.set(cache_key, result.text, timeout=60 * 60 * 24 * 30)
        return result.text
    except Exception:
        return text
