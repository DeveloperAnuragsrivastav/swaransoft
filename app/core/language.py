"""
Handles multi-language support:
- Detects what language the user typed (auto mode)
- Translates queries to English internally (so RAG/location logic
  only ever has to deal with one language)
- Translates the final answer back to the user's language

Uses deep-translator for retrieval queries and fixed location responses.
Groq generates other replies directly in the selected language.
"""
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator

# Makes langdetect's results consistent across runs (it's non-deterministic by default)
DetectorFactory.seed = 0

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "bn": "Bengali",
    "pa": "Punjabi",
}


def detect_language(text: str) -> str:
    """
    Returns a language code (e.g. 'en', 'hi'). Falls back to English
    if detection fails (e.g. text too short, or only an image was sent).
    """
    if not text or not text.strip():
        return "en"
    try:
        code = detect(text)
        return code if code in SUPPORTED_LANGUAGES else "en"
    except Exception:
        return "en"


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translates text between two language codes. No-op if they're the same."""
    if not text or source_lang == target_lang:
        return text
    try:
        return GoogleTranslator(source=source_lang, target=target_lang).translate(text)
    except Exception:
        # If translation fails (e.g. no internet), fall back to original text
        # rather than breaking the whole response.
        return text


def to_english(text: str, source_lang: str) -> str:
    return translate_text(text, source_lang, "en")


def from_english(text: str, target_lang: str) -> str:
    return translate_text(text, "en", target_lang)
