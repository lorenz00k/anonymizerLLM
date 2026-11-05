from piifilter.languages import DEFAULT_LANG
from piifilter.languages.detect import detect_language


class ChatLanguages:
    """Merkt sich pro Chat die zuletzt erkannte Sprache."""

    def __init__(self):
        self._by_chat: dict = {}

    def resolve(self, chat_id, text: str, override: str | None = None) -> str:
        default = self._by_chat.get(chat_id, DEFAULT_LANG)
        lang = override or detect_language(text, default=default)
        self._by_chat[chat_id] = lang
        return lang

    def get(self, chat_id) -> str:
        return self._by_chat.get(chat_id, DEFAULT_LANG)


chat_languages = ChatLanguages()