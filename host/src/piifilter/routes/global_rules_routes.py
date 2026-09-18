from fastapi import APIRouter
from pydantic import BaseModel

from piifilter.custom_rules import load_rules, add_rule, remove_rule

router = APIRouter()


class Rule(BaseModel):
    original: str
    fake_value: str


@router.get("/rules")
def get_rules():
    return load_rules()


@router.post("/rules")
def create_rule(rule: Rule):
    add_rule(rule.original, rule.fake_value)
    return {"ok": True}


@router.delete("/rules/{original}")
def delete_rule(original: str):
    remove_rule(original)
    return {"ok": True}