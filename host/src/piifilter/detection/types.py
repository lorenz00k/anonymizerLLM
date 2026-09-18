"""
Gemeinsame Datentypen fuer alle Erkennungsstufen.
"""
from dataclasses import dataclass


@dataclass
class Match:
    """Eine Fundstelle im ORIGINALTEXT, noch nicht angewendet."""
    start: int
    end: int
    original: str
    fake_value: str
    category: str


@dataclass
class Finding:
    """Eine tatsaechlich angewendete (oder vault-only) Ersetzung."""
    placeholder: str
    original: str
    category: str