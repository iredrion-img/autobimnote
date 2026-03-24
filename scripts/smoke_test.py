"""
scripts/smoke_test.py
=====================
서버 없이 엔진만 직접 검증하는 스모크 테스트.

실행 (bim-reporter-saas/ 루트에서):
  python scripts/smoke_test.py

성공 기준:
  1. 템플릿 HWPX 정합성 점검 통과
  2. 보고서 생성 성공 (output/smoke/ 에 .hwpx 파일 생성)
  3. 생성 파일 내부 XML에 플레이스홀더 잔재 없음
  4. linesegarray 초기화 확인
  5. 오류 처리 확인 (템플릿 없는 경우)
"""

import os
import sys
import zipfile
import re
from pathlib import Path

# 프로젝트 루트를 기준으로 engine 경로 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

from xml_manager import generate_bim_report, validate_template, HwpxManager

TEMPLATE    = str(ROOT / "templates_hwpx" / "template.hwpx")
OUTPUT_DIR  = str(ROOT / "output" / "smoke")

SAMPLE = {
    "structure_name":    "OO대교 취수탑 배관",
    "discipline":        "기계/배관",
    "issue_description": (
        "취수탑 D700(S.P) 배관 BOP EL.(+)29.60 구간에서\n"
        "설계도면과 BIM 모델 간 배관 경로 불일치 확인.\n"
        "정합성 검토 및 설계 변경 요청."
    ),
    "img_1_title": "설계 도면 (평면도)",
    "img_2_title": "BIM 모델 검토 뷰",
}

PASS, FAIL = "✅", "❌"
_results: list[bool] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    mark = PASS if ok else FAIL
    msg  = f"  {mark} {label}"
    if detail:
        msg += f"  →  {detail}"
    print(msg)
    _results.append(ok)
    return ok


# ── 테스트 1: 템플릿 정합성 ─────────────────────────────────────────────────
def t1_validate():
    print("\n[1] 템플릿 정합성 점검")
    res = validate_template(TEMPLATE)
    check("valid=True",        res["valid"])
    check("필드 5개 감지",     len(res["found_fields"]) == 5,  str(res["found_fields"]))
    check("이미지 슬롯 2개",   len(res["found_images"]) == 2,  str(res["found_images"]))
    for issue in res.get("issues", []):
        print(f"     ⚠  {issue}")


# ── 테스트 2: 보고서 생성 ────────────────────────────────────────────────────
def t2_generate():
    print("\n[2] 보고서 생성 (이미지 없음)")
    res = generate_bim_report(TEMPLATE, OUTPUT_DIR, SAMPLE)
    ok_gen = check("success=True",       res["success"])
    check("output_path 존재", os.path.exists(res.get("output_path") or ""))

    if ok_gen and res["output_path"]:
        with zipfile.ZipFile(res["output_path"]) as zf:
            with zf.open("Contents/section0.xml") as f:
                xml = f.read().decode("utf-8")

        remaining = re.findall(r"\{\{[^}]+\}\}", xml)
        check("플레이스홀더 전부 치환",   len(remaining) == 0,
              f"남은 항목: {remaining}" if remaining else "")
        check("구조물명 XML 포함",        "OO대교 취수탑 배관" in xml)
        check("linesegarray 초기화",      "<hp:linesegarray/>" in xml)

        for w in res.get("warnings", []):
            print(f"     ℹ  {w}")
    else:
        for w in res.get("warnings", []):
            print(f"     ❌  {w}")


# ── 테스트 3: HwpxManager 어댑터 ────────────────────────────────────────────
def t3_adapter():
    print("\n[3] HwpxManager 어댑터")
    mgr = HwpxManager(TEMPLATE)
    mgr.fill_text_fields(SAMPLE)
    res = mgr.save(OUTPUT_DIR, prefix="Smoke_Adapter")
    check("HwpxManager.save() success", res["success"])
    check("output_path 존재",           os.path.exists(res.get("output_path") or ""))


# ── 테스트 4: 템플릿 누락 오류 처리 ─────────────────────────────────────────
def t4_missing_template():
    print("\n[4] 템플릿 누락 오류 처리")
    res = generate_bim_report("nonexistent.hwpx", OUTPUT_DIR, SAMPLE)
    check("success=False",          not res["success"])
    check("warnings에 오류 메시지", len(res.get("warnings", [])) > 0)


# ── 진입점 ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{'='*55}")
    print(f"  BIM Reporter SaaS – Engine Smoke Test")
    print(f"  템플릿: {TEMPLATE}")
    print(f"{'='*55}")

    if not os.path.exists(TEMPLATE):
        print(f"\n⚠  템플릿 없음: {TEMPLATE}")
        print("   templates_hwpx/template.hwpx 를 배치한 후 재실행하세요.\n")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    t1_validate()
    t2_generate()
    t3_adapter()
    t4_missing_template()

    passed = sum(_results)
    total  = len(_results)
    print(f"\n{'='*55}")
    result_str = "전체 통과 🎉" if passed == total else f"{total - passed}개 실패"
    print(f"  결과: {passed}/{total}  {result_str}")
    print(f"{'='*55}\n")
    sys.exit(0 if passed == total else 1)
