# Watchlist 기능 스펙 (v1.0)

## 목차
1. [개요](#개요)
2. [핵심 사용자 시나리오](#핵심-사용자-시나리오)
3. [데이터 요구사항](#데이터-요구사항)
4. [API 엔드포인트](#api-엔드포인트)
5. [사용자 플로우](#사용자-플로우)
6. [우선순위 및 페이징](#우선순위-및-페이징)
7. [기술 제약사항](#기술-제약사항)

---

## 개요

### 정의
Watchlist는 사용자가 **관심있는 종목들을 모아서 한눈에 모니터링**하는 화면입니다.
- Portfolio(보유종목)와는 다름: 관심만 표시, 실제 소유 여부 상관없음
- 실시간 변동성 감시, 진입 기회 포착, 경쟁사 모니터링 등 다양한 목적 지원

### 핵심 가치
```
"관심종목을 체계적으로 추적하고,
 포트폴리오의 경쟁사/관련 종목과의 관계를 파악해서
 더 나은 투자 결정을 내린다"
```

### 차별화 포인트: Stock-Vis 관계 그래프 연동
- **경쟁사 자동 추가**: Portfolio의 종목 → 같은 업계 경쟁사 추천
- **공급망 추적**: 관련 종목들의 관계를 시각적으로 표현
- **예시**: AAPL 보유 → MSFT, GOOGL 자동 추천

---

## 핵심 사용자 시나리오

### Scenario 1: 진입 기회 감시자 (Entry Hunter)
**사용자**: "지금은 못 사지만, 좋은 가격에 떨어지면 사고싶어"

**행동**:
1. AAPL, MSFT, NVDA를 Watchlist에 추가
2. 각 종목별로 목표가(진입가) 설정 예: AAPL $150에 사고 싶음
3. 실시간 가격 모니터링 → 목표가 근처 도달하면 알림 받음
4. 실시간 뉴스/시장 심리 관찰 (일일 변동률, 거래량, 기술적 지표)

**필요 데이터**:
- 실시간 가격 (현재가, 일일 변동률%)
- 목표 진입가 설정 필드
- 진입가와 현재가의 거리 표시 (%)
- 52주 고가/저가 대비 현재 위치 (%)
- 기술적 지표: RSI, MACD (과매도/과매수 판단용)
- 일일 거래량 vs 평균 거래량 비교

**화면 요소**:
```
┌─────────────────────────────────────────────────────┐
│ AAPL | 현재가: $180 | 진입목표: $150 | -16.7% 남음  │
│ 52주 범위: $150 — $200 | 현재위치: [========]      │
│ 일일변동: +2.5% | 거래량: 5.2M (평균 3.8M) | RSI: 42 │
└─────────────────────────────────────────────────────┘
```

---

### Scenario 2: 포트폴리오 컨텍스트 리더 (Context Analyzer)
**사용자**: "내 AAPL 투자가 잘되는지, 경쟁사는 어떨까?"

**행동**:
1. Portfolio에서 AAPL 보유
2. Watchlist 자동으로 경쟁사 추가됨: MSFT, GOOGL, META 등
3. AAPL vs 경쟁사 성과 비교
   - "AAPL은 +5%, MSFT는 +3%, GOOGL은 +8%" → AAPL은 중간 수준
   - 업계 평균 대비 AAPL 위치 파악
4. 관련 부품사 추적 (공급망 위험 관리)
   - 예: AAPL을 위한 반도체 회사 (TSMC, QUALCOMM)

**필요 데이터**:
- 업계/섹터 내 경쟁 순위 정보
- 같은 섹터 종목들의 일일 변동률 비교
- 섹터 평균 대비 개별 종목 성과 (상대강도)
- 관련 회사 관계 정보 (공급사, 고객사, 경쟁사)
- 52주 성과 비교 (누적 수익률 %)

**화면 요소**:
```
┌─────── 포트폴리오 관련 Watchlist ──────────┐
│ 카테고리: 경쟁사 (5개)                     │
│ ┌─────────────────────────────────────┐  │
│ │ MSFT: +3.2% | 섹터평균 대비 -2.1%  │  │
│ │ GOOGL: +8.1% | 섹터평균 대비 +3%   │  │
│ │ META: -1.5% | 섹터평균 대비 -6.6%  │  │
│ └─────────────────────────────────────┘  │
│                                         │
│ 카테고리: 공급망 (3개)                   │
│ ┌─────────────────────────────────────┐  │
│ │ TSMC: +2.5% (반도체 공급사)        │  │
│ │ QCOM: +1.8% (칩셋 공급사)         │  │
│ └─────────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

### Scenario 3: 섹터 전략가 (Sector Strategist)
**사용자**: "요즘 기술주가 핫한데, 기술 섹터의 전체 구도를 이해하고 싶어"

**행동**:
1. 기술 섹터 기업 10~15개를 Watchlist에 그룹으로 추가
2. **섹터 대시보드**로 전체 모습 파악
   - 섹터 내 종목별 가격 변동률 히트맵
   - 섹터 평균 대비 상위/하위 5개 기업
   - 월간 성과 추이 (섹터 평균)
3. 섹터 내 강자 vs 약자 전략 수립
   - 강자들은 이미 오른 상태 → 진입 회피
   - 약자 중 펀더멘탈 좋은 것 찾아서 진입 준비

**필요 데이터**:
- 섹터별 분류 (미리 설정)
- 섹터 내 종목 개수, 평균 수익률
- 개별 종목 vs 섹터 평균 성과 비교 (상대강도 지표)
- 일일/주간/월간 성과 추이
- 관심도/변동성 랭킹

**화면 요소**:
```
┌─ Technology Sector Dashboard ────────────────┐
│ 섹터 평균: +4.2% | 추적 종목: 12개        │
│                                             │
│ 가격 변동률 히트맵:                        │
│ ┌──────────┬──────────┬──────────┐        │
│ │ NVDA +15%│ MSFT +8% │ GOOGL +7%│  🔴    │
│ │ AAPL +2% │ META -2% │ AMD +3%  │  🟢    │
│ └──────────┴──────────┴──────────┘        │
│                                             │
│ 상위 5개: NVDA(+15%), MSFT(+8%), ...      │
│ 하위 5개: META(-2%), INTC(-1%), ...       │
└─────────────────────────────────────────────┘
```

---

## 데이터 요구사항

### Phase 1 (MVP): 핵심 기능
| 데이터 항목 | 출처 | 갱신 빈도 | 용도 | 우선순위 |
|----------|-----|---------|------|--------|
| **현재가** | Alpha Vantage | 실시간 | 실시간 모니터링 | P0 |
| **일일 변동률(%)** | Alpha Vantage | 실시간 | 수익성 판단 | P0 |
| **거래량** | Alpha Vantage | 일일 | 기술적 분석 | P0 |
| **52주 고가/저가** | Alpha Vantage | 주간 | 가격 범위 분석 | P1 |
| **기술적 지표 (RSI, MACD)** | 자체 계산 | 일일 | 진입/매도 신호 | P1 |
| **실시간 뉴스 헤드라인** | NewsAPI | 일일 | 시장 심리 파악 | P2 |
| **섹터/산업 분류** | Alpha Vantage | 월간 | 그룹핑 | P1 |
| **목표가 (사용자 설정)** | 로컬 DB | 업데이트 시 | 진입 기회 감시 | P1 |

### Phase 2 (Future): 고급 기능
| 데이터 항목 | 출처 | 갱신 빈도 | 용도 |
|----------|-----|---------|------|
| **관계 그래프 (경쟁사/공급사)** | 수동/AI | 월간 | 포트폴리오 컨텍스트 |
| **섹터 평균 수익률** | 자체 계산 | 일일 | 상대강도 분석 |
| **컨센서스 추천등급** | Yahoo Finance | 주간 | 애널리스트 의견 |
| **공급망 정보** | DBpia/전문지 | 분기 | 관련 기업 추적 |
| **AI 진입/매도 신호** | ML 모델 | 일일 | 스마트 알림 |

---

## API 엔드포인트

### Watchlist 기본 CRUD
```
POST   /api/v1/users/watchlist/
       # 새 Watchlist 생성 (사용자당 1개 기본, 여러 개 가능)
       # Request: { name: "진입준비", description: "..." }

GET    /api/v1/users/watchlist/
       # 사용자의 모든 Watchlist 조회

GET    /api/v1/users/watchlist/{watchlist_id}/
       # 특정 Watchlist 상세 조회
       # Response: { id, name, stocks: [...], created_at, updated_at }

PATCH  /api/v1/users/watchlist/{watchlist_id}/
       # Watchlist 정보 수정 (이름, 설명)

DELETE /api/v1/users/watchlist/{watchlist_id}/
       # Watchlist 삭제
```

### Watchlist 종목 관리
```
POST   /api/v1/users/watchlist/{watchlist_id}/add-stock/
       # 종목 추가
       # Request: { symbol: "AAPL", target_entry_price: 150 }
       # Response: { symbol, added_at, position_in_list: 5 }

DELETE /api/v1/users/watchlist/{watchlist_id}/stocks/{symbol}/
       # 종목 제거

PATCH  /api/v1/users/watchlist/{watchlist_id}/stocks/{symbol}/
       # 종목 설정 수정 (목표가 등)
       # Request: { target_entry_price: 150, notes: "..." }

GET    /api/v1/users/watchlist/{watchlist_id}/stocks/
       # Watchlist 종목 상세 조회 (실시간 가격 포함)
       # Query params: ?sort=change_percent&order=desc
       # Response: [{
       #   symbol, stock_name, sector, industry,
       #   current_price, daily_change_percent,
       #   target_entry_price, distance_to_target,
       #   rsi, macd_signal, volume_vs_avg,
       #   52w_high, 52w_low, position_in_52w
       # }, ...]
```

### 관계 그래프 연동 (Phase 2)
```
GET    /api/v1/users/watchlist/recommended-competitors/
       # Portfolio의 종목들과 경쟁사 추천
       # Response: {
       #   portfolio_symbols: ["AAPL"],
       #   competitors: [
       #     { symbol: "MSFT", sector: "Technology", ... },
       #     { symbol: "GOOGL", sector: "Technology", ... }
       #   ]
       # }

POST   /api/v1/users/watchlist/{watchlist_id}/add-related/
       # 관련 종목 자동 추가 (경쟁사, 공급사 등)
       # Request: { base_symbol: "AAPL", relationship_type: "competitors" }
```

### 섹터 대시보드 (Phase 2)
```
GET    /api/v1/analysis/sector-dashboard/{sector}/
       # 섹터 전체 분석 대시보드
       # Response: {
       #   sector: "Technology",
       #   total_stocks: 15,
       #   sector_average_return: 4.2,
       #   top_performers: [...],
       #   bottom_performers: [...],
       #   heatmap_data: {...}
       # }
```

### 알림 설정 (Phase 2)
```
POST   /api/v1/users/watchlist/{watchlist_id}/alerts/
       # 가격 알림 설정
       # Request: {
       #   symbol: "AAPL",
       #   alert_type: "target_reached",  # or "percentage_change"
       #   threshold: 150  # 목표가 또는 변동률
       # }

GET    /api/v1/users/watchlist/{watchlist_id}/alerts/
       # 설정된 알림 조회
```

---

## 사용자 플로우

### 플로우 1: Watchlist 생성 및 종목 추가
```
사용자 액션                          시스템 응답
────────────────────────────────────────────────
[Watchlist 탭 클릭]
                    → Watchlist 리스트 표시
                    → "새로운 Watchlist" 버튼

["새로운 Watchlist" 클릭]
                    → 모달 열기 (이름, 설명 입력)

["생성" 버튼 클릭]
                    → POST /api/v1/users/watchlist/
                    → 새 Watchlist 생성됨

[종목 검색 & 추가 (AAPL)]
                    → 자동완성: AAPL 추천
                    → POST /api/v1/users/watchlist/1/add-stock/
                    → 종목 추가됨

[목표가 입력 ($150)]
                    → PATCH /api/v1/users/watchlist/1/stocks/AAPL/
                    → 저장됨

[실시간 가격 모니터링]
                    → WebSocket 또는 1초 폴링
                    → "현재가: $180, 진입까지 -$30"
```

### 플로우 2: Portfolio → Watchlist 자동 연동 (Phase 2)
```
사용자가 Portfolio에 AAPL 추가
                    → 백그라운드: 경쟁사 추천 쿼리
                    → Watchlist 자동 생성 (선택적)
                    → "관련 종목을 Watchlist에 추가했습니다"
                    → MSFT, GOOGL, META 추가 (사용자 확인)
```

---

## 우선순위 및 페이징

### MVP (Phase 1: v1.0)
**목표**: 기본 관심종목 추적 기능 제공

- Watchlist 기본 CRUD
- 종목 추가/제거/목표가 설정
- 실시간 가격 및 일일 변동률 표시
- 기술적 지표 기본 (RSI, MACD)
- 단순 리스트 뷰

**예상 구현 시간**: 2-3주
**API Rate Limit 영향**: 낮음 (종목당 1회/일 호출)

### Phase 2 (v1.1~v1.3)
**목표**: 포트폴리오 컨텍스트 & 섹터 분석

**우선순위별**:
1. **P2-A**: 포트폴리오 경쟁사 자동 추가 (1주)
2. **P2-B**: 섹터 대시보드 (1.5주)
3. **P2-C**: 실시간 뉴스 인테그레이션 (2주)
4. **P2-D**: AI 기반 알림 (3주)

### Phase 3 (v2.0)
**목표**: 고급 분석 및 AI 추천

- 공급망 시각화
- 머신러닝 기반 진입/매도 신호
- 포트폴리오 최적화 제안

---

## 기술 제약사항

### Alpha Vantage API 무료 티어 제약
```
제약: 5 calls/분, 500 calls/일, 12초 간격 필수

영향:
- Watchlist 종목 10개 추가 시: 120초 소요
- 실시간 모니터링 위해 yfinance 병행 추천
- 기술적 지표는 자체 계산 (API 호출 절약)

해결책:
1. yfinance 추가 활용 (Rate limit 없음)
   - 실시간 가격 조회용
   - 기술적 지표 계산용

2. Redis 캐싱
   - 같은 종목 반복 조회 시 1분 캐시
   - 종목당 일일 1회만 Alpha Vantage 호출

3. 배치 처리
   - 밤 10시~새벽 2시에 일괄 업데이트
   - 실시간이 필요한 데이터만 WebSocket/폴링
```

### 데이터베이스 설계

**새 모델**:
```python
class Watchlist(models.Model):
    """사용자의 관심종목 리스트"""
    user = ForeignKey(User)
    name = CharField(max_length=100)  # "진입준비", "경쟁사 추적" 등
    description = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class WatchlistItem(models.Model):
    """Watchlist에 포함된 개별 종목"""
    watchlist = ForeignKey(Watchlist, CASCADE, related_name='items')
    stock = ForeignKey(Stock, CASCADE, to_field='symbol')

    # 사용자 설정
    target_entry_price = DecimalField(blank=True, null=True)
    notes = TextField(blank=True)

    # 메타데이터
    added_at = DateTimeField(auto_now_add=True)
    last_updated = DateTimeField(auto_now=True)
    position_order = IntegerField()  # 드래그 정렬용

    class Meta:
        unique_together = ('watchlist', 'stock')

class WatchlistAlert(models.Model):
    """가격 알림 설정 (Phase 2)"""
    watchlist_item = ForeignKey(WatchlistItem, CASCADE)
    alert_type = CharField(choices=[
        ('target_reached', '목표가 도달'),
        ('percentage_change', '변동률'),
        ('volume_spike', '거래량 급증'),
    ])
    threshold = DecimalField()
    is_active = BooleanField(default=True)
```

### 성능 최적화
1. **쿼리 최적화**
   - `select_related('stock')` 사용
   - Watchlist 조회 시 종목 정보 한 번에 로드

2. **캐싱 전략**
   - 종목 가격 데이터: Redis 1분 캐시
   - 기술적 지표: 일일 재계산

3. **실시간 업데이트**
   - WebSocket 또는 1초 폴링 (자동갱신 토글)
   - 백그라운드 태스크로 일괄 업데이트

---

## 고려사항

### 사용자 경험
1. **첫 시작 시 서툰 경험 방지**
   - 추천 기본 Watchlist ("인기 종목", "기술주")
   - 1-Click 추가 (이미 조회한 종목 제안)

2. **모바일 최적화**
   - 좌우 스와이프로 Watchlist 전환
   - 세로 정렬로 화면 공간 최대화

3. **정보 과부하 방지**
   - 기본 뷰: 현재가, 일일변동률만 표시
   - 상세 뷰: 기술적 지표, 뉴스 등 추가 정보

### 법적/윤리적 고려
1. **투자 조언 아님 명시**
   - Watchlist = 개인 추적용, 매매 신호 아님
   - 면책조항: "본 기능은 참고용이며, 실제 매매 결정은 본인 책임"

2. **개인정보 보호**
   - Watchlist는 사용자 개인 데이터 (공개 안 함)
   - 포트폴리오와 달리 사회적 공유 기능 불포함 (v1.0)

---

## 마이그레이션 계획

### v1.0 출시
```bash
# 1. 모델 생성 및 마이그레이션
python manage.py makemigrations users
python manage.py migrate

# 2. API 엔드포인트 구현
# - users/views.py: WatchlistViewSet 추가
# - users/serializers.py: WatchlistSerializer 추가

# 3. Frontend 구현
# - pages/watchlist/index.tsx: 리스트 화면
# - components/watchlist/WatchlistCard.tsx: 카드 컴포넌트
```

### v1.1 출시 (경쟁사 자동 추가)
```bash
# 1. 관계 그래프 데이터 확보
#    - Stock 모델에 competitor_ids, supplier_ids 필드 추가
#    - 수동 또는 외부 API 연동

# 2. 추천 로직 구현
#    - Stock.get_competitors() 메서드 추가
#    - Portfolio → Watchlist 자동 연동 로직

# 3. API 엔드포인트 추가
#    - GET /api/v1/users/watchlist/recommended-competitors/
```

---

## 성공 지표 (KPI)

### Phase 1 (MVP)
- 활성 사용자 중 50% 이상이 최소 1개 Watchlist 생성
- 평균 Watchlist 당 5개 종목 추적
- 일일 평균 방문 시간 3분 이상

### Phase 2+
- 포트폴리오 보유 사용자의 80% 이상이 경쟁사 Watchlist 사용
- 알림 기반 진입 거래율 15% 이상 달성
- 사용자 만족도(NPS) 7 이상

---

## 참고자료

### 유사 기능 벤치마크
- **Yahoo Finance**: My Watchlist (기본 가격 모니터링)
- **TD Ameritrade**: Watchlist (고급 필터링, 알림)
- **eToro**: Watchlist (포트폴리오 비교)

### 기술 스택
- **Backend**: Django DRF, Redis (캐싱), Celery (배치)
- **Frontend**: React Query (데이터 페칭), Zustand (상태 관리)
- **Real-time**: WebSocket (선택) 또는 1초 폴링
- **External APIs**: Alpha Vantage (가격), yfinance (기술지표)
