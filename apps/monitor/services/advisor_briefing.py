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

PROMPT_VERSION = "v1.2"
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
- 전할 수 있는 것은 오직 사실·거리·상태다: 종합 점수와 그 변화, 현재가로부터 시나리오 레벨(진입/목표/손절)까지의 거리, 상태(달 위상), 근거 지표의 충분성.
- 반드시 근거 지표 커버리지(n/총)를 문장에 포함하라. 숫자를 지어내지 마라 — 주어진 값만 쓴다.
- **제공된 수치(점수·%·가격)는 기준·부호·정밀도를 그대로 인용하라.** 재계산·기준 변경·반올림 금지 — 예: "+0.0185"를 "+0.02"로 줄이거나, "현재가로부터 +5.02%"를 "매입가 대비 -5%"처럼 기준·부호를 뒤집지 마라. 거리는 항상 '현재가로부터'가 기준이다.
- **가격은 프롬프트에 주어진 통화 표기(예 "$")를 그대로 써라.** "원" 등 다른 통화 단위로 임의 치환하지 마라 — 프롬프트에 없는 통화 단위를 지어내지 마라.
- 근거 점검 수치(생존 m/n, 소멸 연속거래일수, 재확인 D-n)도 위 인용 원칙과 동일하게 제공된 값 그대로 쓴다 — 계산·반올림 금지.
- 상태는 주어진 상태 어휘(달 위상 라벨)를 그대로 쓴다.
- 무변화(unchanged=true)로 표시되면 1~2문장으로 짧게 "큰 변화 없음 + 현재 상태" 정도만 전한다.
- headline은 40자 이내, body는 350자 이내.

출력은 반드시 아래 JSON 형식 하나만. 그 외 텍스트·코드펜스 금지:
{"headline": "...", "body": "..."}"""


# 통화 코드 → 프롬프트 표기 접두(B-BE-2). 값은 Stock.CURRENCY_CHOICES 범위 내에서만
# 늘어난다 — 미등록 코드는 코드 그대로 접두(예 "EUR 100")로 안전 폴백.
_CURRENCY_PREFIX = {"USD": "$", "KRW": "₩"}


def _currency_prefix(code):
    return _CURRENCY_PREFIX.get(code, f"{code} " if code else "")


def _fmt_price(price, currency):
    """가격에 통화 접두를 붙인다 — 숫자 자체(정밀도)는 원문 그대로 보존(인용 계약 무변)."""
    prefix = _currency_prefix(currency)
    return f"{prefix}{price}"


def _pct_distance(close, level):
    """현재가로부터 레벨까지 거리 % — **기준=현재가**. level>close 양수(위), <close 음수(아래)."""
    if close in (None, 0) or level is None:
        return None
    return round((float(level) - float(close)) / float(close) * 100.0, 2)


def _state_display(score):
    """화면 display 정본 상태 어휘(달 위상 라벨). MonitorSerializer.get_display와 동일 원천
    (score_to_phase) — MonitorSnapshot.state(관제 라이프사이클 밴드)나 Monitor.status
    (setting_up 등 등록 단계)와 다른 축이며, 사용자가 화면에서 보는 어휘가 이것이다.
    """
    from apps.monitor.services.state_machine import score_to_phase

    return score_to_phase(score)["label"]


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

    # 통화 표기(B-BE-2) — target_ref 배후 Stock.currency. 미매칭·비주식 scope는 USD 폴백.
    from packages.shared.stocks.models import Stock

    currency = (
        Stock.objects.filter(symbol=monitor.target_ref.upper())
        .values_list("currency", flat=True)
        .first()
    ) or "USD"

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

    # 근거 점검 (RECON-SWAP-0813 PART 2) — 시나리오 claim(levels용, target/stop 필수)과
    # 별개로 monitor의 active Claim(가격 파라미터 무관)을 찾아 evidences를 판정한다.
    # 없으면 evidence=None → 프롬프트에서 근거 섹션 생략.
    evidence_claim = monitor.claims.filter(status="active").first()
    evidence = (
        _evidence_summary(evidence_claim, latest.asof_date)
        if evidence_claim is not None
        else None
    )

    return {
        "symbol": monitor.target_ref,
        "asof": latest.asof_date,
        "overall_score": latest.overall_score,
        "delta": delta,
        "state": latest.state,
        "state_display": _state_display(latest.overall_score),
        "prev_state": prev.state if prev else None,
        "coverage_n": coverage_n,
        "coverage_total": coverage_total,
        "indicators": indicators,
        "close": close,
        "currency": currency,
        "levels": levels,
        "claim": claim,
        "evidence": evidence,
    }


def _evidence_summary(claim, as_of_date):
    """근거 점검 요약(RECON-SWAP-0813 PART 2) — judge_claim_evidences 판정을 브리핑용으로 정리.

    반환: {"total": n, "alive": m, "extinct": [...], "unstructured": bool}.
    - total=0(evidences 없음, assertion만) → unstructured=True(근거 미등록).
    - extinct = 소멸(dead/expired) 근거만. 자동형=지표명+dead_streak_days,
      수동형=description+재확인 기한 경과일수(overdue_days). unknown(판정 보류)은
      생존도 소멸도 아니므로 목록에 올리지 않는다(alive count에도 미포함).
    """
    from datetime import timedelta

    from apps.monitor.models.evidence import ClaimEvidence
    from apps.monitor.services.evidence_judge import (
        ALIVE,
        DEAD,
        EXPIRED,
        judge_claim_evidences,
    )

    ev_by_id = {e.id: e for e in claim.evidences.select_related("indicator")}
    judged = judge_claim_evidences(claim, as_of_date=as_of_date)
    total = len(judged)
    if total == 0:
        return {"total": 0, "alive": 0, "extinct": [], "unstructured": True}

    alive_n = sum(1 for j in judged if j["status"] == ALIVE)
    extinct = []
    for j in judged:
        if j["status"] not in (DEAD, EXPIRED):
            continue
        ev = ev_by_id.get(j["evidence_id"])
        if j["kind"] == ClaimEvidence.Kind.AUTO:
            label = ev.indicator.name if ev is not None and ev.indicator_id else "(지표 삭제됨)"
            extinct.append(
                {"kind": "auto", "label": label, "dead_streak_days": j["dead_streak_days"]}
            )
        else:
            if ev is not None:
                baseline = ev.last_confirmed_at or ev.created_at.date()
                due = baseline + timedelta(days=ev.recheck_period_days)
                overdue_days = (as_of_date - due).days
                label = ev.description
            else:
                overdue_days = j["dead_streak_days"]
                label = ""
            extinct.append({"kind": "manual", "label": label, "overdue_days": overdue_days})
    return {"total": total, "alive": alive_n, "extinct": extinct, "unstructured": False}


def _render_evidence_lines(evidence):
    """근거 점검 프롬프트 라인(RECON-SWAP-0813 PART 2). evidence=None → 빈 리스트(섹션 생략)."""
    if evidence is None:
        return []
    if evidence["unstructured"]:
        return ["", "근거 점검: 근거 미등록 — 빌더에서 등록 가능"]

    total, alive = evidence["total"], evidence["alive"]
    if alive == total:
        # 무변화 압축 준용 — 전 근거 생존이면 1줄로 묶는다.
        return ["", f"근거 점검: 근거 {alive}/{total} 전부 생존"]

    lines = ["", f"근거 점검: 근거 {alive}/{total} 생존"]
    if alive == 0:
        lines.append("  ⚠ 등록 근거 전부 소멸 — 브리핑을 이 소멸 경고로 시작하라.")
    for item in evidence["extinct"]:
        if item["kind"] == "auto":
            lines.append(
                f"  - [자동] {item['label']}: 연속 {item['dead_streak_days']}거래일 위반(소멸)"
            )
        else:
            lines.append(f"  - [수동] {item['label']}: 재확인 D-{item['overdue_days']}")
    return lines


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
    currency = ctx.get("currency", "USD")
    lines = [
        f"종목: {ctx['symbol']}  기준일(asof): {ctx['asof']}",
        f"종합 점수: {ctx['overall_score']:+.4f} (범위 -1~1, 소수 4자리 그대로 인용)"
        + (f", 직전 대비 Δ {ctx['delta']:+.4f}" if ctx["delta"] is not None else ", 직전 스냅샷 없음"),
        f"상태(달 위상): {ctx['state_display']}",
        f"근거 지표 커버리지: {ctx['coverage_n']}/{ctx['coverage_total']} (충분/등록)",
        f'통화 표기: 아래 가격은 전부 "{_currency_prefix(currency)}" 표기(다른 통화 단위로 바꾸지 말 것)',
    ]
    if ctx["close"] is not None:
        lines.append(f"현재가(종가): {_fmt_price(ctx['close'], currency)}")
    if ctx["levels"]:
        lines.append("시나리오 레벨 (거리 기준 = 현재가로부터):")
        for lv in ctx["levels"]:
            d = f"현재가로부터 {lv['distance_pct']:+.2f}%" if lv["distance_pct"] is not None else "n/a"
            lines.append(f"  - {lv['label']} {_fmt_price(lv['price'], currency)}: {d}")
    suff_names = [i["name"] for i in ctx["indicators"] if i["sufficient"]]
    if suff_names:
        lines.append("충분 지표: " + ", ".join(suff_names))
    lines.extend(_render_evidence_lines(ctx.get("evidence")))
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
