"""기업 소개 + 문단 확장 + 관계 서술 재생성 (⑳-3 REVIEW-TOOL-4, 1회성).

review_batch_v4.csv → review_batch_v5.csv. **DB 읽기 전용**(SELECT만).
전문·item 전문은 이미 DB → EDGAR 재방문 0(문단 확장도 저장 item_text에서).
  - intro_a/intro_b: 심볼별 기업 소개 2줄(Stock.description=FMP 프로필, 심볼 dedupe·재사용).
    description 미보유 심볼 → LLM 일반 지식 + "(일반 지식 기반)" 표기.
  - evidence_paragraph: evidence가 속한 문단 전체(item_text 단일 \\n 경계).
  - summary_ko(재생성): 관계 서술 4~10문장. 원료=문단+프로필. 타입 enum·현재타입 정오 판단 금지.
basis 불변(rowKey). LLM=BOUNDARY-LLM 래퍼 경유.

사용:
  python tools/review/build_v5.py --dry-run   # DB만(문단·프로필 조회), LLM 미호출
  python tools/review/build_v5.py             # 전량(인트로 + 관계서술)
"""
from __future__ import annotations
import argparse, csv, json, os, re, sys, time

IN_DEFAULT = "outputs/domain_tagging/review_batch_v4.csv"
OUT_DEFAULT = "outputs/domain_tagging/review_batch_v5.csv"
INTRO_BATCH = 25
NARR_BATCH = 8
MAX_RETRY = 3
RATE_SLEEP_S = 4.2
GEN_FAIL = "(재생성 실패 — v4 서술 유지)"
PARA_CAP = 2200  # 문단 확장 상한(토큰 제어)

TYPE_ENUMS = ("SUPPLIES_TO", "COMPETES_WITH", "DEPENDS_ON", "PARTNER_WITH")

INTRO_SYSTEM = (
    "너는 미국 상장사를 한국어로 소개하는 애널리스트다. 각 기업을 정확히 2줄로:\n"
    "1줄=주력 사업(무엇을 만들고 파는가), 2줄=시장 위치(어느 시장/부문에서).\n"
    "description(회사 개요)이 주어지면 그 사실만 압축한다. description이 비어 있으면 "
    "일반 지식으로 작성하되 소개 끝에 '(일반 지식 기반)'을 붙인다.\n"
    "추측성 표현 금지('~일 것','~로 추정'). 반드시 JSON 배열만: "
    '[{"symbol":"...","intro_ko":"...(2줄)"}] (입력 수와 동일 길이).'
)

NARR_SYSTEM = (
    "너는 SEC 10-K '문단'과 두 회사 프로필을 읽는 한국어 애널리스트다.\n"
    "두 회사의 관계를 4~10문장으로 서술한다. 반드시 포함:\n"
    "① 이 문단이 놓인 맥락(누가 왜 쓴 대목인지 — 예: 경쟁 환경 설명, 공급망 서술).\n"
    "② 두 회사가 무엇(제품·시장·거래)을 놓고 어떻게 얽히는지(문단 사실 기반).\n"
    "③ 문서에 없는 관계 축이 있으면 '문서에는 ~ 서술 없음'이라고 명시.\n"
    "원료는 **주어진 문단과 프로필뿐**. 관계 사실은 문단이 유일 원천 — 외부 사건·뉴스·"
    "자기 지식으로 관계를 보태지 마라(회사 정체성만 프로필 참고 가능).\n"
    f"금지: 관계 타입 명칭({'/'.join(TYPE_ENUMS)}) 사용, '현재 타입이 맞다/틀리다'류 정오 판단, "
    "라벨 제안. 사실 서술(누가 무엇을 공급/경쟁/의존)은 허용.\n"
    'flags 해당 시: "m&a","indirect". JSON 배열만: '
    '[{"row_id":<int>,"narration_ko":"...","flags":[...]}] (입력 수와 동일).'
)


def _b(x):
    return str(x).strip().lower() in ("true", "1")


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


def paragraph_window(item_text: str, sentence: str) -> str:
    """item_text에서 sentence가 속한 문단(단일 \\n 경계) 확장. 실패 시 sentence."""
    if not item_text or not sentence:
        return sentence
    idx = item_text.find(sentence[:60])
    if idx < 0:
        return sentence
    left = item_text.rfind("\n", 0, idx)
    start = left + 1 if left >= 0 else 0
    right = item_text.find("\n", idx + len(sentence))
    end = right if right >= 0 else len(item_text)
    para = item_text[start:end].strip()
    if len(para) > PARA_CAP:  # 과대 문단 상한(중심 문장 주변으로 자름)
        c = para.find(sentence[:40])
        s2 = max(0, c - PARA_CAP // 2)
        para = para[s2:s2 + PARA_CAP].strip()
    return para if len(para) >= len(sentence) else sentence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=IN_DEFAULT)
    ap.add_argument("--out", dest="out", default=OUT_DEFAULT)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import django
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from packages.shared.stocks.models import Stock
    from services.sec_pipeline.models import SupplyChainEvidence

    with open(args.inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames[:]
        rows = list(reader)
    if args.limit:
        rows = rows[: args.limit]
    n = len(rows)

    def sym_pair(r):
        a, _, b = (r["symbol_pair"] + "↔").partition("↔")
        return a, b.rstrip("↔")

    # ── 유니크 심볼 → 프로필 SELECT ──
    syms = set()
    for r in rows:
        a, b = sym_pair(r)
        syms |= {a, b}
    syms.discard("")
    profiles = {s.symbol: s for s in Stock.objects.filter(symbol__in=syms)}
    missing_desc = sorted(s for s in syms if not (profiles.get(s) and (profiles[s].description or "").strip()))
    print(f"유니크 심볼 {len(syms)} · description 보유 {len(syms)-len(missing_desc)} · 미보유(일반지식) {len(missing_desc)}")

    # ── 문단 확장(DB) ──
    para = {}
    for i, r in enumerate(rows):
        basis = r["basis"]
        b100 = basis[len("SEC 10-K: "):] if basis.startswith("SEC 10-K: ") else basis
        a, b = sym_pair(r)
        cands = list(SupplyChainEvidence.objects.filter(evidence_text__startswith=b100)
                     .select_related("source_document", "source_company"))
        ev = next((c for c in cands if c.source_company_id in (a, b)), cands[0] if cands else None)
        if not ev or not ev.source_document:
            para[i] = r.get("full_evidence") or basis
            continue
        sd = ev.source_document
        item = ""
        for txt in (sd.item_1_text, sd.item_1a_text, sd.item_7_text):
            if txt and ev.evidence_text[:60] in txt:
                item = txt
                break
        para[i] = paragraph_window(item, ev.evidence_text) if item else (r.get("full_evidence") or ev.evidence_text)
    pglen = [len(v) for v in para.values()]
    print(f"문단 확장: 평균 {sum(pglen)//len(pglen)}자 (v4 full_evidence 평균 대비 확대)")

    intros = {}
    calls = {"c": 0, "p": 0, "o": 0}
    if args.dry_run:
        _write(args.out, header, rows, {}, para, intros, missing_desc, dry=True)
        print(f"dry-run 출력: {args.out}")
        return

    from apps.market_pulse.llm.client import generate_with_circuit

    def llm(system, user):
        resp = generate_with_circuit(system_instruction=system, contents=[user])
        calls["c"] += 1
        calls["p"] += getattr(resp, "prompt_tokens", 0)
        calls["o"] += getattr(resp, "completion_tokens", 0)
        return getattr(resp, "text", "") or ""

    # ── 인트로 생성(심볼 dedupe) ──
    sym_list = sorted(syms)
    for b0 in range(0, len(sym_list), INTRO_BATCH):
        chunk = sym_list[b0:b0 + INTRO_BATCH]
        payload = []
        for s in chunk:
            p = profiles.get(s)
            payload.append({"symbol": s, "name": (p.stock_name if p else s) or s,
                            "sector": (p.sector if p else "") or "", "industry": (p.industry if p else "") or "",
                            "description": ((p.description if p else "") or "")[:600]})
        user = "각 기업을 2줄 소개(JSON 배열, 수 동일):\n" + json.dumps(payload, ensure_ascii=False)
        for _ in range(MAX_RETRY):
            arr = parse_arr(llm(INTRO_SYSTEM, user))
            if arr and len(arr) == len(chunk):
                for it in arr:
                    intros[str(it.get("symbol", "")).strip()] = str(it.get("intro_ko") or "").strip()
                if all(s in intros for s in chunk):
                    break
            time.sleep(RATE_SLEEP_S)
        print(f"  인트로 {b0//INTRO_BATCH+1}/{(len(sym_list)+INTRO_BATCH-1)//INTRO_BATCH}")
        time.sleep(RATE_SLEEP_S)
    for s in syms:
        intros.setdefault(s, "(소개 생성 실패)")

    # ── 관계 서술 재생성 ──
    narr = {}
    gen_fail = 0
    for b0 in range(0, n, NARR_BATCH):
        chunk = list(range(b0, min(b0 + NARR_BATCH, n)))
        payload = []
        for gid in chunk:
            a, b = sym_pair(rows[gid])
            payload.append({"row_id": gid, "symbol_a": a, "symbol_b": b,
                            "profile_a": intros.get(a, ""), "profile_b": intros.get(b, ""),
                            "paragraph": para[gid]})
        user = "다음 각 항목의 두 회사 관계를 4~10문장으로(JSON 배열, 수 동일):\n" + json.dumps(payload, ensure_ascii=False)
        ok = False
        for _ in range(MAX_RETRY):
            arr = parse_arr(llm(NARR_SYSTEM, user))
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
                    m[rid] = {"narration": str(it.get("narration_ko") or "").strip(), "llm_flags": fl}
                if good and all(g in m for g in chunk):
                    narr.update(m)
                    ok = True
                    break
            time.sleep(RATE_SLEEP_S)
        if not ok:
            for gid in chunk:
                narr[gid] = {"narration": "", "llm_flags": []}
                gen_fail += 1
        print(f"  관계서술 {b0//NARR_BATCH+1}/{(n+NARR_BATCH-1)//NARR_BATCH} (fail {gen_fail})")
        time.sleep(RATE_SLEEP_S)

    _write(args.out, header, rows, narr, para, intros, missing_desc, sym_pair_fn=sym_pair)
    print("\n=== 통계 ===")
    print(f"출력: {args.out} ({n}행)")
    print(f"LLM 콜: {calls['c']} · tokens p{calls['p']}/o{calls['o']} · 생성실패 {gen_fail}")


def _write(out, header, rows, narr, para, intros, missing_desc, dry=False, sym_pair_fn=None):
    def sp(r):
        a, _, b = (r["symbol_pair"] + "↔").partition("↔")
        return a, b.rstrip("↔")
    add = ["intro_a", "intro_b", "evidence_paragraph"]
    cols = header[:] + [c for c in add if c not in header]
    miss = set(missing_desc)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i, r in enumerate(rows):
            a, b = sp(r)
            rec = dict(r)
            rec["intro_a"] = f"{a}: " + (intros.get(a, "") if not dry else "(dry)")
            rec["intro_b"] = f"{b}: " + (intros.get(b, "") if not dry else "(dry)")
            rec["evidence_paragraph"] = para.get(i, "")
            if not dry:
                nk = narr.get(i, {}).get("narration", "")
                if nk:
                    rec["summary_ko"] = nk
                    det = [x for x in (r.get("summary_flags") or "").split("|") if x]
                    fl = sorted(set(det) | set(narr.get(i, {}).get("llm_flags", [])))
                    rec["summary_flags"] = "|".join(fl)
                else:
                    rec["summary_ko"] = (r.get("summary_ko") or "").strip() or GEN_FAIL
            w.writerow(rec)


if __name__ == "__main__":
    main()
