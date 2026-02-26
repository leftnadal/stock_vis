"""
EOD Pipeline (Step 6)

8단계 파이프라인 오케스트레이터.

Stage 1  Ingest     DailyPrice에서 S&P500 데이터 로드 + 품질 체크
Stage 2  Filter     volume >= 100K, dollar_volume >= $500K
Stage 3  Calculate  EODSignalCalculator.calculate_batch()
Stage 4  Tag        EODSignalTagger.tag_signals()
Stage 5  Enrich     EODNewsEnricher.enrich()
Stage 6  DB Upsert  bulk_create(update_conflicts=True)
Stage 7  JSON Bake  EODJSONBaker.bake()
Stage 8  Accuracy   SignalAccuracy 소급 업데이트
Health              signal_count > 0 확인
"""

import logging
import time
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
from django.db import transaction
from django.utils import timezone as dj_timezone

from stocks.models import (
    DailyPrice,
    EODSignal,
    PipelineLog,
    SignalAccuracy,
    SP500Constituent,
    Stock,
)
from stocks.services.eod_json_baker import EODJSONBaker
from stocks.services.eod_news_enricher import EODNewsEnricher
from stocks.services.eod_signal_calculator import EODSignalCalculator
from stocks.services.eod_signal_tagger import EODSignalTagger

logger = logging.getLogger(__name__)


class EODPipeline:
    """
    EOD Dashboard 데이터 생성 파이프라인.

    run() 메서드 하나로 전체 파이프라인을 실행하며
    PipelineLog에 각 단계 결과를 기록합니다.
    """

    def run(self, target_date: date = None) -> 'PipelineLog':
        """
        8단계 파이프라인을 실행합니다.

        Args:
            target_date: 처리 대상 거래일 (기본: 오늘)

        Returns:
            PipelineLog 인스턴스
        """
        if target_date is None:
            # DailyPrice의 최신 날짜를 기본값으로 사용
            latest = DailyPrice.objects.order_by('-date').values_list('date', flat=True).first()
            target_date = latest if latest else date.today()

        pipeline_start = time.perf_counter()
        run_id = uuid.uuid4()

        # PipelineLog 생성
        log = PipelineLog.objects.create(
            date=target_date,
            run_id=run_id,
            status='running',
            stages={},
            ingest_quality={},
            started_at=dj_timezone.now(),
        )

        logger.info(f"[EODPipeline] 시작: {target_date}, run_id={run_id}")

        try:
            # ── Stage 1: Ingest ───────────────────────────────────────
            stage1_start = time.perf_counter()
            raw_df, ingest_quality = self._stage_ingest(target_date)
            stage1_elapsed = time.perf_counter() - stage1_start
            log.stages['ingest'] = {
                'status': 'ok',
                'rows': len(raw_df),
                'symbols': int(raw_df['symbol'].nunique()) if not raw_df.empty else 0,
                'duration_seconds': round(stage1_elapsed, 2),
            }
            log.ingest_quality = ingest_quality
            log.save(update_fields=['stages', 'ingest_quality'])
            logger.info(f"[EODPipeline] Stage1 Ingest: {len(raw_df)}행, {stage1_elapsed:.1f}s")

            # ── Stage 2: Filter ───────────────────────────────────────
            stage2_start = time.perf_counter()
            filtered_df = self._stage_filter(raw_df, target_date)
            stage2_elapsed = time.perf_counter() - stage2_start
            filtered_symbols = int(filtered_df['symbol'].nunique()) if not filtered_df.empty else 0
            log.stages['filter'] = {
                'status': 'ok',
                'symbols_before': int(raw_df['symbol'].nunique()) if not raw_df.empty else 0,
                'symbols_after': filtered_symbols,
                'duration_seconds': round(stage2_elapsed, 2),
            }
            log.save(update_fields=['stages'])
            logger.info(f"[EODPipeline] Stage2 Filter: {filtered_symbols}종목, {stage2_elapsed:.1f}s")

            # ── Stage 3: Calculate ────────────────────────────────────
            stage3_start = time.perf_counter()
            calculator = EODSignalCalculator()
            signals_df = calculator.calculate_batch(target_date)
            stage3_elapsed = time.perf_counter() - stage3_start
            signals_count = len(signals_df) if not signals_df.empty else 0
            log.stages['calculate'] = {
                'status': 'ok',
                'stocks_with_signals': signals_count,
                'duration_seconds': round(stage3_elapsed, 2),
            }
            log.save(update_fields=['stages'])
            logger.info(f"[EODPipeline] Stage3 Calculate: {signals_count}종목, {stage3_elapsed:.1f}s")

            if signals_df.empty:
                raise ValueError(f"시그널 계산 결과 없음: {target_date}")

            # filter: filtered_symbols 중 신호 있는 행만 유지
            if not filtered_df.empty:
                valid_symbols = set(
                    filtered_df[filtered_df['date'] == target_date]['symbol'].tolist()
                ) if 'date' in filtered_df.columns else set()
                if valid_symbols:
                    signals_df = signals_df[signals_df['symbol'].isin(valid_symbols)].copy()

            # ── Stage 4: Tag ──────────────────────────────────────────
            stage4_start = time.perf_counter()
            tagger = EODSignalTagger()
            tagged = tagger.tag_signals(signals_df)
            # 시그널이 1개 이상인 종목만 유지
            tagged = [t for t in tagged if t['signal_count'] > 0]
            stage4_elapsed = time.perf_counter() - stage4_start
            log.stages['tag'] = {
                'status': 'ok',
                'stocks_tagged': len(tagged),
                'total_signals': sum(t['signal_count'] for t in tagged),
                'duration_seconds': round(stage4_elapsed, 2),
            }
            log.save(update_fields=['stages'])
            logger.info(f"[EODPipeline] Stage4 Tag: {len(tagged)}종목, {stage4_elapsed:.1f}s")

            # ── Stage 5: News Enrich ──────────────────────────────────
            stage5_start = time.perf_counter()
            enricher = EODNewsEnricher()
            enriched = enricher.enrich(tagged, target_date)
            stage5_elapsed = time.perf_counter() - stage5_start
            news_matched = sum(
                1 for e in enriched
                if e.get('news_context', {}).get('match_type') not in ('none', 'profile', '')
            )
            log.stages['enrich'] = {
                'status': 'ok',
                'news_matched': news_matched,
                'duration_seconds': round(stage5_elapsed, 2),
            }
            log.save(update_fields=['stages'])
            logger.info(f"[EODPipeline] Stage5 Enrich: {news_matched}건 뉴스 매칭, {stage5_elapsed:.1f}s")

            # ── Stage 6: DB Upsert ────────────────────────────────────
            stage6_start = time.perf_counter()
            upserted = self._stage_db_upsert(enriched, target_date)
            stage6_elapsed = time.perf_counter() - stage6_start
            log.stages['db_upsert'] = {
                'status': 'ok',
                'upserted': upserted,
                'duration_seconds': round(stage6_elapsed, 2),
            }
            log.save(update_fields=['stages'])
            logger.info(f"[EODPipeline] Stage6 DB Upsert: {upserted}건, {stage6_elapsed:.1f}s")

            # market_summary 구성
            market_summary = self._build_market_summary(signals_df, enriched, target_date)

            # ── Stage 7: JSON Bake ────────────────────────────────────
            stage7_start = time.perf_counter()
            baker = EODJSONBaker()
            bake_result = baker.bake(target_date, enriched, market_summary, log)
            stage7_elapsed = time.perf_counter() - stage7_start
            log.stages['json_bake'] = {
                'status': 'ok',
                'files_written': bake_result.get('files_written', 0),
                'snapshot_id': bake_result.get('snapshot_id'),
                'duration_seconds': round(stage7_elapsed, 2),
            }
            log.save(update_fields=['stages'])
            logger.info(f"[EODPipeline] Stage7 JSON Bake: {bake_result.get('files_written')}파일, {stage7_elapsed:.1f}s")

            # ── Stage 8: Accuracy Backfill ────────────────────────────
            stage8_start = time.perf_counter()
            backfilled = self._stage_accuracy_backfill(target_date)
            stage8_elapsed = time.perf_counter() - stage8_start
            log.stages['accuracy_backfill'] = {
                'status': 'ok',
                'updated': backfilled,
                'duration_seconds': round(stage8_elapsed, 2),
            }
            log.save(update_fields=['stages'])
            logger.info(f"[EODPipeline] Stage8 Accuracy Backfill: {backfilled}건 업데이트, {stage8_elapsed:.1f}s")

            # ── Health Check ──────────────────────────────────────────
            total_signals = sum(t['signal_count'] for t in enriched)
            if total_signals == 0:
                log.status = 'partial'
                log.error_message = f'signal_count=0: {target_date}'
                logger.warning(f"[EODPipeline] Health Check 실패: signal_count=0")
            else:
                log.status = 'success'

        except Exception as e:
            logger.exception(f"[EODPipeline] 파이프라인 실패: {e}")
            log.status = 'failed'
            log.error_message = str(e)
        finally:
            total_elapsed = time.perf_counter() - pipeline_start
            log.total_duration_seconds = round(total_elapsed, 2)
            log.completed_at = dj_timezone.now()
            log.save(update_fields=['status', 'error_message', 'total_duration_seconds', 'completed_at'])
            logger.info(
                f"[EODPipeline] 완료: {target_date}, status={log.status}, "
                f"총 {total_elapsed:.1f}s"
            )

        return log

    def _stage_ingest(self, target_date: date) -> tuple[pd.DataFrame, dict]:
        """
        Stage 1: DailyPrice에서 S&P500 데이터 로드 + 품질 체크.

        Returns:
            (raw_df, ingest_quality_dict)
        """
        calculator = EODSignalCalculator()
        raw_df = calculator._load_price_data(target_date)

        if raw_df.empty:
            return raw_df, {'total_symbols': 0, 'total_rows': 0, 'quality_score': 0.0}

        total_symbols = int(raw_df['symbol'].nunique())
        total_rows = len(raw_df)
        sp500_count = SP500Constituent.objects.filter(is_active=True).count()

        coverage_pct = (total_symbols / sp500_count * 100) if sp500_count > 0 else 0.0

        # target_date 행 수
        today_rows = len(raw_df[raw_df['date'] == target_date])
        today_coverage = (today_rows / sp500_count * 100) if sp500_count > 0 else 0.0

        ingest_quality = {
            'total_symbols': total_symbols,
            'sp500_universe': sp500_count,
            'total_rows': total_rows,
            'today_rows': today_rows,
            'coverage_pct': round(coverage_pct, 1),
            'today_coverage_pct': round(today_coverage, 1),
            'quality_score': round(today_coverage / 100, 4),
        }

        return raw_df, ingest_quality

    def _stage_filter(self, df: pd.DataFrame, target_date: date) -> pd.DataFrame:
        """
        Stage 2: 최소 유동성 필터 적용.
        - volume >= 100,000
        - dollar_volume >= $500,000

        target_date 이외의 날짜는 필터 제외 (히스토리 보존).
        """
        if df.empty:
            return df

        # dollar_volume 계산 (아직 없을 경우 대비)
        if 'dollar_volume' not in df.columns:
            df = df.copy()
            df['dollar_volume'] = df['close'] * df['volume']

        today_mask = df['date'] == target_date
        today_df = df[today_mask].copy()
        history_df = df[~today_mask].copy()

        # 필터 적용
        filtered_today = today_df[
            (today_df['volume'] >= 100_000) &
            (today_df['dollar_volume'] >= 500_000)
        ]

        # 필터 통과한 심볼만 히스토리도 유지
        valid_symbols = set(filtered_today['symbol'].tolist())
        filtered_history = history_df[history_df['symbol'].isin(valid_symbols)]

        return pd.concat([filtered_today, filtered_history], ignore_index=True)

    def _stage_db_upsert(self, enriched: list[dict], target_date: date) -> int:
        """
        Stage 6: EODSignal을 bulk_create(update_conflicts=True)로 upsert.
        for-loop 금지 - bulk 연산만 사용.
        """
        if not enriched:
            return 0

        # Stock 심볼 → pk 매핑
        symbols = [item['stock_id'] for item in enriched]
        stock_map = dict(
            Stock.objects.filter(symbol__in=symbols).values_list('symbol', 'symbol')
        )

        records = []
        for item in enriched:
            symbol = item['stock_id']
            if symbol not in stock_map:
                continue

            close_price = Decimal(str(item.get('close', 0)))
            dollar_volume = Decimal(str(item.get('dollar_volume', 0)))

            records.append(EODSignal(
                stock_id=symbol,
                date=target_date,
                signals=item.get('signals', []),
                tag_details=item.get('tag_details', {}),
                signal_count=item.get('signal_count', 0),
                bullish_count=item.get('bullish_count', 0),
                bearish_count=item.get('bearish_count', 0),
                composite_score=item.get('composite_score', 0.0),
                news_context=item.get('news_context', {}),
                close_price=close_price,
                change_percent=item.get('change_pct', 0.0),
                volume=item.get('volume', 0),
                dollar_volume=dollar_volume,
                sector=item.get('sector', ''),
                industry=item.get('industry', ''),
                market_cap=item.get('market_cap'),
            ))

        if not records:
            return 0

        with transaction.atomic():
            EODSignal.objects.bulk_create(
                records,
                update_conflicts=True,
                unique_fields=['stock', 'date'],
                update_fields=[
                    'signals', 'tag_details', 'signal_count', 'bullish_count',
                    'bearish_count', 'composite_score', 'news_context',
                    'close_price', 'change_percent', 'volume', 'dollar_volume',
                    'sector', 'industry', 'market_cap',
                ],
            )

        return len(records)

    def _stage_accuracy_backfill(self, target_date: date) -> int:
        """
        Stage 8: SignalAccuracy 소급 업데이트.

        이전 시그널에 대해 1d/5d/20d 수익률을 계산하여 업데이트합니다.
        이미 채워진 항목은 건너뜁니다.
        """
        updated_count = 0

        # 수익률 업데이트가 필요한 SignalAccuracy 조회
        # - return_1d is None AND signal_date가 1일 이상 전
        # - return_5d is None AND signal_date가 5일 이상 전
        # - return_20d is None AND signal_date가 20일 이상 전

        lookback_configs = [
            ('return_1d', 'excess_1d', 1),
            ('return_5d', 'excess_5d', 5),
            ('return_20d', 'excess_20d', 20),
        ]

        for return_field, excess_field, days in lookback_configs:
            cutoff = target_date - timedelta(days=days)
            pending = SignalAccuracy.objects.filter(
                **{f'{return_field}__isnull': True},
                signal_date__lte=cutoff,
            ).select_related('stock')[:500]  # 배치 한도

            for accuracy in pending:
                try:
                    # 시그널 당일 종가
                    signal_price_qs = DailyPrice.objects.filter(
                        stock=accuracy.stock,
                        date=accuracy.signal_date,
                    ).values_list('close_price', flat=True).first()

                    if signal_price_qs is None:
                        continue

                    signal_price = float(signal_price_qs)
                    if signal_price == 0:
                        continue

                    # target_date (현재일) 종가
                    current_price_qs = DailyPrice.objects.filter(
                        stock=accuracy.stock,
                        date__lte=target_date,
                        date__gte=accuracy.signal_date + timedelta(days=days - 1),
                    ).order_by('date').values_list('close_price', flat=True).first()

                    if current_price_qs is None:
                        continue

                    current_price = float(current_price_qs)
                    stock_return = (current_price - signal_price) / signal_price * 100

                    # SPY 수익률 (초과 수익률 계산)
                    spy_signal = DailyPrice.objects.filter(
                        stock__symbol='SPY',
                        date=accuracy.signal_date,
                    ).values_list('close_price', flat=True).first()
                    spy_current = DailyPrice.objects.filter(
                        stock__symbol='SPY',
                        date__lte=target_date,
                        date__gte=accuracy.signal_date + timedelta(days=days - 1),
                    ).order_by('date').values_list('close_price', flat=True).first()

                    excess = None
                    if spy_signal and spy_current:
                        spy_return = (float(spy_current) - float(spy_signal)) / float(spy_signal) * 100
                        excess = stock_return - spy_return

                    setattr(accuracy, return_field, round(stock_return, 4))
                    setattr(accuracy, excess_field, round(excess, 4) if excess is not None else None)
                    accuracy.save(update_fields=[return_field, excess_field])
                    updated_count += 1

                except Exception as e:
                    logger.warning(
                        f"[EODPipeline] Accuracy backfill 실패: "
                        f"{accuracy.stock_id} {accuracy.signal_date} {return_field}: {e}"
                    )
                    continue

        return updated_count

    def _build_market_summary(
        self,
        signals_df: pd.DataFrame,
        enriched: list[dict],
        target_date: date,
    ) -> dict:
        """
        파이프라인 market_summary를 구성합니다.

        {
            'sp500_change': float,  # SPY 변동률
            'qqq_change': float,    # QQQ 변동률
            'vix': float,
            'vix_regime': str,
            'total_signals': int,
            'bullish_count': int,
            'bearish_count': int,
            'stocks_with_signals': int,
            'stock_universe': int,
            'headline': str,
        }
        """
        # SPY/QQQ 변동률 조회
        spy_change = self._get_index_change('SPY', signals_df, target_date)
        qqq_change = self._get_index_change('QQQ', signals_df, target_date)

        # VIX 값
        vix_value = self._get_vix_value(target_date)
        regime = 'high_vol' if vix_value > 25 else 'normal'

        total_signals = sum(e.get('signal_count', 0) for e in enriched)
        bullish_count = sum(e.get('bullish_count', 0) for e in enriched)
        bearish_count = sum(e.get('bearish_count', 0) for e in enriched)
        stocks_with_signals = len(enriched)
        total_sp500_count = SP500Constituent.objects.filter(is_active=True).count()

        return {
            'sp500_change': round(spy_change, 4),
            'qqq_change': round(qqq_change, 4),
            'vix': round(vix_value, 2),
            'vix_regime': regime,
            'total_signals': total_signals,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'stocks_with_signals': stocks_with_signals,
            'stock_universe': total_sp500_count,
            'headline': f"{total_sp500_count}종목에서 {total_signals}개 시그널 감지",
        }

    def _get_index_change(self, symbol: str, signals_df: pd.DataFrame, target_date: date) -> float:
        """
        signals_df에서 해당 심볼의 변동률을 반환합니다.
        없으면 DailyPrice에서 직접 조회, 그래도 없으면 0.0.
        """
        if not signals_df.empty and 'symbol' in signals_df.columns:
            mask = (signals_df['symbol'] == symbol) & (signals_df['date'] == target_date)
            rows = signals_df[mask]
            if not rows.empty:
                val = rows['change_pct'].values[0]
                if not pd.isna(val):
                    return float(val)

        # DailyPrice fallback
        try:
            prices = list(
                DailyPrice.objects.filter(
                    stock__symbol=symbol,
                    date__lte=target_date,
                )
                .order_by('-date')
                .values_list('close_price', flat=True)[:2]
            )
            if len(prices) == 2:
                current, prev = float(prices[0]), float(prices[1])
                if prev != 0:
                    return (current - prev) / prev * 100
        except Exception as e:
            logger.warning(f"[EODPipeline] {symbol} 변동률 조회 실패: {e}")

        return 0.0

    def _get_vix_value(self, target_date: date) -> float:
        """
        macro.MarketIndexPrice에서 VIX 값을 반환합니다.
        없으면 20.0 기본값.
        """
        try:
            from macro.models import MarketIndex, MarketIndexPrice
            vix_index = MarketIndex.objects.filter(
                symbol__in=['VIX', '^VIX', 'VIXX'],
                category='volatility',
            ).first()
            if vix_index:
                price = (
                    MarketIndexPrice.objects.filter(
                        index=vix_index,
                        date__lte=target_date,
                    )
                    .order_by('-date')
                    .values_list('close', flat=True)
                    .first()
                )
                if price is not None:
                    return float(price)
        except Exception as e:
            logger.warning(f"[EODPipeline] VIX 조회 실패: {e}")
        return 20.0
