"""
Gemeinsame JSON-Persistenz fuer alle drei Regel-Ebenen.
Liegt bewusst ausserhalb des Repos unter ~/.piifilter/, damit die
Regeln Neuinstallationen ueberleben.
"""
import json
from pathlib import Path

RULES_PATH = Path.home() / ".piifilter" / "custom_rules.json"


def load_rules_raw() -> dict:
    """Laedt die komplette Regelstruktur (alle drei Ebenen)."""
    if not RULES_PATH.exists():
        return {"global": {}, "folders": {}, "chats": {}}

    with open(RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    data.setdefault("global", {})
    data.setdefault("folders", {})
    data.setdefault("chats", {})
    return data


def save_rules(data: dict) -> None:
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)