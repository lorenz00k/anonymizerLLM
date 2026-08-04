"""
Native Messaging Protokoll (Chrome-Spezifikation).

Jede Nachricht (in beide Richtungen) hat:
  - 4 Byte Länge, little-endian, unsigned int
  - danach UTF-8 kodiertes JSON dieser Länge
"""
import sys
import json
import struct


def read_message():
    """Liest eine Nachricht von stdin. Gibt None zurück, wenn die
    Verbindung geschlossen wurde (Chrome killt den Prozess irgendwann)."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length or len(raw_length) < 4:
        return None
    message_length = struct.unpack("=I", raw_length)[0]
    message_bytes = sys.stdin.buffer.read(message_length)
    return json.loads(message_bytes.decode("utf-8"))


def send_message(message_dict: dict) -> None:
    """Schreibt eine Nachricht nach stdout, im von Chrome erwarteten Format."""
    encoded = json.dumps(message_dict).encode("utf-8")
    length_bytes = struct.pack("=I", len(encoded))
    sys.stdout.buffer.write(length_bytes)
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()