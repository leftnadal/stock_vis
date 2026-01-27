# Market Movers 키워드 생성 시스템 V2

풍부한 컨텍스트(Overview + 뉴스)를 활용한 개선된 키워드 생성 시스템

---

## 📌 개요

### V1 (Basic) vs V2 (Enhanced)

| 항목 | V1 (Basic) | V2 (Enhanced) |
|------|-----------|---------------|
| **입력 데이터** | 기본 정보 + 지표 (5개) | 기본 정보 + 지표 + **Overview** + **뉴스** |
| **키워드 구조** | 단순 텍스트 리스트 | 카테고리 + Confidence 점수 |
| **키워드 카테고리** | 없음 | 6개 (event, product, sector, technical, fundamental, risk) |
| **Summary** | 없음 | 1-2문장 종합 요약 |
| **토큰 사용량** | ~150 토큰/종목 | ~200 토큰/종목 (+33%) |
| **비용** | $0.000045/종목 | $0.000060/종목 (+33%) |
| **품질** | 기본 | **높음** (뉴스 기반 이벤트 키워드) |
| **Fallback** | 기본 키워드 | 데이터별 단계적 Fallback |

---

## 🏗️ 아키텍처

```
MarketMover (DB)
    │
    ├─ ContextEnricher ──────────────┐
    │   ├─ Overview (stocks 앱)      │
    │   └─ 뉴스 (news 앱, 최대 3개)   │
    │                                 │
    ▼                                 ▼
KeywordContextBuilder ◄───────────────┘
    │ (토큰 최적화, Fallback 전략)
    ▼
EnhancedKeywordPromptBuilder
    │ (mover_type별 프롬프트)
    ▼
Gemini 2.5 Flash API
    │ (배치 처리: 20개 종목)
    ▼
EnhancedKeywordResponseParser
    │ (카테고리별 검증)
    ▼
StockKeyword (DB)
```

---

## 📦 핵심 컴포넌트

### 1. KeywordContextBuilder

**역할**: MarketMover 데이터를 LLM 프롬프트용 컨텍스트로 변환

**Features**:
- Overview description 200자 제한
- 뉴스 최대 3개 (제목만)
- 토큰 사용량 추정
- 배치 처리 시 4000 토큰 제한

**메서드**:
```python
def build_stock_context(
    symbol, company_name, mover_type,
    price_data, indicators,
    sector=None, industry=None,
    overview=None,  # 선택
    news=None       # 선택
) -> Dict[str, Any]
```

**출력**:
```python
{
    'basic': {...},
    'overview': {...},  # description, market_cap, pe_ratio 등
    'news': [...],      # 최대 3개 (title, source, sentiment)
    'indicators': {...},
    'has_overview': bool,
    'has_news': bool,
    'estimated_tokens': int
}
```

---

### 2. ContextEnricher

**역할**: Overview/뉴스 데이터를 외부 소스에서 가져오기

**메서드**:
```python
@staticmethod
def fetch_overview(symbol: str) -> Optional[Dict[str, Any]]
    """stocks 앱에서 Overview 조회"""

@staticmethod
def fetch_news(symbol: str, days=7, limit=3) -> Optional[List[Dict[str, Any]]]
    """news 앱에서 최근 뉴스 조회"""

@classmethod
def enrich_stock_data(symbol, **kwargs) -> Dict[str, Any]
    """종목 데이터 자동 보강"""
```

---

### 3. EnhancedKeywordPromptBuilder

**역할**: mover_type별 프롬프트 생성

**시스템 프롬프트 특징**:
- mover_type별 지침 조정
  - `gainers`: 상승 요인 강조
  - `losers`: 하락 요인 강조
  - `actives`: 거래량 급증 이유 강조
- 5개 지표 해석 가이드 포함
- 6개 키워드 카테고리 정의
- Fallback 전략 명시

**키워드 카테고리**:
- `event`: 뉴스/이벤트 기반 (예: "실적 서프라이즈")
- `product`: 제품/서비스 관련 (예: "아이폰 판매 호조")
- `sector`: 섹터/산업 트렌드 (예: "기술주 강세")
- `technical`: 기술적 신호 (예: "폭발적 거래량")
- `fundamental`: 펀더멘털 (예: "밸류에이션 매력")
- `risk`: 리스크 경고 (예: "규제 리스크")

**출력 형식**:
```json
{
  "symbol": "AAPL",
  "keywords": [
    {"text": "AI 칩 수요 급증", "category": "event", "confidence": 0.95},
    {"text": "폭발적 거래량", "category": "technical", "confidence": 0.90},
    {"text": "섹터 초과수익", "category": "sector", "confidence": 0.85}
  ],
  "summary": "AI 칩 수요 급증으로 폭발적 거래량 기록"
}
```

---

### 4. EnhancedKeywordGenerator

**역할**: LLM API 호출 및 키워드 생성 오케스트레이션

**메서드**:
```python
async def generate_keywords_for_movers(
    mover_date: date,
    mover_type: str,
    max_stocks: int = 20
) -> List[Dict[str, Any]]
    """배치 처리 (최대 20개)"""

async def generate_keywords_single(
    mover: MarketMover
) -> Optional[Dict[str, Any]]
    """단일 종목 처리"""

def estimate_batch_cost(num_stocks: int) -> Dict[str, Any]
    """비용 추정"""
```

**초기화 옵션**:
```python
generator = EnhancedKeywordGenerator(
    language="ko",            # 'ko' 또는 'en'
    enable_enrichment=True    # Overview/뉴스 보강 활성화
)
```

---

### 5. EnhancedKeywordResponseParser

**역할**: LLM 응답 파싱 및 검증

**검증 규칙**:
- JSON 형식 검증
- 필수 필드 검증 (symbol, keywords)
- 키워드 구조 검증 (text, category, confidence)
- Confidence 범위 검증 (0.0~1.0)
- 카테고리 유효성 검증

**유틸리티 메서드**:
```python
@staticmethod
def get_keywords_by_category(keywords) -> Dict[str, List[Dict]]
    """카테고리별 키워드 그룹화"""
```

---

## 🚀 사용 예시

### 1. 비동기 배치 처리 (권장)

```python
from serverless.services.keyword_generator_v2 import EnhancedKeywordGenerator
from datetime import date

async def generate_daily_keywords():
    generator = EnhancedKeywordGenerator(
        language="ko",
        enable_enrichment=True  # Overview + 뉴스 활성화
    )

    today = date.today()

    # Gainers 키워드 생성
    results = await generator.generate_keywords_for_movers(
        mover_date=today,
        mover_type='gainers',
        max_stocks=20
    )

    for result in results:
        print(f"{result['symbol']}: {result['summary']}")
        for kw in result['keywords']:
            print(f"  [{kw['category']}] {kw['text']} (conf: {kw['confidence']:.2f})")

# 실행
import asyncio
asyncio.run(generate_daily_keywords())
```

### 2. Celery 태스크 (동기)

```python
# serverless/tasks.py

from celery import shared_task
from datetime import date
from .services.keyword_generator_v2 import generate_keywords_sync_v2
from .models import StockKeyword
from django.utils import timezone
from datetime import timedelta

@shared_task(bind=True, max_retries=2)
def generate_market_movers_keywords_v2(self):
    """
    Market Movers 키워드 생성 (V2 Enhanced)

    일일 배치: Gainers/Losers/Actives 각 20개
    """
    today = date.today()
    results = {'success': 0, 'failed': 0}

    for mover_type in ['gainers', 'losers', 'actives']:
        try:
            # 키워드 생성
            keywords_data = generate_keywords_sync_v2(
                mover_date=today,
                mover_type=mover_type,
                language='ko',
                max_stocks=20,
                enable_enrichment=(mover_type == 'gainers')  # Gainers만 뉴스 보강
            )

            # DB 저장
            for item in keywords_data:
                # MarketMover에서 company_name 조회
                from serverless.models import MarketMover
                mover = MarketMover.objects.get(
                    symbol=item['symbol'],
                    date=today,
                    mover_type=mover_type
                )

                StockKeyword.objects.update_or_create(
                    symbol=item['symbol'],
                    date=today,
                    defaults={
                        'company_name': mover.company_name,
                        'keywords': [kw['text'] for kw in item['keywords']],
                        'status': 'completed',
                        'llm_model': 'gemini-2.5-flash-v2',
                        'expires_at': timezone.now() + timedelta(days=7),
                    }
                )
                results['success'] += 1

        except Exception as e:
            results['failed'] += 1
            logger.exception(f"Failed: {mover_type} - {e}")

    return results
```

### 3. Celery Beat 스케줄

```python
# config/celery.py

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'generate-market-movers-keywords-v2': {
        'task': 'serverless.tasks.generate_market_movers_keywords_v2',
        'schedule': crontab(hour=7, minute=45),  # 07:45 EST (Movers 동기화 후)
        'options': {'expires': 3600}
    }
}
```

---

## 💰 비용 분석

### 토큰 사용량 (종목당)

| 항목 | 토큰 수 (평균) |
|------|---------------|
| 시스템 프롬프트 | 1500 (배치 공통) |
| 종목당 입력 (지표만) | 150 |
| 종목당 입력 (Overview 포함) | +30 |
| 종목당 입력 (뉴스 포함) | +20 |
| **종목당 총 입력** | **200** |
| 종목당 출력 | 300 |
| **종목당 총 토큰** | **500** |

### 비용 추정 (Gemini 2.5 Flash)

**가격** (2025년 1월 기준):
- Input: $0.30 / 1M tokens
- Output: $1.20 / 1M tokens

**배치 처리 비용** (20개 종목):
```
Input:  1500 + (20 * 200) = 5,500 tokens → $0.00165
Output: 20 * 300 = 6,000 tokens → $0.00720
Total: $0.00885 (20개 종목)
```

**일일 비용** (60개 종목):
```
Gainers (20개, enrichment=True):  $0.00885
Losers (20개, enrichment=False):  $0.00750
Actives (20개, enrichment=False): $0.00750
Total: $0.02385/day
```

**월간 비용**: $0.72/month

---

## 🎯 Fallback 전략

### 데이터 부족 시 키워드 생성 방법

| 상황 | 처리 방법 |
|------|----------|
| **Overview 없음** | fundamental 카테고리 제외, technical/sector 중심 키워드 생성 |
| **뉴스 없음** | event 카테고리 제외, 지표 기반 키워드 생성 |
| **둘 다 없음** | 기본 정보(섹터, mover_type) + 지표만 사용 |
| **지표 일부 누락** | 사용 가능한 지표만 해석, 누락 지표는 "N/A" 표시 |

### 최소 키워드 예시

데이터 부족 시에도 다음 키워드는 보장:
- 섹터 기반: "기술주 강세", "에너지 섹터 회복"
- mover_type 기반: "급등 종목", "급락 종목", "거래량 급증"
- 지표 기반: "폭발적 거래량", "강한 상승세"

---

## 📊 품질 비교

### V1 (Basic) 예시

```python
{
  "symbol": "NVDA",
  "keywords": ["급등", "거래량 증가", "모멘텀"]
}
```

### V2 (Enhanced) 예시

```python
{
  "symbol": "NVDA",
  "keywords": [
    {"text": "AI 데이터센터 수요 급증", "category": "event", "confidence": 0.95},
    {"text": "GPU 판매 호조", "category": "product", "confidence": 0.92},
    {"text": "반도체 섹터 강세", "category": "sector", "confidence": 0.88},
    {"text": "폭발적 거래량 (2.5x)", "category": "technical", "confidence": 0.90},
    {"text": "높은 변동성 경고", "category": "risk", "confidence": 0.75}
  ],
  "summary": "AI 데이터센터 수요 급증으로 GPU 판매 호조세를 보이며 반도체 섹터를 견인"
}
```

**차이점**:
- V1: 추상적 키워드 ("급등")
- V2: 구체적 이유 ("AI 데이터센터 수요 급증")
- V2: 카테고리 분류로 투자 판단 용이
- V2: Confidence 점수로 신뢰도 확인

---

## 🔧 통합 가이드

### Phase 1: V2 병렬 운영 (2주)
- V1 유지 (기존 프로덕션)
- V2 실험 (일일 배치 1회)
- 품질 비교 (수동 검토)

### Phase 2: V2 부분 전환 (2주)
- Gainers: V2 (뉴스 중요도 높음)
- Losers: V1 (기존 로직)
- Actives: V1 (기존 로직)

### Phase 3: V2 전환 (1주)
- 모든 mover_type을 V2로 전환
- V1 코드 제거 또는 백업

### Phase 4: 최적화 (지속)
- `enable_enrichment` 조건부 활성화
  - Gainers: 항상 활성화 (뉴스 필수)
  - Losers: RVOL > 2.0일 때만 활성화
  - Actives: 변동성 상위 10개만 활성화

---

## 🧪 테스트

### 단위 테스트

```bash
# 컨텍스트 빌더 테스트
python manage.py test serverless.tests.test_keyword_context_builder

# 프롬프트 빌더 테스트
python manage.py test serverless.tests.test_keyword_prompts_v2

# 파서 테스트
python manage.py test serverless.tests.test_keyword_parser
```

### 수동 테스트

```python
# serverless/services/keyword_usage_example.py 참고
python -m serverless.services.keyword_usage_example
```

---

## 📝 TODO

- [ ] 단위 테스트 작성 (컨텍스트 빌더, 프롬프트 빌더, 파서)
- [ ] Celery 태스크 구현 및 테스트
- [ ] V1 vs V2 품질 비교 (A/B 테스트)
- [ ] Frontend 통합 (카테고리별 키워드 표시)
- [ ] 비용 모니터링 대시보드
- [ ] 캐싱 전략 (Semantic Cache 활용)

---

## 📚 참고 문서

- RAG Analysis 시스템: `/rag_analysis/services/`
- LLM Service Lite: `/rag_analysis/services/llm_service.py`
- Market Movers 지표: `CLAUDE.md` - Market Movers 섹션

---

## 🤝 협업

| 에이전트 | 협업 내용 |
|---------|----------|
| @backend | MarketMover 모델, StockKeyword 모델 협의 |
| @rag-llm | LLM 프롬프트 최적화, 토큰 관리 |
| @frontend | 키워드 카테고리별 UI 표시 |
| @infra | Celery 태스크 스케줄링, 비용 모니터링 |

---

**작성자**: @rag-llm
**버전**: 2.0.0
**최종 수정**: 2026-01-24
