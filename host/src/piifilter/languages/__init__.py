from .base import LanguageConfig
from .de import GERMAN
from .en import ENGLISH

DEFAULT_LANG = "de"
LANGUAGES: dict[str, LanguageConfig] = {c.lang_code: c for c in (GERMAN, ENGLISH)}


def get_language(lang_code: str | None) -> LanguageConfig:
    """Unbekannte oder fehlende Codes fallen auf Deutsch zurück."""
    return LANGUAGES.get(lang_code or DEFAULT_LANG, LANGUAGES[DEFAULT_LANG])