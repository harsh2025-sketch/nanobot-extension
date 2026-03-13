"""nanobot.i18n â€” multilingual support for Indian and world languages.

Usage::

    from nanobot.i18n import detect_language, LANGUAGES, get_display_name

    lang = detect_language("à¤¨à¤®à¤¸à¥à¤¤à¥‡, à¤†à¤ª à¤•à¥ˆà¤¸à¥‡ à¤¹à¥ˆà¤‚?")  # â†’ "hi"
    lang = detect_language("Hello world")             # â†’ "en"
    lang = detect_language("ã“ã‚“ã«ã¡ã¯")               # â†’ "ja"
    print(get_display_name("hi"))                      # â†’ "Hindi (à¤¹à¤¿à¤‚à¤¦à¥€)"
"""

from nanobot.i18n.detector import detect_language, detect_script_language
from nanobot.i18n.languages import (
    INDIA_LANGUAGES,
    LANGUAGES,
    WORLD_LANGUAGES,
    build_language_list_text,
    get_display_name,
)

__all__ = [
    "detect_language",
    "detect_script_language",
    "LANGUAGES",
    "INDIA_LANGUAGES",
    "WORLD_LANGUAGES",
    "get_display_name",
    "build_language_list_text",
]
