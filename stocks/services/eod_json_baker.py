"""
EOD JSON Baker (Step 5)

Atomic Write 패턴 + 파일시스템 직접 서빙.

1. TMP_DIR에 JSON 생성
2. _atomic_swap(): OLD → 기존 OUTPUT, TMP → OUTPUT, OLD 삭제
3. DB EODDashboardSnapshot upsert
"""

import json
import logging
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from django.conf import settings
from django.utils import timezone as dj_timezone

from stocks.models import DailyPrice, EODDashboardSnapshot, PipelineLog

logger = logging.getLogger(__name__)

# 카테고리 메타데이터 (tagger와 동일)
from stocks.services.eod_signal_tagger import (
    ALL_SIGNAL_IDS,
    CATEGORY_COLORS,
    EDUCATION_TIPS,
    SIGNAL_CATEGORIES,
    SIGNAL_METADATA,
)


class EODJSONBaker:
    """
    시그널 데이터를 JSON 파일로 bake하고 DB 스냅샷을 upsert합니다.

    Atomic Write 패턴으로 파일 교체 시 일관성을 보장합니다.
    """

    OUTPUT_DIR = Path(settings.BASE_DIR) / 'frontend' / 'public' / 'static' / 'signals'
    TMP_DIR = Path(settings.BASE_DIR) / 'frontend' / 'public' / 'static' / 'signals_tmp'
    OLD_DIR = Path(settings.BASE_DIR) / 'frontend' / 'public' / 'static' / 'signals_old'

    def bake(
        self,
        target_date: date,
        signals_data: list[dict],
        market_summary: dict,
        pipeline_log: 'PipelineLog',
    ) -> dict:
        """
        전체 bake 프로세스를 실행합니다.

        Args:
            target_date: 거래일
            signals_data: EODNewsEnricher.enrich() 반환값
            market_summary: 시장 요약 dict
            pipeline_log: PipelineLog 인스턴스

        Returns:
            {'files_written': int, 'snapshot_id': int}
        """
        # TMP 디렉토리 초기화
        if self.TMP_DIR.exists():
            shutil.rmtree(self.TMP_DIR)
        self.TMP_DIR.mkdir(parents=True, exist_ok=True)
        (self.TMP_DIR / 'cards').mkdir(exist_ok=True)
        (self.TMP_DIR / 'stocks').mkdir(exist_ok=True)

        files_written = 0

        # dashboard.json
        dashboard_json = self._build_dashboard_json(target_date, signals_data, market_summary, pipeline_log)
        self._write_json(self.TMP_DIR / 'dashboard.json', dashboard_json)
        files_written += 1

        # cards/{category}.json
        card_count = self._build_card_jsons(signals_data, market_summary)
        files_written += card_count

        # stocks/{SYMBOL}.json
        stock_count = self._build_stock_jsons(signals_data, target_date)
        files_written += stock_count

        # meta.json
        meta_json = self._build_meta_json(target_date, pipeline_log)
        self._write_json(self.TMP_DIR / 'meta.json', meta_json)
        files_written += 1

        # Atomic swap
        self._atomic_swap()

        # DB upsert
        snapshot = self._upsert_snapshot(target_date, dashboard_json, signals_data, pipeline_log)

        logger.info(
            f"[EODJSONBaker] bake 완료: {files_written}개 파일, "
            f"snapshot_id={snapshot.pk}"
        )
        return {'files_written': files_written, 'snapshot_id': snapshot.pk}

    def _build_dashboard_json(
        self,
        target_date: date,
        signals_data: list[dict],
        market_summary: dict,
        pipeline_log: 'PipelineLog',
    ) -> dict:
        """
        메인 dashboard.json 구조 생성.

        {
            "generated_at": "...",
            "trading_date": "...",
            "is_stale": false,
            "market_summary": {...},
            "signal_cards": [...],
            "pipeline_meta": {...}
        }
        """
        generated_at = dj_timezone.now()
        is_stale = generated_at.date() != date.today()

        # mini_chart_20d 미리 로드하여 signals_data에 주입
        self._preload_mini_charts(signals_data, target_date)

        signal_cards = self._group_signals_into_cards(signals_data, market_summary)

        return {
            'generated_at': generated_at.isoformat(),
            'trading_date': str(target_date),
            'is_stale': is_stale,
            'market_summary': market_summary,
            'signal_cards': signal_cards,
            'pipeline_meta': {
                'run_id': str(pipeline_log.run_id) if pipeline_log else '',
                'status': pipeline_log.status if pipeline_log else '',
                'total_duration_seconds': pipeline_log.total_duration_seconds if pipeline_log else 0,
                'stages': pipeline_log.stages if pipeline_log else {},
            },
        }

    def _group_signals_into_cards(self, signals_data: list[dict], market_summary: dict) -> list[dict]:
        """
        시그널 데이터를 시그널 ID별 카드로 그룹화합니다.
        """
        from collections import defaultdict

        # 시그널별 종목 그룹핑
        signal_stocks: dict[str, list[dict]] = defaultdict(list)
        for item in signals_data:
            for sig in item.get('signals', []):
                sig_id = sig['id']
                signal_stocks[sig_id].append(item)

        cards = []
        for sig_id in ALL_SIGNAL_IDS:
            stocks_with_sig = signal_stocks.get(sig_id, [])
            if not stocks_with_sig:
                continue

            # 해당 시그널의 signal_value 기준 내림차순 정렬
            sorted_stocks = sorted(
                stocks_with_sig,
                key=lambda x: self._get_signal_value(x, sig_id),
                reverse=True,
            )

            preview_stocks = [self._build_preview_stock(s, sig_id) for s in sorted_stocks[:3]]
            more_count = max(0, len(sorted_stocks) - 3)

            # 섹터 분포
            chain_sight_sectors = self._get_sector_distribution(stocks_with_sig)

            # 거래량/수익률/시총 랭킹 (상위 10개)
            rank_by_volume = [
                self._build_preview_stock(s, sig_id)
                for s in sorted(stocks_with_sig, key=lambda x: x.get('volume', 0), reverse=True)[:10]
            ]
            rank_by_return = [
                self._build_preview_stock(s, sig_id)
                for s in sorted(stocks_with_sig, key=lambda x: abs(x.get('change_pct', 0.0)), reverse=True)[:10]
            ]
            rank_by_market_cap = [
                self._build_preview_stock(s, sig_id)
                for s in sorted(stocks_with_sig, key=lambda x: x.get('market_cap') or 0, reverse=True)[:10]
            ]

            category = SIGNAL_CATEGORIES.get(sig_id, 'technical')
            meta = SIGNAL_METADATA.get(sig_id, {})
            edu = EDUCATION_TIPS.get(sig_id, {})

            cards.append({
                'id': sig_id,
                'category': category,
                'color': CATEGORY_COLORS.get(category, '#8B949E'),
                'title': meta.get('title', sig_id),
                'count': len(stocks_with_sig),
                'description_ko': meta.get('description_ko', ''),
                'education_tip': edu.get('tip', ''),
                'education_risk': edu.get('risk', ''),
                'preview_stocks': preview_stocks,
                'more_count': more_count,
                'chain_sight_sectors': chain_sight_sectors,
                'rank_by_volume': rank_by_volume,
                'rank_by_return': rank_by_return,
                'rank_by_market_cap': rank_by_market_cap,
            })

        return cards

    @staticmethod
    def _get_signal_value(item: dict, signal_id: str) -> float:
        """종목의 특정 시그널 value를 추출합니다 (정렬용)."""
        for sig in item.get('signals', []):
            if sig['id'] == signal_id:
                return abs(sig.get('value', 0.0))
        return 0.0

    def _build_preview_stock(self, item: dict, signal_id: str) -> dict:
        """단일 종목의 preview dict를 생성합니다."""
        # 해당 signal_id의 value/direction 추출
        sig_value = 0.0
        sig_direction = 'neutral'
        sig_label = ''
        for sig in item.get('signals', []):
            if sig['id'] == signal_id:
                sig_value = sig.get('value', 0.0)
                sig_direction = sig.get('direction', 'neutral')
                sig_label = sig.get('label', '')
                break

        news_ctx = item.get('news_context', {})

        # Stock 모델에서 company_name 조회 (캐시)
        symbol = item.get('stock_id', '')
        if not hasattr(self, '_company_name_cache'):
            self._company_name_cache = {}
        if symbol and symbol not in self._company_name_cache:
            from stocks.models import Stock
            stock = Stock.objects.filter(symbol=symbol).values_list('stock_name', flat=True).first()
            self._company_name_cache[symbol] = stock or ''

        return {
            'symbol': symbol,
            'company_name': self._company_name_cache.get(symbol, ''),
            'sector': item.get('sector', ''),
            'industry': item.get('industry', ''),
            'close_price': item.get('close', 0.0),
            'change_percent': item.get('change_pct', 0.0),
            'volume': item.get('volume', 0),
            'dollar_volume': item.get('dollar_volume', 0.0),
            'market_cap': item.get('market_cap'),
            'composite_score': item.get('composite_score', 0.0),
            'signal_value': sig_value,
            'signal_direction': sig_direction,
            'signal_label': sig_label,
            'news_context': {
                'headline': news_ctx.get('headline', ''),
                'source': news_ctx.get('source', ''),
                'url': news_ctx.get('url', ''),
                'match_type': news_ctx.get('match_type', 'none'),
                'confidence': news_ctx.get('confidence', 'info'),
                'age_days': news_ctx.get('age_days', 0),
            },
            'mini_chart_20d': item.get('_mini_chart_20d', []),
            'chain_sight_cta': False,
        }

    def _preload_mini_charts(self, signals_data: list[dict], target_date: date):
        """
        preview_stocks에 포함될 종목의 최근 20일 종가를 bulk 로드하여
        signals_data 각 항목에 '_mini_chart_20d' 키로 주입합니다.
        """
        from datetime import timedelta

        symbols = [item['stock_id'] for item in signals_data]
        if not symbols:
            return

        start_date = target_date - timedelta(days=40)  # 20거래일 확보

        rows = list(
            DailyPrice.objects.filter(
                stock__symbol__in=symbols,
                date__gte=start_date,
                date__lte=target_date,
            )
            .values_list('stock__symbol', 'date', 'close_price')
            .order_by('stock__symbol', 'date')
        )

        # symbol별 종가 배열 생성
        chart_map: dict[str, list[float]] = {}
        for sym, dt, close in rows:
            if sym not in chart_map:
                chart_map[sym] = []
            chart_map[sym].append(float(close))

        # 최근 20개만 유지
        for sym in chart_map:
            chart_map[sym] = chart_map[sym][-20:]

        # signals_data에 주입
        for item in signals_data:
            item['_mini_chart_20d'] = chart_map.get(item['stock_id'], [])

    def _get_sector_distribution(self, stocks: list[dict]) -> list[str]:
        """섹터별 종목 수 상위 10개의 섹터명을 반환합니다."""
        from collections import Counter
        sector_counts = Counter(s.get('sector', 'Unknown') for s in stocks)
        return [sector for sector, _ in sector_counts.most_common(10)]

    def _build_card_jsons(self, signals_data: list[dict], market_summary: dict) -> int:
        """
        cards/{signal_id}.json 파일 생성.
        각 시그널의 전체 종목 목록 + 사전 정렬 포함.

        Returns:
            생성된 파일 수
        """
        from collections import defaultdict

        signal_stocks: dict[str, list[dict]] = defaultdict(list)
        for item in signals_data:
            for sig in item.get('signals', []):
                signal_stocks[sig['id']].append(item)

        files_written = 0
        for sig_id, stocks in signal_stocks.items():
            if not stocks:
                continue

            sorted_by_score = sorted(stocks, key=lambda x: self._get_signal_value(x, sig_id), reverse=True)
            sorted_by_volume = sorted(stocks, key=lambda x: x.get('volume', 0), reverse=True)
            sorted_by_return = sorted(stocks, key=lambda x: abs(x.get('change_pct', 0.0)), reverse=True)
            sorted_by_market_cap = sorted(stocks, key=lambda x: x.get('market_cap') or 0, reverse=True)

            card_data = {
                'signal_id': sig_id,
                'category': SIGNAL_CATEGORIES.get(sig_id, 'technical'),
                'title': SIGNAL_METADATA.get(sig_id, {}).get('title', sig_id),
                'total_count': len(stocks),
                'stocks_by_score': [self._build_preview_stock(s, sig_id) for s in sorted_by_score],
                'stocks_by_volume': [self._build_preview_stock(s, sig_id) for s in sorted_by_volume],
                'stocks_by_return': [self._build_preview_stock(s, sig_id) for s in sorted_by_return],
                'stocks_by_market_cap': [self._build_preview_stock(s, sig_id) for s in sorted_by_market_cap],
                'sector_distribution': self._get_sector_distribution(stocks),
                'market_summary': market_summary,
            }

            self._write_json(self.TMP_DIR / 'cards' / f'{sig_id}.json', card_data)
            files_written += 1

        return files_written

    def _build_stock_jsons(self, signals_data: list[dict], target_date: date) -> int:
        """
        stocks/{SYMBOL}.json 파일 생성. 최근 60일 히스토리 포함.

        Returns:
            생성된 파일 수
        """
        files_written = 0
        symbols = [item['stock_id'] for item in signals_data]

        # 60일 히스토리 bulk 로드
        from datetime import timedelta
        history_start = target_date - timedelta(days=90)  # 60 거래일 확보를 위해 90일 조회

        history_qs = list(
            DailyPrice.objects.filter(
                stock__symbol__in=symbols,
                date__gte=history_start,
                date__lte=target_date,
            )
            .values_list('stock__symbol', 'date', 'close_price', 'volume')
            .order_by('stock__symbol', 'date')
        )

        # symbol별 그룹핑
        history_map: dict[str, list] = {}
        for sym, dt, close, vol in history_qs:
            if sym not in history_map:
                history_map[sym] = []
            history_map[sym].append({
                'date': str(dt),
                'close': float(close),
                'volume': int(vol),
            })
        # 최근 60일만 유지
        for sym in history_map:
            history_map[sym] = history_map[sym][-60:]

        for item in signals_data:
            symbol = item['stock_id']
            mini_chart = self._get_mini_chart_data_from_history(symbol, history_map)

            stock_data = {
                'symbol': symbol,
                'trading_date': str(target_date),
                'close': item.get('close', 0.0),
                'change_pct': item.get('change_pct', 0.0),
                'volume': item.get('volume', 0),
                'dollar_volume': item.get('dollar_volume', 0.0),
                'sector': item.get('sector', ''),
                'industry': item.get('industry', ''),
                'market_cap': item.get('market_cap'),
                'composite_score': item.get('composite_score', 0.0),
                'signal_count': item.get('signal_count', 0),
                'bullish_count': item.get('bullish_count', 0),
                'bearish_count': item.get('bearish_count', 0),
                'signals': item.get('signals', []),
                'tag_details': item.get('tag_details', {}),
                'news_context': item.get('news_context', {}),
                'price_history': history_map.get(symbol, []),
                'mini_chart': mini_chart,
            }

            self._write_json(self.TMP_DIR / 'stocks' / f'{symbol}.json', stock_data)
            files_written += 1

        return files_written

    def _build_meta_json(self, target_date: date, pipeline_log: 'PipelineLog') -> dict:
        """meta.json 생성."""
        return {
            'trading_date': str(target_date),
            'generated_at': dj_timezone.now().isoformat(),
            'pipeline_run_id': str(pipeline_log.run_id) if pipeline_log else '',
            'pipeline_status': pipeline_log.status if pipeline_log else '',
            'total_duration_seconds': pipeline_log.total_duration_seconds if pipeline_log else 0.0,
            'ingest_quality': pipeline_log.ingest_quality if pipeline_log else {},
        }

    def _atomic_swap(self) -> None:
        """
        3단계 디렉토리 swap으로 파일 교체의 일관성을 보장합니다.

        1. OUTPUT → OLD (기존 OUTPUT 백업)
        2. TMP → OUTPUT (새 파일 적용)
        3. OLD 삭제
        """
        # 기존 OLD 제거
        if self.OLD_DIR.exists():
            shutil.rmtree(self.OLD_DIR)

        # OUTPUT → OLD
        if self.OUTPUT_DIR.exists():
            shutil.move(str(self.OUTPUT_DIR), str(self.OLD_DIR))

        # TMP → OUTPUT
        shutil.move(str(self.TMP_DIR), str(self.OUTPUT_DIR))

        # OLD 삭제
        if self.OLD_DIR.exists():
            shutil.rmtree(self.OLD_DIR)

        logger.info("[EODJSONBaker] atomic swap 완료")

    def _get_mini_chart_data(self, symbol: str, target_date: date) -> list:
        """
        최근 20일 종가 배열을 반환합니다.
        (개별 조회용 - _build_stock_jsons에서는 _get_mini_chart_data_from_history 사용)
        """
        from datetime import timedelta
        start = target_date - timedelta(days=40)
        prices = list(
            DailyPrice.objects.filter(
                stock__symbol=symbol,
                date__gte=start,
                date__lte=target_date,
            )
            .order_by('date')
            .values_list('close_price', flat=True)
        )
        return [float(p) for p in prices[-20:]]

    def _get_mini_chart_data_from_history(self, symbol: str, history_map: dict) -> list:
        """
        bulk 로드된 history_map에서 최근 20일 종가만 추출합니다.
        """
        history = history_map.get(symbol, [])
        return [row['close'] for row in history[-20:]]

    def _write_json(self, path: Path, data: dict) -> None:
        """JSON 파일을 안전하게 씁니다."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, default=str)

    def _upsert_snapshot(
        self,
        target_date: date,
        dashboard_json: dict,
        signals_data: list[dict],
        pipeline_log: 'PipelineLog',
    ) -> 'EODDashboardSnapshot':
        """
        EODDashboardSnapshot을 DB에 upsert합니다.
        """
        from collections import Counter
        total_signals = sum(item.get('signal_count', 0) for item in signals_data)
        total_stocks = len(signals_data)

        # 시그널 분포 계산
        all_signal_ids = []
        for item in signals_data:
            for sig in item.get('signals', []):
                all_signal_ids.append(sig['id'])
        signal_distribution = dict(Counter(all_signal_ids))

        duration = pipeline_log.total_duration_seconds if pipeline_log else 0.0

        snapshot, _ = EODDashboardSnapshot.objects.update_or_create(
            date=target_date,
            defaults={
                'json_data': dashboard_json,
                'total_signals': total_signals,
                'total_stocks': total_stocks,
                'signal_distribution': signal_distribution,
                'generated_at': dj_timezone.now(),
                'pipeline_duration_seconds': duration,
            },
        )
        return snapshot
