"""표적 재추출 + 3부 요약 재생성 (⑳-3 REVIEW-TOOL-3, 1회성).

review_batch_v3.csv → review_batch_v4.csv. **DB 읽기 전용**(쓰기 0).
전문은 이미 DB에 존재 → EDGAR 재방문 불필요(STEP 0 게이트: 저장분 활용).
  - full_evidence: SupplyChainEvidence.evidence_text(무캡) + item 전문 ±1문장 맥락.
  - source_line: filer·FY·섹션(결정론 메타).
  - summary_ko(재생성): 3부 중 '서술'(전체 문장 기준). roles_ko: '역할'. 출처는 결정론.
  - decision_hint: 플래그 파생 사전 정의 문구(결정론, 타입 추천 아님).
basis는 **절대 불변**(rowKey 구성요소) — 재추출문은 별도 컬럼(full_evidence).
LLM은 BOUNDARY-LLM 래퍼 경유, 요약에 타입 추천·판단 금지(v2 계약 승계).

사용:
  python tools/review/build_v4.py --dry-run   # DB만(재추출·힌트), LLM 미호출
  python tools/review/build_v4.py             # 전량(재추출 + 요약 재생성)
"""
from __future__ import annotations
import argparse, csv, json, os, re, sys, time

IN_DEFAULT = "outputs/domain_tagging/review_batch_v3.csv"
OUT_DEFAULT = "outputs/domain_tagging/review_batch_v4.csv"
BATCH = 10
MAX_RETRY = 3
RATE_SLEEP_S = 4.2
GEN_FAIL = "(전문 확보 실패 — 절단본 기준)"

SYSTEM = (
    "너는 미국 상장사 SEC 10-K '전체 문장'을 읽는 한국어 금융 애널리스트다.\n"
    "각 항목에 대해 아래 둘을 사실만으로 작성한다:\n"
    "- narration_ko: 전체 문장이 서술하는 바를 한국어 1~2문장(중립 사실).\n"
    "- roles_ko: 주어진 두 심볼(symbol_a, symbol_b)이 이 문장에서 각각 어떤 자격으로 "
    "등장하는지 짧게. 문장에 없으면 '<심볼> 미등장'이라고 명시.\n"
    "절대 금지: 관계 타입 추천·적절성 판단·라벨 제안. "
    "'~로 보임','~가 적절','~해야','공급 관계로 판단' 등 추천·판단 표현 금지.\n"
    'flags는 해당 시에만: "m&a"(인수·합병·분사), "indirect"(간접/주변/인물 이력 언급).\n'
    "반드시 JSON 배열만 출력(마크다운·코드펜스 금지). 입력 행수와 출력 길이가 정확히 같고 "
    "row_id를 그대로 반영:\n"
    '[{"row_id":<int>,"narration_ko":"...","roles_ko":"...","flags":["m&a"|"indirect"]}]'
)

# 결정 힌트(사전 정의만 — 신규 문구 추가 금지)
HINT_TARGET_ABSENT = "근거 문장에 상대 종목 미등장 — 관계 근거로 불충분"
HINT_MA_LIST = "업계 M&A 나열 — 두 종목 직접 관계 서술인지 확인"


def _b(x):
    return str(x).strip().lower() in ("true", "1")


def deterministic_flags(row):
    flags = []
    basis = (row.get("basis") or "").rstrip()
    if not re.search(r"[.!?\"”'’)]$", basis):
        flags.append("truncated")
    if _b(row.get("is_enumeration")):
        flags.append("list")
    if not _b(row.get("target_in_basis")):
        flags.append("target_absent")
    return flags


def decision_hint(flags: list[str], full_ok: bool) -> str:
    """결정론 힌트(사전 정의 문구만)."""
    if "target_absent" in flags:
        return HINT_TARGET_ABSENT
    if "m&a" in flags and "list" in flags:
        return HINT_MA_LIST
    # truncated ∧ 전문 확보 → 힌트 없음(전문이 있으면 불요)
    return ""


def sentence_window(item_text: str, sentence: str) -> str:
    """item 전문에서 sentence 위치 → ±1문장 확장(best-effort). 실패 시 sentence."""
    if not item_text or not sentence:
        return sentence
    core = sentence[:60]
    idx = item_text.find(core)
    if idx < 0:
        return sentence
    # 왼쪽: 직전 문장 종결부호 다음부터
    left = item_text.rfind(". ", max(0, idx - 400), idx)
    start = left + 2 if left >= 0 else idx
    # 오른쪽: 문장 끝 + 다음 문장 끝
    end_sent = item_text.find(". ", idx + len(sentence) - 5)
    nxt = item_text.find(". ", end_sent + 2) if end_sent >= 0 else -1
    end = (nxt + 1) if nxt >= 0 else (end_sent + 1 if end_sent >= 0 else idx + len(sentence))
    win = item_text[start:end].strip()
    return win if len(win) >= len(sentence) else sentence


def parse_arr(text):
    if not text:
        return None
    s = re.sub(r"^```(?:json)?\s*", "", text.strip())
    s = re.sub(r"\s*```$", "", s)
    m = re.search(r"\[.*\]", s, re.S)
    if m:
        s = m.group(0)
    try:
        o = json.loads(s)
        return o if isinstance(o, list) else None
    except (json.JSONDecodeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=IN_DEFAULT)
    ap.add_argument("--out", dest="out", default=OUT_DEFAULT)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # Django (DB 읽기 + LLM 래퍼)
    import django
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from services.sec_pipeline.models import SupplyChainEvidence

    with open(args.inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames[:]
        rows = list(reader)
    if args.limit:
        rows = rows[: args.limit]
    n = len(rows)
    print(f"입력 {n}행 (dry_run={args.dry_run})")

    # ── 재추출: 행별 매칭 → full_evidence·source_line ──
    reext = {}       # i -> {full_evidence, source_line, filer, sym_a, sym_b, matched}
    matched = 0
    for i, r in enumerate(rows):
        basis = r["basis"]
        b100 = basis[len("SEC 10-K: "):] if basis.startswith("SEC 10-K: ") else basis
        a, _, b = (r["symbol_pair"] + "↔").partition("↔")
        b = b.rstrip("↔")
        cands = list(
            SupplyChainEvidence.objects.filter(evidence_text__startswith=b100)
            .select_related("source_document", "source_company")
        )
        ev = None
        for c in cands:
            if c.source_company_id in (a, b):
                ev = c
                break
        if ev is None and cands:
            ev = cands[0]
        if ev is None:
            reext[i] = {"full_evidence": "", "source_line": "", "matched": False,
                        "sym_a": a, "sym_b": b}
            continue
        matched += 1
        sd = ev.source_document
        item = ""
        section = ""
        if sd:
            for txt, name in ((sd.item_1_text, "Item 1 사업"), (sd.item_1a_text, "Item 1A 위험"),
                              (sd.item_7_text, "Item 7 MD&A")):
                if txt and ev.evidence_text[:60] in txt:
                    item, section = txt, name
                    break
        full = sentence_window(item, ev.evidence_text) if item else ev.evidence_text
        filer = ev.source_company_id or "?"
        fy = sd.fiscal_year if sd else "?"
        src = f"{filer} 10-K FY{fy}" + (f" · {section}" if section else "")
        reext[i] = {"full_evidence": full, "source_line": src, "matched": True,
                    "sym_a": a, "sym_b": b}
    print(f"재추출 매칭: {matched}/{n}")

    # ── LLM 3부 요약(서술+역할) ──
    summaries = {}
    calls = {"c": 0, "p": 0, "o": 0}
    gen_fail = 0
    if not args.dry_run:
        from apps.market_pulse.llm.client import generate_with_circuit

        def llm_call(system, contents):
            resp = generate_with_circuit(system_instruction=system, contents=contents)
            calls["c"] += 1
            calls["p"] += getattr(resp, "prompt_tokens", 0)
            calls["o"] += getattr(resp, "completion_tokens", 0)
            return getattr(resp, "text", "") or ""

        for b0 in range(0, n, BATCH):
            chunk = list(range(b0, min(b0 + BATCH, n)))
            payload = [
                {"row_id": gid, "symbol_a": reext[gid]["sym_a"], "symbol_b": reext[gid]["sym_b"],
                 "evidence": reext[gid]["full_evidence"] or rows[gid]["basis"]}
                for gid in chunk
            ]
            user = "다음 전체 문장들을 각각 서술·역할로(JSON 배열, 행수 동일):\n" + json.dumps(
                payload, ensure_ascii=False)
            ok = False
            for _ in range(MAX_RETRY):
                arr = parse_arr(llm_call(SYSTEM, [user]))
                if arr and len(arr) == len(chunk):
                    m = {}
                    good = True
                    for it in arr:
                        try:
                            rid = int(it.get("row_id"))
                        except (TypeError, ValueError):
                            good = False
                            break
                        fl = [f for f in (it.get("flags") or []) if f in ("m&a", "indirect")]
                        m[rid] = {"narration": str(it.get("narration_ko") or "").strip(),
                                  "roles": str(it.get("roles_ko") or "").strip(), "llm_flags": fl}
                    if good and all(g in m for g in chunk):
                        for gid in chunk:
                            summaries[gid] = m[gid]
                        ok = True
                        break
                time.sleep(RATE_SLEEP_S)
            if not ok:
                for gid in chunk:
                    summaries[gid] = {"narration": "", "roles": "", "llm_flags": []}
                    gen_fail += 1
            print(f"  배치 {b0//BATCH+1}/{(n+BATCH-1)//BATCH} (gen_fail {gen_fail})")
            time.sleep(RATE_SLEEP_S)

    # ── v4 CSV(원본 전 컬럼 불변 + full_evidence·source_line·roles_ko·decision_hint, summary_ko 재생성) ──
    add_cols = ["full_evidence", "source_line", "roles_ko", "decision_hint"]
    new_cols = header[:] + [c for c in add_cols if c not in header]
    from collections import Counter
    hint_dist = Counter()
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=new_cols)
        w.writeheader()
        for i, r in enumerate(rows):
            rec = dict(r)
            rx = reext.get(i, {})
            det = deterministic_flags(r)
            s = summaries.get(i, {"narration": "", "roles": "", "llm_flags": []})
            # summary_flags = 결정론 ∪ LLM
            flags = sorted(set(det) | set(s.get("llm_flags", [])))
            rec["summary_flags"] = "|".join(flags)
            hint = decision_hint(flags, rx.get("matched", False))
            hint_dist[hint or "(없음)"] += 1
            rec["full_evidence"] = rx.get("full_evidence", "") or r["basis"]
            rec["source_line"] = rx.get("source_line", "")
            rec["decision_hint"] = hint
            if args.dry_run:
                rec["roles_ko"] = ""
                # dry-run: summary_ko는 v3 유지
            else:
                narr = s.get("narration", "")
                if narr:
                    rec["summary_ko"] = narr
                    rec["roles_ko"] = s.get("roles", "")
                else:
                    # 생성 실패 → v3 요약 유지 + 표기
                    rec["summary_ko"] = (r.get("summary_ko") or "").strip() or GEN_FAIL
                    rec["roles_ko"] = GEN_FAIL
            w.writerow(rec)

    print("\n=== 통계 ===")
    print(f"출력: {args.out} ({n}행, 컬럼 {len(new_cols)})")
    print(f"재추출 매칭: {matched}/{n} · 전문>캡: {sum(1 for i in reext if len(reext[i].get('full_evidence',''))>110)}")
    if not args.dry_run:
        print(f"LLM 콜: {calls['c']} · tokens p{calls['p']}/o{calls['o']} · 생성실패 {gen_fail}")
    print(f"힌트 분포: {dict(hint_dist)}")


if __name__ == "__main__":
    main()
