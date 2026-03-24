"""
main.py
=======
FastAPI 앱 진입점.

lifespan:
  - DB 테이블 자동 생성 (개발용; 프로덕션은 Alembic 마이그레이션 권장)
  - HWPX 템플릿 정합성 사전 점검

미들웨어:
  - SessionMiddleware (Google OAuth 세션 쿠키)
  - CORSMiddleware (로컬 개발 편의)
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.auth.router import router as auth_router
from app.reports.router import router as report_router
from app.pages import router as pages_router
from app.reports.service import startup_validate_template

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 시작 ──────────────────────────────────
    logger.info("서버 시작 중...")

    # DB 테이블 생성 (개발 환경)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB 테이블 준비 완료")

    # HWPX 템플릿 정합성 점검
    startup_validate_template()

    yield

    # ── 종료 ──────────────────────────────────
    logger.info("서버 종료")
    await engine.dispose()


app = FastAPI(
    title="BIM 이슈 보고서 SaaS",
    description="건화기술연구소 BIM 이슈 보고서 자동화 플랫폼",
    version="1.0.0",
    lifespan=lifespan,
)

# ── 미들웨어 ──────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=not settings.DEBUG,  # 로컬 개발 시 False
    max_age=60 * 60 * 8,            # 8시간 세션 유지
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [settings.ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 정적 파일 ────────────────────────────────
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── 라우터 등록 ──────────────────────────────
app.include_router(pages_router)
app.include_router(auth_router,   prefix="/auth",   tags=["인증"])
app.include_router(report_router, prefix="/report", tags=["보고서"])


# ── 헬스체크 ─────────────────────────────────
@app.get("/health", tags=["시스템"])
async def health():
    return {"status": "ok", "version": app.version}
