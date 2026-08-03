"""L2 Peer 도메인 태깅 코어 (L2-ADOPT, D-L2-SOURCE 결정 2) — 커맨드·훅 공유 단일 소스.

PEER_OF는 SEC 근거가 없어 L1(domain_tagging) 대상이 아니다. L2는 LLM 추측 태그를 **기본**으로
채택하되, 결정론 판정기(peer_adjudicator)가 **거부권**(grounded_ratio ≤ 0.2)을 행사한다.
거부권 발동 시 태그를 기각하고 **업종 버킷 폴백**으로 마킹한다.

파이프라인: 회사명+industry(㉯ 프롬프트) → LLM 초안(도메인 태그·claim 영어·rationale)
           → 접지 판정(ground_claim) → 거부권(veto) → machine_check + status.

★안전핀(하드 룰):
  - relation_domain(승인본)은 이 코어가 절대 쓰지 않는다(L1과 동일 규약, 검수=Phase 2).
    L2 태그는 relation_domain_draft + domain_review_status('auto'/'pending') + domain_machine_check에만 기록.
  - 거부권 발동 = status **'pending'**(미채택→서빙 버킷 폴백). **'rejected' 금지** — ego 서빙이
    'rejected'를 soft-drop(엣지 숨김)하므로, 거부권으로 PEER 관계 자체가 사라지면 안 된다
    (거부권은 "태그 기각·버킷 폴백"이지 "관계 은닉"이 아니다).
  - claim은 **영어**로 출력(L2X-SWEEP-EN-CLAIM) → 영어 FMP desc와 동일언어 접지(교차언어 매칭 제거).
    단 판정기는 언어 무관(ground_claim이 한국어 claim도 처리 → A3 파일럿의 기존 실험 CSV 재사용 가능).
  - 하·상이 구획(저시총·타산업)은 "추정" 라벨(is_estimate) 기록 — 실험상 최저 접지·최고 과신.
"""

from __future__ import annotations

from apps.chain_sight.services.domain_tagging import extract_rationale, parse_llm_json
from apps.chain_sight.services.peer_adjudicator import ground_claim, veto

PEER_RELATION_TYPES = ("PEER_OF",)
TAG_SOURCE = "L2-ADOPT"

# ── ㉯ 프롬프트: 회사명+industry, domain_tag 한국어(표시 일관성)·claim 영어(접지) ──
_PEER_SYSTEM = (
    "너는 미국 상장사 간 관계를 분류하는 금융 애널리스트다. 두 Peer 종목이 어떤 사업 "
    "도메인에서 경쟁·연결되는지 판단한다. "
    "반드시 JSON만 출력(설명·마크다운 금지):\n"
    '{"domain_tag": "짧은 한국어 명사구", "confidence": 0.0, '
    '"rationale": {"claim": "one English sentence grounding the shared business domain", '
    '"claim_type": "known_fact", "basis_hint": "hint", '
    '"counter_signal": "signal that would overturn this (empty string if none)"}}\n'
    "- domain_tag: 한국어 명사구 1개, 예 \"반도체·메모리\", \"클라우드·엔터프라이즈SW\". "
    "근거 없으면 빈 문자열.\n"
    "- claim: MUST be in ENGLISH — describe the concrete shared domain using terms that would "
    "appear in the companies' business descriptions (products, markets, technologies).\n"
    "- claim_type: known_fact(확실)|inference(추론)|uncertain(불확실).\n"
    "- rationale는 감사용 자기보고 — 왜 그 태그인지, 무엇이 판단을 뒤집을 수 있는지."
)


def build_peer_prompt(symbol_a, symbol_b, name_a="", name_b="", industry_a="", industry_b=""):
    """㉯ 프롬프트 (심볼+회사명+industry). (system_instruction, contents) 반환."""
    user = (
        f"두 Peer 종목:\n"
        f"- {symbol_a} ({name_a}, {industry_a})\n"
        f"- {symbol_b} ({name_b}, {industry_b})"
    )
    return _PEER_SYSTEM, [user]


def is_estimate_cell(mcap_tercile, industry_same) -> bool:
    """하·상이 구획 → "추정" 라벨. (저시총 tercile ∧ 타산업).

    industry_same: True(동일)/False(상이)/None(결측). 결측은 상이로 취급하지 않음(보수적 False).
    """
    return str(mcap_tercile).strip() == "하" and industry_same is False


def _domain_tag(out: dict) -> str | None:
    """LLM 출력에서 domain_tag 추출(한국어 명사구, 80자 절단)."""
    t = str(out.get("domain_tag", "") or "").strip()
    return t[:80] or None


def build_peer_machine_check(
    *, g: dict, vetoed: bool, veto_reason: str, is_estimate: bool,
    mcap_tercile, industry_same, llm_conf, claim: str, rationale, correlation=None,
    json_parse: bool = True,
) -> dict:
    """L2 판정 감사 JSON(domain_machine_check에 저장). source=L2-ADOPT로 L1과 구분."""
    return {
        "source": TAG_SOURCE,
        "json_parse": json_parse,
        "grounded_ratio": g.get("grounded_ratio") if g else None,
        "grounded_en": f"{g['grounded_en']}/{g['en_total']}" if g else None,
        "grounded_syn": f"{g['grounded_syn']}/{g['syn_total']}" if g else None,
        "ungrounded_terms": g.get("ungrounded_terms") if g else None,
        "veto": vetoed,
        "veto_reason": veto_reason,
        "bucket_fallback": vetoed,   # 거부권 발동 = 태그 기각 → 서빙 시 업종 버킷 폴백
        "is_estimate": is_estimate,  # 하·상이 "추정" 라벨
        "mcap_tercile": mcap_tercile,
        "industry_same": industry_same,
        "llm_conf": llm_conf,
        "claim": claim,
        "llm_rationale": rationale,
        "correlation": correlation,
    }


def tag_peer_one(
    *, symbol_a, symbol_b, name_a="", name_b="", industry_a="", industry_b="",
    desc_a="", desc_b="", mcap_tercile="", industry_same=None, dct, llm_call,
    correlation=None,
) -> dict:
    """단건 Peer 쌍 태깅 코어(커맨드·훅 공유). llm_call=(system, contents)->raw_text 콜러블.

    반환: {ok, draft, adopted_tag, review_status, machine_check, is_estimate, veto, raw}
      - draft: LLM 원 태그(항상 기록, 거부권 무관) → relation_domain_draft
      - adopted_tag: 거부권 통과 시 태그, 기각 시 None(버킷 폴백)
      - review_status: 'auto'(채택) | 'rejected'(거부권/파싱실패 → 버킷 폴백)
    relation_domain(승인본)은 절대 미기록(하드 룰).
    """
    est = is_estimate_cell(mcap_tercile, industry_same)
    system, contents = build_peer_prompt(symbol_a, symbol_b, name_a, name_b, industry_a, industry_b)
    raw = llm_call(system, contents)
    out = parse_llm_json(raw)

    # 파싱 실패 → 태깅 불가 → 거부권(버킷 폴백).
    if out is None:
        mc = build_peer_machine_check(
            g=None, vetoed=True, veto_reason="json_fail", is_estimate=est,
            mcap_tercile=mcap_tercile, industry_same=industry_same,
            llm_conf=None, claim="", rationale=None, correlation=correlation,
            json_parse=False,
        )
        return {
            "ok": False, "draft": None, "adopted_tag": None,
            "review_status": "pending", "machine_check": mc,  # 미채택→버킷 폴백('rejected' 금지)
            "is_estimate": est, "veto": True, "raw": raw,
        }

    tag = _domain_tag(out)
    rationale = extract_rationale(out)  # {claim, claim_type, basis_hint, counter_signal} | None
    claim = rationale["claim"] if rationale else ""
    try:
        conf = float(out.get("confidence")) if out.get("confidence") not in (None, "") else None
    except (TypeError, ValueError):
        conf = None

    # 접지 판정 → 거부권(grounded_ratio ≤ 0.2 또는 접지 불가).
    g = ground_claim(claim, symbol_a, symbol_b, desc_a, desc_b, dct)
    vetoed = veto(g["grounded_ratio"])
    veto_reason = (
        "no_claim" if g["grounded_ratio"] is None
        else ("low_grounding" if vetoed else "")
    )
    mc = build_peer_machine_check(
        g=g, vetoed=vetoed, veto_reason=veto_reason, is_estimate=est,
        mcap_tercile=mcap_tercile, industry_same=industry_same,
        llm_conf=conf, claim=claim, rationale=rationale, correlation=correlation,
    )
    return {
        "ok": True,
        "draft": tag,                                  # 원 LLM 태그(항상 기록)
        "adopted_tag": None if vetoed else tag,        # 거부권 통과분만 채택
        "review_status": "pending" if vetoed else "auto",  # 거부권→pending(버킷 폴백, soft-drop 아님)
        "machine_check": mc,
        "is_estimate": est,
        "veto": vetoed,
        "raw": raw,
    }
