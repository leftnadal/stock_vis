#!/usr/bin/env python3
"""
프리셋-필터 동기화 및 AI 테제 빌더 구현 교훈을 KB에 추가하는 스크립트
"""
import sys
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).parent))

from shared_kb.ontology_kb import OntologyKB
from shared_kb.schema import KnowledgeItem, KnowledgeType, ConfidenceLevel

# KB 연결
kb = OntologyKB()

lessons = [
    {
        "title": "FMP Key Metrics TTM API 필드 매핑 주의사항",
        "content": """FMP /stable/key-metrics-ttm API 사용 시 필드명이 직관적이지 않아 발생하는 문제

문제 상황:
Enhanced 스크리너에서 PE, ROE 필터가 작동하지 않음 (항상 None)

원인 분석:
1. `peRatioTTM` 필드가 존재하지 않음 → `earningsYieldTTM` 사용 (역수 계산 필요)
2. `roeTTM` 필드 존재 안 함 → `returnOnEquityTTM` 사용 (decimal 형식)
3. ROE 값이 decimal (1.5994 = 159.94%)로 반환됨

실제 API 응답 예시 (AAPL):
```json
{
  "earningsYieldTTM": 0.030919,     // PE = 1/0.030919 = 32.34
  "returnOnEquityTTM": 1.5994,     // ROE = 159.94%
  "returnOnAssetsTTM": 0.3105,     // ROA = 31.05%
  "currentRatioTTM": 0.9737,
  "priceToBookRatioTTM": null,     // 일부 필드는 null
  "debtToEquityTTM": null
}
```

올바른 필드 매핑:
```python
# PE Ratio: earningsYield의 역수
earnings_yield = m.get('earningsYieldTTM')
pe_ratio = round(1 / earnings_yield, 2) if earnings_yield and earnings_yield > 0 else None

# ROE: decimal → percentage
roe_decimal = m.get('returnOnEquityTTM')
roe_percent = round(roe_decimal * 100, 2) if roe_decimal is not None else None

# ROA: decimal → percentage
roa_decimal = m.get('returnOnAssetsTTM')
roa_percent = round(roa_decimal * 100, 2) if roa_decimal is not None else None
```

교훈:
1. FMP API 문서가 불완전하므로 실제 응답을 반드시 확인
2. 필드명이 직관적이지 않을 수 있음 (peRatioTTM 대신 earningsYieldTTM)
3. 값 변환이 필요한 경우가 많음 (decimal → percentage, 역수 계산)
4. null 값 처리 필수

출처: Stock-Vis Enhanced Screener Service 구현""",
        "knowledge_type": KnowledgeType.TROUBLESHOOT,
        "domain": "tech",
        "tags": ["fmp", "api", "field-mapping", "pe-ratio", "roe", "screener"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "프리셋 타입 분리 패턴 (instant vs enhanced)",
        "content": """외부 API가 지원하지 않는 필터를 처리하기 위한 프리셋 타입 분리 패턴

문제 상황:
FMP company-screener API가 market_cap, volume은 지원하지만
PE, ROE, EPS Growth 등 펀더멘탈 필터는 지원하지 않음

해결 패턴: 프리셋 타입 분리

1. instant 타입: API 직접 지원 필터만 사용
   - market_cap_min/max
   - volume_min/max
   - price_min/max
   - beta_min/max
   - dividend_min/max
   - sector, exchange

2. enhanced 타입: 추가 API 호출 필요
   - pe_ratio_min/max
   - roe_min/max
   - eps_growth_min/max
   - revenue_growth_min/max
   - debt_equity_max
   - rsi_min/max

구현:
```python
class EnhancedScreenerService:
    ENHANCED_FILTERS = {
        'pe_ratio_min', 'pe_ratio_max',
        'roe_min', 'roe_max',
        'eps_growth_min', 'eps_growth_max',
        # ...
    }

    def has_enhanced_filters(self, filters: Dict) -> bool:
        return any(k in self.ENHANCED_FILTERS for k in filters.keys())

    def get_filter_type(self, filters: Dict) -> str:
        return 'enhanced' if self.has_enhanced_filters(filters) else 'instant'
```

DB 모델:
```python
class ScreenerPreset(models.Model):
    preset_type = models.CharField(
        max_length=20,
        choices=[('instant', 'Instant'), ('enhanced', 'Enhanced')],
        default='instant'
    )
```

장점:
1. UX 개선: 사용자에게 예상 로딩 시간 표시 가능
2. 성능 최적화: instant는 즉시, enhanced는 추가 로딩 표시
3. API 비용 절감: enhanced 필터 없으면 추가 API 호출 안 함

출처: Stock-Vis Screener Upgrade Phase 2.4""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["screener", "preset", "api-optimization", "filter-type"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "2단계 필터링 패턴 (Two-Stage Filtering)",
        "content": """외부 API 제한을 우회하기 위한 2단계 필터링 패턴

사용 사례:
FMP company-screener API가 펀더멘탈 필터(PE, ROE 등)를 지원하지 않을 때

패턴 흐름:
```
1단계: FMP company-screener (서버 사이드)
   └─ market_cap, volume, sector 등 기본 필터
   └─ 결과: 500개 종목

2단계: FMP key-metrics-ttm (온디맨드)
   └─ 1단계 결과 중 상위 100개에 대해 펀더멘탈 조회
   └─ Redis 캐싱 (1시간 TTL)

3단계: 클라이언트 사이드 필터링
   └─ PE, ROE, EPS Growth 필터 적용
   └─ 결과: 15개 종목
```

구현:
```python
def screen_enhanced(self, filters: Dict, limit: int = 100) -> Dict:
    # 1. 필터 분리
    fmp_filters = self._extract_fmp_filters(filters)
    enhanced_filters = self._extract_enhanced_filters(filters)

    # 2. 1차 필터링 (FMP API)
    fetch_limit = 500 if enhanced_filters else limit * 2
    fmp_results = self._fetch_fmp_screener(fmp_filters, limit=fetch_limit)

    # 3. Enhanced 필터 있으면 추가 API 호출
    if enhanced_filters:
        symbols = [r['symbol'] for r in fmp_results[:100]]
        metrics = self._fetch_key_metrics_batch(symbols)
        enriched = self._merge_metrics(fmp_results[:100], metrics)
        filtered = self._apply_enhanced_filters(enriched, enhanced_filters)
    else:
        filtered = fmp_results

    return {'results': filtered[:limit], 'is_enhanced': bool(enhanced_filters)}
```

Rate Limit 대응:
```python
def _fetch_key_metrics_batch(self, symbols: List[str]) -> Dict:
    # 캐시 확인
    for symbol in symbols:
        cache_key = f'fmp:metrics_ttm:{symbol}'
        cached = cache.get(cache_key)
        if cached:
            result[symbol] = cached
        else:
            uncached_symbols.append(symbol)

    # 캐시 미스만 API 호출 (최대 20개, Rate Limit 고려)
    for symbol in uncached_symbols[:20]:
        data = self._fetch_single_key_metrics(symbol)
        if data:
            cache.set(f'fmp:metrics_ttm:{symbol}', data, 3600)  # 1시간
```

장점:
1. API 제한 우회: 지원하지 않는 필터도 적용 가능
2. 비용 효율: 캐싱으로 중복 API 호출 방지
3. 확장성: 새로운 필터 추가 용이

출처: Stock-Vis Enhanced Screener Service 구현""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["two-stage-filtering", "api-optimization", "caching", "screener"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "AI 투자 테제 빌더 - LLM 폴백 전략",
        "content": r"""LLM 기반 투자 테제 생성 시 안정성을 위한 폴백 전략

문제 상황:
1. LLM API Rate Limit 초과
2. JSON 파싱 실패 (불완전한 응답)
3. 네트워크 타임아웃

폴백 전략:
```python
def build_thesis(self, stocks, filters, user) -> InvestmentThesis:
    try:
        # LLM 호출
        response = self._call_llm(stocks, filters)
        thesis_data = self._parse_json_response(response)
        return self._create_thesis(thesis_data, user)

    except (RateLimitError, JSONDecodeError, TimeoutError) as e:
        logger.warning(f"LLM 호출 실패, 폴백 테제 생성: {e}")
        return self._create_fallback_thesis(stocks, filters, user)

def _create_fallback_thesis(self, stocks, filters, user) -> InvestmentThesis:
    return InvestmentThesis.objects.create(
        user=user,
        title="스크리너 결과 분석",
        summary=f"{len(stocks)}개 종목이 선별되었습니다. 필터 조건을 검토하세요.",
        filters_snapshot=filters,
        key_metrics=[self._format_filter(k, v) for k, v in filters.items()],
        top_picks=[s['symbol'] for s in stocks[:5]],
        risks=["자동 생성 실패로 기본 테제 생성됨"],
        rationale="LLM 분석을 사용할 수 없어 기본 정보만 제공됩니다.",
        llm_model="fallback",
        generation_time_ms=0,
    )
```

JSON 파싱 복구:
```python
def _parse_json_response(self, text: str) -> Dict:
    # 1차: 직접 파싱 시도
    try:
        return json.loads(text)
    except JSONDecodeError:
        pass

    # 2차: JSON 블록 추출
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except JSONDecodeError:
            pass

    # 3차: 부분 추출 (title, top_picks 등)
    result = {}
    title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
    if title_match:
        result['title'] = title_match.group(1)
    # ... 다른 필드도 추출

    if result:
        return result

    raise JSONDecodeError("Failed to parse", text, 0)
```

교훈:
1. LLM 응답은 항상 불완전할 수 있음 → 폴백 필수
2. JSON 파싱 실패 시 부분 복구 시도
3. 사용자에게 투명하게 폴백 상태 표시 (llm_model="fallback")
4. 폴백 테제도 유용한 정보 제공 (종목 목록, 필터 조건)

출처: Stock-Vis Investment Thesis Builder 구현""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["llm", "fallback", "thesis-builder", "json-parsing", "error-handling"],
        "confidence": ConfidenceLevel.HIGH
    },
    {
        "title": "프리셋 필터 캐스케이딩 결합 로직",
        "content": """여러 프리셋을 순차 적용할 때 필터 충돌을 처리하는 캐스케이딩 로직

핵심 원칙:
- 교집합 적용: 범위 필터는 더 엄격한 조건이 적용됨
- 충돌 = 교집합이 없는 경우만 (예: min > max)

범위 필터 병합:
```typescript
// range_max (≤X): 더 작은 값이 더 엄격
function mergeRangeMax(first: number, second: number): number {
  return Math.min(first, second);  // 교집합
}

// range_min (≥X): 더 큰 값이 더 엄격
function mergeRangeMin(first: number, second: number): number {
  return Math.max(first, second);  // 교집합
}
```

충돌 감지:
```typescript
// 교집합이 없는 경우만 충돌
// 예: per_max=15 이미 있는데 per_min=20 추가 → 교집합 없음!
function checkRangeContradiction(
  effectiveFilters: Filters,
  key: string,
  value: number
): boolean {
  const meta = FILTER_METADATA[key];
  if (!meta?.pairKey) return false;

  const pairValue = effectiveFilters[meta.pairKey];
  if (pairValue === undefined) return false;

  // min > max → 교집합 없음 = 충돌
  if (meta.type === 'range_max' && value < pairValue) return true;
  if (meta.type === 'range_min' && value > pairValue) return true;

  return false;
}
```

충돌 처리:
```typescript
if (isContradiction) {
  // 1차 프리셋 값 유지, 2차 무시
  conflicts.push({
    filterKey: key,
    resolution: `${firstPreset.name}의 값 유지, ${secondPreset.name} 적용 불가`,
  });
  continue;  // 2차 필터 적용 안 함
}
```

예시:
- 1차: per_max=20 (PE ≤ 20)
- 2차: per_max=15 (PE ≤ 15)
- 결과: per_max=15 (더 엄격, 교집합)
- 충돌 없음!

- 1차: per_max=15
- 2차: per_min=20
- 결과: 충돌! (교집합 없음)
- 1차 유지, 2차 무시

출처: Stock-Vis Preset Combiner 구현""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["preset", "filter", "cascading", "conflict-resolution"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "투자 프리셋 설계 원칙",
        "content": """효과적인 투자 스크리너 프리셋 설계 원칙

프리셋 유형별 필터 조합:

1. 가치투자 프리셋 (Undervalued Quality)
   - pe_ratio_max: 15-20 (저PER)
   - roe_min: 15-20% (고수익성)
   - debt_equity_max: 1.0 (낮은 부채)
   - market_cap_min: 1B+ (안정성)

2. 성장주 프리셋 (High Growth)
   - eps_growth_min: 20%+
   - revenue_growth_min: 15%+
   - market_cap_min: 500M+ (소형 성장주)
   - pe_ratio_max: 50 (과열 방지)

3. 배당 프리셋 (Dividend Income)
   - dividend_min: 3%+
   - market_cap_min: 10B+ (대형 안정주)
   - beta_max: 1.2 (낮은 변동성)

4. 모멘텀 프리셋 (Strong Uptrend)
   - change_percent_min: 5%+ (최근 상승)
   - volume_min: 1M+ (유동성)
   - rsi_max: 70 (과매수 방지)

5. 과매도 반등 프리셋 (Bounce Opportunity)
   - rsi_max: 30 (과매도)
   - market_cap_min: 1B+ (퀄리티)
   - change_percent_max: -3% (최근 하락)

필터 개수 가이드라인:
- 최소: 2개 (너무 적으면 의미 없음)
- 최적: 4-6개 (적절한 선별)
- 최대: 8개 (너무 많으면 결과 없음)

주의사항:
1. 상충되는 필터 조합 피하기 (예: 고배당 + 고성장)
2. 필터가 많을수록 결과가 적어짐
3. Enhanced 필터 사용 시 응답 시간 증가 고려
4. 사용자에게 프리셋 의도/철학 설명 제공

출처: Stock-Vis Screener Preset 설계""",
        "knowledge_type": KnowledgeType.STRATEGY,
        "domain": "investment",
        "tags": ["preset", "value-investing", "growth-investing", "momentum", "screener"],
        "confidence": ConfidenceLevel.HIGH
    }
]

print("프리셋-필터 동기화 및 AI 테제 빌더 교훈 KB 추가 시작...\n")

for i, lesson in enumerate(lessons, 1):
    try:
        item = KnowledgeItem(
            id=str(uuid.uuid4()),
            title=lesson["title"],
            content=lesson["content"],
            knowledge_type=lesson["knowledge_type"],
            domain=lesson["domain"],
            tags=lesson["tags"],
            confidence=lesson["confidence"],
            source="Stock-Vis Screener Upgrade Phase 2.4",
            created_by="qa-architect"
        )

        knowledge_id = kb.add_knowledge(item)
        print(f"[{i}/{len(lessons)}] 추가 완료: {lesson['title']}")
        print(f"   ID: {knowledge_id[:8]}...")
        print(f"   Type: {lesson['knowledge_type'].value}")
        print(f"   Tags: {', '.join(lesson['tags'][:3])}...")
        print()

    except Exception as e:
        print(f"[{i}/{len(lessons)}] 추가 실패: {lesson['title']}")
        print(f"   에러: {str(e)}\n")

kb.close()
print("\n모든 교훈 추가 완료!")
print("\n확인 명령어:")
print("  python shared_kb/search.py 'FMP API' --type troubleshoot")
print("  python shared_kb/search.py 'preset' --type pattern")
print("  python shared_kb/search.py 'thesis' --type pattern")
