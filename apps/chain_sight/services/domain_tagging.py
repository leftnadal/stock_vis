"""관계 도메인 태깅 코어 (⑳-3 S2-B, 자동-C 파이프라인) — 커맨드·훅 공유 단일 소스.

파이프라인: basis 원문 + 양끝 심볼 → LLM 초안(도메인 태그·type_match·refined_basis)
           → 기계검증(타깃 실존·타입 시그니처·confidence) → 게이트(auto후보/pending).

★안전핀(하드 룰):
  - relation_domain(승인본)은 이 코어가 절대 쓰지 않는다(검수 승인=Phase 2).
  - LLM이 타입 변경을 제안하면 status와 무관하게 auto 불가 → 항상 pending(검수만이 타입 변경).
  - auto 후보라도 DOMAIN_AUTO_APPROVE(기본 False)가 켜져야 status='auto', 아니면 pending.

LLM 최소 전송: basis 원문 + 양끝 심볼만(그 외 데이터 금지).
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

from django.conf import settings

# SEC 계열(도메인 태깅 대상). PEER/시장 신호는 대상 아님.
SEC_RELATION_TYPES = ("SUPPLIES_TO", "COMPETES_WITH", "DEPENDS_ON", "PARTNER_WITH")

# 검증 규칙 ②: 경쟁 어휘가 비경쟁 타입에 있으면 시그니처 불일치(fail).
_COMPETE_VOCAB = re.compile(r"\bcompet(e|es|ing|itor|itors|ition|itive)\b", re.I)


def _norm_type(x) -> str:
    """관계 타입 정규화(대소문자·공백 무시 비교용)."""
    return (x or "").strip().upper()


def _is_enumeration(text: str) -> bool:
    """나열문 판정(S2-C-2): 쉼표/세미콜론 3+ 구분 & 대문자 회사토큰 3+."""
    parts = re.split(r"[;,]", text or "")
    caps = sum(1 for p in parts if re.search(r"\b[A-Z][A-Za-z]{2,}", p))
    return len(parts) >= 3 and caps >= 3


# ── 태그 정규화(S2-C-3) : 매핑 테이블=데이터 파일(버전관리), 적용=코드 ──
_TAG_MAP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "domain_tag_normalization.json"
)


@lru_cache(maxsize=1)
def _load_tag_map() -> dict:
    try:
        with open(_TAG_MAP_PATH, encoding="utf-8") as f:
            return json.load(f).get("map", {})
    except (OSError, json.JSONDecodeError):
        return {}


def normalize_tag(tag):
    """원 draft_domain → canonical(정규화). 미등록 신규 태그는 원문 유지(identity)."""
    if not tag:
        return tag
    t = str(tag).strip()
    return _load_tag_map().get(t, t) or t

# 설정(초기 보수적). 캘리브레이션(첫 배치 검수) 후 확정.
def _threshold() -> float:
    return float(getattr(settings, "DOMAIN_CONFIDENCE_THRESHOLD", 0.75))


def _auto_approve_enabled() -> bool:
    return bool(getattr(settings, "DOMAIN_AUTO_APPROVE", False))


# ── 프롬프트 계약 ─────────────────────────────────────────────
_SYSTEM = (
    "너는 미국 상장사 간 관계를 분류하는 금융 애널리스트다. "
    "SEC 10-K 발췌 문장과 두 종목 심볼이 주어지면, 두 회사가 어떤 사업 도메인에서 "
    "연결되는지 짧은 한국어 명사구로 태깅한다. "
    "반드시 아래 JSON 스키마만 출력한다(설명·마크다운 금지):\n"
    '{"domain_tags": ["명사구1", "명사구2"], '
    '"type_match": {"match": true, "suggested_type": null}, '
    '"refined_basis": "타깃 중심 1문장(선택, 없으면 빈 문자열)", '
    '"confidence": 0.0}\n'
    "- domain_tags: 1~2개, 예 \"메모리·HBM\", \"GPU·데이터센터\". 문장에 근거 없으면 빈 배열.\n"
    "- type_match.match: 현재 관계 타입이 문장과 맞으면 true. 틀리면 false + suggested_type에 "
    "SUPPLIES_TO/COMPETES_WITH/DEPENDS_ON/PARTNER_WITH 중 하나.\n"
    "- confidence: 0~1. 문장이 타깃을 명시하지 않으면 낮게."
)


def build_prompt(symbol_a: str, symbol_b: str, relation_type: str, basis: str):
    """(system_instruction, contents) 반환 — 최소 전송(basis+심볼만)."""
    user = (
        f"현재 관계 타입: {relation_type}\n"
        f"종목: {symbol_a} ↔ {symbol_b}\n"
        f"SEC 10-K 발췌: {basis}"
    )
    return _SYSTEM, [user]


def parse_llm_json(text: str) -> dict | None:
    """LLM 원문에서 JSON 추출(마크다운 펜스 제거). 실패 시 None(HALT 집계용)."""
    if not text:
        return None
    s = text.strip()
    # ```json ... ``` 펜스 제거
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    # 첫 { ~ 마지막 } 구간만
    m = re.search(r"\{.*\}", s, re.S)
    if m:
        s = m.group(0)
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


# ── 기계검증 ─────────────────────────────────────────────────
def machine_check(
    *, symbol_a: str, symbol_b: str, center: str, relation_type: str,
    basis: str, target_name: str, llm_out: dict,
) -> dict:
    """검증 항목별 pass/fail + type_match + confidence. 순수 함수(부수효과 없음)."""
    other = symbol_b if symbol_a == center else symbol_a
    basis_l = (basis or "").lower()

    # ① 타깃 실존(S2-C-2 나열 인식·오탐 차단):
    #   - 심볼은 단어경계로만 매칭(짧은 심볼 substring 오탐 차단: V∈"over", A∈"and").
    #   - 사명은 유의어 토큰(≥4자)을 나열 구분자(;,:()"'&/)까지 분해해 매칭 → 나열 항목 정합.
    is_enumeration = _is_enumeration(basis or "")
    symbol_hit = bool(other) and re.search(
        rf"\b{re.escape(other)}\b", basis or ""
    ) is not None
    name_tokens = [
        t for t in re.split(r"[\s,.;:()\"'&/]+", target_name or "") if len(t) >= 4
    ]
    name_hit = any(t.lower() in basis_l for t in name_tokens)
    target_in_basis = bool(other) and (symbol_hit or name_hit)

    # ② 타입-문장 시그니처: 경쟁 어휘가 비경쟁 타입에 있으면 불일치
    has_compete_vocab = bool(_COMPETE_VOCAB.search(basis or ""))
    type_signature_ok = not (relation_type != "COMPETES_WITH" and has_compete_vocab)

    # ③ LLM confidence 임계
    try:
        conf = float(llm_out.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    confidence_ok = conf >= _threshold()

    # LLM type_match
    tm = llm_out.get("type_match") or {}
    type_match_ok = bool(tm.get("match", False))
    suggested_type = tm.get("suggested_type")

    # 자가모순(S2-C-1): match=False인데 동일 타입 재제안 = LLM 노이즈(타입변경 아님).
    self_contradiction = (
        (not type_match_ok)
        and bool(suggested_type)
        and _norm_type(suggested_type) == _norm_type(relation_type)
    )

    return {
        "target_in_basis": target_in_basis,
        "type_signature_ok": type_signature_ok,
        "confidence_ok": confidence_ok,
        "confidence": conf,
        "type_match_ok": type_match_ok,
        "suggested_type": suggested_type,
        "has_compete_vocab": has_compete_vocab,
        "is_enumeration": is_enumeration,
        "self_contradiction": self_contradiction,
    }


def decide_gate(mc: dict) -> tuple[str, str]:
    """(gate_class, review_status) 반환.

    하드 룰: LLM이 타입 변경 제안(type_match_ok=False 또는 suggested_type 존재) → 항상 pending.
    S2-C-1: 자가모순(match=False인데 동일 타입 재제안)은 LLM 노이즈 → 'noise_self_contradiction'
            버킷으로 분리(타입변경 아님). 보수적으로 auto 미승격(항상 pending) — 자기모순 자체가 품질 신호.
    auto 후보 = 3검증 pass ∧ type_match_ok. 단 DOMAIN_AUTO_APPROVE 꺼져 있으면 status=pending.
    """
    if mc.get("self_contradiction"):
        return "noise_self_contradiction", "pending"
    type_change_proposed = (not mc["type_match_ok"]) or bool(mc.get("suggested_type"))
    all_checks = (
        mc["target_in_basis"] and mc["type_signature_ok"] and mc["confidence_ok"]
    )
    if type_change_proposed:
        return "pending", "pending"  # 타입 변경 제안 = 자동 반영 절대 금지
    if all_checks:
        gate_class = "auto_candidate"
        status = "auto" if _auto_approve_enabled() else "pending"
        return gate_class, status
    return "pending", "pending"


def first_domain_tag(llm_out: dict) -> str | None:
    tags = llm_out.get("domain_tags")
    if isinstance(tags, list) and tags:
        t = str(tags[0]).strip()
        return t[:80] or None
    return None


def tag_one(*, symbol_a, symbol_b, center, relation_type, basis, target_name, llm_call):
    """단건 태깅 코어(커맨드·훅 공유). llm_call=(system, contents)->raw_text 콜러블.

    반환: {ok, draft, review_status, gate_class, machine_check, refined_basis, raw}
    draft/machine_check만 산출 — relation_domain(승인본)은 절대 미기록.
    """
    system, contents = build_prompt(symbol_a, symbol_b, relation_type, basis)
    raw = llm_call(system, contents)
    llm_out = parse_llm_json(raw)
    if llm_out is None:
        return {
            "ok": False, "draft": None, "review_status": "pending",
            "gate_class": "pending", "machine_check": {"json_parse": False},
            "refined_basis": None, "raw": raw,
        }
    mc = machine_check(
        symbol_a=symbol_a, symbol_b=symbol_b, center=center,
        relation_type=relation_type, basis=basis,
        target_name=target_name, llm_out=llm_out,
    )
    mc["json_parse"] = True
    gate_class, review_status = decide_gate(mc)
    return {
        "ok": True,
        "draft": first_domain_tag(llm_out),
        "review_status": review_status,
        "gate_class": gate_class,
        "machine_check": mc,
        "refined_basis": (llm_out.get("refined_basis") or "").strip()[:200] or None,
        "raw": raw,
    }
