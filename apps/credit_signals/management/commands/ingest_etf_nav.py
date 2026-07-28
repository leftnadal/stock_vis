"""
ETF NAV·시장가 일 1회 수집 (P2a-1, 로컬 수동/스크립트 전용).

FMP etf/info(nav) + quote(price)를 정본 거래일로 resolve해 EtfNavHistory에
upsert한 뒤 compute_all_signals()로 디스카운트 신호를 갱신한다.
beat 등록은 본 슬라이스 범위 밖(로컬 수동/스크립트만).

★ 운영 규칙: 포그라운드 블로킹 실행(harness reaping 정책). nohup/& 금지.

NOTE: nav는 FMP에서 이력이 제공되지 않아(당일 스냅숏만 — P2a-RECON 실측)
      별도 backfill 커맨드가 성립하지 않는다. 3년 z-창은 일 1회 수집으로
      시간에 따라 채워지며, 60관측 미만 구간은 기존 콜드스타트(gray) 계약 적용.

사용:
    python manage.py ingest_etf_nav
"""
from django.core.management.base import BaseCommand

from ...constants import ETF_DISCOUNT_MAP, ETF_SYMBOLS


class Command(BaseCommand):
    help = (
        "ETF NAV/시장가 1회 수집 → EtfNavHistory upsert → 디스카운트 신호 갱신 "
        "(로컬 수동, 포그라운드 블로킹 전용)."
    )

    def handle(self, *args, **options):
        import os

        from packages.shared.api_request.providers.fmp.client import FMPClient
        from ...services.etf_nav_service import collect_etf_nav
        from ...services.signal_service import compute_all_signals

        client = FMPClient(api_key=os.getenv("FMP_API_KEY"))
        summary = collect_etf_nav(client, ETF_SYMBOLS)
        for sym, result in summary.items():
            self.stdout.write(f"  {sym}: {result}")

        results = compute_all_signals()
        etf = {k: results.get(k) for k in ETF_DISCOUNT_MAP}
        self.stdout.write(self.style.SUCCESS(f"디스카운트 신호 갱신: {etf}"))
