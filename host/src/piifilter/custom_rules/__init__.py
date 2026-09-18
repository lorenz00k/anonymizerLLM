"""
Oeffentliche Schnittstelle fuer alle Custom-Rules-Funktionen.
Andere Module importieren ausschliesslich von hier
(from piifilter.custom_rules import ...), nie direkt aus den
Untermodulen - so bleibt die interne Aufteilung frei aenderbar.
"""
from piifilter.custom_rules.storage import load_rules_raw, save_rules
from piifilter.custom_rules.global_rules import add_global_rule, remove_global_rule
from piifilter.custom_rules.folders import (
    add_folder,
    delete_folder,
    set_folder_enabled,
    add_folder_rule,
    remove_folder_rule,
)
from piifilter.custom_rules.chats import add_chat_rule, remove_chat_rule, set_chat_label
from piifilter.custom_rules.effective import get_effective_rules


# ---- Abwaertskompatibilitaet (alte Rules-UI/Popup nutzen diese Namen) ----

def load_rules() -> dict:
    """Nur die globale Ebene, im alten flachen Format."""
    return load_rules_raw()["global"]


def add_rule(original: str, fake_value: str) -> None:
    add_global_rule(original, fake_value)


def remove_rule(original: str) -> None:
    remove_global_rule(original)


__all__ = [
    "load_rules_raw",
    "save_rules",
    "add_global_rule",
    "remove_global_rule",
    "add_folder",
    "delete_folder",
    "set_folder_enabled",
    "add_folder_rule",
    "remove_folder_rule",
    "add_chat_rule",
    "remove_chat_rule",
    "set_chat_label",
    "get_effective_rules",
    "load_rules",
    "add_rule",
    "remove_rule",
]