from langdetect import DetectorFactory, detect_langs

from . import DEFAULT_LANG, LANGUAGES

DetectorFactory.seed = 0  # deterministische Ergebnisse


def detect_language(
    text: str, default: str = DEFAULT_LANG, min_chars: int = 20, min_prob: float = 0.8
) -> str:
    if len(text.strip()) < min_chars:
        return default
    try:
        best = detect_langs(text)[0]
    except Exception:
        return default
    if best.prob < min_prob or best.lang not in LANGUAGES:
        return default
    return best.lang
