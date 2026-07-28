"""SEC β G1 — grounding 결정론 매처 단위 테스트 (순수 함수, django 무의존).

판정 4종: verified / normalized_match / not_found / missing_source.
매처 규율(개정문1): EDGAR 원문 특이 케이스 — 유니코드 대시·스마트 따옴표·말줄임·공백/개행.
V-A 결정론 — LLM 0콜.
"""
from services.sec_pipeline.grounding import (
    GROUNDING_METHOD,
    STATUS_MISSING_SOURCE,
    STATUS_NORMALIZED_MATCH,
    STATUS_NOT_FOUND,
    STATUS_VERIFIED,
    ground_evidence,
    normalize,
)


# ── verified: 정규화 전 원문 그대로 substring ──────────────────────────
def test_verified_exact_substring():
    source = "Apple relies on TSMC for advanced chip fabrication. Other suppliers exist."
    evidence = "Apple relies on TSMC for advanced chip fabrication."
    r = ground_evidence(evidence, source)
    assert r.status == STATUS_VERIFIED
    assert r.method == GROUNDING_METHOD


# ── normalized_match: 정규화 후에만 substring ──────────────────────────
def test_normalized_match_whitespace_and_newline():
    # 원문은 개행·다중 공백, 인용은 단일 공백 → 정규화 후 일치
    source = "The Company\n  purchases   components\nfrom multiple vendors worldwide."
    evidence = "The Company purchases components from multiple vendors worldwide."
    r = ground_evidence(evidence, source)
    assert r.status == STATUS_NORMALIZED_MATCH


def test_normalized_match_smart_quotes():
    # 원문 스마트 따옴표, 인용 ASCII 따옴표
    source = 'We signed a “long-term” agreement with our ‘key’ partner.'
    evidence = 'We signed a "long-term" agreement with our \'key\' partner.'
    r = ground_evidence(evidence, source)
    assert r.status == STATUS_NORMALIZED_MATCH


def test_normalized_match_unicode_dashes():
    # 원문 em/en 대시, 인용 ASCII 하이픈
    source = "Revenue — net of returns – grew during the co-development period."
    evidence = "Revenue - net of returns - grew during the co-development period."
    r = ground_evidence(evidence, source)
    assert r.status == STATUS_NORMALIZED_MATCH


def test_normalized_match_ellipsis():
    # 원문 유니코드 말줄임(…, NFKC→...), 인용 마침표 3개
    source = "The agreement covers manufacturing… and distribution rights."
    evidence = "The agreement covers manufacturing... and distribution rights."
    r = ground_evidence(evidence, source)
    assert r.status == STATUS_NORMALIZED_MATCH


# ── not_found: 정규화 후에도 부재(소스는 존재) ─────────────────────────
def test_not_found_absent_sentence():
    source = "Apple relies on TSMC for chip fabrication."
    evidence = "Microsoft owns a stake in a lithium mining venture."
    r = ground_evidence(evidence, source)
    assert r.status == STATUS_NOT_FOUND


# ── missing_source: 소스 텍스트 부재(not_found와 구분·합산 금지) ────────
def test_missing_source_none():
    r = ground_evidence("Apple relies on TSMC.", None)
    assert r.status == STATUS_MISSING_SOURCE


def test_missing_source_empty_and_whitespace():
    assert ground_evidence("evidence", "").status == STATUS_MISSING_SOURCE
    assert ground_evidence("evidence", "   \n\t  ").status == STATUS_MISSING_SOURCE


# ── 방어: 빈 인용은 자명 verified가 되면 안 됨(빈 문자열은 만능 substring) ──
def test_empty_evidence_is_not_trivially_verified():
    r = ground_evidence("", "some source text here")
    assert r.status == STATUS_NOT_FOUND


# ── normalize 순수 함수 계약 ───────────────────────────────────────────
def test_normalize_idempotent_and_collapses():
    raw = "  A—B  “x”\n\ty  "
    once = normalize(raw)
    assert once == normalize(once)  # 멱등
    assert "  " not in once and once == once.strip()  # 다중공백 제거·strip
    assert "—" not in once and "“" not in once  # 대시·스마트따옴표 ASCII화
