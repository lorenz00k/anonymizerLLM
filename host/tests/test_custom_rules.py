"""Tests fuer die Custom-Rules-Stufe (Stufe 1): Prioritaet der drei Ebenen."""

import pytest

from piifilter.custom_rules import effective


@pytest.fixture
def set_rules(monkeypatch):
    """Ersetzt das Laden der Regeldatei, damit ~/.piifilter nie angefasst wird."""

    def _set(data: dict) -> None:
        data.setdefault("global", {})
        data.setdefault("folders", {})
        data.setdefault("chats", {})
        monkeypatch.setattr(effective, "load_rules_raw", lambda: data)

    return _set


def test_global_rules_are_returned(set_rules):
    set_rules({"global": {"Phoenix": "Projekt X"}})
    assert effective.get_effective_rules() == {"Phoenix": "Projekt X"}


def test_enabled_folder_overrides_global(set_rules):
    set_rules(
        {
            "global": {"Phoenix": "global"},
            "folders": {"f1": {"enabled": True, "rules": {"Phoenix": "ordner"}}},
        }
    )
    assert effective.get_effective_rules()["Phoenix"] == "ordner"


def test_disabled_folder_is_ignored(set_rules):
    set_rules(
        {
            "global": {"Phoenix": "global"},
            "folders": {"f1": {"enabled": False, "rules": {"Phoenix": "ordner"}}},
        }
    )
    assert effective.get_effective_rules()["Phoenix"] == "global"


def test_chat_rule_has_highest_priority(set_rules):
    set_rules(
        {
            "global": {"Phoenix": "global"},
            "folders": {"f1": {"enabled": True, "rules": {"Phoenix": "ordner"}}},
            "chats": {"chat-1": {"rules": {"Phoenix": "chat"}}},
        }
    )
    assert effective.get_effective_rules("chat-1")["Phoenix"] == "chat"


def test_other_chats_rules_do_not_leak(set_rules):
    set_rules({"chats": {"chat-1": {"rules": {"Geheim": "X"}}}})
    assert effective.get_effective_rules("chat-2") == {}
