from piifilter.custom_rules.storage import load_rules_raw, save_rules


def add_chat_rule(chat_id: str, original: str, fake_value: str, label: str | None = None) -> None:
    data = load_rules_raw()
    data["chats"].setdefault(chat_id, {"label": label or chat_id, "rules": {}})
    if label:
        data["chats"][chat_id]["label"] = label
    data["chats"][chat_id]["rules"][original] = fake_value
    save_rules(data)


def remove_chat_rule(chat_id: str, original: str) -> None:
    data = load_rules_raw()
    if chat_id in data["chats"]:
        data["chats"][chat_id]["rules"].pop(original, None)
        save_rules(data)


def set_chat_label(chat_id: str, label: str) -> None:
    data = load_rules_raw()
    if chat_id in data["chats"]:
        data["chats"][chat_id]["label"] = label
        save_rules(data)