"""ADVISOR L-A 정기 브리핑 서비스 (MON-P4-LA, D-MON-P4-LA).

'비서'의 사실 요약: 점수·거리·상태만 전한다. 매매 명령은 하지 않는다(언어 계약 +
사후 lexical 가드 이중 방어). 점수 정본 = MonitorSnapshot(재계산 금지 — 인용만).
LLM = packages.shared.llm.complete(provider="anthropic") (leaf-safe 공용 게이트웨이).
실패 = 무음 스킵 + 로그(일지에 오류 행 생성 금지).
"""
import json
import logging

from django.conf import settings

from apps.monitor.models import AdvisorNote
from apps.monitor.models.monitoring import MonitorSnapshot
from apps.monitor.services.price_zone import zone_anchor
from apps.monitor.services.scenario import latest_close
from apps.monitor.services.technical import score_indicator_dispatch

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1"
SURFACE_LA = AdvisorNote.Surface.L_A

# 무변화 임계 (D-MON-P4-LA, STEP0 실측 48델타 P50 0.0125<0.02<P75 0.0252로 확정)
UNCHANGED_SCORE_EPS = 0.02

# 사후 lexical 가드 — 명령형 매매 지시어(프롬프트 계약의 이중 방어). 검출 시 저장 안 함.
FORBIDDEN_LEXEMES = [
    "매수하", "매수해", "매도하", "매도해", "사세요", "파세요", "매집",
    "추가매수", "추가 매수", "물타기", "불타기", "청산하", "청산해",
    "손절하", "손절해", "익절하", "익절해", "진입하", "진입해",
    "들어가세요", "빠져나", "비중을 늘", "비중을 줄", "담으세요", "정리하세요",
]

SYSTEM_PROMPT_V1 = """너는 개인 투자자의 종목 관제를 돕는 '비서'다. 한국어로 그날의 상황을 사실만 담아 요약한다.

절대 규칙:
- 매매 행동을 지시하지 마라. "매수/매도/추가/청산/손절/익절하라", "사세요/파세요", "비중을 늘/줄여라" 같은 명령형 표현을 절대 쓰지 마라.
- 전할 수 있는 것은 오직 사실·거리·상태다: 종합 점수와 그 변화, 현재가와 시나리오 레벨(진입/목표/손절)까지의 거리, 상태 밴드, 근거 지표의 충분성.
- 반드시 근거 지표 커버리지(n/총)를 문장에 포함하라. 숫자를 지어내지 마라 — 주어진 값만 쓴다.
- 무변화(unchanged=true)로 표시되면 1~2문장으로 짧게 "큰 변화 없음 + 현재 상태" 정도만 전한다.
- headline은 40자 이내, body는 350자 이내.

출력은 반드시 아래 JSON 형식 하나만. 그 외 텍스트·코드펜스 금지:
{"headline": "...", "body": "..."}"""


def _pct_distance(close, level):
    """현재가 대비 레벨까지 거리 %. level 위=양수(더 올라야), 아래=음수."""
    if close in (None, 0) or level is None:
        return None
    return round((float(level) - float(close)) / float(close) * 100.0, 2)


def build_context(monitor, as_of=None):
    """브리핑 컨텍스트 조립 — 전 수치는 기존 정본 소스에서만 조회(점수 재계산 없음).

    반환 None = 브리핑 불가(스냅샷 없음). 그 외 dict.
    """
    snaps = list(
        MonitorSnapshot.objects.filter(monitor=monitor).order_by("-asof_date")[:2]
    )
    if not snaps:
        return None
    latest = snaps[0]
    prev = snaps[1] if len(snaps) > 1 else None
    delta = (
        round(latest.overall_score - prev.overall_score, 4)
        if prev is not None
        else None
    )

    # 커버리지 = P2A 충분성 로직. 분모 = 해당 모니터 등록 지표 총수(9 하드코딩 금지).
    inds = list(monitor.indicators.filter(is_active=True, is_paused=False))
    coverage_total = len(inds)
    indicators = []
    coverage_n = 0
    for ind in inds:
        r = score_indicator_dispatch(ind, as_of_date=latest.asof_date)
        suff = bool(r.get("is_sufficient", False))
        if suff:
            coverage_n += 1
        indicators.append(
            {"name": ind.name, "score": r.get("score"), "sufficient": suff}
        )

    # 시나리오 레벨 3종과 현재가 거리
    close = latest_close(monitor.target_ref)
    claim = monitor.claims.filter(
        status="active", target_price__isnull=False, stop_price__isnull=False
    ).first()
    levels = []
    if claim:
        anchor = zone_anchor(claim)
        anchor_label = "매입가" if claim.scenario_type == "hold" else "진입"
        for label, price in [
            (anchor_label, anchor),
            ("목표", claim.target_price),
            ("손절", claim.stop_price),
        ]:
            if price is not None:
                levels.append(
                    {
                        "label": label,
                        "price": float(price),
                        "distance_pct": _pct_distance(close, price),
                    }
                )

    return {
        "symbol": monitor.target_ref,
        "asof": latest.asof_date,
        "overall_score": latest.overall_score,
        "delta": delta,
        "state": latest.state,
        "prev_state": prev.state if prev else None,
        "coverage_n": coverage_n,
        "coverage_total": coverage_total,
        "indicators": indicators,
        "close": close,
        "levels": levels,
        "claim": claim,
    }


def _crossed_level(monitor, claim, close):
    """최근 2거래일 종가로 시나리오 레벨(진입/목표/손절) 교차 판정."""
    if claim is None:
        return False
    from packages.shared.stocks.models import DailyPrice

    rows = list(
        DailyPrice.objects.filter(stock__symbol=monitor.target_ref)
        .order_by("-date")
        .values_list("close_price", flat=True)[:2]
    )
    if len(rows) < 2:
        return False
    today, yday = float(rows[0]), float(rows[1])
    lo, hi = min(today, yday), max(today, yday)
    anchor = zone_anchor(claim)
    for level in (anchor, claim.target_price, claim.stop_price):
        if level is not None and lo <= float(level) <= hi:
            return True
    return False


def is_unchanged(ctx, monitor):
    """무변화 = 상태 전이 없음 AND |Δ overall|<0.02 AND 종가가 레벨 3종 미교차."""
    state_same = ctx["prev_state"] is None or ctx["state"] == ctx["prev_state"]
    delta_small = ctx["delta"] is None or abs(ctx["delta"]) < UNCHANGED_SCORE_EPS
    crossed = _crossed_level(monitor, ctx["claim"], ctx["close"])
    return state_same and delta_small and not crossed


def _lexical_guard(text):
    """명령형 매매 지시어 검출 시 True(저장 거부)."""
    return any(lex in text for lex in FORBIDDEN_LEXEMES)


def _render_user_prompt(ctx, unchanged):
    lines = [
        f"종목: {ctx['symbol']}  기준일(asof): {ctx['asof']}",
        f"종합 점수: {ctx['overall_score']:+.4f} (범위 -1~1)"
        + (f", 직전 대비 Δ {ctx['delta']:+.4f}" if ctx["delta"] is not None else ", 직전 스냅샷 없음"),
        f"상태 밴드: {ctx['state']}",
        f"근거 지표 커버리지: {ctx['coverage_n']}/{ctx['coverage_total']} (충분/등록)",
    ]
    if ctx["close"] is not None:
        lines.append(f"현재가(종가): {ctx['close']}")
    if ctx["levels"]:
        lines.append("시나리오 레벨까지 거리:")
        for lv in ctx["levels"]:
            d = f"{lv['distance_pct']:+.2f}%" if lv["distance_pct"] is not None else "n/a"
            lines.append(f"  - {lv['label']}: {lv['price']} ({d})")
    suff_names = [i["name"] for i in ctx["indicators"] if i["sufficient"]]
    if suff_names:
        lines.append("충분 지표: " + ", ".join(suff_names))
    lines.append(
        f"\nunchanged={str(unchanged).lower()}  "
        + ("(큰 변화 없음 — 1~2문장 축약)" if unchanged else "(변화 있음 — 상세 브리핑)")
    )
    return "\n".join(lines)


def generate_briefing(monitor, as_of=None):
    """단일 모니터 브리핑 생성 — 멱등 스킵·실패 무음. 반환 AdvisorNote | None."""
    ctx = build_context(monitor, as_of=as_of)
    if ctx is None:
        logger.info("[advisor] %s 스냅샷 없음 — 스킵", monitor.target_ref)
        return None

    asof = ctx["asof"]
    # 멱등: 존재 시 스킵(브리핑은 동결 기록 — update 없음)
    if AdvisorNote.objects.filter(
        monitor=monitor, asof=asof, surface=SURFACE_LA
    ).exists():
        logger.info("[advisor] %s @ %s 이미 존재 — 스킵", monitor.target_ref, asof)
        return None

    unchanged = is_unchanged(ctx, monitor)
    user_prompt = _render_user_prompt(ctx, unchanged)

    from packages.shared.llm import complete

    try:
        resp = complete(
            user_prompt,
            provider="anthropic",
            model=settings.ADVISOR_MODEL,
            system=SYSTEM_PROMPT_V1,
            max_tokens=1024,
        )
    except Exception as exc:  # 실패 = 해당 종목만 스킵 + ERROR 로그
        logger.error("[advisor] %s LLM 호출 실패 — 스킵: %s", monitor.target_ref, exc)
        return None

    raw = (resp.text or "").strip()
    # 코드펜스 방어(모델이 감쌀 경우)
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") : raw.rfind("}") + 1] if "{" in raw else raw
    try:
        parsed = json.loads(raw)
        headline = str(parsed["headline"]).strip()
        body = str(parsed["body"]).strip()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error("[advisor] %s JSON 파싱 실패 — 스킵: %s", monitor.target_ref, exc)
        return None

    # 사후 lexical 가드 — 금지어 검출 시 저장하지 않음(프롬프트+가드 이중 방어)
    if _lexical_guard(headline) or _lexical_guard(body):
        logger.warning(
            "[advisor] %s 명령형 지시어 검출 — 저장 거부(lexical 가드)", monitor.target_ref
        )
        return None

    return AdvisorNote.objects.create(
        monitor=monitor,
        asof=asof,
        surface=SURFACE_LA,
        headline=headline[:120],
        body=body,
        coverage_n=ctx["coverage_n"],
        coverage_total=ctx["coverage_total"],
        model_id=resp.model,
        prompt_version=PROMPT_VERSION,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
    )
