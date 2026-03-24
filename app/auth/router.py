"""
app/auth/router.py – Google OAuth 2.0 flow using Authlib.

Endpoints:
  GET /auth/login    → redirect to Google consent screen
  GET /auth/callback → handle code exchange, store user in session
  GET /auth/logout   → clear session
  GET /auth/me       → return current user info (JSON)
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth

from app.core.config import settings

router = APIRouter()

# ── Authlib OAuth registry ─────────────────────────────────────────────────────
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "prompt": "select_account",
    },
)


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/login", summary="Redirect to Google OAuth consent screen")
async def login(request: Request):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", summary="Handle OAuth callback from Google")
async def callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    if not user_info:
        # Fallback: fetch from userinfo endpoint
        user_info = await oauth.google.userinfo(token=token)

    # Persist minimal user data in the encrypted session cookie
    request.session["user"] = {
        "sub": user_info["sub"],
        "email": user_info["email"],
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
    }
    return RedirectResponse(url="/")


@router.get("/logout", summary="Clear session and redirect to home")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@router.get("/me", summary="Return current user info as JSON")
async def me(request: Request):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return JSONResponse(user)
