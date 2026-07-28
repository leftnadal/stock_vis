"""뉴스 URL 정규화 — provider 공통 단일 소스 (S3 + NEWS-URLNORM-IDQUERY).

cross-provider dedup 은 `NewsArticle.url` exact match(+ url_hash)에 의존한다. provider마다
정규화가 달라 같은 기사가 다른 url 로 저장되던 것을 이 함수 하나로 통일한다.

## id-보존 정규화 (지시서⑩, Blocklist 베이스)

과거 규칙은 **쿼리 전량 제거**였다. 그 결과 기사 id 가 query 에 있는 URL
(youtube `?v=`·finviz `?t=`·CMS `?idxno=`)이 base path 로 붕괴 → 서로 다른 페이지가
1건으로 병합돼 **co-mention 조작(허위 공동언급)** 위험이었다(지시서⑨ 실측: 공유경로
collapse 22그룹/3,695행, finviz(AV) 1,675·youtube(FMP) 1,961).

새 규칙: **고신뢰 tracking key 만 제거하고 나머지 쿼리(id·ambig 포함)는 보존**한다.
  - tracking blocklist = `utm_*` prefix + {fbclid, gclid, ref} (지시서⑨ 확정 고신뢰분).
  - ambiguous 후보(cid·ocid·ncid·mod·amp·msn 렌더링·lang 등)는 **넣지 않는다** —
    보존 쪽 실패(과소병합=가역)가 오병합(비가역)보다 안전. Hybrid 세션에서 재판정.

## 행위보존 (지시서⑩ STEP 3 골든셋)

문자열 기반으로 구 규칙의 (a)무쿼리·(b)tracking-only 출력을 **IDENTICAL** 유지한다:
  - 쿼리가 없거나(=a) 모든 쿼리 key 가 tracking 이면(=b) → 구 규칙과 동일한
    base(스킴·호스트·경로 소문자, `?` 이후 제거, 끝 슬래시 제거)를 낸다.
  - id/ambig 쿼리가 남으면(=c) → base + `?` + (tracking 제거된) 쿼리 를 보존(변경 허용).
정규화 규칙 변경은 이 함수에 국한한다(경계 위반 신설 금지).
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode

# 고신뢰 tracking key (지시서⑨ 확정). utm_* 는 prefix 로 별도 처리.
_TRACKING_KEYS = frozenset({"fbclid", "gclid", "ref"})


def _is_tracking(key: str) -> bool:
    return key.startswith("utm_") or key in _TRACKING_KEYS


def normalize_news_url(url: str | None) -> str:
    """뉴스 기사 URL 을 dedup 용으로 정규화한다. None/빈값은 "" 반환.

    고신뢰 tracking 파라미터만 제거하고 id·기타 쿼리는 보존한다.
    """
    normalized = (url or "").strip().lower()
    if not normalized:
        return ""

    if "?" in normalized:
        base, _, tail = normalized.partition("?")
        # tail = "query[#fragment]". fragment 은 구 규칙과 동일하게 버린다(? 이후 절단).
        query_str = tail.partition("#")[0]
        kept = [
            (k, v)
            for k, v in parse_qsl(query_str, keep_blank_values=True)
            if not _is_tracking(k)
        ]
        # kept 가 비면(=쿼리 없음/tracking-only) 구 규칙과 동일하게 base 만 남긴다(IDENTICAL).
        normalized = f"{base}?{urlencode(kept)}" if kept else base

    if normalized.endswith("/"):
        normalized = normalized[:-1]

    return normalized
