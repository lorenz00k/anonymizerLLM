from piifilter.custom_rules.storage import load_rules_raw, save_rules


def add_global_rule(original: str, fake_value: str) -> None:
    data = load_rules_raw()
    data["global"][original] = fake_value
    save_rules(data)


def remove_global_rule(original: str) -> None:
    data = load_rules_raw()
    data["global"].pop(original, None)
    save_rules(data)