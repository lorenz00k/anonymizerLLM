"""
Lokale Weboberfläche zum Verwalten eigener Regeln.
Laeuft nur auf localhost, nie extern erreichbar.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from piifilter.custom_rules import load_rules, add_rule, remove_rule

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"


class Rule(BaseModel):
    original: str
    fake_value: str


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC_DIR / "rules_ui.html")


@app.get("/rules")
def get_rules():
    return load_rules()


@app.post("/rules")
def create_rule(rule: Rule):
    add_rule(rule.original, rule.fake_value)
    return {"ok": True}


@app.delete("/rules/{original}")
def delete_rule(original: str):
    remove_rule(original)
    return {"ok": True}


def run():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8756)