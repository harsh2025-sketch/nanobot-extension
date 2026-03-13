"""Multilingual language catalog for nanobot.

Covers all 22 official languages of India plus major world languages (~70 total).
Each entry: iso_code -> {name, native, region, script}
"""

from __future__ import annotations

# fmt: off
LANGUAGES: dict[str, dict[str, str]] = {
    # ─── India: 22 official (8th Schedule) + major regional ──────────────────
    "hi":  {"name": "Hindi",        "native": "हिंदी",           "script": "Devanagari",  "region": "India"},
    "bn":  {"name": "Bengali",      "native": "বাংলা",            "script": "Bengali",     "region": "India/Bangladesh"},
    "ta":  {"name": "Tamil",        "native": "தமிழ்",             "script": "Tamil",       "region": "India/SriLanka"},
    "te":  {"name": "Telugu",       "native": "తెలుగు",            "script": "Telugu",      "region": "India"},
    "mr":  {"name": "Marathi",      "native": "मराठी",             "script": "Devanagari",  "region": "India"},
    "gu":  {"name": "Gujarati",     "native": "ગુજરાતી",           "script": "Gujarati",    "region": "India"},
    "kn":  {"name": "Kannada",      "native": "ಕನ್ನಡ",             "script": "Kannada",     "region": "India"},
    "ml":  {"name": "Malayalam",    "native": "മലയാളം",            "script": "Malayalam",   "region": "India"},
    "pa":  {"name": "Punjabi",      "native": "ਪੰਜਾਬੀ",            "script": "Gurmukhi",    "region": "India/Pakistan"},
    "or":  {"name": "Odia",         "native": "ଓଡ଼ିଆ",             "script": "Odia",        "region": "India"},
    "as":  {"name": "Assamese",     "native": "অসমীয়া",            "script": "Bengali",     "region": "India"},
    "ur":  {"name": "Urdu",         "native": "اردو",              "script": "Nastaliq",    "region": "India/Pakistan"},
    "sa":  {"name": "Sanskrit",     "native": "संस्कृत",            "script": "Devanagari",  "region": "India"},
    "ne":  {"name": "Nepali",       "native": "नेपाली",             "script": "Devanagari",  "region": "India/Nepal"},
    "ks":  {"name": "Kashmiri",     "native": "کٲشُر",             "script": "Perso-Arabic","region": "India"},
    "sd":  {"name": "Sindhi",       "native": "سنڌي",              "script": "Perso-Arabic","region": "India/Pakistan"},
    "mai": {"name": "Maithili",     "native": "मैथिली",             "script": "Devanagari",  "region": "India"},
    "kok": {"name": "Konkani",      "native": "कोंकणी",             "script": "Devanagari",  "region": "India"},
    "doi": {"name": "Dogri",        "native": "डोगरी",              "script": "Devanagari",  "region": "India"},
    "mni": {"name": "Manipuri",     "native": "মৈতৈলোন্",           "script": "Meitei Mayek","region": "India"},
    "sat": {"name": "Santali",      "native": "ᱥᱟᱱᱛᱟᱲᱤ",         "script": "Ol Chiki",    "region": "India"},
    "brx": {"name": "Bodo",         "native": "बड़ो",               "script": "Devanagari",  "region": "India"},
    "si":  {"name": "Sinhala",      "native": "සිංහල",              "script": "Sinhala",     "region": "India/SriLanka"},
    # ─── World: Global / Continental languages ────────────────────────────────
    "en":  {"name": "English",      "native": "English",           "script": "Latin",       "region": "Global"},
    "es":  {"name": "Spanish",      "native": "Español",           "script": "Latin",       "region": "Global"},
    "fr":  {"name": "French",       "native": "Français",          "script": "Latin",       "region": "Global"},
    "de":  {"name": "German",       "native": "Deutsch",           "script": "Latin",       "region": "Europe"},
    "pt":  {"name": "Portuguese",   "native": "Português",         "script": "Latin",       "region": "Global"},
    "it":  {"name": "Italian",      "native": "Italiano",          "script": "Latin",       "region": "Europe"},
    "nl":  {"name": "Dutch",        "native": "Nederlands",        "script": "Latin",       "region": "Europe"},
    "pl":  {"name": "Polish",       "native": "Polski",            "script": "Latin",       "region": "Europe"},
    "cs":  {"name": "Czech",        "native": "Čeština",           "script": "Latin",       "region": "Europe"},
    "ro":  {"name": "Romanian",     "native": "Română",            "script": "Latin",       "region": "Europe"},
    "hu":  {"name": "Hungarian",    "native": "Magyar",            "script": "Latin",       "region": "Europe"},
    "sv":  {"name": "Swedish",      "native": "Svenska",           "script": "Latin",       "region": "Europe"},
    "da":  {"name": "Danish",       "native": "Dansk",             "script": "Latin",       "region": "Europe"},
    "fi":  {"name": "Finnish",      "native": "Suomi",             "script": "Latin",       "region": "Europe"},
    "no":  {"name": "Norwegian",    "native": "Norsk",             "script": "Latin",       "region": "Europe"},
    "ca":  {"name": "Catalan",      "native": "Català",            "script": "Latin",       "region": "Europe"},
    "ru":  {"name": "Russian",      "native": "Русский",           "script": "Cyrillic",    "region": "Eastern Europe/Asia"},
    "uk":  {"name": "Ukrainian",    "native": "Українська",        "script": "Cyrillic",    "region": "Europe"},
    "el":  {"name": "Greek",        "native": "Ελληνικά",          "script": "Greek",       "region": "Europe"},
    "tr":  {"name": "Turkish",      "native": "Türkçe",            "script": "Latin",       "region": "Europe/Asia"},
    "az":  {"name": "Azerbaijani",  "native": "Azərbaycan",        "script": "Latin",       "region": "Asia"},
    "kk":  {"name": "Kazakh",       "native": "Қазақ тілі",        "script": "Cyrillic",    "region": "Asia"},
    "uz":  {"name": "Uzbek",        "native": "O'zbek",            "script": "Latin",       "region": "Asia"},
    "mn":  {"name": "Mongolian",    "native": "Монгол",            "script": "Cyrillic",    "region": "Asia"},
    "zh":  {"name": "Chinese",      "native": "中文",               "script": "Han",         "region": "Asia"},
    "ja":  {"name": "Japanese",     "native": "日本語",              "script": "Kana+Han",    "region": "Asia"},
    "ko":  {"name": "Korean",       "native": "한국어",              "script": "Hangul",      "region": "Asia"},
    "vi":  {"name": "Vietnamese",   "native": "Tiếng Việt",        "script": "Latin",       "region": "Asia"},
    "th":  {"name": "Thai",         "native": "ภาษาไทย",            "script": "Thai",        "region": "Asia"},
    "id":  {"name": "Indonesian",   "native": "Bahasa Indonesia",  "script": "Latin",       "region": "Asia"},
    "ms":  {"name": "Malay",        "native": "Bahasa Melayu",     "script": "Latin",       "region": "Asia"},
    "tl":  {"name": "Filipino",     "native": "Filipino",          "script": "Latin",       "region": "Asia"},
    "my":  {"name": "Burmese",      "native": "မြန်မာဘာသာ",        "script": "Myanmar",     "region": "Asia"},
    "km":  {"name": "Khmer",        "native": "ភាសាខ្មែរ",          "script": "Khmer",       "region": "Asia"},
    "lo":  {"name": "Lao",          "native": "ພາສາລາວ",            "script": "Lao",         "region": "Asia"},
    "bo":  {"name": "Tibetan",      "native": "བོད་ཡིག",             "script": "Tibetan",     "region": "Asia"},
    "ar":  {"name": "Arabic",       "native": "العربية",            "script": "Arabic",      "region": "Middle East/Africa"},
    "fa":  {"name": "Persian",      "native": "فارسی",              "script": "Perso-Arabic","region": "Middle East"},
    "he":  {"name": "Hebrew",       "native": "עברית",              "script": "Hebrew",      "region": "Middle East"},
    "am":  {"name": "Amharic",      "native": "አማርኛ",              "script": "Ethiopic",    "region": "Africa"},
    "sw":  {"name": "Swahili",      "native": "Kiswahili",         "script": "Latin",       "region": "Africa"},
    "ha":  {"name": "Hausa",        "native": "Hausa",             "script": "Latin",       "region": "Africa"},
    "yo":  {"name": "Yoruba",       "native": "Yorùbá",            "script": "Latin",       "region": "Africa"},
    "zu":  {"name": "Zulu",         "native": "isiZulu",           "script": "Latin",       "region": "Africa"},
}
# fmt: on

# Convenient sub-sets
INDIA_LANGUAGES: dict[str, dict[str, str]] = {
    k: v for k, v in LANGUAGES.items() if "India" in v.get("region", "")
}

WORLD_LANGUAGES: dict[str, dict[str, str]] = LANGUAGES


def get_display_name(code: str) -> str:
    """Return 'English (Native)' display string for a language code."""
    lang = LANGUAGES.get(code)
    if not lang:
        return code
    name, native = lang["name"], lang["native"]
    return name if name == native else f"{name} ({native})"


def build_language_list_text() -> str:
    """Build a compact one-liner list of all supported languages for system prompt injection."""
    india = ", ".join(
        f"{v['name']} ({v['native']})" for v in INDIA_LANGUAGES.values()
    )
    world_only = {k: v for k, v in LANGUAGES.items() if k not in INDIA_LANGUAGES}
    world = ", ".join(f"{v['name']} ({v['native']})" for v in world_only.values())
    return (
        f"**Indian languages:** {india}\n\n"
        f"**World languages:** {world}"
    )
