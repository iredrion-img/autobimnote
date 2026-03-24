"""
Page routes for HTML rendering.
Add this router to main.py or integrate into app package init.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.core.database import get_db
from app.reports import service
from app.auth.dependencies import get_current_user

router = APIRouter(include_in_schema=False)

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_TEMPLATE_DIR)


def _user(request: Request) -> dict | None:
    try:
        return get_current_user(request)
    except Exception:
        return None


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"user": _user(request)}
    )


@router.get("/reports/history", response_class=HTMLResponse)
async def history(request: Request):
    user = _user(request)
    if not user:
        return RedirectResponse("/auth/login")
    reports = await service.get_user_reports(user["email"])
    return templates.TemplateResponse(
        request=request, name="history.html", context={"user": user, "reports": reports}
    )
