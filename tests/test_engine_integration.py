"""
tests/test_engine_integration.py
=================================
엔진 통합 테스트 — 서버 없이 엔진 직접 호출.

실행:
  cd bim-reporter-saas
  python tests/test_engine_integration.py
"""

import os
import sys
import zipfile
import re
from pathlib import Path

# engine/ 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from xml_manager import generate_bim_report, validate_template, HwpxManager

TEMPLATE = "templates_hwpx/template.hwpx"
OUTPUT   = "output/test"

SAMPLE_DATA = {
    "structure_name":    "OO대교 취수탑 배관",
    "discipline":        "기계/배관",
    "issue_description": (
        "취수탑 D700(S.P) 배관 BOP EL.(+)29.60 구간에서 "
        "설계도면과 BIM 모델 간 배관 경로 불일치 확인.\n"
        "도면상 수평 직선 구간이 모델에서는 엘보 연결로 처리되어 있음.\n"
        "정합성 검토 및 설계 변경 요청."
    ),
    "img_1_title": "설계 도면 (평면)",
    "img_2_title": "BIM 모델 검토 뷰",
}


def _check(label: str, condition: bool, detail: str = "") -> bool:
    mark = "✅" if condition else "❌"
    print(f"  {mark} {label}" + (f" — {detail}" if detail else ""))
    return condition


def test_validate_template():
    print("\n[1] 템플릿 정합성 점검")
    result = validate_template(TEMPLATE)
    ok = True
    ok &= _check("템플릿 valid", result["valid"])
    ok &= _check("필드 5개 감지", len(result["found_fields"]) == 5,
                 str(result["found_fields"]))
    ok &= _check("이미지 슬롯 2개 감지", len(result["found_images"]) == 2,
                 str(result["found_images"]))
    if result["issues"]:
        for issue in result["issues"]:
            print(f"     ⚠ {issue}")
    return ok


def test_generate_report():
    print("\n[2] 보고서 생성 (이미지 없음)")
    result = generate_bim_report(TEMPLATE, OUTPUT, SAMPLE_DATA)
    ok = True
    ok &= _check("success=True", result["success"])
    ok &= _check("output_path 존재", os.path.exists(result["output_path"] or ""))

    if result["success"]:
        # 내용 검증
        with zipfile.ZipFile(result["output_path"]) as zf:
            with zf.open("Contents/section0.xml") as f:
                xml = f.read().decode("utf-8")

        remaining = re.findall(r"\{\{[^}]+\}\}", xml)
        ok &= _check("플레이스홀더 전부 치환", len(remaining) == 0,
                     f"남은 항목: {remaining}")
        ok &= _check("구조물명 포함", "OO대교 취수탑 배관" in xml)
        ok &= _check("linesegarray 초기화", "<hp:linesegarray/>" in xml)

    if result["warnings"]:
        for w in result["warnings"]:
            print(f"     ℹ {w}")
    return ok


def test_hwpx_manager_adapter():
    print("\n[3] HwpxManager 어댑터 (스캐폴딩 호환)")
    mgr = HwpxManager(TEMPLATE)
    mgr.fill_text_fields(SAMPLE_DATA)

    result = mgr.save(OUTPUT, prefix="BIM_Test_Adapter")
    ok = True
    ok &= _check("HwpxManager.save() success", result["success"])
    ok &= _check("output_path 존재", os.path.exists(result["output_path"] or ""))
    return ok


def test_missing_template():
    print("\n[4] 템플릿 없음 — 오류 처리")
    result = generate_bim_report("nonexistent.hwpx", OUTPUT, SAMPLE_DATA)
    ok = _check("success=False", not result["success"])
    ok &= _check("warnings에 오류 메시지", len(result["warnings"]) > 0)
    return ok


if __name__ == "__main__":
    os.makedirs(OUTPUT, exist_ok=True)

    if not os.path.exists(TEMPLATE):
        print(f"\n⚠ 템플릿 없음: '{TEMPLATE}'")
        print("  templates_hwpx/template.hwpx 를 배치한 후 재실행하세요.\n")
        sys.exit(1)

    results = [
        test_validate_template(),
        test_generate_report(),
        test_hwpx_manager_adapter(),
        test_missing_template(),
    ]

    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*40}")
    print(f"결과: {passed}/{total} 통과")
    print("=" * 40)
    sys.exit(0 if passed == total else 1)
