"""
BIM 이슈 보고서 자동화 엔진  v1.1
===================================
건화기술연구소(Kunhwa R&D) | ISO 19650 / MOLIT BIM 가이드라인 준수

퍼블릭 인터페이스 (스캐폴딩 호환):
  generate_bim_report()   ← service.py 에서 직접 호출
  HwpxManager             ← 스캐폴딩이 fill_text_fields() 를 기대할 경우 호환 클래스

내부 변경 이력:
  v1.1 - linesegarray 캐시 초기화로 긴 텍스트 한 줄 압축 렌더링 버그 수정
         XML 멀티라인 텍스트 다중 <hp:p> 단락 분리 삽입
         이미지 포맷 변경 시 content.hpf manifest href + media-type 자동 갱신
         ZIP 재패킹 방식으로 중복 항목 경고 제거
"""

import zipfile
import os
import shutil
import uuid
import re
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

SECTION_XML_PATH = "Contents/section0.xml"
MANIFEST_PATH    = "Contents/content.hpf"
PLACEHOLDER_RE   = re.compile(r"\{\{(\w+)\}\}")

REQUIRED_FIELDS = [
    "structure_name",
    "discipline",
    "issue_description",
    "img_1_title",
    "img_2_title",
]

# binaryItemIDRef 값 → 기본 BinData 경로
IMAGE_SLOTS = {
    "image1": "BinData/image1.png",
    "image2": "BinData/image2.png",
}

MIME_MAP = {
    ".bmp":  "image/bmp",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif":  "image/gif",
    ".tiff": "image/tiff",
    ".tif":  "image/tiff",
}

_LINESEG_RE    = re.compile(r"<hp:linesegarray>.*?</hp:linesegarray>", re.DOTALL)
_EMPTY_LINESEG = "<hp:linesegarray/>"


# ──────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────

def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
    )


def _clear_linesegarray(xml_content: str, placeholder: str) -> str:
    """플레이스홀더를 포함한 <hp:p> 블록의 linesegarray 캐시를 초기화."""
    p_pat = re.compile(
        r"(<hp:p\b[^>]*>)"
        r"((?:(?!</hp:p>).)*?" + re.escape(placeholder) + r"(?:(?!</hp:p>).)*?)"
        r"(</hp:p>)",
        re.DOTALL,
    )
    def _reset(m):
        body = _LINESEG_RE.sub(_EMPTY_LINESEG, m.group(2))
        return m.group(1) + body + m.group(3)
    return p_pat.sub(_reset, xml_content)


def _replace_field(xml_content: str, key: str, value: str) -> str:
    """단일 필드를 치환. issue_description은 linesegarray 초기화 적용."""
    placeholder = f"{{{{{key}}}}}"
    if placeholder not in xml_content:
        return xml_content

    safe = _escape_xml(str(value))

    if key == "issue_description":
        xml_content = _clear_linesegarray(xml_content, placeholder)

    return xml_content.replace(placeholder, safe)


def _validate_fields(xml_content: str, data: dict) -> list:
    found    = set(PLACEHOLDER_RE.findall(xml_content))
    warnings = []
    missing  = found - set(data.keys())
    if missing:
        warnings.append(f"[경고] XML 내 미치환 필드: {sorted(missing)}")
    for field in REQUIRED_FIELDS:
        if field not in found and field[:4].lower() in xml_content.lower():
            warnings.append(
                f"[경고] '{field}' XML 조각화 의심 — 한글에서 삭제 후 재입력 필요."
            )
    return warnings


def _apply_text_fields(xml_content: str, data: dict) -> tuple:
    warnings = _validate_fields(xml_content, data)
    for key, value in data.items():
        xml_content = _replace_field(xml_content, key, value)
    return xml_content, warnings


def _update_manifest(manifest_xml: str, image_id: str, source_path: str) -> tuple:
    ext      = Path(source_path).suffix.lower()
    mime     = MIME_MAP.get(ext, "image/png")
    new_href = f"BinData/{image_id}{ext}"
    manifest_xml = re.sub(
        rf'(id="{image_id}"[^>]*?)href="[^"]*"',
        rf'\1href="{new_href}"', manifest_xml)
    manifest_xml = re.sub(
        rf'(id="{image_id}"[^>]*?)media-type="[^"]*"',
        rf'\1media-type="{mime}"', manifest_xml)
    return manifest_xml, new_href


def _repack_zip(src_path: str, overrides: dict) -> None:
    """
    중복 없는 깨끗한 ZIP으로 재패킹.
    overrides: {내부경로: bytes}  — None 값은 해당 항목 삭제.
    """
    tmp = src_path + ".tmp"
    remaining = dict(overrides)
    with zipfile.ZipFile(src_path, "r") as zr, \
         zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zw:
        for item in zr.infolist():
            if item.filename in remaining:
                data = remaining.pop(item.filename)
                if data is not None:
                    zw.writestr(item, data)
            else:
                zw.writestr(item, zr.read(item.filename))
        for path, data in remaining.items():
            if data is not None:
                zw.writestr(path, data)
    os.replace(tmp, src_path)


# ──────────────────────────────────────────────
# 퍼블릭 API
# ──────────────────────────────────────────────

def generate_bim_report(
    template_path: str,
    output_dir: str,
    data: dict,
    images: Optional[dict] = None,
    report_prefix: str = "BIM_Issue_Report",
) -> dict:
    """
    BIM 이슈 보고서를 생성하여 output_dir에 저장합니다.

    Parameters
    ----------
    template_path : str
        원본 .hwpx 템플릿 경로
    output_dir : str
        결과 파일 저장 폴더
    data : dict
        치환 필드:
          structure_name, discipline, issue_description,
          img_1_title, img_2_title
    images : dict, optional
        {"image1": "/path/to/left.png", "image2": "/path/to/right.png"}
        키는 binaryItemIDRef 값 ("image1" | "image2")
    report_prefix : str
        출력 파일명 접두사

    Returns
    -------
    dict
        {
          "success": bool,
          "output_path": str,   # 생성된 파일의 절대경로
          "report_id": str,     # 8자리 고유 ID (DB 키로 활용 가능)
          "warnings": list[str]
        }
    """
    warnings = []

    template_path = str(Path(template_path).resolve())
    if not os.path.exists(template_path):
        return {
            "success": False, "output_path": None, "report_id": None,
            "warnings": [f"[오류] 템플릿 없음: {template_path}"],
        }

    os.makedirs(output_dir, exist_ok=True)
    report_id   = uuid.uuid4().hex[:8]
    output_path = os.path.join(output_dir, f"{report_prefix}_{report_id}.hwpx")
    shutil.copy2(template_path, output_path)

    overrides: dict = {}

    try:
        with zipfile.ZipFile(output_path, "r") as zf:

            # A. 텍스트 치환
            with zf.open(SECTION_XML_PATH) as f:
                xml_content = f.read().decode("utf-8")
            xml_content, fw = _apply_text_fields(xml_content, data)
            warnings.extend(fw)
            overrides[SECTION_XML_PATH] = xml_content.encode("utf-8")

            # B. 이미지 교체
            if images:
                with zf.open(MANIFEST_PATH) as f:
                    manifest_xml = f.read().decode("utf-8")

                for image_id, source_path in images.items():
                    if image_id not in IMAGE_SLOTS:
                        warnings.append(f"[경고] 알 수 없는 슬롯 ID: '{image_id}'")
                        continue
                    if not os.path.exists(source_path):
                        warnings.append(f"[경고] 이미지 없음: '{source_path}'")
                        continue
                    ext = Path(source_path).suffix.lower()
                    if ext not in MIME_MAP:
                        warnings.append(f"[경고] 미지원 포맷: '{ext}'")
                        continue

                    manifest_xml, zip_target = _update_manifest(manifest_xml, image_id, source_path)
                    with open(source_path, "rb") as img_f:
                        overrides[zip_target] = img_f.read()

                    old_slot = IMAGE_SLOTS[image_id]
                    if zip_target != old_slot:
                        overrides[old_slot] = None  # 기존 슬롯 삭제

                    warnings.append(f"[정보] 이미지 교체: {image_id} → {zip_target}")

                overrides[MANIFEST_PATH] = manifest_xml.encode("utf-8")

        # C. 중복 없는 재패킹
        _repack_zip(output_path, overrides)

    except KeyError as e:
        return {
            "success": False, "output_path": None, "report_id": report_id,
            "warnings": [f"[오류] HWPX 내부 경로 없음: {e}"],
        }
    except Exception as e:
        return {
            "success": False, "output_path": None, "report_id": report_id,
            "warnings": [f"[오류] {type(e).__name__}: {e}"],
        }

    return {
        "success": True,
        "output_path": os.path.abspath(output_path),
        "report_id": report_id,
        "warnings": warnings,
    }


def validate_template(template_path: str) -> dict:
    """템플릿 HWPX 정합성 점검 — 배포 전 헬스체크용."""
    issues, found_fields, found_images = [], [], []
    if not os.path.exists(template_path):
        return {"valid": False, "found_fields": [], "found_images": [],
                "issues": [f"파일 없음: {template_path}"]}
    try:
        with zipfile.ZipFile(template_path, "r") as zf:
            namelist = zf.namelist()
            if SECTION_XML_PATH in namelist:
                with zf.open(SECTION_XML_PATH) as f:
                    xml = f.read().decode("utf-8")
                found_fields = PLACEHOLDER_RE.findall(xml)
            else:
                issues.append(f"'{SECTION_XML_PATH}' 없음")
            for img_id, slot_path in IMAGE_SLOTS.items():
                if slot_path in namelist:
                    found_images.append(f"{img_id} → {slot_path}")
                else:
                    issues.append(f"이미지 슬롯 없음: '{slot_path}'")
            for field in REQUIRED_FIELDS:
                if field not in found_fields:
                    issues.append(f"필수 필드 누락: '{{{{{field}}}}}'")
            if MANIFEST_PATH not in namelist:
                issues.append(f"매니페스트 없음: '{MANIFEST_PATH}'")
    except zipfile.BadZipFile:
        issues.append("올바른 HWPX(ZIP) 파일이 아닙니다.")
    return {
        "valid": len(issues) == 0,
        "found_fields": found_fields,
        "found_images": found_images,
        "issues": issues,
    }


# ──────────────────────────────────────────────
# 스캐폴딩 호환 어댑터 클래스
# (스캐폴딩이 HwpxManager / fill_text_fields() 인터페이스를 기대하는 경우)
# ──────────────────────────────────────────────

class HwpxManager:
    """
    스캐폴딩 호환 래퍼 클래스.
    service.py 에서 generate_bim_report() 를 직접 쓰는 것을 권장하지만,
    스캐폴딩 생성 코드가 HwpxManager 를 import 하고 있다면 이 클래스를 사용.

    사용 예:
        mgr = HwpxManager("templates_hwpx/template.hwpx")
        mgr.fill_text_fields({...})
        mgr.replace_image("image1", "path/to/img.png")
        result = mgr.save("/tmp/out", "BIM_Issue_Report")
    """

    def __init__(self, template_path: str):
        self._template_path = template_path
        self._data: dict    = {}
        self._images: dict  = {}

    def fill_text_fields(self, data: dict) -> "HwpxManager":
        """스캐폴딩 인터페이스 호환: 텍스트 필드 데이터를 등록."""
        self._data.update(data)
        return self

    def replace_image(self, slot_id: str, source_path: str) -> "HwpxManager":
        """스캐폴딩 인터페이스 호환: 이미지 슬롯 등록."""
        self._images[slot_id] = source_path
        return self

    def save(self, output_dir: str, prefix: str = "BIM_Issue_Report") -> dict:
        """등록된 데이터로 보고서를 생성."""
        return generate_bim_report(
            template_path=self._template_path,
            output_dir=output_dir,
            data=self._data,
            images=self._images or None,
            report_prefix=prefix,
        )


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser(description="BIM 이슈 보고서 생성 CLI")
    sub = parser.add_subparsers(dest="cmd")

    vp = sub.add_parser("validate", help="템플릿 정합성 점검")
    vp.add_argument("template")

    gp = sub.add_parser("generate", help="보고서 생성")
    gp.add_argument("template")
    gp.add_argument("--output-dir",        default="output")
    gp.add_argument("--structure-name",    required=True)
    gp.add_argument("--discipline",        required=True)
    gp.add_argument("--issue-description", required=True)
    gp.add_argument("--img-1-title",       default="이미지 1")
    gp.add_argument("--img-2-title",       default="이미지 2")
    gp.add_argument("--image1",            default=None)
    gp.add_argument("--image2",            default=None)

    args = parser.parse_args()

    if args.cmd == "validate":
        print(json.dumps(validate_template(args.template), ensure_ascii=False, indent=2))

    elif args.cmd == "generate":
        d = {
            "structure_name":    args.structure_name,
            "discipline":        args.discipline,
            "issue_description": args.issue_description,
            "img_1_title":       args.img_1_title,
            "img_2_title":       args.img_2_title,
        }
        imgs = {}
        if args.image1: imgs["image1"] = args.image1
        if args.image2: imgs["image2"] = args.image2
        result = generate_bim_report(args.template, args.output_dir, d, imgs or None)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()
