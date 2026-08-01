"""관계 1차 분류 제안 (⑳-3 REVIEW-TOOL-5, 1회성).

입력=검수 진행분 labeled CSV(병진 A' human_verdict 보존) → review_batch_v6.csv.
LLM이 문단+프로필(산업)로 각 행을 분류 → suggested_verdict 제안(병진 확인/오버라이드).
규칙(디렉터 지정):
  - KEEP: 문단이 두 회사 간 관계(경쟁/공급/구매/의존/제휴/인수)를 **명시적 서술** → 제안 OK.
  - DROP: 두 회사가 **다른 산업군**이고 실제 관계 서술 없음(인물약력·무관·나열 오매칭) → 제안 DROP.
  - HOLD: 명시적 관계 서술 없으나 같은/인접 산업이라 모호 → 제안 HOLD.
human_verdict 불변(제안은 별도 컬럼). 타입 enum·추천 금지. LLM=래퍼 경유.

사용:
  python tools/review/classify_verdicts.py --in <labeled.csv>   # 전량 분류
  python tools/review/classify_verdicts.py --in <labeled.csv> --dry-run
"""
from __future__ import annotations
import argparse, csv, json, os, re, sys, time

OUT_DEFAULT = "outputs/domain_tagging/review_batch_v6.csv"
BATCH = 8
MAX_RETRY = 3
RATE_SLEEP_S = 4.2
MAP = {"KEEP": "OK", "HOLD": "HOLD", "DROP": "DROP"}

SYSTEM = (
    "너는 SEC 10-K 문단과 두 회사 프로필(산업 포함)을 읽고 두 회사의 관계를 1차 분류하는 "
    "한국어 애널리스트다. 각 항목을 아래 중 하나로 분류한다:\n"
    "- KEEP: 문단이 두 회사 간 관계(경쟁·공급·구매·의존·제휴·인수 등)를 **명시적으로 서술**함.\n"
    "- DROP: 두 회사가 **다른 산업군**이고 문단이 실제 관계를 서술하지 않음"
    "(인물 약력·무관한 서술·나열 속 우연 매칭 포함).\n"
    "- HOLD: 두 회사 간 명시적 관계 서술이 **없으나** 같은/인접 산업이라 모호함.\n"
    "판단 근거는 **문단과 프로필뿐**. 관계 명시 여부가 최우선, 산업 이질성은 DROP 보조 근거.\n"
    "금지: 관계 타입 명칭(SUPPLIES_TO 등) 사용, 타입 추천.\n"
    'JSON 배열만: [{"row_id":<int>,"verdict":"KEEP|HOLD|DROP","reason":"<한국어 한 구>"}] '
    "(입력 수와 동일 길이)."
)


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
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", default=OUT_DEFAULT)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames[:]
        rows = list(reader)
    if args.limit:
        rows = rows[: args.limit]
    n = len(rows)
    print(f"입력 {n}행 · human_verdict 보유 {sum(1 for r in rows if r.get('human_verdict','').strip())}")

    def sp(r):
        a, _, b = (r["symbol_pair"] + "↔").partition("↔")
        return a, b.rstrip("↔")

    sug = {}
    calls = {"c": 0, "p": 0, "o": 0}
    if not args.dry_run:
        import django
        repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if repo not in sys.path:
            sys.path.insert(0, repo)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()
        from apps.market_pulse.llm.client import generate_with_circuit

        def llm(system, user):
            resp = generate_with_circuit(system_instruction=system, contents=[user])
            calls["c"] += 1
            calls["p"] += getattr(resp, "prompt_tokens", 0)
            calls["o"] += getattr(resp, "completion_tokens", 0)
            return getattr(resp, "text", "") or ""

        for b0 in range(0, n, BATCH):
            chunk = list(range(b0, min(b0 + BATCH, n)))
            payload = []
            for gid in chunk:
                r = rows[gid]
                a, b = sp(r)
                payload.append({"row_id": gid, "symbol_a": a, "symbol_b": b,
                                "profile_a": r.get("intro_a", ""), "profile_b": r.get("intro_b", ""),
                                "paragraph": r.get("evidence_paragraph", "") or r.get("full_evidence", "") or r.get("basis", "")})
            user = "다음 각 항목을 KEEP/HOLD/DROP로 분류(JSON 배열, 수 동일):\n" + json.dumps(payload, ensure_ascii=False)
            ok = False
            for _ in range(MAX_RETRY):
                arr = parse_arr(llm(SYSTEM, user))
                if arr and len(arr) == len(chunk):
                    m = {}
                    good = True
                    for it in arr:
                        try:
                            rid = int(it.get("row_id"))
                        except (TypeError, ValueError):
                            good = False
                            break
                        v = str(it.get("verdict", "")).strip().upper()
                        if v not in MAP:
                            good = False
                            break
                        m[rid] = {"verdict": v, "reason": str(it.get("reason") or "").strip()}
                    if good and all(g in m for g in chunk):
                        sug.update(m)
                        ok = True
                        break
                time.sleep(RATE_SLEEP_S)
            if not ok:
                for gid in chunk:
                    sug[gid] = {"verdict": "HOLD", "reason": "(분류 실패 — 수동 검수)"}
            print(f"  분류 {b0//BATCH+1}/{(n+BATCH-1)//BATCH}")
            time.sleep(RATE_SLEEP_S)

    # ── v6 CSV(human_verdict 불변 + suggested_verdict·suggest_reason) ──
    add = ["suggested_verdict", "suggest_reason"]
    cols = header[:] + [c for c in add if c not in header]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i, r in enumerate(rows):
            rec = dict(r)
            s = sug.get(i, {"verdict": "", "reason": ""})
            rec["suggested_verdict"] = MAP.get(s["verdict"], "") if not args.dry_run else ""
            rec["suggest_reason"] = s["reason"]
            w.writerow(rec)

    # ── 검증: A'(병진 human_verdict) vs 제안 일치율 ──
    from collections import Counter
    dist = Counter(MAP.get(sug[i]["verdict"], "") for i in sug) if sug else Counter()
    print("\n=== 통계 ===")
    print(f"출력: {args.out} ({n}행, 컬럼 {len(cols)})")
    if not args.dry_run:
        print(f"LLM 콜 {calls['c']} · tokens p{calls['p']}/o{calls['o']}")
        print(f"제안 분포: {dict(dist)}")
        # 검증
        labeled = [(i, r) for i, r in enumerate(rows) if r.get("human_verdict", "").strip()]
        agree = 0
        conflict = []
        for i, r in labeled:
            hv = r["human_verdict"].strip()
            sv = MAP.get(sug.get(i, {}).get("verdict", ""), "")
            hv_base = hv.split(":")[0]  # CHANGE:X → CHANGE
            if hv_base == "OK" and sv == "OK":
                agree += 1
            elif hv_base == sv:
                agree += 1
            else:
                conflict.append((r["symbol_pair"], hv, sv))
        if labeled:
            print(f"검증(병진 검수 {len(labeled)}건 vs 제안): 일치 {agree}/{len(labeled)} ({100*agree//len(labeled)}%)")
            print(f"  불일치 {len(conflict)}건 샘플: {conflict[:8]}")


if __name__ == "__main__":
    main()
