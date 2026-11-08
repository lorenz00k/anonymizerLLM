import importlib
import threading
import time

import pytest

from piifilter.detection.llm import ollama_client, llm_rewrite
from piifilter.detection.rule_based import presidio_engine
from piifilter.detection.rule_based.types import Finding

entry = importlib.import_module("piifilter.__main__")


def wait_for(predicate, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class Host:
    def __init__(self):
        self.sent = []
        self.detect_calls, self.suggest_calls, self.apply_calls, self.rewrite_calls = [], [], [], []
        # ueberschreibbare Fakes
        self.detect_impl = lambda text, *a, **k: (text, [])
        self.suggest_impl = lambda *a, **k: []
        self.apply_impl = lambda text, suggestions, ids: (text, [])
        self.rewrite_impl = lambda *a, **k: "neu"

    def types(self):
        return [m["type"] for m in self.sent]

    def wait_for_type(self, mtype):
        assert wait_for(lambda: mtype in self.types()), self.types()


@pytest.fixture
def host(monkeypatch):
    h = Host()

    send_mod = importlib.import_module("piifilter.host.transport")
    ana_mod = importlib.import_module("piifilter.host.handlers.anonymize")
    llm_mod = importlib.import_module("piifilter.host.handlers.llm")
    h.send = send_mod.send
    h.send_mod = send_mod

    def detect(*a, **k):
        h.detect_calls.append((a, k))
        return h.detect_impl(*a, **k)

    def suggest(*a, **k):
        h.suggest_calls.append((a, k))
        return h.suggest_impl(*a, **k)

    def apply(*a, **k):
        h.apply_calls.append((a, k))
        return h.apply_impl(*a, **k)

    def rewrite(*a, **k):
        h.rewrite_calls.append((a, k))
        return h.rewrite_impl(*a, **k)

    monkeypatch.setattr(send_mod, "send_message", h.sent.append)
    monkeypatch.setattr(ana_mod, "detect_and_anonymize", detect)
    monkeypatch.setattr(llm_mod, "get_llm_suggestions", suggest)
    monkeypatch.setattr(llm_mod, "apply_llm_suggestions", apply)
    monkeypatch.setattr(llm_rewrite, "rewrite_finding", rewrite)
    monkeypatch.setattr(ollama_client, "warmup", lambda: None)
    monkeypatch.setattr(presidio_engine, "warmup", lambda *a, **k: None, raising=False)

    def run(*messages):
        it = iter(messages)
        monkeypatch.setattr(entry, "read_message", lambda: next(it, None))
        entry.main()

    h.run = run
    yield h
    for t in threading.enumerate():
        if t is not threading.main_thread() and t.daemon:
            t.join(timeout=3)
    return h


# ---------- Phase 1: anonymize ----------


def test_anonymize_without_llm_sends_result_then_empty_suggestions(host):
    host.detect_impl = lambda text, *a: ("anon", [Finding("Max", "Jonas", "PERSON")])
    host.run({"type": "anonymize", "text": "Jonas", "chatId": "c", "requestId": 1})

    assert host.types() == ["anonymize_result", "llm_suggestions"]
    assert host.sent[0] == {
        "type": "anonymize_result",
        "requestId": 1,
        "result": "anon",
        "replacements": {"Max": "Jonas"},
    }
    assert host.sent[1] == {"type": "llm_suggestions", "requestId": 1, "suggestions": []}
    assert host.suggest_calls == []  # LLM wurde nicht gefragt


def test_message_without_type_is_treated_as_anonymize(host):
    host.run({"text": "Hallo", "chatId": "c", "requestId": 2})
    assert host.types() == ["anonymize_result", "llm_suggestions"]


def test_anonymize_passes_text_and_chat_id_to_detection(host):
    host.run({"text": "Hallo Welt", "chatId": "chat-7", "requestId": 3})
    ((args, _),) = host.detect_calls
    assert args[0] == "Hallo Welt"
    assert args[1] == "chat-7"


def test_anonymize_error_returns_original_text_and_nothing_else(host):
    def boom(*a):
        raise RuntimeError("kaputt")

    host.detect_impl = boom
    host.run({"text": "geheim", "chatId": "c", "requestId": 4, "llmEnabled": True})

    assert host.sent == [
        {"type": "anonymize_result", "requestId": 4, "result": "geheim", "replacements": {}}
    ]
    assert host.suggest_calls == []


def test_loop_continues_after_error(host):
    calls = {"n": 0}

    def flaky(text, *a):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError
        return text, []

    host.detect_impl = flaky
    host.run({"text": "a", "requestId": 1}, {"text": "b", "requestId": 2})
    results = [m for m in host.sent if m["type"] == "anonymize_result"]
    assert [m["requestId"] for m in results] == [1, 2]


# ---------- Phase 2: LLM-Vorschlaege ----------


def test_llm_runs_on_phase1_result_and_reports_back(host):
    host.detect_impl = lambda text, *a: ("anonymisiert", [])
    host.suggest_impl = lambda text, chat_id, *a, **k: [{"id": 1, "text": "x"}]
    host.run({"text": "Original", "chatId": "c9", "requestId": 5, "llmEnabled": True})
    host.wait_for_type("llm_suggestions")

    # schnelle Antwort kommt zuerst
    assert host.types()[0] == "anonymize_result"
    ((args, _),) = host.suggest_calls
    assert args[0] == "anonymisiert"  # nicht der Klartext
    assert args[1] == "c9"
    assert host.sent[-1] == {
        "type": "llm_suggestions",
        "requestId": 5,
        "suggestions": [{"id": 1, "text": "x"}],
    }


def test_llm_error_yields_empty_suggestions(host):
    def boom(*a, **k):
        raise RuntimeError("ollama down")

    host.suggest_impl = boom
    host.run({"text": "x", "chatId": "c", "requestId": 6, "llmEnabled": True})
    host.wait_for_type("llm_suggestions")
    assert host.sent[-1]["suggestions"] == []
    assert host.sent[-1]["requestId"] == 6


def test_main_loop_is_not_blocked_by_slow_llm(host):
    release = threading.Event()
    host.suggest_impl = lambda *a, **k: (release.wait(2), [])[1]
    try:
        host.run({"text": "a", "requestId": 1, "llmEnabled": True}, {"text": "b", "requestId": 2})
        # Beide Phase-1-Antworten sind da, obwohl das LLM von Nachricht 1 noch haengt
        results = [m["requestId"] for m in host.sent if m["type"] == "anonymize_result"]
        assert results == [1, 2]
    finally:
        release.set()


# ---------- Phase 3: apply_llm ----------


def test_apply_llm_passes_arguments_and_sends_result(host):
    host.apply_impl = lambda text, suggestions, ids: ("fertig", [Finding("[X_1]", "foo", "X")])
    suggestions = [{"id": 1}, {"id": 2}]
    host.run(
        {
            "type": "apply_llm",
            "text": "t",
            "suggestions": suggestions,
            "acceptedIds": [2],
            "requestId": 8,
        }
    )

    ((args, _),) = host.apply_calls
    assert args == ("t", suggestions, {2})
    assert host.sent == [
        {
            "type": "apply_llm_result",
            "requestId": 8,
            "result": "fertig",
            "replacements": {"[X_1]": "foo"},
        }
    ]


def test_apply_llm_defaults_when_fields_missing(host):
    host.run({"type": "apply_llm", "text": "t", "requestId": 9})
    ((args, _),) = host.apply_calls
    assert args == ("t", [], set())


def test_apply_llm_error_returns_input_text(host):
    def boom(*a):
        raise RuntimeError

    host.apply_impl = boom
    host.run({"type": "apply_llm", "text": "t", "requestId": 10})
    assert host.sent == [
        {"type": "apply_llm_result", "requestId": 10, "result": "t", "replacements": {}}
    ]


# ---------- retry_rewrite ----------


def test_retry_rewrite_uses_higher_temperature(host):
    host.rewrite_impl = lambda *a, **k: "Umformuliert"
    host.run(
        {
            "type": "retry_rewrite",
            "text": "Gehalt 5000",
            "category": "PERSONENKENNUNG",
            "chatId": "c",
            "requestId": 11,
        }
    )
    ((args, kwargs),) = host.rewrite_calls
    assert args[:2] == ("Gehalt 5000", "PERSONENKENNUNG")
    assert kwargs.get("temperature") == 0.7
    assert host.sent == [
        {"type": "retry_rewrite_result", "requestId": 11, "suggestedReplacement": "Umformuliert"}
    ]


def test_retry_rewrite_error_falls_back_to_category_placeholder(host):
    def boom(*a, **k):
        raise RuntimeError

    host.rewrite_impl = boom
    host.run({"type": "retry_rewrite", "text": "x", "category": "FIRMENGEHEIMNIS", "requestId": 12})
    assert host.sent == [
        {
            "type": "retry_rewrite_result",
            "requestId": 12,
            "suggestedReplacement": "[FIRMENGEHEIMNIS]",
        }
    ]


# ---------- Dispatch und Schleife ----------


def test_unknown_type_sends_nothing_and_loop_continues(host):
    host.run({"type": "gibts_nicht", "requestId": 1}, {"text": "x", "requestId": 2})
    assert host.types() == ["anonymize_result", "llm_suggestions"]
    assert host.sent[0]["requestId"] == 2


def test_read_error_ends_loop_without_crashing(host, monkeypatch):
    def boom():
        raise OSError("pipe kaputt")

    monkeypatch.setattr(entry, "read_message", boom)
    entry.main()
    assert host.sent == []


def test_empty_input_ends_loop(host):
    host.run()
    assert host.sent == []


def test_warmup_is_started_in_background(host, monkeypatch):
    started = threading.Event()
    monkeypatch.setattr(ollama_client, "warmup", started.set)
    host.run()
    assert started.wait(1)


# ---------- Transport ----------


def test_sends_never_overlap(host, monkeypatch):
    active, overlaps = [], []

    def slow_send(payload):
        active.append(1)
        if len(active) > 1:
            overlaps.append(payload)
        time.sleep(0.01)
        active.pop()

    monkeypatch.setattr(host.send_mod, "send_message", slow_send)
    threads = [threading.Thread(target=host.send, args=({"n": i},)) for i in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert overlaps == []


@pytest.fixture(autouse=True)
def _reset_languages():
    from piifilter.host.session import chat_languages

    chat_languages._by_chat.clear()


EN_TEXT = "I have been living in London for three years now and I really like it."
DE_TEXT = "Ich wohne seit drei Jahren in Hamburg und fuehle mich dort sehr wohl."


def test_detected_language_reaches_detection(host):
    host.run({"text": EN_TEXT, "chatId": "lang-1", "requestId": 1})
    ((args, _),) = host.detect_calls
    assert args[2] == "en"


def test_german_text_is_detected_as_german(host):
    host.run({"text": DE_TEXT, "chatId": "lang-2", "requestId": 1})
    ((args, _),) = host.detect_calls
    assert args[2] == "de"


def test_explicit_lang_overrides_detection(host):
    host.run({"text": EN_TEXT, "chatId": "lang-3", "requestId": 1, "lang_code": "de"})
    ((args, _),) = host.detect_calls
    assert args[2] == "de"


def test_short_message_keeps_chat_language(host):
    host.run(
        {"text": EN_TEXT, "chatId": "lang-4", "requestId": 1},
        {"text": "ok", "chatId": "lang-4", "requestId": 2},
    )
    assert [a[2] for a, _ in host.detect_calls] == ["en", "en"]


def test_languages_are_tracked_per_chat(host):
    host.run(
        {"text": EN_TEXT, "chatId": "lang-5", "requestId": 1},
        {"text": "ok", "chatId": "lang-6", "requestId": 2},
    )
    assert [a[2] for a, _ in host.detect_calls] == ["en", "de"]
