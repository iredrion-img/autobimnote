"""
app/auth/dependencies.py
========================
개발 모드(DEBUG=True)에서 OAuth 없이 테스트할 수 있도록
더미 유저를 반환하는 바이패스 포함.

운영 환경(DEBUG=False)에서는 세션 인증만 허용.
"""
from fastapi import Request, HTTPException, status
from typing import Annotated
from fastapi import Depends

from app.core.config import settings

# 개발용 더미 유저 (DEBUG=True 일 때만 사용)
_DEV_USER = {
    "sub":     "dev-local-001",
    "email":   "dev@kunhwa.local",
    "name":    "개발자 (Dev Bypass)",
    "picture": "",
}


def get_current_user(request: Request) -> dict:
    """
    세션에서 로그인 유저를 반환.
    DEBUG=True 이고 세션이 비어 있으면 더미 유저로 자동 바이패스.
    """
    user = request.session.get("user")

    if user:
        return user

    if settings.DEBUG:
        # OAuth 없이 로컬 테스트 가능
        return _DEV_USER

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please login at /auth/login",
    )


# 편의 타입 앨리어스
CurrentUser = Annotated[dict, Depends(get_current_user)]
