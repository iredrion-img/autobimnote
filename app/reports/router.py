"""
app/reports/router.py
=====================
REST API 엔드포인트.

POST /report/generate        보고서 생성 요청 (pending 즉시 반환)
GET  /report/status/{id}     생성 상태 폴링 (pending / done / error)
GET  /report/download/{id}   HWPX 다운로드 URL 발급 (done 상태만)
GET  /report/history         사용자 보고서 이력
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import RedirectResponse
from typing import Optional

from app.auth.dependencies import get_current_user
from app.reports.schemas import ReportResponse, ReportStatusResponse
from app.reports.service import (
    create_report,
    get_user_reports,
    get_report_download_url,
    get_report_status,
)

router = APIRouter()


@router.post("/generate", response_model=ReportResponse, status_code=202)
async def generate(
    background_tasks: BackgroundTasks,
    structure_name:    str          = Form(..., description="구조물명"),
    discipline:        str          = Form(..., description="검토 분야"),
    issue_description: str          = Form(..., description="이슈 내용"),
    img_1_title:       str          = Form(..., description="좌측 이미지 제목"),
    img_2_title:       str          = Form(..., description="우측 이미지 제목"),
    image1: Optional[UploadFile]    = File(None, description="좌측 이미지 (image1 슬롯)"),
    image2: Optional[UploadFile]    = File(None, description="우측 이미지 (image2 슬롯)"),
    user:   dict                    = Depends(get_current_user),
):
    """
    보고서 생성 요청.
    202 Accepted 즉시 반환 → /report/status/{id} 로 상태 폴링.
    """
    data = {
        "structure_name":    structure_name,
        "discipline":        discipline,
        "issue_description": issue_description,
        "img_1_title":       img_1_title,
        "img_2_title":       img_2_title,
    }
    report = await create_report(
        background_tasks=background_tasks,
        user_email=user["email"],
        data=data,
        image1=image1,
        image2=image2,
    )
    return report


@router.get("/status/{report_id}", response_model=ReportStatusResponse)
async def status(
    report_id: str,
    user: dict = Depends(get_current_user),
):
    """생성 상태 폴링 엔드포인트. 프론트에서 1~2초 간격으로 호출."""
    return await get_report_status(report_id, user["email"])


@router.get("/download/{report_id}")
async def download(
    report_id: str,
    user: dict = Depends(get_current_user),
):
    """
    보고서 다운로드.
    - 로컬 환경: 파일을 StreamingResponse로 직접 반환
    - GCS 환경: 서명 URL로 리다이렉트
    """
    url = await get_report_download_url(report_id, user["email"])

    # 로컬 파일 경로인 경우 직접 스트리밍
    import os
    from fastapi.responses import FileResponse
    if os.path.exists(url):
        filename = f"BIM_Report_{report_id[:8]}.hwpx"
        return FileResponse(
            path=url,
            media_type="application/octet-stream",
            filename=filename,
        )

    # GCS 서명 URL이면 리다이렉트
    return RedirectResponse(url=url, status_code=302)


@router.get("/history", response_model=list[ReportResponse])
async def history(
    user: dict = Depends(get_current_user),
):
    """사용자의 보고서 이력 (최신순)."""
    return await get_user_reports(user["email"])
