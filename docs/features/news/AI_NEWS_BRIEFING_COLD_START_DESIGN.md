# AI 뉴스 브리핑 - Cold Start 해결 설계 문서

> 작성일: 2026-02-24
> 상태: 설계 완료, 구현 대기

## 1. 배경 및 목적

첫 사용자(포트폴리오/관심종목 없음)가 뉴스 페이지에 접속 시 아무런 맥락 없이 뉴스가 나열되는 "콜드 스타트" 문제를 해결합니다.

**핵심 아이디어**: 매일 Celery Beat으로 수집된 뉴스를 **LLM(Gemini 2.5 Flash)이 분석**하여 "오늘 이 키워드를 주목하세요" + **왜 중요한지 맥락 설명** + 관련 종목을 함께 보여주는 **AI 뉴스 브리핑**을 제공합니다.

기존 `extract_daily_news_keywords` 파이프라인(08:00 EST)을 확장하여 추가 API 호출 없이 구현합니다.

---

## 2. 에러 시나리오 분석 및 대응

### 2.1 LLM 응답 실패 / 파싱 실패 (Critical)

**문제**: Gemini API 오류, rate limit, 또는 응답 JSON 파싱 실패 시 `reason` 필드 없는 키워드 반환

**대응**:
- 기존 `FALLBACK_KEYWORDS`에 기본 `reason` 추가: `{"text": "시장 동향", "reason": "전반적인 시장 흐름을 확인하세요", ...}`
- `_parse_response()`에서 `reason` 필드 없으면 빈 문자열로 기본값 설정 (기존 키워드와 하위 호환)
- Frontend에서 `reason`이 없으면 기존 `KeywordBadge` 스타일로 폴백 표시

### 2.2 데이터 부재 - 뉴스 없음 / 키워드 미생성 (High)

**문제**:
- 08:00 EST 이전에 한국 사용자 접속 → 오늘 키워드 없음
- 주말/공휴일에는 키워드 생성 태스크 자체가 미실행

**대응**: 3단계 날짜 Fallback (SectorPerformance 패턴 `serverless/views.py:860-866` 재사용)
```python
def _get_latest_keywords():
    """최신 완료된 키워드를 가져옴. 오늘 없으면 최근 거래일 데이터로 fallback."""
    today = timezone.now().date()
    kw = DailyNewsKeyword.objects.filter(date=today, status='completed').first()
    if kw:
        return kw, False  # (data, is_fallback)
    # 최근 완료된 키워드로 fallback
    kw = DailyNewsKeyword.objects.filter(status='completed').order_by('-date').first()
    return kw, True if kw else (None, True)
```
Frontend에서 `is_fallback=true`일 때 "2026-02-21(금) 분석 결과 표시 중" 안내

### 2.3 프롬프트 확장 시 토큰 예산 초과 (Medium)

**문제**: `reason` 필드 추가로 출력 토큰 증가. 현재 `MAX_OUTPUT_TOKENS=4000` → 10개 키워드 × (기존 + reason 60자) ≈ 2500~3500 토큰

**대응**:
- `MAX_OUTPUT_TOKENS` 4000 → 6000으로 확장 (Gemini 2.5 Flash는 최대 8192 출력 지원)
- `reason`을 50자 이내로 제한하여 토큰 절약
- 일 1회 실행이므로 Gemini Free 15 RPM / 1500 RPD 한도 영향 없음

### 2.4 JSON 스키마 하위 호환성 (Medium)

**문제**: `DailyNewsKeyword.keywords` JSON에 `reason` 필드 추가 시 기존 데이터에는 `reason` 없음

**대응**:
- JSON 필드는 스키마리스 → 새 필드 추가해도 기존 레코드 문제 없음
- Frontend `DailyKeyword` 타입에 `reason?: string` (optional)로 추가
- 기존 `DailyKeywordCard`는 `reason` 무시하고 동작 (하위 호환)
- 새 `AINewsBriefingCard`에서만 `reason` 활용

### 2.5 Next.js Hydration / Auth 분기 (Medium)

**문제**: 서버 렌더링 시 `user=null` → 클라이언트에서 `user=실제값` → HTML 불일치

**대응**:
- AuthContext(`contexts/AuthContext.tsx:124-131`): `loading=true` 초기값 → `useEffect` 후 `false`
- `loading` 상태에서 스켈레톤 표시로 hydration mismatch 방지
- Portfolio 체크는 `enabled: !!user`로 미인증 시 401 방지

### 2.6 뉴스-키워드 매칭 부정확 (Low)

**문제**: LLM이 생성한 키워드와 실제 뉴스 헤드라인 매칭 시, 단순 텍스트 검색은 부정확할 수 있음

**대응**:
- Post-processing에서 `related_symbols` 기반 매칭 (키워드의 관련 종목이 뉴스 entity에 포함되면 매칭)
- 이 방식이 텍스트 매칭보다 정확하고 이미 NewsEntity 데이터 활용 가능

### 2.7 캐시 일관성 (Low)

**문제**: 키워드 캐시(24시간) 중 새 키워드 생성되면 stale 데이터

**대응**: 기존 `daily_keywords` API(views.py:565)가 이미 `status='completed'`일 때만 24시간 캐시. 새 키워드 생성 시 `update_or_create`로 DB 갱신되고, 다음 캐시 미스 시 자동 반영.

---

## 3. Phase A: AI 뉴스 브리핑 (기존 파이프라인 확장)

### 3.1 Backend - NewsKeywordExtractor 프롬프트 확장

**수정 파일**: `news/services/keyword_extractor.py`

현재 키워드 JSON 구조:
```json
{"text": "AI 반도체 수요", "sentiment": "positive", "related_symbols": ["NVDA", "AMD"], "importance": 0.95}
```

확장된 구조 (**`reason` 필드 추가**):
```json
{
  "text": "AI 반도체 수요",
  "sentiment": "positive",
  "related_symbols": ["NVDA", "AMD", "AVGO"],
  "importance": 0.95,
  "reason": "NVDA 실적 발표 임박, 공급망 전체 주목. TSMC 증설 뉴스도 호재"
}
```

수정 사항:
1. `_build_system_prompt()` (line 196): `reason` 필드 규칙 추가
   ```
   - reason: 이 키워드가 왜 중요한지 투자자 관점에서 1-2문장 설명 (50자 이내)
     예: "NVDA 실적 발표 임박, AI 칩 수요 지속 확인 기대"
     예: "Fed 의사록 공개 예정, 금리 인하 시점 단서 주목"
   ```
2. `_build_system_prompt()`: 출력 형식 예시에 `reason` 포함
3. `MAX_OUTPUT_TOKENS`: 4000 → 6000
4. `_parse_response()` (line 251): `reason` 필드 파싱 추가
   ```python
   validated.append({
       'text': str(kw.get('text', ''))[:15],
       'sentiment': kw.get('sentiment', 'neutral'),
       'related_symbols': kw.get('related_symbols', [])[:3],
       'importance': float(kw.get('importance', 0.5)),
       'reason': str(kw.get('reason', ''))[:80],  # 추가
   })
   ```
5. `FALLBACK_KEYWORDS` (line 42): `reason` 기본값 추가

### 3.2 Backend - MarketFeedService

**새 파일**: `news/services/market_feed.py`

```python
class MarketFeedService:
    """AI 뉴스 브리핑 + 시장 컨텍스트를 조합한 cold start 피드"""

    def get_feed(self) -> dict:
        """
        Returns:
        {
            "date": "2026-02-24",
            "is_fallback": false,
            "fallback_message": null,
            "briefing": {
                "keywords": [
                    {
                        "text": "AI 반도체 수요",
                        "sentiment": "positive",
                        "related_symbols": ["NVDA", "AMD", "AVGO"],
                        "importance": 0.95,
                        "reason": "NVDA 실적 발표 임박, 공급망 전체 주목",
                        "news_count": 12,
                        "headlines": [
                            {"title": "NVIDIA Q4 실적 컨센서스...", "url": "..."},
                            {"title": "TSMC 미국 공장 증설 확정", "url": "..."}
                        ]
                    },
                    ...
                ],
                "total_news_count": 150,
                "llm_model": "gemini-2.5-flash"
            },
            "market_context": {
                "top_sectors": [...],       # SectorPerformance (있으면)
                "hot_movers": [...]         # MarketMover top 5 (있으면)
            }
        }
        """
```

핵심 로직:
1. `DailyNewsKeyword`에서 최신 완료 키워드 조회 (fallback 포함)
2. **Post-processing**: 각 키워드의 `related_symbols`로 실제 뉴스 매칭
   ```python
   for keyword in keywords:
       symbols = keyword.get('related_symbols', [])
       if symbols:
           matching_news = NewsArticle.objects.filter(
               entities__symbol__in=symbols,
               published_at__date=best_date
           ).distinct().order_by('-published_at')[:3]
           keyword['news_count'] = matching_news.count()
           keyword['headlines'] = [
               {'title': n.title, 'url': n.url} for n in matching_news
           ]
   ```
3. `SectorPerformance`, `MarketMover` 조회 (있으면 포함, 없으면 생략)
4. Redis 캐시: `market_feed:{date}`, TTL 10분

**의존 모델**:
- `news.models.DailyNewsKeyword` (models.py:322) - LLM 키워드 + reason
- `news.models.NewsArticle` (models.py:19) + `NewsEntity` - 뉴스-키워드 매칭
- `serverless.models.SectorPerformance` (models.py:516) - 섹터 수익률 (optional)
- `serverless.models.MarketMover` (models.py:4) - 핫 종목 (optional)

### 3.3 Backend - API Endpoint

**수정 파일**: `news/api/views.py`

```python
@action(detail=False, methods=['get'], url_path='market-feed')
def market_feed(self, request):
    """
    GET /api/v1/news/market-feed/
    AI 뉴스 브리핑 + 시장 컨텍스트. AllowAny.
    """
    from news.services.market_feed import MarketFeedService
    service = MarketFeedService()
    data = service.get_feed()
    return Response(data)
```

기존 NewsViewSet에 action 추가. DefaultRouter 자동 등록.

### 3.4 Frontend - Types 확장

**수정 파일**: `frontend/types/news.ts`

```typescript
// 기존 DailyKeyword 확장 (하위 호환)
export interface DailyKeyword {
  text: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  related_symbols: string[];
  importance?: number;
  reason?: string;  // 추가: AI 분석 이유
}

// 새 타입: Market Feed Response
export interface MarketFeedResponse {
  date: string;
  is_fallback: boolean;
  fallback_message: string | null;
  briefing: {
    keywords: BriefingKeyword[];
    total_news_count: number;
    llm_model: string;
  };
  market_context: {
    top_sectors: MarketFeedSector[];
    hot_movers: MarketFeedMover[];
  };
}

export interface BriefingKeyword extends DailyKeyword {
  news_count: number;
  headlines: { title: string; url: string }[];
}

export interface MarketFeedSector {
  name: string;
  return_pct: number;
  stock_count: number;
}

export interface MarketFeedMover {
  symbol: string;
  company_name: string;
  change_percent: number;
  sector: string;
}
```

### 3.5 Frontend - Service + Hook

**수정 파일**: `frontend/services/newsService.ts`
```typescript
getMarketFeed(): Promise<MarketFeedResponse> {
  return fetch(`${API_URL}/news/market-feed/`).then(r => r.json());
}
```

**수정 파일**: `frontend/hooks/useNews.ts`
```typescript
export function useMarketFeed() {
  return useQuery<MarketFeedResponse>({
    queryKey: ['market-feed'],
    queryFn: () => newsService.getMarketFeed(),
    staleTime: 1000 * 60 * 10,  // 10분
    retry: 2,
  });
}
```

### 3.6 Frontend - AINewsBriefingCard 컴포넌트

**새 파일**: `frontend/components/news/AINewsBriefingCard.tsx`

DailyKeywordCard 패턴 참조 (`components/news/DailyKeywordCard.tsx`):

```
+------------------------------------------+
| AI가 분석한 오늘의 뉴스 키워드            |
|    2026-02-24 | 분석 뉴스 150건          |
|    (!) 2026-02-21 분석 결과 (fallback)   |
+------------------------------------------+
|                                          |
|  1. AI 반도체 수요 [========  ] 긍정     |
|     NVDA 실적 발표 임박, 공급망 전체     |
|     주목. TSMC 증설 뉴스도 호재         |
|     관련: NVDA, AMD, AVGO  뉴스 12건    |
|     +- NVIDIA Q4 실적 컨센서스 상회 전망 |
|     +- TSMC 미국 공장 증설 확정          |
|     +- AMD, MI300X 수주 급증 보도        |
|     [이 키워드 추적하기]                  |
|                                          |
|  2. 금리 인하 기대 [======    ] 중립     |
|     Fed 의사록 공개 예정, 시장은         |
|     6월 인하 가능성에 주목               |
|     관련: JPM, GS, BAC  뉴스 8건        |
|     +- Fed 2월 의사록, 비둘기파 신호?    |
|     +- 10년물 국채 수익률 4.2%로 하락    |
|     [이 키워드 추적하기]                  |
|                                          |
|  -- 시장 컨텍스트 --                     |
|  상위 섹터: [Tech +2.5%] [Health +1.2%] |
|  핫 종목: NVDA +5.2%, TSLA +3.1%        |
|                                          |
|     gemini-2.5-flash                     |
+------------------------------------------+
```

각 키워드 항목:
- **importance 바**: 중요도에 비례하는 프로그레스 바 (색상: 긍정=초록, 부정=빨강, 중립=노랑)
- **reason**: `reason` 필드를 1-2줄로 표시
- **관련 종목**: 심볼 칩 (클릭 -> `/stocks/{symbol}`)
- **뉴스 건수**: `news_count` 배지
- **대표 헤드라인**: `headlines` 최대 3건 (접기/펼치기)
- **"이 키워드 추적하기"**: Phase B에서 UserInterest 연결 (Phase A에서는 `disabled` or 로그인 유도)

**Empty State**: 키워드 전혀 없을 때 "시장 데이터가 다음 거래일 이후 제공됩니다" 메시지

### 3.7 Frontend - News 페이지 통합

**수정 파일**: `frontend/app/news/page.tsx`

```tsx
import AINewsBriefingCard from '@/components/news/AINewsBriefingCard';
import { useAuth } from '@/contexts/AuthContext';

// NewsPage 내부
const { user, loading: authLoading } = useAuth();

// 미인증/콜드스타트: AINewsBriefingCard (풀 너비)
// 기존 사용자: DailyKeywordCard + NewsHighlightedStocks (현행 유지)
```

### 3.8 기존 DailyKeywordCard reason 툴팁

**수정 파일**: `frontend/components/news/DailyKeywordCard.tsx`

기존 `DailyKeywordCard`에도 `reason`이 있으면 hover 시 팝오버로 표시. 기존 UI 레이아웃 변경 없음.

---

## 4. Phase B: Interest-Based Quick Setup (관심 테마 선택)

### 4.1 Backend - UserInterest 모델

**수정 파일**: `users/models.py`

```python
class UserInterest(models.Model):
    """사용자 관심 테마 (뉴스 개인화용)"""
    INTEREST_TYPE_CHOICES = [
        ('sector', 'Sector'),
        ('theme', 'Theme'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interests')
    interest_type = models.CharField(max_length=20, choices=INTEREST_TYPE_CHOICES)
    value = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    auto_category_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_interest'
        unique_together = ('user', 'interest_type', 'value')
```

### 4.2 Backend - InterestOptionsService + API

**새 파일**: `news/services/interest_options.py`

8개 사전 정의 테마 (`category_generator.py:87` THEME_KEYWORDS 기반):

| ID | 이름 | 아이콘 | 대표 종목 |
|----|------|--------|----------|
| ai_semiconductor | AI & 반도체 | cpu | NVDA, AMD, INTC, AVGO, QCOM |
| ev_battery | 전기차 & 배터리 | battery-charging | TSLA, RIVN, F, GM, LI |
| cloud_saas | 클라우드 & SaaS | cloud | AMZN, MSFT, GOOG, CRM, SNOW |
| biotech_pharma | 바이오 & 제약 | dna | JNJ, PFE, UNH, ABBV, LLY |
| fintech | 핀테크 & 결제 | credit-card | V, MA, SQ, PYPL, COIN |
| clean_energy | 클린에너지 | leaf | ENPH, SEDG, NEE, FSLR, RUN |
| gaming_metaverse | 게임 & 메타버스 | gamepad-2 | RBLX, TTWO, EA, NFLX, META |
| cybersecurity | 사이버보안 | shield-check | CRWD, PANW, FTNT, ZS, S |

+ SP500Constituent distinct sector (11개 GICS 섹터) 동적 포함.

### 4.3 Backend - User Interests CRUD + Category 연결

**수정 파일**: `users/views.py`, `users/urls.py`
- `POST /api/v1/users/interests/` (bulk create)
- `GET /api/v1/users/interests/`
- `DELETE /api/v1/users/interests/{id}/`

관심사 저장 시 `NewsCollectionCategory` 자동 연결 (`get_or_create()` 패턴으로 중복 방지).

### 4.4 Backend - PersonalizedFeedService

**새 파일**: `news/services/personalized_feed.py`

우선순위 캐스케이드:
1. 포트폴리오 심볼 -> 해당 종목 뉴스 (최대 8건)
2. 관심종목 심볼 -> 해당 종목 뉴스 (최대 6건)
3. 명시적 관심사 -> NewsCollectionCategory -> resolve_symbols() -> 뉴스 (최대 6건)
4. Fallback -> MarketFeedService.get_feed()

### 4.5 Frontend - 온보딩 컴포넌트

**새 파일**: `frontend/components/news/InterestSelector.tsx` - 테마 카드 그리드
**새 파일**: `frontend/components/news/OnboardingBanner.tsx` - 배너 + CTA

AINewsBriefingCard의 "이 키워드 추적하기" 버튼과 연결:
- 미인증 -> "로그인하고 맞춤 뉴스 받기" 안내
- 인증 -> UserInterest에 저장 + NewsCollectionCategory 자동 생성

---

## 5. Phase C: Progressive Personalization (별도 이슈)

> Phase A, B 완성 후 진행. 설계만 기록.

- UserBehaviorSignal 모델 (stock_view, news_click, keyword_click)
- fire-and-forget POST `/api/v1/users/signals/`
- PersonalizationEngine: 30일 행동 분석 -> 관심사 추론
- Celery 주간 분석 태스크

---

## 6. 구현 순서

| # | Phase | 작업 | 파일 | 소요 |
|---|-------|------|------|------|
| 1 | A | 프롬프트 확장 (reason 필드) | `news/services/keyword_extractor.py` (수정) | 2h |
| 2 | A | MarketFeedService (브리핑 + 뉴스 매칭 + 시장 컨텍스트) | `news/services/market_feed.py` (신규) | 4h |
| 3 | A | market-feed API endpoint | `news/api/views.py` (수정) | 1h |
| 4 | A | Frontend types 확장 | `frontend/types/news.ts` (수정) | 1h |
| 5 | A | Frontend service + hook | `frontend/services/newsService.ts`, `frontend/hooks/useNews.ts` (수정) | 1h |
| 6 | A | AINewsBriefingCard 컴포넌트 | `frontend/components/news/AINewsBriefingCard.tsx` (신규) | 5h |
| 7 | A | News 페이지 통합 (조건부 렌더링) | `frontend/app/news/page.tsx` (수정) | 2h |
| 8 | A | 기존 DailyKeywordCard reason 툴팁 | `frontend/components/news/DailyKeywordCard.tsx` (수정) | 1h |
| 9 | A | 테스트 | `tests/news/test_market_feed.py` (신규) | 2h |
| 10 | B | UserInterest 모델 + migration | `users/models.py` (수정) | 2h |
| 11 | B | InterestOptionsService + API | `news/services/interest_options.py` (신규), `news/api/views.py` | 4h |
| 12 | B | User interests CRUD + Category 연결 | `users/views.py`, `users/urls.py` (수정) | 3h |
| 13 | B | PersonalizedFeedService | `news/services/personalized_feed.py` (신규) | 4h |
| 14 | B | InterestSelector + OnboardingBanner | `frontend/components/news/` (신규 2개) | 6h |
| 15 | B | 온보딩 통합 | `frontend/app/news/page.tsx` (수정) | 3h |

**Phase A: ~19h | Phase B: ~22h | Phase C: ~17h (별도)**

---

## 7. 핵심 설계 결정

1. **기존 파이프라인 확장** - `extract_daily_news_keywords` (08:00 EST) 프롬프트에 `reason` 필드만 추가. 별도 태스크/API 호출 불필요.
2. **Post-processing 뉴스 매칭** - LLM이 생성한 `related_symbols`로 실제 뉴스를 매칭하여 `news_count` + `headlines` 추가. LLM에게 뉴스 카운팅을 맡기지 않음 (팩트 기반).
3. **하위 호환** - `DailyNewsKeyword.keywords` JSON에 `reason` 추가해도 기존 레코드/컴포넌트 영향 없음. `DailyKeyword` 타입에 `reason?: string` (optional).
4. **콜드스타트 = AI 브리핑** - 미인증/신규 사용자에게 `AINewsBriefingCard` (풍부한 분석), 기존 사용자에게 `DailyKeywordCard` (간결한 뱃지). 동일 데이터 소스, 다른 UI.
5. **3단계 Fallback** - 오늘 키워드 -> 최근 거래일 키워드 -> empty state. 어떤 경우든 빈 화면 없음.

---

## 8. 검증 방법

### Phase A
1. **프롬프트 테스트**: Celery에서 `extract_daily_news_keywords.delay(force=True)` 실행 -> DB에서 `reason` 필드 포함된 키워드 확인
2. **API 테스트**: `curl localhost:8000/api/v1/news/market-feed/` -> `briefing.keywords[0].reason` 존재 확인
3. **Fallback 테스트**: DailyNewsKeyword 없는 날짜로 API 호출 -> `is_fallback=true` 확인
4. **Backend 단위 테스트**: `pytest tests/news/test_market_feed.py`
   - 키워드 있을 때 정상 응답 (reason + headlines)
   - 키워드 없을 때 fallback 응답
   - 뉴스 매칭 로직 (related_symbols -> headlines)
5. **Frontend 확인**: 미인증 상태로 `localhost:3000/news` -> AINewsBriefingCard 표시
6. **Chrome 브라우저**: MCP 도구로 시각적 검증

### Phase B
7. **User interests CRUD 테스트**: `pytest tests/users/test_user_interests.py`
8. **E2E**: 회원가입 -> 뉴스 페이지 -> 온보딩 -> 관심사 선택 -> 개인화 피드
