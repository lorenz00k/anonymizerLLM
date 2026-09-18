from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from piifilter.custom_rules import load_rules_raw, add_chat_rule, remove_chat_rule

router = APIRouter()


class RuleWithLabel(BaseModel):
    original: str
    fake_value: str
    label: Optional[str] = None


@router.get("/chats/{chat_id}")
def get_chat(chat_id: str):
    return load_rules_raw()["chats"].get(chat_id, {"label": chat_id, "rules": {}})


@router.post("/chats/{chat_id}/rules")
def create_chat_rule(chat_id: str, rule: RuleWithLabel):
    add_chat_rule(chat_id, rule.original, rule.fake_value, rule.label)
    return {"ok": True}


@router.delete("/chats/{chat_id}/rules/{original}")
def remove_chat_rule_endpoint(chat_id: str, original: str):
    remove_chat_rule(chat_id, original)
    return {"ok": True}