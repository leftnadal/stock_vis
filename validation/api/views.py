"""
1차 검증 REST API

1. GET /api/v1/validation/{symbol}/summary/
2. GET /api/v1/validation/{symbol}/metrics/?category=all
3. GET /api/v1/validation/{symbol}/leader-comparison/
4. GET /api/v1/validation/{symbol}/presets/
5. POST /api/v1/validation/{symbol}/peer-preference/
6. DELETE /api/v1/validation/{symbol}/peer-preference/
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from packages.shared.metrics.models import (
    CompanyMetricSnapshot,
    MetricDefinition,
    PeerListCache,
    PeerMetricBenchmark,
)
from packages.shared.stocks.models import SP500Constituent, Stock
from validation.models import (
    CategorySignal,
    CompanyBenchmarkDelta,
    PeerPreset,
    UserPeerPreference,
)
from validation.services.category_signal_calculator import (
    CATEGORY_DISPLAY,
    CATEGORY_METRICS,
)
from validation.services.interpretation import (
    determine_trend,
    generate_leader_summary,
    generate_metric_interpretation,
    generate_summary_text,
)

# 카테고리 설명
CATEGORY_DESCRIPTIONS = {
    'profitability': '기업이 매출에서 얼마나 효율적으로 이익을 만들어내는지 보여줍니다.',
    'growth': '기업의 성장 속도를 보여줍니다. 업종 평균 대비 얼마나 빠르게 성장하는지도 함께 확인합니다.',
    'financial_structure': '기업이 위기 상황에서 생존할 수 있는지 평가합니다. 부채 수준, 현금 보유, 이자 지급 능력 등.',
    'cash_flow_quality': '회계상 이익이 아니라 실제 현금 창출 능력을 평가합니다.',
    'operational_efficiency': '기업이 자산과 자원을 얼마나 효율적으로 활용하는지 보여줍니다.',
    'dilution_shareholder': '기업이 주주 가치를 보호하는지 확인합니다. 주식 희석과 자사주 매입 규모를 주시합니다.',
    'valuation': '현재 주가가 기업 가치 대비 얼마나 비싼지 보여줍니다. 참고용 보조 지표입니다.',
}

# 대장주 비교 대표 6개 지표
LEADER_SUMMARY_METRICS = [
    'operating_margin', 'revenue_growth_yoy', 'debt_to_equity',
    'fcf_margin', 'asset_turnover', 'net_shareholder_yield',
]


class ValidationSummaryView(APIView):
    """1차 검증 종합 요약 API"""

    def get(self, request, symbol):
        symbol = symbol.upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return Response({'error': f'Stock {symbol} not found'}, status=status.HTTP_404_NOT_FOUND)

        # S&P 500 여부
        is_sp500 = SP500Constituent.objects.filter(symbol=symbol, is_active=True).exists()
        if not is_sp500:
            return Response({
                'symbol': symbol, 'error': 'not_in_universe',
                'message': '현재 S&P 500 종목만 지원합니다.',
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # 커스텀 peer 분기
        if request.user.is_authenticated:
            pref = UserPeerPreference.objects.filter(user=request.user, symbol_id=symbol).first()
            if pref and pref.mode == 'custom' and pref.custom_peers:
                from validation.services.custom_benchmark_engine import (
                    CustomBenchmarkEngine,
                )
                engine = CustomBenchmarkEngine()
                result = engine.compute_summary(symbol, pref.custom_peers, user_id=request.user.id)
                result['company_name'] = stock.stock_name or symbol
                return Response(result)

        # CategorySignal
        signals = list(CategorySignal.objects.filter(symbol=stock).order_by('category'))
        if not signals:
            return Response({
                'symbol': symbol, 'error': 'no_data',
                'message': '재무 분석 데이터 준비 중입니다.',
            }, status=status.HTTP_404_NOT_FOUND)

        fiscal_year = signals[0].fiscal_year

        # 종합 요약
        summary_text = generate_summary_text(signals)

        # Peer info
        peer_cache = PeerListCache.objects.filter(symbol=stock).first()
        peer_info = None
        if peer_cache:
            # 대장주 (market_cap 1위)
            leader = self._find_leader(stock, peer_cache.peer_symbols)
            peer_info = {
                'industry': stock.industry or '',
                'peer_count': peer_cache.peer_count,
                'confidence': peer_cache.benchmark_basis,
                'benchmark_basis': peer_cache.benchmark_basis,
                'size_bucket': peer_cache.size_bucket,
                'basis_description': self._basis_desc(peer_cache, stock),
                'top_peers': peer_cache.peer_symbols[:5],
                'industry_leader': leader,
            }

        # 산업 내 순위 (핵심 5개 지표)
        rank_metrics = ['revenue_growth_yoy', 'operating_margin', 'roe', 'fcf_margin', 'debt_to_equity']
        ranks = []
        for mc in rank_metrics:
            delta = CompanyBenchmarkDelta.objects.filter(
                symbol=stock, fiscal_year=fiscal_year, metric_code_id=mc,
            ).first()
            if delta and delta.rank and delta.total:
                md = MetricDefinition.objects.filter(pk=mc).first()
                ranks.append({
                    'metric': mc,
                    'display_name': md.display_name if md else mc,
                    'rank': delta.rank,
                    'total': delta.total,
                    'value': float(delta.company_value) if delta.company_value else None,
                })

        return Response({
            'symbol': symbol,
            'company_name': stock.stock_name or symbol,
            'data_fiscal_year': fiscal_year,
            'data_freshness': signals[0].calculated_at.isoformat() if signals else None,
            'category_signals': [
                {
                    'category': s.category,
                    'display_name': CATEGORY_DISPLAY.get(s.category, s.category),
                    'signal': s.signal,
                    'description': CATEGORY_DESCRIPTIONS.get(s.category, ''),
                    'metric_count': s.metric_count,
                    'signal_reason': s.signal_reason,
                }
                for s in signals
            ],
            'summary_text': summary_text,
            'summary_source': 'rule',
            'peer_info': peer_info,
            'industry_position': {'ranks': ranks},
        })

    def _find_leader(self, stock, peer_symbols):
        if not peer_symbols:
            return None
        peers = Stock.objects.filter(symbol__in=peer_symbols).order_by('-market_capitalization')
        leader = peers.first()
        if leader and leader.symbol == stock.symbol and peers.count() > 1:
            leader = peers[1]
        if leader:
            return {
                'symbol': leader.symbol,
                'name': leader.stock_name or leader.symbol,
                'market_cap': float(leader.market_capitalization) if leader.market_capitalization else None,
            }
        return None

    def _basis_desc(self, cache, stock):
        basis = cache.benchmark_basis
        ind = stock.industry or stock.sector or ''
        if basis == 'industry_size':
            return f"{ind} 업종 내 유사 규모 기업"
        elif basis == 'industry':
            return f"{ind} 업종 전체"
        return f"{stock.sector or ''} 섹터 전체"


class ValidationMetricsView(APIView):
    """카테고리별 지표 상세 API"""

    def get(self, request, symbol):
        symbol = symbol.upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return Response({'error': f'Stock {symbol} not found'}, status=status.HTTP_404_NOT_FOUND)

        category_param = request.query_params.get('category', 'all')

        if category_param == 'all':
            categories = list(CATEGORY_METRICS.keys())
        elif category_param in CATEGORY_METRICS:
            categories = [category_param]
        else:
            return Response({'error': f'Unknown category: {category_param}'}, status=status.HTTP_400_BAD_REQUEST)

        result_categories = []
        for cat in categories:
            cat_data = self._build_category(stock, cat)
            if cat_data:
                result_categories.append(cat_data)

        return Response({'symbol': symbol, 'categories': result_categories})

    def _build_category(self, stock, category):
        metric_codes = CATEGORY_METRICS.get(category, [])
        signal_obj = CategorySignal.objects.filter(symbol=stock, category=category).first()

        metrics_data = []
        for mc in metric_codes:
            md = MetricDefinition.objects.filter(pk=mc).first()
            if not md:
                continue
            metrics_data.append(self._build_metric(stock, md))

        return {
            'category': category,
            'display_name': CATEGORY_DISPLAY.get(category, category),
            'display_name_en': category.replace('_', ' ').title(),
            'signal': signal_obj.signal if signal_obj else 'gray',
            'description': CATEGORY_DESCRIPTIONS.get(category, ''),
            'metrics': metrics_data,
        }

    def _build_metric(self, stock, md):
        # 최신 연도 snapshot
        latest_snap = (
            CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=md, value_status='normal')
            .order_by('-fiscal_year').first()
        )

        # current
        current = None
        if latest_snap:
            current = {
                'value': float(latest_snap.metric_value) if latest_snap.metric_value else None,
                'fiscal_year': latest_snap.fiscal_year,
                'value_status': latest_snap.value_status,
            }
        else:
            # not_applicable / missing 확인
            any_snap = CompanyMetricSnapshot.objects.filter(symbol=stock, metric_code=md).order_by('-fiscal_year').first()
            if any_snap:
                current = {
                    'value': float(any_snap.metric_value) if any_snap.metric_value else None,
                    'fiscal_year': any_snap.fiscal_year,
                    'value_status': any_snap.value_status,
                }

        # benchmark delta
        benchmark = None
        delta = None
        if current and current['value_status'] == 'normal':
            delta = CompanyBenchmarkDelta.objects.filter(
                symbol=stock, fiscal_year=current['fiscal_year'], metric_code=md,
            ).first()
            if delta:
                benchmark = {
                    'basis': delta.benchmark_basis,
                    'confidence': delta.benchmark_confidence,
                    'median': float(delta.benchmark_median) if delta.benchmark_median else None,
                    'p25': float(delta.benchmark_p25) if delta.benchmark_p25 else None,
                    'p75': float(delta.benchmark_p75) if delta.benchmark_p75 else None,
                    'percentile_rank': float(delta.percentile_rank) if delta.percentile_rank else None,
                    'rank': delta.rank,
                    'total': delta.total,
                }

        # history (최대 5년)
        history = []
        snaps = CompanyMetricSnapshot.objects.filter(
            symbol=stock, metric_code=md,
        ).order_by('fiscal_year')[:5]
        for s in snaps:
            entry = {
                'fiscal_year': s.fiscal_year,
                'company_value': float(s.metric_value) if s.metric_value else None,
            }
            # peer band
            peer_bench = PeerMetricBenchmark.objects.filter(
                symbol=stock, fiscal_year=s.fiscal_year, metric_code=md,
            ).first()
            if peer_bench:
                entry['peer_median'] = float(peer_bench.median_value) if peer_bench.median_value else None
                entry['peer_p25'] = float(peer_bench.p25_value) if peer_bench.p25_value else None
                entry['peer_p75'] = float(peer_bench.p75_value) if peer_bench.p75_value else None
            else:
                entry['peer_median'] = None
                entry['peer_p25'] = None
                entry['peer_p75'] = None
            history.append(entry)

        # trend
        company_vals = [h['company_value'] for h in history if h['company_value'] is not None]
        trend = determine_trend(company_vals)

        # interpretation
        interpretation = generate_metric_interpretation(
            metric_code=md.metric_code,
            higher_is_better=md.higher_is_better,
            percentile_rank=float(delta.percentile_rank) if delta and delta.percentile_rank else None,
            trend=trend,
            value_status=current['value_status'] if current else 'missing',
            benchmark_confidence=delta.benchmark_confidence if delta else 'low',
            not_applicable_reason=md.not_applicable_reason,
        )

        return {
            'metric_code': md.metric_code,
            'display_name': md.display_name,
            'display_name_en': md.display_name_en,
            'unit': md.unit,
            'higher_is_better': md.higher_is_better,
            'current': current,
            'benchmark': benchmark,
            'history': history,
            'trend': trend,
            'interpretation': interpretation,
            'interpretation_source': 'rule',
        }


class LeaderComparisonView(APIView):
    """업종 리더 대비 비교 API"""

    def get(self, request, symbol):
        symbol = symbol.upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return Response({'error': f'Stock {symbol} not found'}, status=status.HTTP_404_NOT_FOUND)

        peer_cache = PeerListCache.objects.filter(symbol=stock).first()
        if not peer_cache or peer_cache.peer_count < 2:
            return Response({
                'symbol': symbol,
                'error': 'insufficient_peers',
                'message': '비교 대상 부족',
            })

        # 대장주 찾기
        peers = Stock.objects.filter(symbol__in=peer_cache.peer_symbols).order_by('-market_capitalization')
        leader = peers.first()
        if leader and leader.symbol == stock.symbol and peers.count() > 1:
            leader = peers[1]
        if not leader:
            return Response({'symbol': symbol, 'error': 'no_leader'})

        # 최신 fiscal_year
        latest_fy = (
            CompanyBenchmarkDelta.objects.filter(symbol=stock)
            .values_list('fiscal_year', flat=True)
            .distinct().order_by('-fiscal_year').first()
        )
        if not latest_fy:
            return Response(
                {'symbol': symbol, 'error': 'no_data'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 비교 지표 수집
        all_metrics = []
        for cat, codes in CATEGORY_METRICS.items():
            for mc in codes:
                all_metrics.append((cat, mc))

        comparisons = []
        advantages = []
        disadvantages = []

        for cat, mc in all_metrics:
            md = MetricDefinition.objects.filter(pk=mc).first()
            if not md:
                continue

            company_snap = CompanyMetricSnapshot.objects.filter(
                symbol=stock, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
            ).first()
            leader_snap = CompanyMetricSnapshot.objects.filter(
                symbol_id=leader.symbol, fiscal_year=latest_fy, metric_code_id=mc, value_status='normal',
            ).first()

            if not company_snap or not leader_snap:
                continue
            if company_snap.metric_value is None or leader_snap.metric_value is None:
                continue

            c_val = float(company_snap.metric_value)
            l_val = float(leader_snap.metric_value)
            gap = c_val - l_val

            if md.higher_is_better:
                is_advantage = c_val > l_val
            else:
                is_advantage = c_val < l_val

            entry = {
                'metric_code': mc,
                'display_name': md.display_name,
                'category': cat,
                'company_value': c_val,
                'leader_value': l_val,
                'gap': gap,
                'is_advantage': is_advantage,
            }
            comparisons.append(entry)
            if is_advantage:
                advantages.append(entry)
            else:
                disadvantages.append(entry)

        summary = generate_leader_summary(advantages, disadvantages)

        return Response({
            'symbol': symbol,
            'fiscal_year': latest_fy,
            'leader': {
                'symbol': leader.symbol,
                'name': leader.stock_name or leader.symbol,
                'market_cap': float(leader.market_capitalization) if leader.market_capitalization else None,
            },
            'comparisons': comparisons,
            'summary_metrics': [c for c in comparisons if c['metric_code'] in LEADER_SUMMARY_METRICS],
            'total_compared': len(comparisons),
            'advantages_count': len(advantages),
            'summary': summary,
            'summary_source': 'rule',
        })


class PresetListView(APIView):
    """프리셋 목록 API"""

    def get(self, request, symbol):
        symbol = symbol.upper()
        presets = PeerPreset.objects.filter(symbol_id=symbol).order_by('preset_key')

        # 현재 사용자의 선택된 프리셋 확인
        selected_key = 'default'
        if request.user.is_authenticated:
            pref = UserPeerPreference.objects.filter(
                user=request.user, symbol_id=symbol
            ).first()
            if pref and pref.mode == 'preset':
                selected_key = pref.preset_key

        result = []
        for p in presets:
            if not p.is_active:
                continue
            conf_label = '높음' if p.confidence_score >= 0.7 else ('보통' if p.confidence_score >= 0.4 else '낮음')
            result.append({
                'preset_key': p.preset_key,
                'display_name': p.display_name,
                'logic_summary': p.logic_summary,
                'peer_count': p.peer_count,
                'confidence_score': p.confidence_score,
                'confidence_label': conf_label,
                'is_selected': p.preset_key == selected_key,
                'is_default': p.is_default,
            })

        return Response({'symbol': symbol, 'presets': result})


class PeerPreferenceView(APIView):
    """프리셋 선택 / 커스텀 설정 API"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request, symbol):
        symbol = symbol.upper()
        if not request.user.is_authenticated:
            return Response({'error': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        mode = request.data.get('mode', 'preset')
        preset_key = request.data.get('preset_key', 'default')
        custom_peers = request.data.get('custom_peers', [])

        # 프리셋 모드: 해당 프리셋이 존재하는지 확인
        if mode == 'preset':
            exists = PeerPreset.objects.filter(symbol_id=symbol, preset_key=preset_key, is_active=True).exists()
            if not exists:
                return Response({'error': f'프리셋 {preset_key}을(를) 찾을 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        UserPeerPreference.objects.update_or_create(
            user=request.user, symbol_id=symbol,
            defaults={
                'mode': mode,
                'preset_key': preset_key if mode == 'preset' else 'custom',
                'custom_peers': custom_peers if mode == 'custom' else [],
            }
        )

        return Response({'status': 'ok', 'mode': mode, 'preset_key': preset_key})

    def delete(self, request, symbol):
        symbol = symbol.upper()
        if not request.user.is_authenticated:
            return Response({'error': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        UserPeerPreference.objects.filter(user=request.user, symbol_id=symbol).delete()
        return Response({'status': 'ok', 'message': 'default로 리셋'})


class LLMPeerFilterView(APIView):
    """
    Phase 7: LLM 대화형 Peer 조정 API

    POST /api/v1/validation/{symbol}/llm-filter/
    Body: {"query": "성숙기 기업 중 ROE 15% 이상만", "preset_key": "default"}
    """

    def post(self, request, symbol):
        symbol = symbol.upper()
        query = request.data.get('query', '')

        if not query:
            return Response(
                {'error': '검색어를 입력하세요.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return Response(
                {'error': f'Stock {symbol} not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 기반 peer 풀 (프리셋 or 전체)
        preset_key = request.data.get('preset_key')
        base_peers = None
        if preset_key:
            preset = PeerPreset.objects.filter(
                symbol_id=symbol, preset_key=preset_key, is_active=True,
            ).first()
            if preset:
                base_peers = preset.peer_symbols

        # Step 1: 자연어 → 구조화 필터
        from validation.services.llm_peer_filter import (
            execute_peer_filter,
            parse_filter_with_llm,
        )

        parsed = parse_filter_with_llm(
            user_input=query,
            symbol=symbol,
            sector=stock.sector or '',
        )

        if 'error' in parsed:
            return Response({
                'symbol': symbol,
                'query': query,
                'error': parsed['error'],
            })

        # Step 2: 필터 실행
        result = execute_peer_filter(symbol, parsed, base_peers)

        return Response({
            'symbol': symbol,
            'query': query,
            'parsed_filter': parsed,
            'peers': result['peers'][:50],
            'count': result['count'],
            'filters_applied': result['filters_applied'],
        })
