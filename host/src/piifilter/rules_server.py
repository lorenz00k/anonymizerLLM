"""
Lokale Weboberfläche zum Verwalten eigener Regeln.
Laeuft nur auf localhost, nie extern erreichbar.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from piifilter.routes.global_rules_routes import router as global_rules_router
from piifilter.routes.folder_routes import router as folder_router
from piifilter.routes.chat_routes import router as chat_router

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"

app.include_router(global_rules_router)
app.include_router(folder_router)
app.include_router(chat_router)

# CSS/JS unter /static/... ausliefern
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC_DIR / "rules_ui.html")


def run():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8756)