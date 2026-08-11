"""관계 evidence 한국어 요약 배치 (⑳-3 REVIEW-TOOL-2, 1회성).

review_batch_v2.csv → review_batch_v3.csv (summary_ko·summary_flags 컬럼 추가).
LLM은 **BOUNDARY-LLM 공유 래퍼**(packages.shared.llm.legacy_gemini.generate_with_circuit)
경유만 — 직접 genai 호출 금지. 요약은 "evidence가 무엇을 서술하는가"만(타입 추천·판단 금지).

플래그 하이브리드:
  - 결정론(CSV): truncated(종결부호 부재)·list(is_enumeration)·target_absent(not target_in_basis)
  - LLM 판독: m&a(인수합병 서술)·indirect(간접/주변 언급)
  → union 하여 summary_flags(파이프 구분).

사용:
  python tools/review/generate_summaries.py --dry-run        # LLM 미호출, 결정론 플래그만·요약 placeholder
  python tools/review/generate_summaries.py --limit 10       # 1배치 왕복 테스트(0-3)
  python tools/review/generate_summaries.py                  # 전량(270, ~27콜)

★DB 무접촉. summary_ko는 **표시 전용** — Phase 2 DB 로드 대상 아님(하드 룰 승계).
★human_verdict 등 라벨 컬럼은 이 스크립트가 생성하지 않는다(v2엔 없음, 라벨은 localStorage).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time

IN_DEFAULT = "outputs/domain_tagging/review_batch_v2.csv"
OUT_DEFAULT = "outputs/domain_tagging/review_batch_v3.csv"
BATCH = 10
MAX_RETRY = 3
RATE_SLEEP_S = 4.2  # Gemini free 15 RPM 여유
FAIL_TEXT = "(생성 실패 — 원문 검수)"

# ── 프롬프트 계약(상수) ─────────────────────────────────────────
SYSTEM = (
    "너는 미국 상장사 SEC 10-K 발췌 문장을 요약하는 한국어 금융 애널리스트다.\n"
    "각 문장이 **무엇을 서술하는가**만 한국어 1~2문장으로 중립 요약한다.\n"
    "절대 금지: 관계 타입 추천·적절성 판단·라벨 제안. "
    "'~로 보임', '~가 적절', '~해야', '공급 관계로 판단' 같은 추천·판단 표현 금지. "
    "사실 서술만(누가 누구를/무엇을 언급·경쟁·공급·인수 등).\n"
    "플래그는 해당할 때만 부여: "
    '"m&a"(인수·합병·분사·지분 인수 서술), "indirect"(대상이 직접 아닌 간접/주변/인물 이력 언급).\n'
    "반드시 아래 JSON 배열만 출력(설명·마크다운·코드펜스 금지). "
    "입력 행수와 출력 배열 길이가 정확히 같아야 하고 row_id를 그대로 반영한다:\n"
    '[{"row_id": <정수>, "summary_ko": "<1~2문장>", "flags": ["m&a"|"indirect", ...]}]'
)


def _b(x) -> bool:
    return str(x).strip().lower() in ("true", "1")


def deterministic_flags(row: dict) -> list[str]:
    """CSV 결정론 플래그: truncated·list·target_absent."""
    flags = []
    basis = (row.get("basis") or "").rstrip()
    if not re.search(r"[.!?\"”'’)]$", basis):
        flags.append("truncated")
    if _b(row.get("is_enumeration")):
        flags.append("list")
    if not _b(row.get("target_in_basis")):
        flags.append("target_absent")
    return flags


def parse_llm_array(text: str):
    """LLM 원문 → JSON 배열. 실패 시 None."""
    if not text:
        return None
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    m = re.search(r"\[.*\]", s, re.S)
    if m:
        s = m.group(0)
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, list) else None
    except (json.JSONDecodeError, ValueError):
        return None


def call_batch(rows_slice, start_id, llm_call):
    """한 배치(≤10행) 요약. (results dict row_id->{summary_ko,llm_flags}, ok) 반환."""
    payload = [
        {"row_id": start_id + i, "evidence": (r.get("basis") or "")}
        for i, r in enumerate(rows_slice)
    ]
    user = "다음 SEC 발췌들을 각각 요약하라(JSON 배열, 행수 동일):\n" + json.dumps(
        payload, ensure_ascii=False
    )
    for attempt in range(1, MAX_RETRY + 1):
        raw = llm_call(SYSTEM, [user])
        arr = parse_llm_array(raw)
        if arr is not None and len(arr) == len(rows_slice):
            out = {}
            ok = True
            for item in arr:
                try:
                    rid = int(item.get("row_id"))
                except (TypeError, ValueError):
                    ok = False
                    break
                summ = str(item.get("summary_ko") or "").strip()
                fl = item.get("flags") or []
                fl = [str(f).strip() for f in fl if str(f).strip() in ("m&a", "indirect")]
                out[rid] = {"summary_ko": summ, "llm_flags": fl}
            if ok and all((start_id + i) in out for i in range(len(rows_slice))):
                return out, True
        sys.stderr.write(
            f"  [배치 {start_id}] 재시도 {attempt}/{MAX_RETRY} "
            f"(파싱/행수 불일치: got={None if arr is None else len(arr)}/{len(rows_slice)})\n"
        )
        time.sleep(RATE_SLEEP_S)
    return {}, False  # 실패


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=IN_DEFAULT)
    ap.add_argument("--out", dest="out", default=OUT_DEFAULT)
    ap.add_argument("--limit", type=int, default=0, help="앞 N행만(0=전량)")
    ap.add_argument("--dry-run", action="store_true", help="LLM 미호출(결정론 플래그만)")
    args = ap.parse_args()

    with open(args.inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames[:]
        rows = list(reader)
    if args.limit:
        rows = rows[: args.limit]
    n = len(rows)
    print(f"입력 {n}행 (dry_run={args.dry_run}, batch={BATCH})")

    # LLM 콜러블(래퍼 경유)
    llm_call = None
    calls = 0
    prompt_tokens = 0
    completion_tokens = 0
    if not args.dry_run:
        import django

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()
        from packages.shared.llm.legacy_gemini import generate_with_circuit

        stats = {"c": 0, "p": 0, "o": 0}

        def llm_call(system, contents):
            resp = generate_with_circuit(system_instruction=system, contents=contents)
            stats["c"] += 1
            stats["p"] += getattr(resp, "prompt_tokens", 0)
            stats["o"] += getattr(resp, "completion_tokens", 0)
            return getattr(resp, "text", "") or ""

    # 배치 처리
    summaries = {}  # global_index -> {summary_ko, flags[]}
    failed = 0
    for b0 in range(0, n, BATCH):
        chunk = rows[b0 : b0 + BATCH]
        det = [deterministic_flags(r) for r in chunk]
        if args.dry_run:
            for i, r in enumerate(chunk):
                summaries[b0 + i] = {
                    "summary_ko": "(dry-run placeholder)",
                    "flags": det[i],
                }
            continue
        res, ok = call_batch(chunk, b0, llm_call)
        for i, r in enumerate(chunk):
            gid = b0 + i
            if ok and gid in res:
                fl = sorted(set(det[i]) | set(res[gid]["llm_flags"]))
                summaries[gid] = {"summary_ko": res[gid]["summary_ko"] or FAIL_TEXT, "flags": fl}
                if not res[gid]["summary_ko"]:
                    failed += 1
            else:
                summaries[gid] = {"summary_ko": FAIL_TEXT, "flags": det[i]}
                failed += 1
        done = min(b0 + BATCH, n)
        print(f"  배치 {b0//BATCH+1}/{(n+BATCH-1)//BATCH} → {done}/{n} (실패누적 {failed})")
        if not args.dry_run:
            time.sleep(RATE_SLEEP_S)

    # ── v3 CSV 산출(원본 전 컬럼 + summary_ko·summary_flags) ──
    new_cols = header[:]
    for c in ("summary_ko", "summary_flags"):
        if c not in new_cols:
            new_cols.append(c)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=new_cols)
        w.writeheader()
        for i, r in enumerate(rows):
            s = summaries.get(i, {"summary_ko": FAIL_TEXT, "flags": []})
            rec = dict(r)
            rec["summary_ko"] = s["summary_ko"]
            rec["summary_flags"] = "|".join(s["flags"])
            w.writerow(rec)

    # ── 통계 ──
    from collections import Counter

    flag_dist = Counter()
    for s in summaries.values():
        for fl in s["flags"]:
            flag_dist[fl] += 1
    print("\n=== 통계 ===")
    print(f"출력: {args.out} ({n}행, 컬럼 {len(new_cols)})")
    if not args.dry_run:
        print(f"LLM 콜: {stats['c']} · prompt_tokens {stats['p']} · completion_tokens {stats['o']}")
    print(f"생성 실패 행: {failed}")
    print(f"플래그 분포: {dict(flag_dist)}")


if __name__ == "__main__":
    main()
