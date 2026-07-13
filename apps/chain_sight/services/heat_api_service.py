"""
Theme Heat API 빌더 (TH-15, 결정23B/24C/25③) — 읽기 전용(원장 조회, 재계산 없음).

E1 버튼바 / E2 카드 응답을 ThemeHeatScore(영속) + ThemeNewsVolume(누적 days)에서 조립.
성분 라벨은 heat_labels(단일 사전)만 참조. 밴드·가중치는 heat_synthesis 상수 재사용.

driver 산식(결정24 정본):
  delta = 전일 대비 각 성분 w_norm·s 증분. 양(+)의 증분만 합산, contribution_pct = 성분 증분 /
  양의 증분 합(basis="delta"). 전 성분 증분 ≤ 0 → driver=null. 전일 행 부재 → 수준 폴백:
  성분 w_norm·s / Σ(present w_norm·s)의 최대(basis="level").
"""

import math
from datetime import date, timedelta
from typing import Optional

from apps.chain_sight.services.heat_labels import COMPONENT_ORDER, component_label
from apps.chain_sight.services.heat_synthesis import HEAT_WEIGHTS, _is_present

DAYS_REQUIRED = 26        # C3_EXPAND_MIN (결정13 체계)
HISTORY_CAPACITY = 60     # 스파크라인 용량
ETA_WINDOW = 14           # 축적 속도 관측 창(일)
ETA_CV_GATE = 0.3         # CV < 0.3 일 때만 eta 산출

_BAND_DISPLAY = {"cool": "냉각", "warning": "가열", "overheated": "과열"}


def band_display(band: Optional[str]) -> Optional[str]:
    """공식 밴드명 → 표시층 라벨(결정24, 공식 규약 무변경). 0-39 냉각/40-69 가열/70-100 과열."""
    return _BAND_DISPLAY.get(band) if band else None


def _norm_z_mode(mode: Optional[str]) -> str:
    """z_mode 정규화: time_series* → time_series, 그 외 → cross_sectional."""
    if mode and str(mode).startswith("time_series"):
        return "time_series"
    return "cross_sectional"


def _theme_days(ref_id: str) -> int:
    """테마 C3 누적 days = ThemeNewsVolume 행수(재집계 원장 실측)."""
    from apps.chain_sight.models import HeatEntity, ThemeNewsVolume

    e = HeatEntity.objects.filter(kind="sector", ref_id=ref_id).first()
    if not e:
        return 0
    return ThemeNewsVolume.objects.filter(theme=e).count()


def _latest_rows(ref_id: str, limit: int = HISTORY_CAPACITY):
    """테마 ThemeHeatScore 최신순 조회(원장, 재계산 없음)."""
    from apps.chain_sight.models import HeatEntity, ThemeHeatScore

    e = HeatEntity.objects.filter(kind="sector", ref_id=ref_id).first()
    if not e:
        return []
    return list(ThemeHeatScore.objects.filter(theme=e).order_by("-date")[:limit])


def component_contributions(components: dict) -> dict:
    """present 성분의 점수 기여 {Cn: w_norm·s}. w_norm = w/Σ(present w)."""
    present = {k: components.get(k) for k in COMPONENT_ORDER
               if k in components and _is_present(components.get(k))}
    pw = sum(HEAT_WEIGHTS[k] for k in present)
    if pw <= 0:
        return {}
    out = {}
    for k, c in present.items():
        s = c.get("s")
        if s is None:
            s = 1.0 / (1.0 + math.exp(-float(c["z"])))  # 폴백(저장 s 부재)
        out[k] = (HEAT_WEIGHTS[k] / pw) * float(s)
    return out


def compute_driver(
    today_components: dict, prev_components: Optional[dict], delta_1d: Optional[int] = None
):
    """
    (driver dict | None, shares dict) 반환 — 대칭 확장(결정27=B).

    방향 판정 = delta_1d **부호** 기준(성분 증분 부호 아님):
      delta_1d > 0 → direction="up", 양(+) 증분만 합산, contribution = 증분/Σ양증분.
      delta_1d < 0 → direction="down", 음(−) 증분만 합산, contribution = |증분|/Σ|음증분|.
      delta_1d == 0 또는 전일 부재 → direction="none", level 폴백(성분 w_norm·s / Σ).
    퇴화(delta 부호와 일치하는 증분 성분 없음 = 재분배·반올림 기인) → level 폴백 + direction 유지.
    shares 합 = 100(±0.1) 항상.
    """
    today = component_contributions(today_components)
    if not today:
        return None, {}

    if prev_components is not None and delta_1d is not None and delta_1d != 0:
        prev = component_contributions(prev_components)
        deltas = {k: today[k] - prev.get(k, 0.0) for k in today}
        if delta_1d > 0:
            direction = "up"
            mags = {k: d for k, d in deltas.items() if d > 0}
        else:
            direction = "down"
            mags = {k: -d for k, d in deltas.items() if d < 0}  # |음증분|
        if mags:
            pool, basis = mags, "delta"
        else:  # 퇴화: delta 부호와 일치하는 증분 성분 없음 → level 폴백, direction 유지
            pool, basis = today, "level"
    else:
        direction, pool, basis = "none", today, "level"

    total = sum(pool.values())
    shares = {k: 100.0 * v / total for k, v in pool.items()}
    top = max(shares, key=shares.get)
    lbl = component_label(top)
    driver = {
        "component": top,
        "label_surface": lbl["label_surface"],
        "label_technical": lbl["label_technical"],
        "z": float(today_components[top]["z"]),
        "contribution_pct": round(shares[top], 1),
        "basis": basis,
        "direction": direction,
    }
    return driver, shares


def eta_days(ref_id: str, current_days: int, as_of: Optional[date] = None) -> Optional[int]:
    """
    accumulating 진행 ETA(D-n). 최근 14일 일별 축적 증분(0/1)의 CV < 0.3 일 때만 산출.

    산식: 최근 ETA_WINDOW일 각 날짜에 ThemeNewsVolume 행 존재=1/부재=0 → 수열.
      rate=mean, cv=std(모집단)/mean. cv<0.3 & rate>0 → ceil((26−days)/rate), 아니면 None.
    """
    from apps.chain_sight.models import HeatEntity, ThemeNewsVolume
    from django.utils import timezone

    if current_days >= DAYS_REQUIRED:
        return None
    as_of = as_of or timezone.now().date()
    e = HeatEntity.objects.filter(kind="sector", ref_id=ref_id).first()
    if not e:
        return None
    win_start = as_of - timedelta(days=ETA_WINDOW - 1)
    hit_dates = set(
        ThemeNewsVolume.objects.filter(theme=e, date__gte=win_start, date__lte=as_of)
        .values_list("date", flat=True)
    )
    seq = [1 if (win_start + timedelta(days=i)) in hit_dates else 0 for i in range(ETA_WINDOW)]
    mean = sum(seq) / ETA_WINDOW
    if mean <= 0:
        return None
    var = sum((x - mean) ** 2 for x in seq) / ETA_WINDOW
    cv = math.sqrt(var) / mean
    if cv >= ETA_CV_GATE:
        return None
    return math.ceil((DAYS_REQUIRED - current_days) / mean)


def _blocked(components: dict, as_of: date) -> Optional[dict]:
    """universe_stale=True → blocked 구조(값+사유 동봉, 은닉 아님)."""
    if not components.get("universe_stale"):
        return None
    ua = components.get("universe_as_of")
    days_stale = None
    if ua:
        try:
            days_stale = (as_of - date.fromisoformat(ua)).days
        except (TypeError, ValueError):
            days_stale = None
    return {"reason": "universe_stale", "since": ua, "days_stale": days_stale}


def build_bar_items() -> list:
    """E1 버튼바 — 테마 11종. computed(score desc) → accumulating(days desc)."""
    from apps.chain_sight.models import HeatEntity
    from apps.chain_sight.services.heat_beat import (
        is_universe_stale,
        universe_last_updated_date,
    )
    from django.utils import timezone

    today = timezone.now().date()
    live_stale = is_universe_stale(universe_last_updated_date(), today)
    computed, accumulating = [], []
    for e in HeatEntity.objects.filter(kind="sector").order_by("ref_id"):
        rows = _latest_rows(e.ref_id, limit=2)
        days = _theme_days(e.ref_id)
        if rows:  # computed = 영속 heat 행 존재
            latest = rows[0]
            prev = rows[1] if len(rows) > 1 else None
            delta = (latest.score - prev.score) if prev else None
            computed.append({
                "theme": e.ref_id, "status": "computed",
                "score": latest.score, "band": latest.status,
                "band_display": band_display(latest.status), "delta_1d": delta,
                "days": days, "days_required": DAYS_REQUIRED, "eta_days": None,
                "universe_stale": bool(latest.components.get("universe_stale", False)),
            })
        else:
            accumulating.append({
                "theme": e.ref_id, "status": "accumulating",
                "score": None, "band": None, "band_display": None, "delta_1d": None,
                "days": days, "days_required": DAYS_REQUIRED,
                "eta_days": eta_days(e.ref_id, days, today),
                "universe_stale": bool(live_stale),
            })
    computed.sort(key=lambda x: x["score"], reverse=True)
    accumulating.sort(key=lambda x: x["days"], reverse=True)
    return computed + accumulating


def build_card(ref_id: str) -> Optional[dict]:
    """E2 카드 — 단일 테마. 원장 최신 행 조립. 테마 미존재 → None."""
    from apps.chain_sight.models import HeatEntity

    e = HeatEntity.objects.filter(kind="sector", ref_id=ref_id).first()
    if not e:
        return None

    rows = _latest_rows(ref_id, limit=HISTORY_CAPACITY)
    days = _theme_days(ref_id)

    if not rows:  # accumulating shell (미산출 — 재계산 없음)
        return {
            "theme": ref_id, "as_of": None, "status": "accumulating",
            "score": None, "band": None, "band_display": None, "delta_1d": None,
            "days": days, "days_required": DAYS_REQUIRED, "eta_days": eta_days(ref_id, days),
            "driver": None, "confidence": None, "components": [],
            "z_mode": None,
            "quadrant": {"heat": None, "dss": None, "dss_status": "coldstart",
                         "dss_eta": "Cycle 2 (DSS 미가동)"},
            "history": {"values": [], "capacity": HISTORY_CAPACITY, "filled": 0},
        }

    latest = rows[0]
    prev = rows[1] if len(rows) > 1 else None
    comps = latest.components or {}
    delta = (latest.score - prev.score) if prev else None
    driver, _shares = compute_driver(comps, (prev.components if prev else None), delta)

    # confidence — 실제 결측 성분에서 도출(하드코딩 금지)
    present = [k for k in COMPONENT_ORDER if k in comps and _is_present(comps.get(k))]
    missing = [k for k in COMPONENT_ORDER if k not in present]
    renorm_divisor = round(sum(HEAT_WEIGHTS[k] for k in present), 4)

    # components 8종
    comp_list, any_ts = [], False
    for cid in COMPONENT_ORDER:
        c = comps.get(cid) or {}
        is_present = _is_present(c)
        zmode = _norm_z_mode(c.get("z_mode"))
        if is_present and zmode == "time_series":
            any_ts = True
        status = ("computed" if is_present
                  else "coldstart" if cid in ("C4", "C8") else "accumulating")
        lbl = component_label(cid)
        comp_list.append({
            "id": cid, "label_surface": lbl["label_surface"],
            "label_technical": lbl["label_technical"],
            "z": c.get("z"), "w": HEAT_WEIGHTS[cid], "s": c.get("s"),
            "z_mode": zmode if is_present else None, "status": status,
        })

    values = [r.score for r in reversed(rows)]  # date 오름차순
    card = {
        "theme": ref_id, "as_of": latest.date.isoformat(), "status": "computed",
        "score": latest.score, "band": latest.status,
        "band_display": band_display(latest.status), "delta_1d": delta,
        "z_mode": "time_series" if any_ts else "cross_sectional",
        "driver": driver,
        "confidence": {"present": len(present), "total": len(HEAT_WEIGHTS),
                       "missing": missing, "renorm_divisor": renorm_divisor},
        "components": comp_list,
        "quadrant": {"heat": latest.score, "dss": None, "dss_status": "coldstart",
                     "dss_eta": "Cycle 2 (DSS 미가동)"},
        "history": {"values": values, "capacity": HISTORY_CAPACITY, "filled": len(values)},
    }
    blocked = _blocked(comps, latest.date)
    if blocked:
        card["blocked"] = blocked
    return card
