"""D-S3-9 제목 적중 게이트 — 카드 멤버가 제목에 등장하는 기사만 제목으로 인용한다.

배경(CS-S3-1D): 스모크 8번에서 급등 묶음 5장 중 2장의 제목이 다른 회사 이야기였다.
`articles_for_pair`가 **본문 co-mention** 기준이라, 제목의 주어는 제3 종목일 수 있다
(계측: ChainNewsEvent.symbol 이 제목 주어인 비율 18/50 = 36% 하한 —
`docs/reports/cs_s3_comention_provenance_recon.md` T-5).

규칙은 이 모듈 한 곳에만 둔다(B-4). 자회사·브랜드명 누락은 **CompanyAlias 행 추가**로
고치는 구조이며, 코드를 고치지 않는다. LLM 0 — 생성·요약·번역 없이 문자열 매칭만.
"""

import re

# 회사명에서 떼는 법인격·수식 접미어(매칭 핵심어만 남긴다).
_LEGAL_SUFFIXES = {
    "inc", "inc.", "incorporated", "corp", "corp.", "corporation", "company",
    "co", "co.", "ltd", "ltd.", "limited", "plc", "llc", "lp", "nv", "sa", "ag",
    "holdings", "holding", "group", "the", "&", "common", "stock", "class",
}
# 단독 토큰 매칭을 허용할 최소 길이(짧은 핵심어는 오탐이 크다).
_MIN_NAME_LEN = 4


def _core_name(name: str) -> str:
    """회사명에서 법인격 접미어를 떼어낸 핵심 구문. 'Amazon.com Inc.' → 'Amazon.com'."""
    if not name:
        return ""
    tokens = [t for t in re.split(r"[\s,]+", name.strip()) if t]
    core = []
    for t in tokens:
        if t.lower().strip(".,") in _LEGAL_SUFFIXES:
            continue
        core.append(t)
    return " ".join(core).strip()


def build_name_index(symbols) -> dict:
    """symbol → 제목 매칭 후보 문자열 목록. 조회 2회(Stock, CompanyAlias)로 고정 — N+1 금지.

    후보 = Stock.stock_name 핵심 구문 + 그 첫 유의어(길이 >= _MIN_NAME_LEN) + CompanyAlias.alias.
    """
    from django.apps import apps

    syms = {s.upper() for s in symbols if s}
    if not syms:
        return {}

    Stock = apps.get_model("stocks", "Stock")
    # 경계: sec_pipeline 직접 import 대신 apps.get_model (선례 market_story_feed.py SEC8K).
    CompanyAlias = apps.get_model("sec_pipeline", "CompanyAlias")

    index: dict[str, set] = {s: set() for s in syms}

    for sym, name in Stock.objects.filter(symbol__in=syms).values_list("symbol", "stock_name"):
        core = _core_name(name or "")
        if len(core) >= _MIN_NAME_LEN:
            index[sym.upper()].add(core)
            head = core.split(" ")[0]
            if len(head) >= _MIN_NAME_LEN and head != core:
                index[sym.upper()].add(head)

    for alias, ticker in CompanyAlias.objects.filter(ticker__in=syms).values_list("alias", "ticker"):
        core = _core_name(alias or "")
        if len(core) >= _MIN_NAME_LEN:
            index[ticker.upper()].add(core)

    return {k: sorted(v) for k, v in index.items()}


def title_mentions_member(title: str, members, name_index: dict) -> bool:
    """제목이 members 중 하나 이상을 말하는가.

    ① 티커: 단어경계 + 대소문자 구분(`\\bAAPL\\b`) — 소문자 일반어 오탐 차단.
    ② 회사명: name_index 의 후보 구문, 대소문자 무시(제목 표기가 일정하지 않다).
    """
    if not title or not members:
        return False
    for m in members:
        sym = (m or "").upper()
        if not sym:
            continue
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(sym) + r"(?![A-Za-z0-9])", title):
            return True
        for cand in name_index.get(sym, ()):
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(cand) + r"(?![A-Za-z0-9])", title, re.I):
                return True
    return False


def covered_members(article: dict, members) -> list:
    """기사가 덮는 멤버 목록(A-3 — 화면 표기용)."""
    mem = {(m or "").upper() for m in (members or [])}
    return sorted(mem & {(s or "").upper() for s in (article.get("symbols_covered") or [])})
