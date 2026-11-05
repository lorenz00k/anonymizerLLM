from piifilter.custom_rules import get_effective_rules
from piifilter.detection.rule_based.text_utils import match_case
from piifilter.detection.rule_based.types import Match

import re


def find_custom_matches(text: str, chat_id: str = None) -> list[Match]:
    rules = get_effective_rules(chat_id)
    matches: list[Match] = []
    for original, fake_value in rules.items():
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        for m in pattern.finditer(text):
            actual_fake = match_case(fake_value, m.group(0))
            matches.append(Match(m.start(), m.end(), m.group(0), actual_fake, "CUSTOM"))
    return matches
