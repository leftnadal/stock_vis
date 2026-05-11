# Peer 프리셋 Phase 6~7 설계서

> 작성일: 2026-04-01
> 전제: Phase 1~5 완료 (프리셋 5종 + 커스텀 Compute-on-Read)
> 의존: CompanyNarrativeTag (chainsight), Thesis Control

---

## Phase 6: Thematic 프리셋 (LLM 큐레이션)

### 핵심 질문

> "섹터가 달라도 사업모델이 비슷한 기업과 비교하면?"

기존 프리셋은 sector/industry/size 기반이라, AAPL을 "구독 전환 기업"(MSFT, ADBE, CRM)과 비교하거나 AMZN을 "마켓플레이스"(EBAY, SHOP)와 비교하는 것이 불가능함.

### 테마 축 (우선순위)

| 순위 | 테마 축 | 설명 | 예시 |
|------|---------|------|------|
| 1 | **사업모델** | 수익 창출 구조 | subscription_saas, platform_marketplace, hardware_services |
| 2 | **수익원 구성** | 매출 비중 분해 | recurring_70pct, advertising_dominant, licensing |
| 3 | **공급망 위치** | 밸류체인 내 위치 | foundry, fabless, distributor, end_product |

Phase 6에서는 **사업모델 축만** 구현. 수익원/공급망은 Phase 6.5로 확장.

### 구현 단계

#### Step 1: Gemini 사업모델 태깅 (배치)

```python
# 프롬프트
"""
아래 기업의 핵심 사업모델을 1~3개 태그로 분류하세요.
태그 풀: subscription_saas, platform_marketplace, hardware_services,
         advertising, financial_services, healthcare_services,
         commodity_producer, industrial_manufacturing,
         consumer_brand, infrastructure_provider, ...

기업: {symbol} {stock_name} ({sector} / {industry})
매출: {revenue}, 주요 제품: {description[:200]}

출력 (JSON): {"tags": ["subscription_saas", "platform_marketplace"], "confidence": 0.85}
"""
```

- 대상: S&P 500 503개
- LLM: Gemini 2.5 Flash (15 RPM → ~34분)
- 저장: `CompanyNarrativeTag.theme_tags` (chainsight 모델, 이미 존재)
- 갱신 주기: 분기 1회

#### Step 2: 태그 클러스터링

```python
# 같은 태그를 가진 종목 그룹핑
tag_groups = {}
for tag in CompanyNarrativeTag.objects.values_list('theme_tags', flat=True):
    for t in tag:
        tag_groups.setdefault(t, []).append(symbol)

# 유효 그룹: 5개 이상만 프리셋 생성
valid_groups = {t: syms for t, syms in tag_groups.items() if len(syms) >= 5}
```

예상 유효 그룹: 10~15개
- `subscription_saas`: MSFT, ADBE, CRM, NOW, WDAY, INTU, ...
- `platform_marketplace`: AMZN, EBAY, ABNB, BKNG, ...
- `hardware_services`: AAPL, HPQ, DELL, ...
- `advertising`: GOOGL, META, TTD, ...

#### Step 3: PeerPreset 생성

```python
PeerPreset.objects.update_or_create(
    symbol=stock, preset_key='thematic',
    defaults={
        'display_name': '비즈니스 테마 (beta)',
        'logic_summary': f"구독 SaaS 모델 {len(peers)}개와 비교",
        'peer_symbols': peers,
        'generation_method': 'curated',
        'is_active': True,  # 수동 검증 후
    }
)
```

UI에서 "(beta)" 표시. 태깅 품질이 낮은 종목은 `is_active=False`.

#### Step 4: 품질 검증

- 태깅 결과를 수동 샘플링 (50개) → 정확도 80% 이상이면 전체 활성화
- 태그가 너무 광범위한 경우 (50개 이상 종목) → 하위 태그로 분리
- 태그가 너무 좁은 경우 (3개 미만) → 상위 태그로 병합

### 비용/리소스

| 항목 | 비용 |
|------|------|
| Gemini 호출 | 503회 × $0 (Free tier) |
| 시간 | ~34분 (배치) |
| DB | CompanyNarrativeTag 503건 (이미 모델 존재) |
| 프리셋 추가 | ~400건 (유효 태그 보유 종목) |

---

## Phase 7: LLM 대화형 Peer 조정

### 핵심 질문

> "내가 원하는 조건으로 peer를 필터링/조정할 수 있을까?"

Phase 5의 커스텀 mode는 심볼을 직접 입력해야 함.
Phase 7은 자연어 → 조건 파싱 → 자동 필터링.

### 사용 시나리오 (투자자 관점)

| # | 사용자 입력 | 파싱 결과 | 목적 |
|---|-----------|----------|------|
| 1 | "성숙 기업만 비교" | revenue_growth < 10%, ROE > 15% | 가치투자 관점 |
| 2 | "해외매출 50% 이상" | foreign_revenue_pct > 50 | 환율 민감도 분석 |
| 3 | "부채비율 30% 이하만" | debt_to_equity < 0.3 | 불황기 강건성 |
| 4 | "R&D 매출 10% 이상" | rd_to_revenue > 0.1 | 혁신 기업 필터 |
| 5 | "반도체 빼줘" | exclude industry='Semiconductors' | 특정 산업 제외 |

### 아키텍처

```
사용자 자연어 입력
    ↓
[LLM 필터 파서] — Gemini 호출 1회
    ↓
구조화된 필터 조건 (JSON)
{
  "include_filters": [
    {"field": "revenue_growth_yoy", "op": "<", "value": 0.1},
    {"field": "roe", "op": ">", "value": 0.15}
  ],
  "exclude_filters": [
    {"field": "industry", "op": "=", "value": "Semiconductors"}
  ]
}
    ↓
[필터 실행 엔진]
    ↓
CompanyMetricSnapshot + Stock 모델에서 조건 충족 종목 추출
    ↓
[CustomBenchmarkEngine.compute_summary()] — 이미 구현됨 (Phase 5)
    ↓
결과 반환 + Redis 캐시
```

### LLM 필터 파서 프롬프트

```python
FILTER_PARSER_PROMPT = """
사용자가 peer 비교 조건을 자연어로 입력했습니다.
이를 구조화된 필터 조건으로 변환하세요.

사용 가능한 필드:
- 지표: gross_margin, operating_margin, net_margin, roe, roic,
         revenue_growth_yoy, debt_to_equity, current_ratio,
         fcf_margin, pe_ratio, ev_to_ebitda, ...
- 기업 속성: sector, industry, market_capitalization,
              foreign_revenue_pct, rd_to_revenue

사용자 입력: "{user_input}"
현재 종목: {symbol} ({sector} / {industry})

출력 (JSON):
{
  "include_filters": [{"field": "...", "op": "<|>|=|>=|<=", "value": ...}],
  "exclude_filters": [{"field": "...", "op": "=|contains", "value": "..."}],
  "description": "해석한 조건 요약 (한글)"
}
"""
```

### 구현 단계

#### Step 1: 필터 파서 서비스

```python
# validation/services/peer_filter_parser.py
class PeerFilterParser:
    def parse(self, user_input: str, symbol: str) -> dict:
        """자연어 → 구조화 필터"""
        # Gemini 호출 → JSON 파싱

    def execute_filter(self, filters: dict, base_symbols: list) -> list:
        """필터 조건으로 종목 추출"""
        # CompanyMetricSnapshot + Stock 모델 쿼리
```

#### Step 2: API 엔드포인트

```
POST /api/v1/validation/{symbol}/peer-filter/
body: {"query": "해외매출 50% 이상인 기업만 비교해줘"}

응답:
{
  "parsed_filters": {...},
  "description": "해외매출 비중 50% 이상 필터 적용",
  "filtered_peers": ["AAPL", "MSFT", "NVDA", ...],
  "filtered_count": 13,
  "preview": {
    "category_signals": [...],
    "summary_text": "..."
  }
}
```

사용자가 "적용" 버튼을 누르면 `POST /peer-preference/` (mode=custom) 호출.

#### Step 3: UI — 대화형 입력

```
┌─ Peer 조정 ───────────────────────────────────┐
│ 💬 입력: [해외매출 50% 이상인 기업만 비교해줘] │
│                                [조건 적용 →]   │
│                                                │
│ 🤖 13개 종목이 필터되었습니다.                  │
│    AAPL(58%), MSFT(52%), NVDA(83%)...          │
│                                                │
│    [이 peer로 적용]  [다시 조정]               │
└────────────────────────────────────────────────┘
```

### Thesis Control 연동

#### 가설 빌더 연결

```
[Thesis 생성 화면]
  Step 3: "비교 기업 선택"
    ├─ 기본: 현재 프리셋 사용
    ├─ Phase 6: 테마 프리셋 선택
    └─ Phase 7: "이 가설에 맞는 조건으로 peer 조정"
         → 대화형 필터 → 결과 미리보기 → 적용
```

#### 관제실 대시보드 연결

```
[Thesis 관제실]
  탭: 전제 관리 | 지표 추적 | Peer 비교 (새 탭)
    └─ 조정된 peer 기준으로:
       - 카테고리 신호등 변화 추적
       - 핵심 지표 분포 (히스토그램/박스플롯)
       - "이 peer 대비 AAPL이 개선 중인가?" 시계열
```

#### DB 연동

```python
# thesis/models.py — Thesis 모델에 필드 추가
class Thesis(models.Model):
    # 기존 필드...

    # Phase 7 연동
    peer_preset_key = models.CharField(max_length=30, blank=True, default='')
    peer_filter_query = models.TextField(blank=True, default='')
    peer_filter_result = models.JSONField(default=list)  # 필터된 심볼 목록
```

---

## 구현 로드맵

```
Phase 6 (2~3일):
  6-1. Gemini 사업모델 태깅 배치 실행 (34분)
  6-2. 태그 클러스터링 + PeerPreset 생성
  6-3. 수동 품질 검증 (샘플 50개)
  6-4. UI "(beta)" 표시 + 프리셋 목록에 추가

Phase 7 (4~5일):
  7-1. PeerFilterParser 서비스 (Gemini 파싱)
  7-2. 필터 실행 엔진 (Snapshot + Stock 쿼리)
  7-3. POST /peer-filter/ API
  7-4. 대화형 UI 컴포넌트 (입력 → 미리보기 → 적용)
  7-5. Thesis Control 연동 (가설 빌더 + 관제실)
```

---

## 성능 목표

| 시나리오 | 목표 | 방법 |
|---------|------|------|
| thematic 프리셋 조회 | < 50ms | 배치 데이터 DB 조회 |
| LLM 필터 파싱 | < 3초 | Gemini Flash 1회 호출 |
| 필터 실행 + 계산 | < 200ms | Snapshot 벌크 쿼리 + numpy |
| Thesis 연동 조회 | < 100ms | 저장된 peer 목록으로 계산 |

---

## 위험 및 완화

| 위험 | 완화 |
|------|------|
| LLM 태깅 품질 불안정 | 수동 검증 후 활성화 + "(beta)" 표시 |
| 사용자 자연어 파싱 실패 | fallback: "조건을 이해하지 못했습니다. 예시: ..." 안내 |
| Gemini 응답 지연 (>5초) | 타임아웃 3초 + "처리 중..." 로딩 상태 |
| 필터 결과 0건 | "조건에 맞는 종목이 없습니다. 조건을 완화해보세요." |
| Thesis 모델 스키마 변경 | nullable 필드만 추가 (기존 Thesis에 영향 없음) |

---

## 구현 준비 상태 평가 (2026-04-01 기준)

### chainsight 모델 데이터 현황

| 모델 | 레코드 | Phase 6 의존 | Phase 7 의존 |
|------|--------|-------------|-------------|
| CompanyNarrativeTag | **0** | **블로킹** (theme_tags) | - |
| CompanySensitivityProfile | **0** | - | **블로킹** (foreign_revenue_pct) |
| CompanyCapitalDNA | **0** | - | **블로킹** (rd_to_revenue) |
| CompanyRevenueStructure | **0** | - | 선택사항 |
| CompanyGrowthStage | **0** | - | 선택사항 |
| CompanyMetricSnapshot | **79,061** | - | ✅ 지표 필터 가능 (31개) |
| Stock (sector/industry/mcap) | **515** | - | ✅ 속성 필터 가능 |

### 구현 난이도

| 항목 | 난이도 | 이유 |
|------|--------|------|
| Phase 6 태깅 배치 | ⭐⭐ 낮음 | Gemini 호출 + DB 저장, KoreanOverviewService 패턴 재활용 |
| Phase 6 클러스터링 | ⭐ 매우 낮음 | ArrayField __overlap 쿼리 그룹핑 |
| Phase 7 필터 파서 | ⭐⭐⭐ 중간 | LLM JSON 파싱 안정적이나 에지케이스 처리 필요 |
| Phase 7 chainsight 데이터 채우기 | ⭐⭐⭐⭐ 높음 | foreign_revenue_pct, rd_to_revenue는 10-K 파싱 or FMP 별도 API |
| Phase 7 Thesis 연동 | ⭐⭐⭐ 중간 | thesis 모델 필드 추가 + 관제실 탭 |

### 유지보수 어려움

| 항목 | 어려움 | 이유 |
|------|--------|------|
| LLM 태깅 품질 | ⭐⭐⭐ 중간 | 분기 재실행 시 태그 변동 → 프리셋 변동 가능 |
| LLM 파싱 안정성 | ⭐⭐⭐⭐ 높음 | 애매한 자연어 입력 ("부채 적은 기업") 처리 |
| chainsight 데이터 갱신 | ⭐⭐⭐⭐ 높음 | foreign_revenue_pct 연 1회(10-K), 별도 파이프라인 필요 |
| Redis 캐시 관리 | ⭐⭐ 낮음 | TTL 1시간, 자동 만료 |

### 판단: Chain Sight 완성 후 진행

**Phase 6~7은 Chain Sight 데이터 파이프라인이 선행되어야 함.**

이유:
1. **테스트 불가** — chainsight 모델이 전부 0건이라 태깅/필터링 결과를 검증할 수 없음
2. **Phase 6은 CompanyNarrativeTag.theme_tags에 의존** — Chain Sight 배치에서 theme_tags를 채우는 파이프라인이 먼저 필요
3. **Phase 7-Full은 SensitivityProfile/CapitalDNA에 의존** — 10-K 파싱 또는 FMP API 파이프라인이 선행
4. **Phase 7-Lite(MetricSnapshot 지표만)는 지금도 가능** — 하지만 5개 시나리오 중 2개(해외매출/R&D)가 빠져 가치가 제한적

### Phase 7-Lite 옵션 (Chain Sight 없이 가능)

MetricSnapshot 31개 지표만으로 필터링하면 Chain Sight 없이도 아래 시나리오는 커버 가능:

| # | 시나리오 | 필요 데이터 | 가능 여부 |
|---|---------|-----------|----------|
| 1 | "성숙 기업만" (growth<10%, ROE>15%) | MetricSnapshot | ✅ |
| 2 | "해외매출 50% 이상" | SensitivityProfile | ❌ Chain Sight 필요 |
| 3 | "부채비율 30% 이하" | MetricSnapshot | ✅ |
| 4 | "R&D 매출 10% 이상" | CapitalDNA | ❌ Chain Sight 필요 |
| 5 | "반도체 빼줘" | Stock.industry | ✅ |

→ 5개 중 3개 커버. Chain Sight 완성 후 나머지 2개 추가.

### 최종 로드맵

```
[현재] Peer System Phase 1~5 완료 ✅
  ↓
[다음] Chain Sight 데이터 파이프라인 구축
  → CompanyNarrativeTag (theme_tags 태깅)
  → CompanySensitivityProfile (foreign_revenue_pct 등)
  → CompanyCapitalDNA (rd_to_revenue 등)
  → CompanyGrowthStage (lifecycle 분류)
  ↓
[이후] Phase 6: Thematic 프리셋 (Chain Sight theme_tags 기반)
  ↓
[이후] Phase 7: LLM 대화형 (Chain Sight + MetricSnapshot 통합 필터)
  ↓
[이후] Thesis Control 연동
```
