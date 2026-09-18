from piifilter.custom_rules.storage import load_rules_raw, save_rules


def add_folder(name: str) -> None:
    data = load_rules_raw()
    data["folders"].setdefault(name, {"enabled": True, "rules": {}})
    save_rules(data)


def delete_folder(name: str) -> None:
    data = load_rules_raw()
    data["folders"].pop(name, None)
    save_rules(data)


def set_folder_enabled(name: str, enabled: bool) -> None:
    data = load_rules_raw()
    if name in data["folders"]:
        data["folders"][name]["enabled"] = enabled
        save_rules(data)


def add_folder_rule(folder: str, original: str, fake_value: str) -> None:
    data = load_rules_raw()
    data["folders"].setdefault(folder, {"enabled": True, "rules": {}})
    data["folders"][folder]["rules"][original] = fake_value
    save_rules(data)


def remove_folder_rule(folder: str, original: str) -> None:
    data = load_rules_raw()
    if folder in data["folders"]:
        data["folders"][folder]["rules"].pop(original, None)
        save_rules(data)