"""
Gemeinsame Datentypen fuer alle Erkennungsstufen.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Match:
    """Eine Fundstelle im ORIGINALTEXT, noch nicht angewendet."""

    start: int
    end: int
    original: str
    fake_value: str
    category: str
    priority: int = 0


@dataclass
class Finding:
    """Eine tatsaechlich angewendete (oder vault-only) Ersetzung."""

    placeholder: str
    original: str
    category: str


@dataclass
class Detector(Protocol):
    priority: int  # hoeher gewinnt bei Ueberschneidung

    def find(
        self, text: str, chat_id: str | None = None, lang_code: str | None = None
    ) -> tuple[list[Match], list[Finding]]:
        """Matches mit Position + zusaetzliche positionslose Findings."""
        ...
