import hashlib

import deepl
from django.conf import settings
from django.core.cache import cache

_translator = None

# Internal DeepL language codes for each app language key
DEEPL_LANG: dict = {
    'zh': 'ZH',
    'en': 'EN-US',
    'id': 'ID',
}

ALL_LANGS: tuple = ('zh', 'en', 'id')


def _get_translator() -> deepl.Translator:
    global _translator
    if _translator is None:
        _translator = deepl.Translator(settings.DEEPL_API_KEY)
    return _translator


def translate(text: str, target_lang: str, source_lang: str = None) -> str:
    """Translate text via DeepL. Results cached by content hash for 30 days.

    target_lang: DeepL code — 'ZH', 'EN-US', or 'ID'.
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


def translate_to_all(text: str, source_lang: str) -> dict:
    """Translate text from source_lang to all supported languages (zh, en, id).

    Returns {lang: translated_text} where source_lang entry = original unchanged.
    Each language pair is independently cached, so repeat calls are free.
    Falls back to original text on DeepL error for any individual language.
    """
    if not text or not text.strip():
        return {lang: '' for lang in ALL_LANGS}

    source_deepl = DEEPL_LANG.get(source_lang)
    result = {}
    for lang in ALL_LANGS:
        if lang == source_lang:
            result[lang] = text
        else:
            result[lang] = translate(text, DEEPL_LANG[lang], source_deepl)
    return result
