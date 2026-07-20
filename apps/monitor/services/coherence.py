"""매수 시나리오 정합 엔진 (TIMING-P2.5, 결정론 퀀트 — 예측 아님).

변동성 스케일링(1σ 랜덤워크 근사)로 목표가↔기한을 상호 정합시킨다. drift(추세)를 무시하는
근사이며 미래를 예측하지 않는다 — "변동성 기준 정합" 힌트를 사용자에게 제공할 뿐, 확정 주체는
항상 사용자(3-B). 전부 순수함수 + Decimal 정밀도(리포 관례). scenario_suggest가 소비.
"""
import math
from decimal import Decimal

# σ 산출 창(거래일) + 최소 행수(부족 시 None).
SIGMA_WINDOW = 120
SIGMA_MIN_ROWS = 60
# 거래일↔달력일 환산(주 5거래일).
CAL_PER_TRADING = 7.0 / 5.0
TRADING_PER_CAL = 5.0 / 7.0
# 기한 지평 클램프(달력일).
HORIZON_MIN_DAYS = 14
HORIZON_MAX_DAYS = 180


def daily_sigma(symbol, as_of=None):
    """DailyPrice 최근 SIGMA_WINDOW 거래일 로그수익률 표준편차(표본, ddof=1).

    행수 < SIGMA_MIN_ROWS → None. 반환 = float 일간 σ.
    """
    from datetime import timedelta

    from django.utils import timezone

    from packages.shared.stocks.models import DailyPrice

    as_of = as_of or timezone.localdate()
    # 창 + 여유(1행은 diff로 소실) — 넉넉히 당김
    since = as_of - timedelta(days=int((SIGMA_WINDOW + 10) * CAL_PER_TRADING) + 10)
    closes = list(
        DailyPrice.objects.filter(
            stock__symbol=symbol.upper(), date__gte=since, date__lte=as_of
        ).order_by("date").values_list("close_price", flat=True)
    )
    closes = [float(c) for c in closes][-(SIGMA_WINDOW + 1):]
    if len(closes) < SIGMA_MIN_ROWS + 1:
        return None
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
    n = len(rets)
    if n < SIGMA_MIN_ROWS:
        return None
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    sigma = math.sqrt(var)
    return sigma if sigma > 0 else None


def horizon_for_target(entry, target, sigma):
    """목표가 도달 정합 기한(달력일). t_거래일 ≈ (ln(target/entry)/σ)².

    entry/target Decimal 또는 float. σ<=0/None·target<=entry → None. 주 단위 반올림 + [14,180] 클램프.
    """
    if sigma is None or sigma <= 0:
        return None
    e = float(entry)
    t = float(target)
    if e <= 0 or t <= e:
        return None
    t_trading = (math.log(t / e) / sigma) ** 2
    cal = t_trading * CAL_PER_TRADING
    weeks = max(2, round(cal / 7.0))  # ≥2주(14일)
    days = weeks * 7
    return max(HORIZON_MIN_DAYS, min(HORIZON_MAX_DAYS, days))


def target_for_horizon(entry, horizon_days, sigma, direction="up"):
    """기한 정합 목표가. entry × exp(σ×√t_거래일). 상승 방향 기본.

    반환 = Decimal(4자리). σ None/≤0 → None.
    """
    if sigma is None or sigma <= 0 or horizon_days is None or horizon_days <= 0:
        return None
    e = float(entry)
    t_trading = float(horizon_days) * TRADING_PER_CAL
    factor = math.exp(sigma * math.sqrt(t_trading))
    target = e * factor if direction == "up" else e / factor
    return Decimal(str(round(target, 4)))


def rr_ratio(entry, target, stop):
    """손익비 R:R = (target−entry)/(entry−stop). 분모≤0 또는 결측 → None."""
    if entry is None or target is None or stop is None:
        return None
    e, t, s = float(entry), float(target), float(stop)
    risk = e - s
    if risk <= 0:
        return None
    return round((t - e) / risk, 2)
