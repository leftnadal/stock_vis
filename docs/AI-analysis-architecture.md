# AI분석 시스템 v4.2.1 Implementation Guide

> **"AI 비서 + 그래프 탐험" 단계별 구현 가이드**
> 
> Gemini/ChatGPT 피드백 반영 + 날짜 기반 데이터 전략

---

## 📋 목차

1. [핵심 설계 원칙](#1-핵심-설계-원칙)
2. [데이터 신선도 전략](#2-데이터-신선도-전략)
3. [단계별 구현 로드맵](#3-단계별-구현-로드맵)
4. [v4.2-lite 상세 스펙](#4-v42-lite-상세-스펙)
5. [v4.2-core 상세 스펙](#5-v42-core-상세-스펙)
6. [v4.2-full 상세 스펙](#6-v42-full-상세-스펙)
7. [PostgreSQL ↔ Neo4j 동기화](#7-postgresql--neo4j-동기화)
8. [성능 최적화 전략](#8-성능-최적화-전략)
9. [LLM 모델 전략](#9-llm-모델-전략)
10. [체크리스트](#10-체크리스트)

---

## 1. 핵심 설계 원칙

### 1.1 "날짜가 있는 데이터" 원칙

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Stock-Vis는 실시간 트레이딩 플랫폼이 아니라                   │
│   "투자 교육 + 분석 학습" 플랫폼이다.                          │
│                                                                 │
│   따라서:                                                       │
│   • 실시간 현재가 ❌ → 전일 종가 ✅                            │
│   • "지금 얼마야?" ❌ → "어제 기준 $178.50" ✅                 │
│   • 모든 데이터에 날짜/시점 명시                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**장점**:
1. PostgreSQL ↔ Neo4j 실시간 동기화 부담 제거
2. 사용자 혼동 방지 (명확한 기준일)
3. 데이터 검증 용이 (어떤 시점 데이터인지 추적 가능)
4. 법적 리스크 감소 (실시간 정보 제공이 아님을 명시)

### 1.2 단계적 복잡도 증가

```
v4.2-lite (4주)     v4.2-core (4주)     v4.2-full (4주)
─────────────────────────────────────────────────────────
│                   │                   │
│  기본 분석        │  + Neo4j 캐시     │  + Discovery
│  + 간단한 탐험    │  + Smart Rerank   │  + Graph Highlight
│  + 날짜 명시      │  + 병렬 처리      │  + Multi-Provider
│                   │                   │
└───────────────────┴───────────────────┴─────────────────
     "동작하는"          "똑똑한"           "완성된"
       탐험               탐험               탐험
```

### 1.3 데이터 역할 분리

```
┌─────────────────────────────────────────────────────────────────┐
│                      데이터 저장소 역할                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PostgreSQL (Source of Truth)                                    │
│  ├── 종목 기본 정보 (symbol, name, sector)                      │
│  ├── 가격 히스토리 (date, close_price) ← 날짜별 저장            │
│  ├── 재무제표 (fiscal_year, fiscal_quarter)                     │
│  ├── 뉴스 (published_at)                                        │
│  ├── 분석 세션/메시지 (과금, 사용량)                            │
│  └── 사용자 데이터                                               │
│                                                                  │
│  Neo4j (Relationship + Cache)                                    │
│  ├── 종목 노드 (symbol만, 가격 없음)                            │
│  ├── 관계 (SUPPLIES, IN_SECTOR, COMPETES_WITH)                  │
│  ├── 뉴스 노드 (id, published_at만)                             │
│  ├── 세션 캐시 (question_embedding, 요약)                       │
│  └── 탐험 경로 (LED_TO 관계)                                    │
│                                                                  │
│  ⚠️ Neo4j에는 "휘발성 데이터(가격)" 저장 안 함                  │
│     → 동기화 부담 제거                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 데이터 신선도 전략

### 2.1 데이터 유형별 기준일 정책

| 데이터 유형 | 기준일 | 표시 형식 | 갱신 주기 |
|------------|--------|----------|----------|
| **주가** | 전 거래일 종가 | "2025-12-11 기준 $178.50" | 매일 장 마감 후 |
| **재무제표** | 분기/연간 | "2025 Q3 기준" | 분기별 |
| **뉴스** | 발행일 | "2025-12-10 발행" | 실시간 수집, 분석 시 고정 |
| **기술적 지표** | 계산 기준일 | "최근 20일 기준 RSI: 65" | 매일 |
| **거시경제** | 발표일 | "2025-12-01 발표 CPI: 3.2%" | 발표 시 |

### 2.2 AI 응답 내 날짜 명시 규칙

```python
# rag_analysis/prompts/date_rules.py

DATE_DISPLAY_RULES = """
## 데이터 날짜 명시 규칙

모든 수치 데이터를 언급할 때 반드시 기준일을 명시하세요.

### 주가
❌ "AAPL의 현재가는 $178.50입니다"
✅ "AAPL의 종가는 $178.50입니다 (2025-12-11 기준)"

### 재무제표
❌ "ROE는 150%입니다"
✅ "ROE는 150%입니다 (2025 Q3 기준)"

### 뉴스
❌ "최근 뉴스에 따르면..."
✅ "12월 10일 Bloomberg 보도에 따르면..."

### 기술적 지표
❌ "RSI가 과매수 구간입니다"
✅ "RSI는 72로 과매수 구간입니다 (12월 11일 기준, 14일 이동평균)"

### 거시경제
❌ "금리는 5.25%입니다"
✅ "기준금리는 5.25%입니다 (2025년 12월 FOMC 기준)"
"""

# 시스템 프롬프트에 추가
SYSTEM_PROMPT_ADDITION = """
중요: 당신이 분석에 사용하는 모든 데이터에는 기준일이 있습니다.
수치를 언급할 때 반드시 해당 데이터의 기준일을 함께 명시하세요.
이는 사용자가 데이터의 시점을 정확히 이해하도록 돕기 위함입니다.

주가 데이터는 전 거래일 종가 기준입니다. 실시간 가격이 아닙니다.
"""
```

### 2.3 컨텍스트 포맷팅

```python
# rag_analysis/context/formatter.py

class DateAwareContextFormatter:
    """날짜를 명시하는 컨텍스트 포맷터"""
    
    def format_stock_context(self, stock_data: dict) -> str:
        """종목 컨텍스트 포맷팅"""
        
        return f"""
## {stock_data['symbol']} ({stock_data['name']})
- 섹터: {stock_data['sector']}
- 종가: ${stock_data['close_price']:,.2f} ({stock_data['price_date']} 기준)
- 시가총액: ${stock_data['market_cap']:,.0f}B ({stock_data['price_date']} 기준)
- 52주 변동: ${stock_data['week_52_low']} ~ ${stock_data['week_52_high']}
"""
    
    def format_financial_context(self, financial_data: dict) -> str:
        """재무제표 컨텍스트 포맷팅"""
        
        period = f"{financial_data['fiscal_year']} {financial_data['fiscal_quarter']}"
        
        return f"""
## 재무제표 ({period} 기준)
- 매출: ${financial_data['revenue']:,.0f}M
- 영업이익: ${financial_data['operating_income']:,.0f}M
- 순이익: ${financial_data['net_income']:,.0f}M
- ROE: {financial_data['roe']:.1f}%
- 부채비율: {financial_data['debt_to_equity']:.1f}%
"""
    
    def format_news_context(self, news_list: list) -> str:
        """뉴스 컨텍스트 포맷팅"""
        
        formatted = "## 관련 뉴스\n"
        
        for news in news_list:
            pub_date = news['published_at'].strftime('%Y-%m-%d')
            sentiment_label = self._sentiment_label(news['sentiment'])
            
            formatted += f"""
### [{pub_date}] {news['title']}
- 출처: {news['source']}
- 감성: {sentiment_label}
- 요약: {news['summary'][:200]}...
"""
        
        return formatted
    
    def format_indicator_context(self, indicators: dict, as_of_date: str) -> str:
        """기술적 지표 컨텍스트 포맷팅"""
        
        return f"""
## 기술적 지표 ({as_of_date} 기준)
- RSI (14일): {indicators['rsi']:.1f}
- MACD: {indicators['macd']:.2f}
- 이동평균 (20일): ${indicators['sma_20']:.2f}
- 이동평균 (50일): ${indicators['sma_50']:.2f}
- 볼린저 밴드: ${indicators['bb_lower']:.2f} ~ ${indicators['bb_upper']:.2f}
"""
```

### 2.4 UI에서 날짜 표시

```typescript
// components/ai-analysis/DataFreshnessIndicator.tsx

interface DataFreshnessProps {
  dataType: 'price' | 'financial' | 'news' | 'indicator';
  asOfDate: string;
}

export function DataFreshnessIndicator({ dataType, asOfDate }: DataFreshnessProps) {
  const labels = {
    price: '주가 기준일',
    financial: '재무제표 기준',
    news: '뉴스 기준',
    indicator: '지표 기준일',
  };
  
  const formattedDate = new Date(asOfDate).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  
  return (
    <div className="flex items-center gap-1 text-xs text-muted-foreground">
      <Calendar className="w-3 h-3" />
      <span>{labels[dataType]}: {formattedDate}</span>
    </div>
  );
}

// 분석 결과 헤더에 표시
function AnalysisHeader({ session }: { session: AnalysisSession }) {
  return (
    <div className="border-b pb-3 mb-4">
      <h2 className="text-lg font-semibold">AI 분석 결과</h2>
      
      <div className="flex flex-wrap gap-3 mt-2">
        <DataFreshnessIndicator 
          dataType="price" 
          asOfDate={session.priceAsOfDate} 
        />
        <DataFreshnessIndicator 
          dataType="financial" 
          asOfDate={session.financialAsOfDate} 
        />
      </div>
      
      <p className="text-xs text-muted-foreground mt-2">
        ※ 본 분석은 위 기준일 데이터를 바탕으로 합니다. 실시간 정보가 아닙니다.
      </p>
    </div>
  );
}
```

---

## 3. 단계별 구현 로드맵

### 3.1 전체 타임라인

```
Week 1-4: v4.2-lite (MVP)
├── Week 1-2: 기반 인프라 + 기본 분석
└── Week 3-4: 간단한 탐험 + 날짜 표시

Week 5-8: v4.2-core
├── Week 5-6: Neo4j 캐시 + 병렬 처리
└── Week 7-8: Smart Re-ranking + Guard 시스템

Week 9-12: v4.2-full
├── Week 9-10: Discovery Engine + Graph Highlight
└── Week 11-12: Multi-Provider + 고급 UX
```

### 3.2 버전별 기능 범위

| 기능 | v4.2-lite | v4.2-core | v4.2-full |
|------|:---------:|:---------:|:---------:|
| 기본 AI 분석 | ✅ | ✅ | ✅ |
| 날짜 명시 시스템 | ✅ | ✅ | ✅ |
| DataBasket CRUD | ✅ | ✅ | ✅ |
| Neo4j 그래프 컨텍스트 | ✅ (기본) | ✅ (최적화) | ✅ (고급) |
| LLM 기반 탐험 제안 | ✅ | ✅ | ✅ |
| Dynamic Policy | ✅ (파일) | ✅ (DB) | ✅ (DB) |
| 스트리밍 응답 | ✅ | ✅ | ✅ |
| Neo4j 세션 캐시 | ❌ | ✅ | ✅ |
| Smart Re-ranking | ❌ | ✅ | ✅ |
| 병렬 처리 | ❌ | ✅ | ✅ |
| Token/Cost Guard | ❌ | ✅ | ✅ |
| Discovery Engine | ❌ | ❌ | ✅ |
| Graph Highlight | ❌ | ❌ | ✅ |
| Multi-Provider | ❌ | ❌ | ✅ |
| Prompt Adapter | ❌ | ❌ | ✅ |
| Graph Playback | ❌ | ❌ | ❌ (v4.3) |
| Crowd Wisdom | ❌ | ❌ | ❌ (v4.3) |

---

## 4. v4.2-lite 상세 스펙

### 4.1 목표

> **"4주 안에 동작하는 탐험 경험 MVP"**

- AI 분석이 작동하고
- Neo4j에서 관계 데이터를 가져와서
- "다음에 볼만한 종목"을 제안하는 것

### 4.2 Django 모델 (최소)

```python
# rag_analysis/models.py (v4.2-lite)

from django.db import models
from django.contrib.postgres.fields import ArrayField


class DataBasket(models.Model):
    """분석 데이터 바구니"""
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default='새 바구니')
    estimated_tokens = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'data_baskets'


class BasketItem(models.Model):
    """바구니 아이템"""
    
    ITEM_TYPES = [
        ('stock', 'Stock'),
        ('financial', 'Financial'),
        ('news', 'News'),
        ('indicator', 'Indicator'),
    ]
    
    basket = models.ForeignKey(
        DataBasket, 
        on_delete=models.CASCADE,
        related_name='items'
    )
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    reference_id = models.CharField(max_length=50)
    
    # 스냅샷 + 날짜 정보
    snapshot_data = models.JSONField(default=dict)
    data_as_of_date = models.DateField(null=True)  # 데이터 기준일
    
    estimated_tokens = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'basket_items'


class AnalysisSession(models.Model):
    """분석 세션"""
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    basket = models.ForeignKey(
        DataBasket, 
        on_delete=models.SET_NULL, 
        null=True
    )
    
    # 탐험 관련 (v4.2-lite는 단순하게)
    starting_entity = models.CharField(max_length=50, null=True)
    exploration_path = models.JSONField(default=list)
    
    # 설정
    persona = models.CharField(max_length=50, default='general')
    
    # 데이터 기준일 (분석 시점의 데이터 날짜)
    price_as_of_date = models.DateField(null=True)
    financial_as_of_date = models.DateField(null=True)
    
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analysis_sessions'


class AnalysisMessage(models.Model):
    """세션 메시지"""
    
    session = models.ForeignKey(
        AnalysisSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20)  # user, assistant
    content = models.TextField()
    
    # 구조화된 응답
    structured_data = models.JSONField(default=dict)
    suggestions = models.JSONField(default=list)  # 탐험 제안
    
    # 메타
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analysis_messages'
        ordering = ['created_at']
```

### 4.3 Neo4j 스키마 (최소)

```cypher
// v4.2-lite Neo4j Schema
// 기존 OAG 스키마 활용 + 최소한의 세션 저장

// 기존 노드들 (이미 존재)
// (:Stock {symbol, name, sector})
// (:Sector {id, name})
// (:News {id, title, published_at, sentiment})

// 기존 관계들 (이미 존재)
// (:Stock)-[:SUPPLIES]->(:Stock)
// (:Stock)-[:IN_SECTOR]->(:Sector)
// (:News)-[:MENTIONS]->(:Stock)

// v4.2-lite 추가: 세션 노드 (단순 버전)
// (:AnalysisSession {
//     id: int,              -- Django PK
//     entities: list,       -- 분석한 종목들
//     created_at: datetime
// })

// 세션 - 종목 관계
// (s:AnalysisSession)-[:ANALYZED]->(stock:Stock)

// 탐험 경로 (선택적)
// (s1:AnalysisSession)-[:LED_TO]->(s2:AnalysisSession)
```

### 4.4 간소화된 파이프라인

```python
# rag_analysis/services/pipeline_lite.py

"""
v4.2-lite 분석 파이프라인
- 단순하고 직관적인 흐름
- 최소한의 컴포넌트
"""

class AnalysisPipelineLite:
    """v4.2-lite 파이프라인"""
    
    def __init__(self):
        self.neo4j_service = Neo4jServiceLite()
        self.llm_service = LLMServiceLite()
        self.context_formatter = DateAwareContextFormatter()
    
    async def analyze(
        self,
        session: AnalysisSession,
        question: str
    ) -> AsyncIterator[dict]:
        """
        간소화된 분석 흐름
        
        1. 컨텍스트 수집 (PostgreSQL + Neo4j)
        2. LLM 분석
        3. 탐험 제안 (LLM 기반)
        4. 저장
        """
        
        basket = session.basket
        
        # ===== Step 1: 컨텍스트 수집 =====
        yield {'phase': 'preparing', 'message': '데이터 준비 중...'}
        
        # PostgreSQL에서 상세 데이터 (날짜 포함)
        basket_context = await self._build_basket_context(basket)
        
        # Neo4j에서 관계 데이터
        entities = self._extract_entities_simple(basket)
        graph_context = await self.neo4j_service.get_simple_context(entities)
        
        yield {
            'phase': 'context_ready',
            'data': {
                'price_as_of': basket_context['price_as_of_date'],
                'related_stocks': len(graph_context['related_stocks'])
            }
        }
        
        # ===== Step 2: LLM 분석 =====
        yield {'phase': 'analyzing', 'message': 'AI가 분석 중...'}
        
        full_context = self.context_formatter.format_all(
            basket_context, 
            graph_context
        )
        
        messages = self._build_messages(question, full_context, session)
        
        full_response = ""
        async for chunk in self.llm_service.stream(messages):
            full_response += chunk
            yield {'phase': 'streaming', 'chunk': chunk}
        
        # ===== Step 3: 탐험 제안 (LLM 기반) =====
        yield {'phase': 'suggesting', 'message': '탐험 제안 생성 중...'}
        
        suggestions = await self._generate_suggestions_with_llm(
            question=question,
            analysis=full_response,
            graph_context=graph_context
        )
        
        # ===== Step 4: 저장 =====
        await self._save_message(session, question, full_response, suggestions)
        await self._save_to_neo4j(session, entities)
        
        # ===== 완료 =====
        yield {
            'phase': 'complete',
            'data': {
                'analysis': full_response,
                'suggestions': suggestions,
                'data_as_of': {
                    'price': basket_context['price_as_of_date'],
                    'financial': basket_context['financial_as_of_date']
                }
            }
        }
    
    async def _build_basket_context(self, basket: DataBasket) -> dict:
        """바구니에서 컨텍스트 빌드 (날짜 포함)"""
        
        context = {
            'stocks': [],
            'financials': [],
            'news': [],
            'indicators': [],
            'price_as_of_date': None,
            'financial_as_of_date': None,
        }
        
        for item in basket.items.all():
            data = item.snapshot_data
            data['as_of_date'] = item.data_as_of_date
            
            if item.item_type == 'stock':
                context['stocks'].append(data)
                context['price_as_of_date'] = item.data_as_of_date
            elif item.item_type == 'financial':
                context['financials'].append(data)
                context['financial_as_of_date'] = data.get('fiscal_period')
            elif item.item_type == 'news':
                context['news'].append(data)
            elif item.item_type == 'indicator':
                context['indicators'].append(data)
        
        return context
    
    async def _generate_suggestions_with_llm(
        self,
        question: str,
        analysis: str,
        graph_context: dict
    ) -> list[dict]:
        """LLM으로 탐험 제안 생성 (v4.2-lite는 LLM 기반)"""
        
        related_stocks = graph_context.get('related_stocks', [])
        
        if not related_stocks:
            return []
        
        prompt = f"""
당신은 투자 분석 가이드입니다.
방금 사용자에게 분석을 제공했고, 다음 탐험을 제안해야 합니다.

[분석 요약]
{analysis[:500]}...

[관련 종목들 (그래프에서 발견)]
{json.dumps(related_stocks, ensure_ascii=False)}

위 정보를 바탕으로 사용자가 다음으로 살펴볼 만한 종목 1-2개를 제안하세요.
각 제안에 "왜 이 종목이 흥미로운지" 이유도 함께 설명하세요.

JSON 형식으로 응답:
[
  {{"symbol": "TSM", "name": "TSMC", "reason": "AAPL의 핵심 칩 공급업체로..."}}
]
"""
        
        response = await self.llm_service.call_simple(prompt, max_tokens=300)
        
        try:
            return json.loads(response)
        except:
            return []
    
    def _extract_entities_simple(self, basket: DataBasket) -> list[str]:
        """바구니에서 종목 심볼 추출 (단순)"""
        
        entities = []
        for item in basket.items.filter(item_type='stock'):
            entities.append(item.reference_id)
        return entities
    
    def _build_messages(
        self, 
        question: str, 
        context: str,
        session: AnalysisSession
    ) -> list[dict]:
        """LLM 메시지 구성"""
        
        system_prompt = f"""
당신은 Stock-Vis의 AI 투자 분석 비서입니다.

## 역할
- 객관적이고 데이터 기반의 투자 분석 제공
- 투자 개념을 쉽게 설명

## 중요 규칙
{DATE_DISPLAY_RULES}

## 면책조항
분석 마지막에 반드시 포함:
"※ 본 분석은 정보 제공 목적이며, 투자 조언이 아닙니다."
"""
        
        return [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"[데이터]\n{context}\n\n[질문]\n{question}"}
        ]
```

### 4.5 Neo4j 서비스 (최소)

```python
# rag_analysis/services/neo4j_service_lite.py

"""
v4.2-lite Neo4j 서비스
- 최소한의 그래프 컨텍스트 수집
- 캐시 기능 없음 (v4.2-core에서 추가)
"""

class Neo4jServiceLite:
    """v4.2-lite용 간소화된 Neo4j 서비스"""
    
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    
    async def get_simple_context(
        self, 
        entities: list[str]
    ) -> dict:
        """
        단순한 그래프 컨텍스트 수집
        
        v4.2-lite: 쿼리 분리 (ChatGPT 피드백 반영)
        """
        
        async with self.driver.session() as session:
            # 쿼리 분리 → 병렬 실행 가능하지만 lite에서는 순차
            supply_chain = await self._get_supply_chain(session, entities)
            sector_peers = await self._get_sector_peers(session, entities)
            
            return {
                'related_stocks': supply_chain + sector_peers,
                'supply_chain': supply_chain,
                'sector_peers': sector_peers,
            }
    
    async def _get_supply_chain(
        self, 
        session, 
        entities: list[str]
    ) -> list[dict]:
        """공급망 관계 종목 조회"""
        
        result = await session.run("""
            MATCH (start:Stock)-[:SUPPLIES|SUPPLIED_BY]-(related:Stock)
            WHERE start.symbol IN $entities
              AND related.symbol <> start.symbol
            RETURN DISTINCT 
                related.symbol as symbol,
                related.name as name,
                'supply_chain' as relationship
            LIMIT 5
        """, entities=entities)
        
        return [dict(r) async for r in result]
    
    async def _get_sector_peers(
        self, 
        session, 
        entities: list[str]
    ) -> list[dict]:
        """동일 섹터 종목 조회"""
        
        result = await session.run("""
            MATCH (start:Stock)-[:IN_SECTOR]->(s:Sector)<-[:IN_SECTOR]-(peer:Stock)
            WHERE start.symbol IN $entities
              AND peer.symbol <> start.symbol
            RETURN DISTINCT 
                peer.symbol as symbol,
                peer.name as name,
                s.name as sector,
                'sector_peer' as relationship
            LIMIT 5
        """, entities=entities)
        
        return [dict(r) async for r in result]
    
    async def save_session(
        self,
        session_id: int,
        entities: list[str],
        previous_session_id: int = None
    ):
        """세션 저장 (단순 버전)"""
        
        async with self.driver.session() as neo_session:
            # 세션 노드 생성
            await neo_session.run("""
                MERGE (s:AnalysisSession {id: $session_id})
                SET s.entities = $entities,
                    s.created_at = datetime()
            """, session_id=session_id, entities=entities)
            
            # 종목 관계 연결
            await neo_session.run("""
                MATCH (s:AnalysisSession {id: $session_id})
                UNWIND $entities as symbol
                MATCH (stock:Stock {symbol: symbol})
                MERGE (s)-[:ANALYZED]->(stock)
            """, session_id=session_id, entities=entities)
            
            # 이전 세션과 연결 (탐험 경로)
            if previous_session_id:
                await neo_session.run("""
                    MATCH (prev:AnalysisSession {id: $prev_id})
                    MATCH (curr:AnalysisSession {id: $curr_id})
                    MERGE (prev)-[:LED_TO]->(curr)
                """, prev_id=previous_session_id, curr_id=session_id)
```

### 4.6 LLM 서비스 (최소)

```python
# rag_analysis/services/llm_service_lite.py

"""
v4.2-lite LLM 서비스
- Claude Sonnet 단일 모델
- 스트리밍 지원
- Multi-Provider는 v4.2-full에서
"""

import anthropic


class LLMServiceLite:
    """v4.2-lite용 간소화된 LLM 서비스"""
    
    def __init__(self):
        self.client = anthropic.AsyncAnthropic()
        self.model = "claude-sonnet-4-20250514"
    
    async def stream(
        self, 
        messages: list[dict],
        max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        """스트리밍 응답"""
        
        async with self.client.messages.stream(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def call_simple(
        self, 
        prompt: str, 
        max_tokens: int = 500
    ) -> str:
        """단순 호출 (탐험 제안 등)"""
        
        response = await self.client.messages.create(
            model=self.model,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=max_tokens,
        )
        
        return response.content[0].text
```

### 4.7 API 엔드포인트 (최소)

```python
# rag_analysis/views_lite.py

from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import StreamingHttpResponse
import json


class BasketViewSet(viewsets.ModelViewSet):
    """바구니 CRUD"""
    
    serializer_class = DataBasketSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DataBasket.objects.filter(user=self.request.user)


class SessionCreateView(APIView):
    """세션 생성"""
    
    def post(self, request):
        basket_id = request.data.get('basket_id')
        basket = get_object_or_404(DataBasket, id=basket_id, user=request.user)
        
        session = AnalysisSession.objects.create(
            user=request.user,
            basket=basket,
            starting_entity=request.data.get('starting_entity'),
            persona=request.data.get('persona', 'general'),
        )
        
        return Response({
            'session_id': session.id,
            'basket_id': basket.id,
        })


class AnalysisStreamView(APIView):
    """스트리밍 분석"""
    
    def post(self, request, session_id):
        session = get_object_or_404(
            AnalysisSession, 
            id=session_id, 
            user=request.user
        )
        question = request.data.get('message')
        
        pipeline = AnalysisPipelineLite()
        
        def event_stream():
            async def async_stream():
                async for event in pipeline.analyze(session, question):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # async to sync wrapper
            import asyncio
            loop = asyncio.new_event_loop()
            
            async_gen = async_stream()
            while True:
                try:
                    event = loop.run_until_complete(async_gen.__anext__())
                    yield event
                except StopAsyncIteration:
                    break
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        return response
```

### 4.8 v4.2-lite 체크리스트

```markdown
## v4.2-lite 구현 체크리스트 (4주)

### Week 1-2: 기반 인프라
- [ ] Django 모델 생성 (DataBasket, BasketItem, AnalysisSession, AnalysisMessage)
- [ ] DataBasket CRUD API
- [ ] AnalysisSession 생성 API
- [ ] DateAwareContextFormatter 구현
- [ ] 날짜 명시 규칙 문서화

### Week 3: 분석 파이프라인
- [ ] Neo4jServiceLite 구현 (get_simple_context)
- [ ] LLMServiceLite 구현 (stream, call_simple)
- [ ] AnalysisPipelineLite 구현
- [ ] 스트리밍 API 엔드포인트

### Week 4: 탐험 기능 + 테스트
- [ ] LLM 기반 탐험 제안 생성
- [ ] Neo4j 세션 저장
- [ ] 탐험 경로 추적 (LED_TO)
- [ ] 프론트엔드 기본 UI
- [ ] 날짜 표시 컴포넌트
- [ ] E2E 테스트
```

---

## 5. v4.2-core 상세 스펙

### 5.1 목표

> **"Neo4j 캐시 + Smart Re-ranking으로 똑똑한 탐험"**

### 5.2 추가 기능

```python
# v4.2-core 추가 구현 항목

1. Neo4j 세션 캐시
   - 벡터 인덱스 생성
   - find_similar_analysis 구현
   - 캐시 히트 시 빠른 응답

2. Smart Re-ranking
   - 그래프 관계 기반 관련성 점수
   - 토큰 예산 내 최적 선택

3. 병렬 처리
   - asyncio.gather로 독립 작업 병렬화
   - 파이프라인 레이턴시 감소

4. Guard 시스템
   - TokenGuard
   - CostGuard
   - 사용량 로깅

5. Dynamic Policy (DB 기반)
   - SystemConfig 모델
   - Redis 캐싱
   - Django Admin 관리
```

### 5.3 Neo4j 캐시 구현

```python
# rag_analysis/services/neo4j_cache.py (v4.2-core)

class Neo4jSessionCache:
    """Neo4j 기반 세션 캐시"""
    
    SIMILARITY_THRESHOLD = 0.85
    
    async def find_similar_analysis(
        self,
        question: str,
        entities: list[str]
    ) -> Optional[dict]:
        """유사 분석 검색 (벡터 + 그래프)"""
        
        embedding = await self.embedding_service.encode(question)
        
        async with self.driver.session() as session:
            # 벡터 유사도 + 엔티티 매칭 결합
            result = await session.run("""
                // 벡터 유사도 검색
                CALL db.index.vector.queryNodes(
                    'session_question_embedding',
                    5,
                    $embedding
                ) YIELD node, score
                WHERE score >= $threshold
                
                // 분석한 종목 매칭
                OPTIONAL MATCH (node)-[:ANALYZED]->(stock:Stock)
                WHERE stock.symbol IN $entities
                
                WITH node, score, COUNT(stock) as entity_match
                
                // 결합 점수: 벡터 60% + 엔티티 40%
                WITH node, 
                     score * 0.6 + (entity_match * 0.1) as combined_score
                WHERE combined_score >= 0.7
                
                RETURN 
                    node.id as session_id,
                    node.summary as summary,
                    combined_score as score
                ORDER BY combined_score DESC
                LIMIT 1
            """, 
                embedding=embedding,
                threshold=self.SIMILARITY_THRESHOLD,
                entities=entities
            )
            
            record = await result.single()
            
            if record:
                return {
                    'cache_hit': True,
                    'session_id': record['session_id'],
                    'summary': record['summary'],
                    'score': record['score']
                }
            
            return None
```

### 5.4 병렬 처리 파이프라인

```python
# rag_analysis/services/pipeline_core.py (v4.2-core)

class AnalysisPipelineCore:
    """v4.2-core 파이프라인 - 병렬 처리"""
    
    async def analyze(self, session, question):
        # ...
        
        # ===== 병렬 처리 구간 =====
        # 캐시 검색과 그래프 컨텍스트는 의존성 없음
        
        cache_result, graph_context = await asyncio.gather(
            self.neo4j_cache.find_similar_analysis(question, entities),
            self.neo4j_service.get_graph_context(entities),
        )
        
        if cache_result and cache_result.get('cache_hit'):
            yield {
                'phase': 'cache_hit',
                'data': cache_result
            }
            # 캐시 히트면 새 분석 옵션 제공
            return
        
        # ===== Re-ranking =====
        reranked_items = await self.reranker.rerank(
            basket.items.all(),
            question,
            graph_context
        )
        
        # ...이후 LLM 호출...
```

---

## 6. v4.2-full 상세 스펙

### 6.1 목표

> **"Discovery Engine + Multi-Provider로 완성된 탐험"**

### 6.2 추가 기능

```python
# v4.2-full 추가 구현 항목

1. Discovery Engine
   - hidden_connections 발견
   - AI 기반 인사이트 생성
   - graph_highlight 경로

2. Multi-Provider LLM
   - Claude + Gemini
   - Provider별 Prompt Adapter
   - Failover 로직

3. 고급 UX
   - Graph Highlight 시각화
   - 사전 견적 모달
   - 분석 깊이 선택
```

### 6.3 Discovery Engine

```python
# rag_analysis/services/discovery_engine.py (v4.2-full)

class DiscoveryEngine:
    """발견 엔진 - 숨겨진 연결 + 인사이트"""
    
    async def generate_discoveries(
        self,
        entities: list[str],
        analysis: str,
        graph_context: dict
    ) -> dict:
        # 1. 숨겨진 연결 찾기
        hidden = await self._find_hidden_connections(entities, graph_context)
        
        # 2. AI로 자연어 인사이트 생성
        insights = await self._generate_insights(analysis, hidden)
        
        # 3. 그래프 하이라이트 경로
        highlights = self._create_highlights(entities, hidden)
        
        return {
            'discoveries': insights,
            'suggestions': await self._create_suggestions(hidden),
            'graph_highlight': highlights
        }
```

---

## 7. PostgreSQL ↔ Neo4j 동기화

### 7.1 동기화 전략 (수정된 버전)

```
┌─────────────────────────────────────────────────────────────────┐
│          PostgreSQL ↔ Neo4j 동기화 전략 (v4.2.1)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  핵심 원칙: Neo4j에는 "휘발성 데이터" 저장 안 함                │
│                                                                  │
│  ┌─────────────────┐         ┌─────────────────┐                │
│  │   PostgreSQL    │         │     Neo4j       │                │
│  ├─────────────────┤         ├─────────────────┤                │
│  │ Stock           │  ─────▶ │ (:Stock)        │                │
│  │  - symbol ✅    │ 동기화  │  - symbol       │                │
│  │  - name ✅      │         │  - name         │                │
│  │  - sector ✅    │         │  - sector       │                │
│  │  - price ❌     │ 안 함   │                 │                │
│  │  - market_cap ❌│         │                 │                │
│  └─────────────────┘         └─────────────────┘                │
│                                                                  │
│  가격, 시가총액 등 휘발성 데이터는:                              │
│  • PostgreSQL에서 직접 조회                                     │
│  • 날짜와 함께 컨텍스트에 포함                                  │
│  • Neo4j는 순수하게 "관계"만 담당                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 동기화 대상

| 데이터 | PostgreSQL | Neo4j | 동기화 방식 |
|--------|:----------:|:-----:|------------|
| 종목 기본 (symbol, name, sector) | ✅ | ✅ | Signal + Celery |
| 가격 | ✅ | ❌ | 동기화 안 함 |
| 재무제표 | ✅ | ❌ | 동기화 안 함 |
| 공급망 관계 | ❌ | ✅ | Neo4j 전용 |
| 섹터 관계 | ❌ | ✅ | Neo4j 전용 |
| 뉴스 | ✅ | ✅ (id, date만) | Signal + Celery |
| 분석 세션 | ✅ | ✅ (캐시용) | 분석 완료 시 저장 |

### 7.3 동기화 구현

```python
# stocks/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=Stock)
def sync_stock_to_neo4j(sender, instance, created, **kwargs):
    """종목 생성/수정 시 Neo4j 동기화"""
    
    # 동기화 대상: 기본 정보만 (가격 제외)
    sync_data = {
        'symbol': instance.symbol,
        'name': instance.name,
        'sector': instance.sector,
    }
    
    # Celery로 비동기 처리
    sync_stock_to_neo4j_task.delay(sync_data, created)


@receiver(post_delete, sender=Stock)
def delete_stock_from_neo4j(sender, instance, **kwargs):
    """종목 삭제 시 Neo4j에서도 삭제"""
    delete_stock_from_neo4j_task.delay(instance.symbol)


# tasks.py

@shared_task(bind=True, max_retries=3)
def sync_stock_to_neo4j_task(self, sync_data: dict, created: bool):
    """Neo4j 종목 동기화 태스크"""
    
    try:
        with neo4j_driver.session() as session:
            if created:
                session.run("""
                    CREATE (s:Stock {
                        symbol: $symbol,
                        name: $name,
                        sector: $sector
                    })
                """, **sync_data)
            else:
                session.run("""
                    MATCH (s:Stock {symbol: $symbol})
                    SET s.name = $name,
                        s.sector = $sector
                """, **sync_data)
                
    except Exception as e:
        # 재시도
        self.retry(exc=e, countdown=60)
```

---

## 8. 성능 최적화 전략

### 8.1 레이턴시 감소 (Gemini 피드백)

```python
# 병렬 처리 적용 위치

async def analyze(self, session, question):
    # Phase 1: 엔티티 추출 (필수 선행)
    entities = await self._extract_entities(question)
    
    # Phase 2: 병렬 처리 가능 구간
    cache_result, graph_context, basket_context = await asyncio.gather(
        self.cache.find_similar(question, entities),      # Neo4j 캐시
        self.neo4j.get_graph_context(entities),           # 그래프 컨텍스트
        self._build_basket_context(session.basket),       # PostgreSQL
    )
    
    # Phase 3: LLM 호출 (캐시 미스 시)
    # ...
    
    # Phase 4: Discovery는 본문 후 비동기
    yield {'phase': 'analysis_complete', 'content': full_response}
    
    # 본문 끝난 후 Discovery 생성 (별도 yield)
    discoveries = await self.discovery.generate(...)
    yield {'phase': 'discoveries', 'data': discoveries}
```

### 8.2 Neo4j 쿼리 최적화 (ChatGPT 피드백)

```python
# 쿼리 분리로 카티션 곱 방지

async def get_graph_context(self, entities: list[str]) -> dict:
    """분리된 쿼리로 그래프 컨텍스트 수집"""
    
    # 각 쿼리 독립 실행 → 병렬 가능
    supply, peers, news = await asyncio.gather(
        self._get_supply_chain(entities),
        self._get_sector_peers(entities),
        self._get_related_news(entities),
    )
    
    return {
        'supply_chain': supply,
        'sector_peers': peers,
        'related_news': news,
    }

async def _get_supply_chain(self, entities):
    """공급망만 조회 (단순 쿼리)"""
    return await self._run_query("""
        MATCH (s:Stock)-[:SUPPLIES|SUPPLIED_BY]-(r:Stock)
        WHERE s.symbol IN $entities AND r.symbol <> s.symbol
        RETURN DISTINCT r.symbol as symbol, r.name as name
        LIMIT 5
    """, entities=entities)
```

---

## 9. LLM 모델 전략

### 9.1 단계별 모델 전략

```python
# v4.2-lite: 단일 모델 (안정성 우선)
MODEL_CONFIG = {
    'default': 'claude:sonnet'
}

# v4.2-core: 2단계 분리 (비용 최적화 시작)
MODEL_CONFIG = {
    'cheap': 'claude:haiku',      # 엔티티 추출, 요약
    'main': 'claude:sonnet',      # 메인 분석
}

# v4.2-full: Multi-Provider (완전 최적화)
MODEL_CONFIG = {
    'entity_extraction': 'gemini:flash',   # 최저가
    'context_summary': 'gemini:flash',
    'discovery': 'claude:haiku',           # JSON 정확도
    'main_analysis': 'claude:sonnet',      # 품질
    'scenario': 'claude:opus',             # 프리미엄
}
```

### 9.2 비용 예상

| 버전 | 분석 1회 예상 비용 | 월 10,000회 |
|------|-------------------|-------------|
| v4.2-lite (Sonnet만) | ~$0.03 | ~$300 |
| v4.2-core (Haiku+Sonnet) | ~$0.025 | ~$250 |
| v4.2-full (최적화) | ~$0.02 | ~$200 |

---

## 10. 체크리스트

### 10.1 v4.2-lite 완료 기준

```markdown
## v4.2-lite Definition of Done

### 기능
- [ ] 바구니에 종목/재무/뉴스 담기
- [ ] 담은 데이터로 AI 분석 요청
- [ ] 스트리밍 응답
- [ ] 날짜 기준 명시 (모든 수치)
- [ ] LLM 기반 "다음 탐험" 제안 1-2개
- [ ] 탐험 경로 기록

### 기술
- [ ] PostgreSQL 모델 마이그레이션
- [ ] Neo4j 기본 스키마 적용
- [ ] SSE 스트리밍 동작
- [ ] 에러 핸들링 (LLM 실패 시)

### 품질
- [ ] 응답에 항상 날짜 포함 검증
- [ ] 면책조항 포함 검증
- [ ] TTFT 5초 이내
```

### 10.2 공통 주의사항

```markdown
## 모든 버전 공통 주의사항

1. 날짜 명시
   - 모든 가격 데이터: "YYYY-MM-DD 기준"
   - 모든 재무 데이터: "YYYY QN 기준"
   - 모든 뉴스: "YYYY-MM-DD 발행"

2. 면책조항
   - 모든 분석 응답 마지막에 포함
   
3. Neo4j 동기화
   - 가격/시가총액은 Neo4j에 저장 안 함
   - 관계 데이터만 Neo4j 담당

4. 에러 처리
   - Neo4j 연결 실패 → PostgreSQL만으로 분석
   - LLM 실패 → 재시도 3회 후 에러 메시지

5. 로깅
   - 모든 LLM 호출 로깅 (토큰, 비용)
   - 세션별 사용량 추적
```

---

## 📊 최종 요약

```
┌─────────────────────────────────────────────────────────────────┐
│                    v4.2.1 Implementation Guide                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  핵심 변경 (피드백 반영):                                        │
│                                                                  │
│  1. 날짜 기반 데이터 전략                                        │
│     • 실시간 가격 ❌ → 전일 종가 ✅                              │
│     • 모든 수치에 기준일 명시                                    │
│     • PostgreSQL ↔ Neo4j 동기화 부담 제거                       │
│                                                                  │
│  2. 단계적 구현                                                   │
│     • v4.2-lite (4주): 동작하는 탐험                             │
│     • v4.2-core (4주): 똑똑한 탐험                               │
│     • v4.2-full (4주): 완성된 탐험                               │
│                                                                  │
│  3. 성능 최적화                                                   │
│     • Neo4j 쿼리 분리 (카티션 곱 방지)                           │
│     • 병렬 처리 (캐시 + 컨텍스트)                                │
│     • Discovery는 본문 후 비동기                                 │
│                                                                  │
│  4. 데이터 역할 분리                                              │
│     • PostgreSQL: Source of Truth (가격, 재무)                   │
│     • Neo4j: 관계 + 캐시 (가격 저장 안 함)                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*v4.2.1 Implementation Guide - 2025-12-12*