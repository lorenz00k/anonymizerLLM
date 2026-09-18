from fastapi import APIRouter
from pydantic import BaseModel

from piifilter.custom_rules import (
    load_rules_raw,
    add_folder,
    delete_folder,
    set_folder_enabled,
    add_folder_rule,
    remove_folder_rule,
)

router = APIRouter()


class Rule(BaseModel):
    original: str
    fake_value: str


class FolderName(BaseModel):
    name: str


class FolderToggle(BaseModel):
    enabled: bool


@router.get("/folders")
def get_folders():
    return load_rules_raw()["folders"]


@router.post("/folders")
def create_folder(folder: FolderName):
    add_folder(folder.name)
    return {"ok": True}


@router.delete("/folders/{name}")
def remove_folder(name: str):
    delete_folder(name)
    return {"ok": True}


@router.post("/folders/{name}/toggle")
def toggle_folder(name: str, toggle: FolderToggle):
    set_folder_enabled(name, toggle.enabled)
    return {"ok": True}


@router.post("/folders/{name}/rules")
def create_folder_rule(name: str, rule: Rule):
    add_folder_rule(name, rule.original, rule.fake_value)
    return {"ok": True}


@router.delete("/folders/{name}/rules/{original}")
def remove_folder_rule_endpoint(name: str, original: str):
    remove_folder_rule(name, original)
    return {"ok": True}