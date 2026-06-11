"""
CS-UNIV Part D — tier별 신규 구간 품질 샘플링 (FMP get_historical_price).
T1(테마 ETF holdings 신규), T2(S&P400 신규)만 측정. T3/T4는 프록시 미가용.
실행: python manage.py shell -c "exec(open('docs/chain_sight/univ_analysis/sample_quality.py').read())"
예산: 30+30 = 60 FMP콜.
"""
import json
import statistics
from datetime import date, timedelta
from django.conf import settings
from packages.shared.stocks.models import Stock
from services.serverless.models import ETFHolding
from packages.shared.api_request.providers.fmp.client import FMPClient

univ = set(Stock.objects.values_list("symbol", flat=True))
etf_t = set(t.upper() for t in ETFHolding.objects.values_list("stock_symbol", flat=True))
idx = json.load(open("docs/chain_sight/univ_analysis/index_constituents.json"))
sp400 = set(idx["sp400"])

t1_new = sorted(etf_t - univ)              # 테마 ETF holdings 신규 213
t2_new = sorted(sp400 - univ - etf_t)      # S&P400만의 신규 386


def sample(lst, n=30):
    if len(lst) <= n:
        return lst
    step = len(lst) / n
    return [lst[int(i * step)] for i in range(n)]


def pctile(sv, p):
    if not sv:
        return None
    k = (len(sv) - 1) * p / 100
    f = int(k)
    cc = min(f + 1, len(sv) - 1)
    return sv[f] + (sv[cc] - sv[f]) * (k - f)


c = FMPClient(api_key=settings.FMP_API_KEY)
fr = (date.today() - timedelta(days=130)).isoformat()
to = date.today().isoformat()
calls = 0


def measure(symbols, label):
    global calls
    advs, zero_ratios, rows = [], [], []
    fail = []
    for s in symbols:
        try:
            d = c.get_historical_price(s, from_date=fr, to_date=to)
            calls += 1
            if not d:
                fail.append(s)
                continue
            d = d[:90]
            vols = [x.get("volume", 0) or 0 for x in d]
            closes = [x.get("close", 0) or 0 for x in d]
            advs.append(statistics.mean(cl * v for cl, v in zip(closes, vols)))
            zero_ratios.append(sum(1 for v in vols if v == 0) / len(vols))
            rows.append(len(d))
        except Exception as e:
            fail.append(s)
            calls += 1
    advs.sort()
    exp_bdays = 90  # 최근 90거래일 요청
    miss = [1 - r / exp_bdays for r in rows]
    print(f"\n── {label} (샘플 {len(symbols)}/{len(symbols)}) ──")
    if advs:
        print(f"  ADV(거래대금) median=${statistics.median(advs)/1e6:.1f}M  p10=${pctile(advs,10)/1e6:.2f}M")
        print(f"  거래량0 비율 평균: {100*statistics.mean(zero_ratios):.2f}%")
        print(f"  행수 중앙값: {statistics.median(rows):.0f}/90  결측률 평균: {100*statistics.mean(miss):.1f}%")
    print(f"  데이터 없음/실패: {len(fail)} {fail[:10]}")


print(f"T1 신규 모수 {len(t1_new)} / T2 신규 모수 {len(t2_new)}")
measure(sample(t1_new), "T1 신규 (테마 ETF holdings)")
measure(sample(t2_new), "T2 신규 (S&P400)")
print(f"\n[FMP 총 호출] {calls} / rate status: {c.get_rate_limit_status()}")
