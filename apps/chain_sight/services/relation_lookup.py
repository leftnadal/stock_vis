"""CS-S3-1C — 종목 쌍 → RelationConfidence 무방향 일괄 조회 + 관계 종류 한 줄(D-S3-8).

공용 자산(§3 사슬 대조도 재사용). BOUNDARY: apps→shared 방향만(shared 무참조).

판정 축 = **원본**(relation_type ∈ RECORDED_SENTENCE·S3-1C 보강 2026-09-10):
- 소속은 매핑표(타입)가 정한다: RECORDED_SENTENCE에 있는 truth 타입 → "…관계로 기록됨".
  (= SEC 4종 + ACQUIRED·HELD_BY_SAME_FUND. 부기 공백(pending)이 관계를 숨기지 않는다.)
- context 계층(PEER_OF·PRICE_CORRELATED)은 RECORDED_SENTENCE에 없어 자동으로 걸러진다
  (맥락이지 근거 아님 — 관계 줄에 안 나온다).
- excluded는 유일한 거부권(자기루프·수동 정제 보존) → 관계 줄에서 뺀다.
- 그 외(CO_MENTIONED만·미매핑 타입·무행) → "관계 기록 없음"(조용한 쪽으로 실패).
등급(relation_status)은 판정에 쓰지 않는다 — stale이든 confirmed든 "기록됨".
serving_layer는 판정 축이 아니라 거부권(excluded)으로만 쓴다 — pending(미분류)은 근거를 못
숨긴다(D-S3-6 H: 캐시가 아니라 원본으로 판정한다).

읽기 전용(prod write 0·외부콜 0·LLM 0·마이그 0).
"""

from collections import defaultdict

# type → 문장. 우선순위 = 이 dict의 삽입 순서(위쪽 우선). 소속(기록됨) 판정은 이 매핑표가 한다.
RECORDED_SENTENCE = {
    "SUPPLIES_TO": "공급 관계로 기록됨",
    "DEPENDS_ON": "의존 관계로 기록됨",
    "PARTNER_WITH": "제휴 관계로 기록됨",
    "ACQUIRED": "인수·합병으로 기록됨",       # 현재 0행 — 매핑은 남긴다
    "COMPETES_WITH": "경쟁 관계로 기록됨",
    "HELD_BY_SAME_FUND": "같은 펀드가 보유",   # 현재 0행 — 매핑은 남긴다
}
_PRIORITY = list(RECORDED_SENTENCE.keys())
NONE_LINE = "관계 기록 없음"


def relation_line_for(rows) -> str:
    """쌍의 행 목록 → 관계 종류 한 줄. rows = [{relation_type, serving_layer, relation_category}, ...].

    기록됨 판정(S3-1C 보강): relation_type ∈ RECORDED_SENTENCE(원본) AND relation_category='truth'
    AND serving_layer != 'excluded'. serving_layer는 축이 아니라 거부권(excluded)으로만 쓴다 —
    pending(미분류)은 근거를 숨기지 못한다. 미매핑 타입(예: HAS_THEME)은 조용히 NONE_LINE(D-8).
    """
    recorded = {
        r["relation_type"]
        for r in rows
        if r.get("relation_type") in RECORDED_SENTENCE
        and r.get("relation_category") == "truth"
        and r.get("serving_layer") != "excluded"
    }
    for t in _PRIORITY:
        if t in recorded:
            return RECORDED_SENTENCE[t]
    return NONE_LINE


def relation_recorded(rows) -> bool:
    """관계 줄이 '기록됨' 계열인지(FE 시각 구분용)."""
    return relation_line_for(rows) != NONE_LINE


def lookup_pairs(pairs):
    """종목 쌍 목록 → {frozenset({a,b}): [행...]} 무방향 일괄 조회.

    N+1 금지 — 1쿼리(symbol 집합 IN 조회) 후 파이썬에서 관심 쌍만 필터. 배치·캐시 불요
    (M 계측 p95 4.92ms). 반환 행 = type·category·status·serving_layer.
    """
    from apps.chain_sight.models import RelationConfidence

    keys = {frozenset((a, b)) for a, b in pairs}
    if not keys:
        return {}
    syms = set()
    for a, b in pairs:
        syms.add(a)
        syms.add(b)

    result = defaultdict(list)
    rows = RelationConfidence.objects.filter(
        symbol_a__in=syms, symbol_b__in=syms
    ).values(
        "symbol_a", "symbol_b", "relation_type", "serving_layer",
        "relation_category", "relation_status",
    )
    for r in rows:
        k = frozenset((r["symbol_a"], r["symbol_b"]))
        if k in keys:
            result[k].append(r)
    return result
