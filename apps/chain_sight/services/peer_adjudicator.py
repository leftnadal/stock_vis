"""L2-X 결정론 자동 판정기 (⑳-3 자동판정 전환).

사람 전건 검수 → 결정론 판정 + 사람 감사. **채점용 LLM 호출 0** — 실데이터(FMP desc·
가격 상관)와 사전만 사용. C 하이브리드 grounding(영어 토큰 직매칭 + 한→영 동의어 사전).

판정기 3종:
  1. ground_claim   : claim 핵심 용어 ↔ desc_a/desc_b 결정론 매칭 → grounded_ratio + ungrounded
  2. market_flag    : 가격 상관 실측 + (llm_conf 상위4분위 × 상관 하위4분위) 불일치 신호(단독판정 아님)
  3. overconfident  : claim_type=known_fact ∧ grounded_ratio 하위 → 과신 플래그

교차언어(claim 한국어 / desc 영어) → SEC β ground_evidence 직접 이식 불가. normalize()만 재사용.
심볼·회사명 토큰은 추출 제외(desc에 자명 존재 → grounding 증거로 무의미, 비율 희석 방지).
"""

import json
import os
import re

from services.sec_pipeline.grounding import normalize

_DICT_PATH = os.path.join(os.path.dirname(__file__), "peer_grounding_dict.json")

# 영어 토큰 추출 시 제외(도메인 무의미 일반어·회사 접미)
_EN_STOP = {
    "and", "the", "for", "with", "inc", "corp", "co", "ltd", "llc", "plc",
    "company", "corporation", "group", "holdings", "its", "are", "that", "this",
}
# 한국어 dict_gap 청크 추출 시 제외(일반어·불용)
_KO_STOP = {
    "모두", "사업", "회사", "제품", "서비스", "관련", "다양한", "시장", "산업", "솔루션",
    "핵심", "주요", "위한", "광범위한", "내에서", "필수적인", "있다", "도메인", "분야",
    "영역", "제공하", "그리고", "또한", "통해", "기업", "매우", "다른", "이러한",
    # dict_gap 1회전 실측 필러(관계/연결 서술어 — 도메인 grounding 무의미)
    "제공", "제공하여", "기반", "같은", "관계", "연결", "연결됩니다", "직접적",
    "직접적인", "직접", "미국", "제공한다", "제공하는", "하여", "된다", "포함",
}
_KO_SUFFIXES = ["으로써", "에서", "에게", "이며", "하며", "하고", "되는", "들의", "이다",
                "한다", "되어", "으로", "에", "를", "을", "은", "는", "이", "가", "의",
                "와", "과", "로", "및"]


def load_dict(path=_DICT_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["dict"]


def _strip_suffix(tok):
    for s in _KO_SUFFIXES:
        if tok.endswith(s) and len(tok) - len(s) >= 2:
            return tok[: -len(s)]
    return tok


def _norm_desc(desc_a, desc_b):
    return normalize((desc_a or "") + " " + (desc_b or "")).lower()


def ground_claim(claim, symbol_a, symbol_b, desc_a, desc_b, dct):
    """claim(한국어)의 핵심 용어를 desc(영어)에 접지. 순수 함수, LLM 무호출.

    반환: {grounded_ratio, grounded_en, en_total, grounded_syn, syn_total,
           ungrounded_terms, dict_gap_terms}
    """
    text = claim or ""
    # 괄호 안 심볼 제거
    text_no_sym = re.sub(r"\([A-Za-z]+\)", "", text)
    nd = _norm_desc(desc_a, desc_b)
    excl = {str(symbol_a).lower(), str(symbol_b).lower()}

    # ── 영어 토큰(심볼·일반어 제외) ──
    en_terms = []
    for m in re.findall(r"[A-Za-z][A-Za-z0-9]{1,}", text):
        t = m.lower()
        if t in excl or t in _EN_STOP:
            continue
        en_terms.append(t)
    en_terms = list(dict.fromkeys(en_terms))  # 유니크·순서보존
    grounded_en = [t for t in en_terms if t in nd]

    # ── 한→영 동의어 사전 히트 ──
    syn_hits = []       # (korean_key, [english variants])
    for ko, ens in dct.items():
        if ko in text:
            syn_hits.append((ko, ens))
    grounded_syn = [(ko, ens) for ko, ens in syn_hits if any(e.lower() in nd for e in ens)]

    en_total, syn_total = len(en_terms), len(syn_hits)
    gcount = len(grounded_en) + len(grounded_syn)
    total = en_total + syn_total
    grounded_ratio = round(gcount / total, 3) if total else None

    ungrounded = [t for t in en_terms if t not in nd] + \
                 [ko for ko, ens in syn_hits if not any(e.lower() in nd for e in ens)]

    # ── 사전 갭 감사: dict 미수록 한국어 명사(정상 도메인어면 사전 보충 대상) ──
    dict_gap = []
    seen = set(dct.keys())
    for tok in re.findall(r"[가-힣]{2,}", text_no_sym):
        base = _strip_suffix(tok)
        if len(base) < 2 or base in _KO_STOP or base in seen:
            continue
        # dict 키가 base의 substring이면 이미 커버(예: '반도체장비' 안에 '반도체')
        if any(k in base for k in dct):
            continue
        dict_gap.append(base)
        seen.add(base)

    return {
        "grounded_ratio": grounded_ratio,
        "grounded_en": len(grounded_en), "en_total": en_total,
        "grounded_syn": len(grounded_syn), "syn_total": syn_total,
        "ungrounded_terms": ungrounded,
        "dict_gap_terms": dict_gap,
    }


# ── 사분위 헬퍼 ──
def quartiles(values):
    """정렬 후 Q1(하위 25%)·Q3(상위 25%) 경계. 빈 리스트면 (None,None)."""
    xs = sorted(v for v in values if v is not None)
    if not xs:
        return None, None
    q1 = xs[len(xs) // 4]
    q3 = xs[(3 * len(xs)) // 4]
    return q1, q3


def market_flag(correlation, llm_conf, corr_q1, conf_q3):
    """가격 상관 불일치 신호(단독 판정 아님). conf 상위4분위 ∧ 상관 하위4분위 → True."""
    if correlation is None or llm_conf is None or corr_q1 is None or conf_q3 is None:
        return False
    try:
        return float(llm_conf) >= conf_q3 and float(correlation) <= corr_q1
    except (TypeError, ValueError):
        return False


def overconfident(claim_type, grounded_ratio, gr_q1):
    """claim_type=known_fact ∧ grounded_ratio 하위4분위 → 과신 플래그."""
    if grounded_ratio is None or gr_q1 is None:
        return False
    return str(claim_type).strip().lower() == "known_fact" and grounded_ratio <= gr_q1


# ── 거부권(veto) — L2-ADOPT 프로덕션 판정 (D-L2-SOURCE 결정 2) ──
# 실험의 overconfident 플래그(동적 gr_q1≈0.667·저정밀, ~10%만 진짜)를 프로덕션에서
# **고정 임계 거부권**으로 대체한다. grounded_ratio ≤ VETO_GROUNDING 이면 LLM 태그를
# 자동 기각 → 업종 버킷 폴백. 판정기가 LLM 태그에 거부권을 행사하는 유일한 하드 룰.
VETO_GROUNDING = 0.2


def veto(grounded_ratio):
    """거부권 판정: LLM 태그를 기각해야 하는가.

    - grounded_ratio ≤ VETO_GROUNDING(0.2) → True(기각·버킷 폴백).
    - grounded_ratio is None(claim 없음·파싱 실패 → 접지 불가) → True(보수적 기각).
      버킷은 항상 존재하므로 접지 불가 시 폴백이 안전. 이 경로는 별도 카운트로 보고.
    - grounded_ratio > 0.2 → False(LLM 태그 채택).
    """
    if grounded_ratio is None:
        return True
    return grounded_ratio <= VETO_GROUNDING
