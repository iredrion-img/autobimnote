"""
app/reports/service.py
======================
보고서 생성 비즈니스 로직.

흐름:
  1. DB에 Report(status=pending) 선 기록 → 즉시 응답 반환
  2. BackgroundTask에서 엔진 실행 (HWPX 생성)
  3. 완료 시 GCS 업로드 + DB 상태 done 갱신
  4. 실패 시 DB 상태 error 갱신

엔진 인터페이스:
  engine.xml_manager.generate_bim_report() 직접 호출
  (스캐폴딩이 HwpxManager를 썼다면 xml_manager.HwpxManager 어댑터 사용)
"""

from __future__ import annotations

import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import BackgroundTasks, UploadFile, HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.storage import upload_file, generate_download_url
from app.reports.models import Report
from app.reports.schemas import ReportResponse

# 엔진 import — 프로젝트 루트 기준 engine/ 폴더
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine"))
from xml_manager import generate_bim_report, validate_template   # noqa: E402

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────

async def _save_upload(upload: UploadFile, dest: str) -> None:
    """UploadFile을 로컬 경로에 저장."""
    contents = await upload.read()
    with open(dest, "wb") as f:
        f.write(contents)


async def _mark_status(report_id: str | UUID, status_val: str, gcs_path: str | None = None) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Report).where(Report.id == str(report_id)))
        report = result.scalar_one_or_none()
        if report:
            report.status = status_val
            if gcs_path:
                report.gcs_path = gcs_path
            await db.commit()


# ──────────────────────────────────────────────────────────────
# 백그라운드 엔진 실행
# ──────────────────────────────────────────────────────────────

async def _run_engine(
    report_id: str,
    data: dict,
    image1_bytes: Optional[bytes],
    image2_bytes: Optional[bytes],
    image1_ext: str,
    image2_ext: str,
) -> None:
    """
    BackgroundTask 진입점.
    이미지 bytes를 임시 파일로 저장 → 엔진 실행 → GCS 업로드 → DB 갱신.
    """
    tmp_dir = tempfile.mkdtemp(prefix="bim_")
    try:
        images: dict = {}

        if image1_bytes:
            p = os.path.join(tmp_dir, f"image1{image1_ext}")
            with open(p, "wb") as f:
                f.write(image1_bytes)
            images["image1"] = p

        if image2_bytes:
            p = os.path.join(tmp_dir, f"image2{image2_ext}")
            with open(p, "wb") as f:
                f.write(image2_bytes)
            images["image2"] = p

        result = generate_bim_report(
            template_path=settings.TEMPLATE_PATH,
            output_dir=tmp_dir,
            data=data,
            images=images or None,
        )

        if result["success"]:
            gcs_dest = f"reports/{report_id}.hwpx"
            gcs_path = await upload_file(result["output_path"], gcs_dest)
            await _mark_status(report_id, "done", gcs_path)
            logger.info("Report done: %s → %s", report_id, gcs_path)

            if result["warnings"]:
                for w in result["warnings"]:
                    logger.warning("report %s: %s", report_id, w)
        else:
            logger.error("Engine failed for %s: %s", report_id, result["warnings"])
            await _mark_status(report_id, "error")

    except Exception as exc:
        logger.exception("Unexpected engine error for %s: %s", report_id, exc)
        await _mark_status(report_id, "error")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ──────────────────────────────────────────────────────────────
# 퍼블릭 서비스 함수
# ──────────────────────────────────────────────────────────────

async def create_report(
    background_tasks: BackgroundTasks,
    user_email: str,
    data: dict,
    image1: Optional[UploadFile] = None,
    image2: Optional[UploadFile] = None,
) -> Report:
    """
    보고서 생성 요청 처리.
    DB에 pending 상태로 선 기록 후 BackgroundTask에 엔진 실행 위임.
    """
    # 템플릿 존재 여부 사전 확인
    if not os.path.exists(settings.TEMPLATE_PATH):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "HWPX 템플릿 파일이 없습니다. "
                f"'{settings.TEMPLATE_PATH}' 에 template.hwpx 를 배치하세요."
            ),
        )

    # 이미지 bytes를 미리 읽어둠 (BackgroundTask는 스트림을 다시 읽을 수 없음)
    image1_bytes = await image1.read() if image1 else None
    image2_bytes = await image2.read() if image2 else None
    image1_ext   = Path(image1.filename).suffix.lower() if image1 else ".png"
    image2_ext   = Path(image2.filename).suffix.lower() if image2 else ".png"

    # DB 선 기록
    report = Report(
        user_email=user_email,
        status="pending",
        structure_name=data["structure_name"],
        discipline=data["discipline"],
        issue_description=data["issue_description"],
        img_1_title=data["img_1_title"],
        img_2_title=data["img_2_title"],
    )
    async with AsyncSessionLocal() as db:
        db.add(report)
        await db.commit()
        await db.refresh(report)

    # 백그라운드 엔진 실행
    background_tasks.add_task(
        _run_engine,
        str(report.id),
        data,
        image1_bytes,
        image2_bytes,
        image1_ext,
        image2_ext,
    )

    return report


async def get_user_reports(user_email: str) -> list[Report]:
    """사용자의 보고서 이력 조회 (최신순)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Report)
            .where(Report.user_email == user_email)
            .order_by(Report.created_at.desc())
        )
        return result.scalars().all()


async def get_report_download_url(report_id: str, user_email: str) -> str:
    """
    보고서 다운로드 URL 발급.
    - 로컬 환경: 직접 파일 경로 반환
    - GCS 환경: 15분 서명 URL 반환
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Report).where(
                Report.id == report_id,
                Report.user_email == user_email,
            )
        )
        report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    if report.status != "done":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"보고서가 아직 준비되지 않았습니다. 현재 상태: {report.status}",
        )

    if not report.gcs_path:
        raise HTTPException(status_code=404, detail="파일 경로가 없습니다.")

    return await generate_download_url(report.gcs_path)


async def get_report_status(report_id: str, user_email: str) -> dict:
    """폴링용 상태 조회 엔드포인트."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Report).where(
                Report.id == report_id,
                Report.user_email == user_email,
            )
        )
        report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    return {
        "id":     str(report.id),
        "status": report.status,
    }


# ──────────────────────────────────────────────────────────────
# 시작 시 템플릿 검증 (main.py lifespan 에서 호출)
# ──────────────────────────────────────────────────────────────

def startup_validate_template() -> None:
    """
    서버 시작 시 템플릿 정합성을 점검.
    이상이 있으면 경고 로그 출력 (서버 기동은 막지 않음).
    """
    result = validate_template(settings.TEMPLATE_PATH)
    if result["valid"]:
        logger.info(
            "템플릿 정상: 필드 %s, 이미지 슬롯 %s",
            result["found_fields"],
            result["found_images"],
        )
    else:
        for issue in result["issues"]:
            logger.warning("템플릿 이슈: %s", issue)
