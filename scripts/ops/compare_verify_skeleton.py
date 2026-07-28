#!/usr/bin/env python3
"""verify-pair 로그 사이클의 PRE/A/B/C 골격(형식·항목 집합) IDENTICAL 비교.

OPS-ISO-CLOSE §3: repoint 전후 라이브 로그가 section D 추가분을 제외하면
PRE/A/B/C 섹션의 형식·항목 집합이 동일함을 입증(검사 대상 데이터 차이는 정규화 제외).

사용:
  python scripts/ops/compare_verify_skeleton.py <log_path> "<old_ts_prefix>" "<new_ts_prefix>"
  예: ... verify-pair.log "2026-07-27 02:30" "2026-07-28 02:30"

판정: 두 골격 diff == 0 (단, 신 사이클의 section D 라인은 골격에서 제외) → IDENTICAL PASS.
"""
import re
import sys


def extract_cycle(text, ts_prefix):
    """헤더 '===== [<ts_prefix>...] ='부터 다음 '=====' 직전까지 사이클 라인 목록."""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("===== [") and ts_prefix in ln:
            start = i
            break
    if start is None:
        raise SystemExit(f"[compare] 사이클 미발견: '{ts_prefix}'")
    out = [lines[start]]
    for ln in lines[start + 1:]:
        if ln.startswith("===== ["):
            break
        out.append(ln)
    return out


def normalize(lines):
    """데이터 값을 자리표시자로 치환하고 section D(추가분)를 제거 → 골격만 남김."""
    skel = []
    for ln in lines:
        # section D 추가분(라인 + 그 상세 ALERT/info)은 골격 비교에서 제외
        if "D(ops isolation)" in ln:
            continue
        if re.search(r"\[ALERT\]|stale 마커|worker tree drift|코드버전 괴리", ln):
            continue
        s = ln
        s = re.sub(r"^===== \[.*?\] (.+) =====$", r"===== [<TS>] \1 =====", s)
        s = re.sub(r"(PASS|WARN|FAIL) @ .*? UTC", r"<STATUS> @ <TS> UTC", s)
        s = re.sub(r"경계 .*? EDT", "경계 <DATE> EDT", s)
        s = re.sub(r"최신 period=[\d-]+, period 수=\d+",
                   "최신 period=<DATE>, period 수=<N>", s)
        s = re.sub(r"\d{4}-\d\d-\d\d\s*→\s*\d+행", "<DATE> → <N>행", s)
        s = re.sub(r"succeeded=\d+ unregistered=\d+",
                   "succeeded=<N> unregistered=<N>", s)
        skel.append(s)
    return skel


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    log_path, old_ts, new_ts = sys.argv[1:4]
    with open(log_path, encoding="utf-8") as f:
        text = f.read()
    old = normalize(extract_cycle(text, old_ts))
    new = normalize(extract_cycle(text, new_ts))
    print(f"=== OLD 골격 ({old_ts}) ===")
    print("\n".join(old))
    print(f"\n=== NEW 골격 ({new_ts}, section D 제외) ===")
    print("\n".join(new))
    print("\n=== 판정 ===")
    if old == new:
        print("✅ IDENTICAL — PRE/A/B/C 형식·항목 집합 동일(diff=0). section D 추가분만 신에 존재.")
        return 0
    print("❌ DIFF 발견:")
    import difflib
    for d in difflib.unified_diff(old, new, "OLD", "NEW", lineterm=""):
        print(d)
    return 1


if __name__ == "__main__":
    sys.exit(main())
