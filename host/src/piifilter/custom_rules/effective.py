from piifilter.custom_rules.storage import load_rules_raw


def get_effective_rules(chat_id: str | None = None) -> dict:
    """
    Fuehrt global + alle aktiven Ordner + (falls angegeben) die
    chat-spezifischen Regeln zu einem flachen {original: fake_value}
    Dict zusammen. Prioritaet bei Ueberschneidungen:
    chat-spezifisch > Ordner > global.
    """
    data = load_rules_raw()
    effective = dict(data["global"])

    for folder in data["folders"].values():
        if folder.get("enabled"):
            effective.update(folder.get("rules", {}))

    if chat_id and chat_id in data["chats"]:
        effective.update(data["chats"][chat_id].get("rules", {}))

    return effective