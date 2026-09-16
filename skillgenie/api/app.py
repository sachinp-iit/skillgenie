# ============================================================================
# Project      : SkillGenie
# File         : app.py
# Description  : FastAPI application factory for SkillGenie.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from skillgenie.api.dependencies import set_engine
from skillgenie.api.routers import router
from skillgenie.core.engine import SkillGenie

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "templates"


def create_app(
    engine: SkillGenie | None = None,
    config_file: str | None = None,
) -> FastAPI:
    """
    Build a SkillGenie FastAPI application.

    Args:
        engine: Optional pre-built engine (used by tests).
        config_file: Optional path to configuration.

    Returns:
        FastAPI application.
    """

    if engine is not None:
        set_engine(engine)

    app = FastAPI(
        title="SkillGenie API",
        description="Autonomous skill discovery, learning, evolution and "
        "recommendation for Agentic AI.",
        version="0.1.0",
    )

    @app.on_event("startup")
    def _startup() -> None:
        """
        Initialize the engine on startup when not injected.
        """

        if engine is None:
            set_engine(
                SkillGenie(
                    config_file=config_file
                    if config_file
                    else "config/config.json"
                )
            )

    app.include_router(router, prefix="/api/v1")

    if TEMPLATES_DIR.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(TEMPLATES_DIR)),
            name="static",
        )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> str:
        """
        Landing page linking to both dashboards.
        """

        return _landing_page()

    @app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
    def admin_dashboard() -> str:
        """
        Admin dashboard.
        """

        return _read_template("admin.html")

    @app.get("/monitor", response_class=HTMLResponse, include_in_schema=False)
    def monitor_dashboard() -> str:
        """
        Monitoring dashboard.
        """

        return _read_template("monitor.html")

    return app


def _read_template(name: str) -> str:
    """
    Read a dashboard template from disk.
    """

    template = TEMPLATES_DIR / name

    if not template.exists():
        return f"<html><body>Template not found: {name}</body></html>"

    return template.read_text(encoding="utf-8")


def _landing_page() -> str:
    """
    Simple landing page.
    """

    return """<html><head><title>SkillGenie</title>
<style>
body{font-family:system-ui;margin:3rem;color:#0f172a;background:#f8fafc}
a{display:inline-block;margin:0.5rem 1rem 0 0;background:#0ea5e9;color:#fff;padding:0.6rem 1.2rem;border-radius:8px;text-decoration:none}
</style></head><body>
<h1>SkillGenie</h1>
<p>Autonomous skill discovery, learning, evolution and recommendation.</p>
<a href="/admin">Admin Dashboard</a>
<a href="/monitor">Monitoring Dashboard</a>
<a href="/docs">API Docs</a>
</body></html>"""