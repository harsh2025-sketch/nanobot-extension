"""Fast language detection using Unicode script ranges.

Primary strategy: count codepoints per Unicode block to identify the dominant script.
Secondary strategy: optional `langdetect` library for Latin-script disambiguation.
No required external dependencies.
"""

from __future__ import annotations

# Unicode block ranges → (language code, weight).
# Ordered so that unambiguous single-language blocks appear first.
_SCRIPT_BLOCKS: list[tuple[int, int, str]] = [
    # ── Indian scripts ────────────────────────────────────────────
    (0x0900, 0x097F, "hi"),   # Devanagari → Hindi (most spoken Devanagari lang)
    (0x0980, 0x09FF, "bn"),   # Bengali / Assamese
    (0x0A00, 0x0A7F, "pa"),   # Gurmukhi → Punjabi
    (0x0A80, 0x0AFF, "gu"),   # Gujarati
    (0x0B00, 0x0B7F, "or"),   # Odia
    (0x0B80, 0x0BFF, "ta"),   # Tamil
    (0x0C00, 0x0C7F, "te"),   # Telugu
    (0x0C80, 0x0CFF, "kn"),   # Kannada
    (0x0D00, 0x0D7F, "ml"),   # Malayalam
    (0x0D80, 0x0DFF, "si"),   # Sinhala
    (0x1C50, 0x1C7F, "sat"),  # Ol Chiki → Santali
    # ── Southeast / East Asia ─────────────────────────────────────
    (0x0E00, 0x0E7F, "th"),   # Thai
    (0x0E80, 0x0EFF, "lo"),   # Lao
    (0x0F00, 0x0FFF, "bo"),   # Tibetan
    (0x1000, 0x109F, "my"),   # Myanmar/Burmese
    (0x1780, 0x17FF, "km"),   # Khmer
    (0x3040, 0x309F, "ja"),   # Hiragana → Japanese
    (0x30A0, 0x30FF, "ja"),   # Katakana → Japanese
    (0xAC00, 0xD7AF, "ko"),   # Hangul → Korean
    # ── Middle East ───────────────────────────────────────────────
    (0x0590, 0x05FF, "he"),   # Hebrew
    (0x0600, 0x06FF, "ar"),   # Arabic (also Urdu/Persian/Sindhi — refined below)
    # ── Africa ────────────────────────────────────────────────────
    (0x1200, 0x137F, "am"),   # Ethiopic → Amharic
    # ── Europe ────────────────────────────────────────────────────
    (0x0400, 0x04FF, "ru"),   # Cyrillic → Russian (most spoken; refined below)
    (0x0370, 0x03FF, "el"),   # Greek
]

# Within Arabic script, short common words identify the actual language.
_ARABIC_WORD_HINTS: dict[str, str] = {
    "ہے": "ur",    # Urdu copula
    "ہیں": "ur",   # Urdu plural copula
    "کا": "ur",    # Urdu possessive
    "است": "fa",   # Persian "is"
    "نیست": "fa",  # Persian "is not"
    "آهي": "sd",   # Sindhi copula
}

# Within Cyrillic script, common words to separate Slavic languages.
_CYRILLIC_WORD_HINTS: dict[str, str] = {
    "і": "uk",    # Ukrainian unique letter
    "є": "uk",    # Ukrainian unique letter
    "ї": "uk",    # Ukrainian unique letter
}


def _count_block(text: str, lo: int, hi: int) -> int:
    return sum(1 for ch in text if lo <= ord(ch) <= hi)


def detect_script_language(text: str) -> str | None:
    """
    Return an ISO language code based on dominant Unicode script, or None
    if the text is primarily Latin/ASCII (inconclusive for specific language).
    """
    if not text or len(text.strip()) < 2:
        return None

    counts: dict[str, int] = {}

    for lo, hi, lang in _SCRIPT_BLOCKS:
        n = _count_block(text, lo, hi)
        if n:
            counts[lang] = counts.get(lang, 0) + n

    # CJK Unified Ideographs — Chinese unless Japanese kana was already found
    cjk = _count_block(text, 0x4E00, 0x9FFF) + _count_block(text, 0x3400, 0x4DBF)
    if cjk:
        if counts.get("ja", 0) > 0:
            counts["ja"] += cjk
        else:
            counts["zh"] = counts.get("zh", 0) + cjk

    if not counts:
        return None  # All ASCII / Latin — let langdetect handle it

    winner = max(counts, key=lambda k: counts[k])

    # Refine ambiguous scripts
    if winner == "ar":
        for hint, lang in _ARABIC_WORD_HINTS.items():
            if hint in text:
                return lang

    if winner == "ru":
        for hint, lang in _CYRILLIC_WORD_HINTS.items():
            if hint in text:
                return lang

    return winner


def detect_language(text: str, default: str = "en") -> str:
    """
    Detect the language of *text*.

    1. Unicode script detection (no dependencies, fast).
    2. Falls back to ``langdetect`` library for Latin-script text.
    3. Returns *default* if everything fails.
    """
    if not text or not text.strip():
        return default

    script_lang = detect_script_language(text)
    if script_lang:
        return script_lang

    # Latin-script: try langdetect (optional dependency)
    try:
        from langdetect import detect as _ld  # type: ignore[import]
        result = _ld(text)
        if result:
            return result
    except Exception:
        pass

    return default
