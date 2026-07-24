"""G2 dry-run 하네스 (TH-C3-LLM-DICT-1, 3f 종결) — READ-ONLY.

override(ovr_v1) 적용 후 2×2 오염/재배정 tally 를 **비변형(non-mutating)** 으로 산출한다.
`aggregate_theme_news_volume` (ThemeNewsVolume write) 를 호출하지 **않고**, 동결 코퍼스
(DailyNewsKeyword ≤ date_cut) 를 in-memory 재집계하며 override 처분을 적용해 셀별 크레딧을
합산한다. 코퍼스·원장 무접촉.

복원 근거: 2351dfa4 세션 scratchpad `final_confirmed.py` (교차 검산 완료). 그 스크립트의
하드코드 30건(A14/FMP6/FINAL6) final_want 는 이제 `ThemeTermOverride(ovr_v1)` 원장에 적재된
disposition 으로 **등가 대체**한다. orig(recheck 원본) 은 `provenance["should_be"]` 에서 읽는다.
산식(cell 정의·after-credit 집계)은 원본과 동일 — 로직 추가 없음.

산출 3종:
  1. after-credit 4셀      : override 적용 후 셀별 크레딧 총합 (목표 92/19/0/0)
  2. orig→final 2×2        : recheck(orig) vs override(final) 셀별 term 카운트
  3. 셀이동 from→to 매트릭스 : orig≠final 인 term 의 이동 집계

⚠ 이 모듈은 ORM write 를 **일절 하지 않는다** (아래 함수 전부 .filter()/.values() 읽기 전용).
"""

import json
import logging
from collections import Counter, defaultdict
from datetime import date
from typing import Optional

from apps.chain_sight.services.c3_narrative_service import (
    KW_SECTOR_TO_HEAT_ENTITY,
    _normalize,
    match_term_to_sectors,
)

logger = logging.getLogger(__name__)

CELLS = ["real_pollute", "real_noeffect", "none_pollute", "none_noeffect"]
DEFAULT_DATE_CUT = date(2026, 7, 11)
DEFAULT_GENERATION = "ovr_v1"


# ── 순수함수 (DB 비의존, 단위 테스트 대상) ─────────────────────────────────

def want_set(spec: Optional[str]) -> frozenset:
    """should_be/disposition 문자열 → 목표 섹터 집합 (원본 final_confirmed.want).

    'none'/빈값 → 공집합(제거 대상). CSV → 각 섹터 문자열 그대로 (entities 교집합 없음 —
    cell 판정은 prod−want 차집합만 보므로 원본 산식과 동일 재현).
    """
    if not spec or spec == "none":
        return frozenset()
    return frozenset(x.strip() for x in spec.split(",") if x.strip())


def classify_cell(prod_refs: frozenset, want_refs: frozenset) -> str:
    """복원 산식 (final_confirmed.cell) — 2×2 셀 판정.

    axis A (real/none) = want 유무. axis B (pollute/noeffect) = 현행 1차규칙(prod) 이 want
    밖 섹터를 만드는가(오염). over = prod 가 있고 prod−want 가 비지 않음.
    """
    over = bool(prod_refs and (prod_refs - want_refs))
    axis_a = "none" if not want_refs else "real"
    axis_b = "_pollute" if over else "_noeffect"
    return axis_a + axis_b


def credit_refs(disposition: Optional[str], entities: frozenset) -> list:
    """override 처분 → after-credit 기여 refs (원본 final_confirmed.ov_refs).

    'none'/빈값 → [] (크레딧 0 = 제거). CSV → entities 에 존재하는 섹터만 (섹터당 크레딧 1).
    """
    if not disposition or disposition == "none":
        return []
    return [s.strip() for s in disposition.split(",") if s.strip() in entities]


def prod_refs(term_original: str, keyword_map: dict) -> frozenset:
    """현행 1차규칙(prod) 매칭 결과 → HeatEntity ref_id 집합 (원본 final_confirmed.prod)."""
    return frozenset(
        KW_SECTOR_TO_HEAT_ENTITY[s]
        for s in match_term_to_sectors(term_original, keyword_map)
        if s in KW_SECTOR_TO_HEAT_ENTITY
    )


def tally_after_credit(corpus_terms, cell_of: dict, refs_after: dict) -> Counter:
    """동결 코퍼스 term 스트림 → 셀별 after-credit 합 (원본 final_confirmed.agg 의 cellc).

    corpus_terms : 정규화 term 이터러블(등장마다 1개 — 중복 포함).
    cell_of      : {norm_term: final_cell}  (override 등재 term).
    refs_after   : {norm_term: 크레딧 수}   (override-후, none=0).
    """
    c: Counter = Counter()
    for nt in corpus_terms:
        if nt in cell_of:
            c[cell_of[nt]] += refs_after[nt]
    return c


# ── orchestration (READ-ONLY — ORM write 0) ───────────────────────────────

def run_g2_dry_run(
    date_cut: date = DEFAULT_DATE_CUT,
    generation: str = DEFAULT_GENERATION,
    now=None,
) -> dict:
    """G2 dry-run 실행 — 3종 산출 + 스코프 메타. **원장 무접촉(읽기 전용).**

    반환 dict = {meta, after_credit, orig_final, moves, provenance_cell, checks}.
    """
    # NOTE: 아래 ORM 접근은 전부 .filter()/.values() 읽기 — 어떤 .save()/.create()/.update()
    #       /.delete() 도 호출하지 않는다 (무쓰기 구조 보장).
    from apps.chain_sight.models import HeatEntity, ThemeTermOverride
    from services.news.models import DailyNewsKeyword
    from services.news.services.keyword_sector_map import KEYWORD_SECTOR_MAP

    if now is None:
        from django.utils import timezone
        now = timezone.now()

    entities = frozenset(
        HeatEntity.objects.filter(kind="sector").values_list("ref_id", flat=True)
    )

    rows = list(
        ThemeTermOverride.objects.filter(generation=generation).values(
            "term_normalized", "term_original", "disposition", "provenance"
        )
    )

    # per-term 재계산: prod, orig(=provenance.should_be), final(=disposition)
    cell_of: dict = {}          # {norm_term: final_cell}
    refs_after: dict = {}       # {norm_term: 크레딧 수}
    orig_ctr: Counter = Counter()
    final_ctr: Counter = Counter()
    disp_ctr: Counter = Counter()
    prov_cell_ctr: Counter = Counter()
    moves: Counter = Counter()
    move_terms: list = []
    mismatches: list = []       # 재계산 final_cell ≠ provenance.cell

    for r in rows:
        nt = r["term_normalized"]
        prov = r["provenance"] or {}
        p = prod_refs(r["term_original"], KEYWORD_SECTOR_MAP)
        orig_want = want_set(prov.get("should_be"))
        final_want = want_set(r["disposition"])
        orig_cell = classify_cell(p, orig_want)
        final_cell = classify_cell(p, final_want)

        orig_ctr[orig_cell] += 1
        final_ctr[final_cell] += 1
        cell_of[nt] = final_cell
        refs_after[nt] = len(credit_refs(r["disposition"], entities))

        # 처분 3분할 (재계산): 제거/유지/재배정
        if not final_want:
            disp_ctr["제거"] += 1
        elif p == final_want:
            disp_ctr["유지"] += 1
        else:
            disp_ctr["재배정"] += 1

        # 저장된 provenance.cell 대조 (검증)
        pc = prov.get("cell")
        if pc:
            prov_cell_ctr[pc] += 1
            if pc != final_cell:
                mismatches.append((nt, pc, final_cell))

        if orig_cell != final_cell:
            moves[(orig_cell, final_cell)] += 1
            move_terms.append((r["term_original"], orig_cell, final_cell))

    # after-credit: 동결 코퍼스(≤ date_cut) in-memory 재집계
    corpus_days = 0
    corpus_term_hits = 0

    def _corpus_terms():
        nonlocal corpus_days, corpus_term_hits
        qs = (
            DailyNewsKeyword.objects.filter(date__lte=date_cut)
            .exclude(keywords__isnull=True)
            .only("date", "keywords")
        )
        for dnk in qs:
            corpus_days += 1
            for kw in dnk.keywords or []:
                if not isinstance(kw, dict):
                    continue
                for term in kw.get("search_terms_en") or []:
                    corpus_term_hits += 1
                    yield _normalize(term)

    after_credit = tally_after_credit(_corpus_terms(), cell_of, refs_after)

    result = {
        "meta": {
            "date_cut": date_cut.isoformat(),
            "generation": generation,
            "universe": "SP500Constituent active − '.' 심볼 (live_universe_symbols)",
            "override_terms": len(rows),
            "corpus_days": corpus_days,
            "corpus_term_hits": corpus_term_hits,
            "run_at": now.isoformat(),
            "mutating": False,
        },
        "after_credit": {c: after_credit.get(c, 0) for c in CELLS},
        "orig_final": {
            c: {"orig": orig_ctr.get(c, 0), "final": final_ctr.get(c, 0)}
            for c in CELLS
        },
        "orig_total": sum(orig_ctr.values()),
        "final_total": sum(final_ctr.values()),
        "moves": {f"{a}→{b}": n for (a, b), n in sorted(moves.items(), key=lambda x: -x[1])},
        "move_terms": move_terms,
        "disposition": dict(disp_ctr),
        "provenance_cell": {c: prov_cell_ctr.get(c, 0) for c in CELLS},
        "checks": {
            "final_total_215": sum(final_ctr.values()) == len(rows),
            "provenance_cell_match": len(mismatches) == 0,
            "provenance_mismatches": mismatches,
        },
    }
    logger.info(
        "g2_dry_run: after_credit=%s date_cut=%s gen=%s (READ-ONLY)",
        result["after_credit"], date_cut, generation,
    )
    return result


def format_report(result: dict) -> str:
    """run_g2_dry_run 결과 → 사람이 읽는 리포트 문자열."""
    m = result["meta"]
    out = []
    out.append("=== G2 dry-run (READ-ONLY, 원장 무접촉) ===")
    out.append(
        f"scope: date_cut={m['date_cut']} generation={m['generation']} "
        f"override_terms={m['override_terms']} corpus_days={m['corpus_days']} "
        f"corpus_term_hits={m['corpus_term_hits']}"
    )
    out.append(f"universe: {m['universe']}")
    out.append(f"run_at: {m['run_at']}  mutating={m['mutating']}")
    out.append("")
    out.append("① after-credit 4셀 (목표 92/19/0/0):")
    for c in CELLS:
        out.append(f"    {c:15s} {result['after_credit'][c]}")
    out.append("")
    out.append("② orig→final 2×2 (term 카운트):")
    for c in CELLS:
        o = result["orig_final"][c]
        out.append(f"    {c:15s} {o['orig']:3d} → {o['final']:3d}  Δ{o['final']-o['orig']:+d}")
    out.append(
        f"    합 orig={result['orig_total']} final={result['final_total']} "
        f"(215 무음탈락0: {result['checks']['final_total_215']})"
    )
    out.append("")
    out.append("③ 셀이동 from→to 매트릭스:")
    for k, n in result["moves"].items():
        out.append(f"    {k:35s} : {n}")
    out.append(f"    셀이동 term 수 = {len(result['move_terms'])}")
    out.append("")
    out.append(f"처분 3분할: {result['disposition']}")
    out.append(
        f"provenance.cell 대조: {result['provenance_cell']} "
        f"(match={result['checks']['provenance_cell_match']})"
    )
    return "\n".join(out)
