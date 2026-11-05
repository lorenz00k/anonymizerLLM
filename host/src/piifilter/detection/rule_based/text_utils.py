def match_case(fake_value: str, matched_text: str) -> str:
    if matched_text.isupper():
        return fake_value.upper()
    if matched_text.istitle():
        return fake_value.title()
    if matched_text.islower():
        return fake_value.lower()
    return fake_value
