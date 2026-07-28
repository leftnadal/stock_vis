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
from dataclasses import dataclass

STATUS_VERIFIED = "verified"
STATUS_NORMALIZED_MATCH = "normalized_match"
STATUS_NOT_FOUND = "not_found"
STATUS_MISSING_SOURCE = "missing_source"

GROUNDING_METHOD = "deterministic_v1"

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
