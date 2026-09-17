"""
Nutzerdefinierte Begriffe, die immer als sensibel gelten sollen -
unabhaengig davon, ob Presidio/Regex sie erkennen wuerden.
"""
import json
from pathlib import Path

RULES_FILE = Path.home() / ".piifilter" / "custom_rules.json"


def load_rules() -> dict[str, str]:
    """Gibt {Originalbegriff: Fake-Wert} zurueck."""
    if not RULES_FILE.exists():
        return {}
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))


def save_rules(rules: dict[str, str]) -> None:
    RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    RULES_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


def add_rule(original: str, fake_value: str) -> None:
    rules = load_rules()
    rules[original] = fake_value
    save_rules(rules)


def remove_rule(original: str) -> None:
    rules = load_rules()
    rules.pop(original, None)
    save_rules(rules)