"""SEC β G1 — evidence grounding 결정론 매처 (순수 함수, django 무의존).

self-reported LLM 인용(temperature 0.1 "exact sentence")이 10-K 원문에 verbatim
존재하는지 **결정적 정규화 매칭**으로 검증한다. V-A (2026-07-02 결정 ③) — **LLM 0콜.**

판정 4종 (개정문1):
- verified          : 정규화 전 원문 그대로 substring 존재
- normalized_match  : 정규화 후에만 substring 존재
- not_found         : 정규화 후에도 부재 (소스는 존재 = 진짜 접지 실패)
- missing_source    : 원문 소스 텍스트 부재 (not_found와 **합산 금지** — 의미 상이)

임계·상수는 모듈 상수(정책표 md는 근거 문서지 런타임 소스 아님 — 하향 :406·상향 UPWARD=60 규율 동형).
"""
import unicodedata
from dataclasses import dataclass, replace

STATUS_VERIFIED = "verified"
STATUS_NORMALIZED_MATCH = "normalized_match"
STATUS_PARTIAL_MATCH = "partial_match"  # G1.6: 접두 ≥70% 절단/tail 발산 (접지 성공에 합산 금지)
STATUS_NOT_FOUND = "not_found"
STATUS_MISSING_SOURCE = "missing_source"

GROUNDING_METHOD = "deterministic_v1"
PARTIAL_MIN_RATIO = 0.70  # G1.6 §1: not_found 접두 연속매치 ≥ 인용길이 70% → partial_match

# 스마트 따옴표/대시 → ASCII (NFKC가 처리 못 하는 문자만 명시 치환).
# NFKC는 말줄임(…→...)·전각 등은 처리하나 대시·곡선따옴표는 유지하므로 별도 매핑.
_ASCII_MAP = {
    "“": '"', "”": '"',   # " "  좌우 큰따옴표
    "‘": "'", "’": "'",   # ' '  좌우 작은따옴표
    "–": "-", "—": "-",   # – —  en/em 대시
    "−": "-",                  # −    마이너스 기호
}
_ASCII_TRANS = str.maketrans(_ASCII_MAP)


@dataclass(frozen=True)
class GroundingResult:
    status: str
    method: str = GROUNDING_METHOD


def normalize(text: str) -> str:
    """정규화 파이프라인(양쪽 텍스트 동일 적용):
    1) Unicode NFKC  2) 스마트 따옴표/대시 → ASCII  3) 연속 공백(개행 포함) → 단일 스페이스, strip.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_ASCII_TRANS)
    text = " ".join(text.split())  # \s+(개행·탭 포함) → 단일 스페이스 + strip
    return text


def ground_evidence(evidence_text: str, source_text: str) -> GroundingResult:
    """인용 1건을 원문 대비 접지 판정. 결정적·LLM 0콜."""
    # 소스 부재 = missing_source (not_found와 구분)
    if source_text is None or not source_text.strip():
        return GroundingResult(STATUS_MISSING_SOURCE)
    # 빈 인용은 자명 verified 방지(빈 문자열은 만능 substring) → 접지 불가 = not_found
    if not evidence_text or not evidence_text.strip():
        return GroundingResult(STATUS_NOT_FOUND)
    # verified: 정규화 전 원문 그대로
    if evidence_text in source_text:
        return GroundingResult(STATUS_VERIFIED)
    # normalized_match: 정규화 후에만
    if normalize(evidence_text) in normalize(source_text):
        return GroundingResult(STATUS_NORMALIZED_MATCH)
    return GroundingResult(STATUS_NOT_FOUND)


def _max_prefix_len(nquote: str, nsource: str) -> int:
    """정규화 인용의 최장 연속 접두 길이 k (nquote[:k] 가 nsource 부분문자열). 이진 탐색(단조).

    접두 단조성: nquote[:k] ⊂ nsource ⇒ nquote[:k-1] ⊂ nsource. 결정론.
    """
    if not nquote or not nsource:
        return 0
    if nquote in nsource:
        return len(nquote)
    lo, hi = 0, len(nquote)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if nquote[:mid] in nsource:
            lo = mid
        else:
            hi = mid - 1
    return lo


def partial_prefix_ratio(evidence_text: str, source_text: str) -> float:
    """정규화 인용 대비 원문 최장 연속 접두 비율 (0~1). 결정론·LLM 0."""
    nq = normalize(evidence_text)
    ns = normalize(source_text)
    if not nq or not ns:
        return 0.0
    return _max_prefix_len(nq, ns) / len(nq)


def ground_evidence_g16(evidence_text: str, source_text: str) -> GroundingResult:
    """G1.6 판정: V-A 매처(ground_evidence) + not_found 를 접두비율 ≥ PARTIAL_MIN_RATIO 이면
    partial_match 로 승격(절단/tail 발산). verified/normalized/missing_source 는 불변. 결정론·LLM 0.

    **단일 출처** — dry-run 리포트(grounding_g16_partial_reclassify.py)와 백필(grounding_backfill.py)
    양쪽이 이 함수를 import 해 동일 판정을 보장(로직 복제 금지, DECISIONS 규약 10장).
    """
    result = ground_evidence(evidence_text, source_text)
    if (
        result.status == STATUS_NOT_FOUND
        and partial_prefix_ratio(evidence_text, source_text) >= PARTIAL_MIN_RATIO
    ):
        return replace(result, status=STATUS_PARTIAL_MATCH)
    return result
