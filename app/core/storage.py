"""
app/core/storage.py
===================
파일 저장소 추상 레이어.

USE_GCS=false (로컬):
  upload_file()       → output/ 디렉터리에 복사, 절대 경로 반환
  generate_download_url() → 로컬 파일 절대 경로 그대로 반환

USE_GCS=true (프로덕션):
  upload_file()       → GCS 버킷에 업로드, gs://... 경로 반환
  generate_download_url() → 15분 유효 서명 URL 반환
"""

from __future__ import annotations

import datetime
import os
import shutil

from app.core.config import settings


async def upload_file(local_path: str, dest: str) -> str:
    """
    파일을 저장소에 업로드.
    반환: 저장소 경로 (로컬: 절대경로 / GCS: gs://...)
    """
    if settings.USE_GCS:
        return await _gcs_upload(local_path, dest)
    return _local_upload(local_path, dest)


async def generate_download_url(stored_path: str) -> str:
    """
    다운로드 URL 생성.
    반환: 로컬 파일 경로 또는 GCS 서명 URL
    """
    if settings.USE_GCS:
        return await _gcs_signed_url(stored_path)
    return stored_path  # 로컬 → router 에서 FileResponse로 처리


# ──────────────────────────────────────────────
# 로컬 구현
# ──────────────────────────────────────────────

def _local_upload(local_path: str, dest: str) -> str:
    out_dir = settings.LOCAL_OUTPUT_DIR
    target  = os.path.join(out_dir, os.path.basename(dest))
    os.makedirs(out_dir, exist_ok=True)
    shutil.copy2(local_path, target)
    return os.path.abspath(target)


# ──────────────────────────────────────────────
# GCS 구현 (USE_GCS=true 일 때만 import)
# ──────────────────────────────────────────────

async def _gcs_upload(local_path: str, dest: str) -> str:
    from google.cloud import storage as gcs
    client = gcs.Client(project=settings.GCS_PROJECT_ID)
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob   = bucket.blob(dest)
    blob.upload_from_filename(local_path)
    return f"gs://{settings.GCS_BUCKET_NAME}/{dest}"


async def _gcs_signed_url(gcs_path: str) -> str:
    from google.cloud import storage as gcs
    client    = gcs.Client(project=settings.GCS_PROJECT_ID)
    blob_name = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
    bucket    = client.bucket(settings.GCS_BUCKET_NAME)
    blob      = bucket.blob(blob_name)
    return blob.generate_signed_url(
        expiration=datetime.timedelta(minutes=15),
        method="GET",
        version="v4",
    )
