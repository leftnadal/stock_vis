# Stock-Vis Screener Next-Phase Upgrade Plan

## Executive Summary

경쟁사(Finviz, TradingView, Investing.com) 벤치마킹을 기반으로 Stock-Vis만의 차별화된 스크리너 업그레이드 전략을 수립한다.

**핵심 차별화**: "Chain Sight DNA" - 연결된 발견 시스템

---

## Part 1: 경쟁사 비교 분석

| Feature | Finviz | TradingView | Investing.com | **Stock-Vis (현재)** | **Stock-Vis (계획)** |
|---------|--------|-------------|---------------|---------------------|---------------------|
| AI 인사이트 | X | X | Pro (유료) | **3개 키워드/종목** | **5+ 키워드 + 투자테제** |
| 프리셋 결합 | X | X | X | **3개 캐스케이딩** | **3개 + DNA 체인** |
| 한국어 UI | X | X | X | **완전 지원** | **KR ETF 매핑 추가** |
| 커스텀 지표 | 기본 | Pine Script | X | **5개 MM 지표** | **8+ 지표** |
| 실시간 알림 | Elite만 | Yes | 제한적 | Graph Anomaly만 | **전체 스크리너 알림** |
| 차트 패턴 | Yes | Yes | X | X | **Phase 3** |
| 모바일 | X | App | App | 웹만 | **PWA** |
| CSV 내보내기 | Elite | Yes | Yes | X | **Yes** |

### 경쟁사 강점
- **Finviz**: 60+ 필터, 차트 패턴 인식, Elite 실시간
- **TradingView**: Pine Script 커스텀 지표, 멀티타임프레임, 글로벌
- **Investing.com**: 사전정의 스크리너, URL 공유, Pro AI 전략

### Stock-Vis 고유 강점 (활용 필요)
1. **AI 키워드**: LLM 기반 종목별 인사이트 (경쟁사 무료 버전에 없음)
2. **5개 Market Movers 지표**: RVOL, Trend Strength, Sector Alpha, ETF Sync Rate, Volatility %ile
3. **캐스케이딩 프리셋**: 최대 3개 프리셋 교집합 결합
4. **한국어 완전 지원**: 한국 투자자 타겟

---

## Part 2: 차별화 전략 - "Chain Sight DNA"

### 개념

**Chain Sight DNA**는 투자 아이디어를 연결된 DNA 체인으로 취급하여, 하나의 발견이 관련 기회로 이어지는 시스템.

```
사용자 프리셋 선택 → 필터링된 종목
                          ↓
                AI가 결과 패턴 분석
                          ↓
                "관련 DNA" 제안 표시
                          ↓
                사용자가 검색 "진화" 가능
```

### DNA 체인 구성요소
- **Gene Segments** = 개별 필터 조건
- **DNA Strands** = 결합된 프리셋 체인 (최대 3개)
- **Mutations** = AI 감지 이상 패턴
- **Evolution** = 사용자 상호작용으로 성장하는 투자 테제

---

## Part 3: Phase 별 구현 계획

### Phase 1: Foundation (Week 1-4)

**목표**: 핵심 기능 격차 해소 + 인프라 준비

#### 1.1 알림 시스템 (Week 1-2)

**새 모델**: `ScreenerAlert`
```python
class ScreenerAlert(models.Model):
    user = ForeignKey('users.User')
    name = CharField(max_length=100)
    preset = ForeignKey('ScreenerPreset', null=True)
    filters_json = JSONField()
    alert_type = CharField()  # price_target, filter_match, volume_spike, ai_signal
    target_count = IntegerField(null=True)
    is_active = BooleanField(default=True)
    last_triggered_at = DateTimeField(null=True)
    cooldown_hours = IntegerField(default=24)
```

**Celery Task**: 15분마다 활성 알림 체크 (시장 시간)

**수정 파일**:
- `serverless/models.py` - ScreenerAlert, AlertHistory 모델
- `serverless/views.py` - alerts CRUD 엔드포인트
- `serverless/tasks.py` - check_screener_alerts 태스크

#### 1.2 CSV 내보내기 (Week 2)

**엔드포인트**: `POST /api/v1/serverless/screener/export`

**프론트엔드**:
- `components/screener/ExportButton.tsx` - 다운로드 버튼

#### 1.3 고급 필터 패널 (Week 3-4)

**새 컴포넌트**: `AdvancedFilterPanel`

```
┌──────────────────────────────────────────────────────┐
│ 필터 검색: [_______________]                         │
├──────────────────────────────────────────────────────┤
│ [밸류에이션] [수익성] [성장성] [기술적] [배당] [MM]   │
├──────────────────────────────────────────────────────┤
│ PER        [────●────] 5 ~ 20                       │
│ PBR        [────●────] 0.5 ~ 3                      │
│ 섹터       [Technology ▼] [Healthcare ▼]             │
└──────────────────────────────────────────────────────┘
```

**기능**:
- 카테고리별 탭 (Valuation, Profitability, Technical, etc.)
- 슬라이더 + 입력 콤보
- 필터 내 검색
- 인기/최근 필터 상단 표시

**수정 파일**:
- `frontend/components/screener/AdvancedFilterPanel.tsx` (신규)
- `frontend/app/screener/page.tsx` - 패널 통합

#### 1.4 모바일 PWA 최적화 (Week 4)

**변경사항**:
- 테이블 → 모바일 카드 뷰
- 터치 친화적 필터 → Bottom Sheet
- PWA manifest 추가
- 오프라인 프리셋 캐싱

**수정 파일**:
- `frontend/components/screener/MobileStockCard.tsx` (신규)
- `frontend/app/manifest.json` (신규)
- `frontend/app/screener/page.tsx` - 반응형 분기

---

### Phase 2: Differentiation (Week 5-8)

**목표**: 경쟁사에 없는 고유 기능 구현

#### 2.1 프리셋 공유 시스템 (Week 5)

**백엔드**:
- `share_code` 생성 (기존 필드 활용)
- 공개 프리셋 갤러리 (opt-in)
- 인기 프리셋 트래킹

**프론트엔드**:
- 공유 모달 (링크 복사)
- 공유 프리셋 import 페이지
- "트렌딩 프리셋" 섹션

**수정 파일**:
- `serverless/views.py` - share_preset, get_shared 엔드포인트
- `frontend/components/screener/SharePresetModal.tsx` (신규)

#### 2.2 Chain Sight DNA - 관련 종목 (Week 6-7)

**백엔드 서비스**:
```python
# serverless/services/chain_sight_service.py
class ChainSightService:
    def find_related_chains(self, filtered_symbols, filters_applied):
        # 1. 섹터/산업 분석
        sector_peers = self._analyze_sectors(filtered_symbols)
        # 2. 상관관계 종목 (graph_analysis 활용)
        correlated = self._find_correlated(filtered_symbols)
        # 3. 유사 펀더멘탈 프로필
        similar = self._find_fundamentally_similar(filtered_symbols)
        # 4. AI 설명 생성
        return chains_with_reasons
```

**프론트엔드**:
```
┌─────────────────────────────────────────────────────┐
│ 🧬 연관 종목 DNA                                    │
├─────────────────────────────────────────────────────┤
│ 섹터 피어: MSFT, GOOGL, META (+3)                  │
│   "동일 Technology 섹터 고ROE 기업"                 │
├─────────────────────────────────────────────────────┤
│ 상관 종목: NVDA, AMD, AVGO                         │
│   "AAPL과 0.8+ 상관관계"                           │
└─────────────────────────────────────────────────────┘
```

**수정 파일**:
- `serverless/services/chain_sight_service.py` (신규)
- `frontend/components/screener/ChainSightPanel.tsx` (신규)

#### 2.3 투자 테제 빌더 (Week 7-8)

**개념**: 스크리너 결과에서 자동 투자 테제 생성

**백엔드**:
```python
# serverless/services/thesis_builder.py
class ThesisBuilder:
    def build_thesis(self, stocks, filters, user_notes=''):
        # LLM으로 구조화된 투자 테제 생성
        return InvestmentThesis(
            title="저평가 배당 성장주",
            summary="...",
            key_metrics=[...],
            top_picks=stocks[:5],
            risks=[...]
        )
```

**프론트엔드**:
- 테제 카드 (핵심 지표 포함)
- Watchlist 원클릭 저장
- PDF 내보내기
- 익명화 공유

**수정 파일**:
- `serverless/models.py` - InvestmentThesis 모델
- `serverless/services/thesis_builder.py` (신규)
- `frontend/components/screener/ThesisBuilder.tsx` (신규)

#### 2.4 한국 시장 통합 (Week 8)

**한국 투자자 전용 기능**:
- KODEX/TIGER ETF 매핑
- KRX 시장 시간 표시
- 미국-한국 상관관계
- 원화 환산 수익률

**수정 파일**:
- `serverless/services/korea_market_service.py` (신규)

---

### Phase 3: Advanced (Week 9-12)

**목표**: 고급 기능으로 플랫폼 차별화

#### 3.1 실시간 알림 WebSocket (Week 9)

**WebSocket Consumer**:
```python
# serverless/consumers.py
class AlertConsumer(AsyncWebsocketConsumer):
    async def alert_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'screener_alert',
            'alert': event['alert'],
            'matched_stocks': event['matched_stocks']
        }))
```

**프론트엔드**: Toast 알림 UI

#### 3.2 포트폴리오 시뮬레이션 (Week 10)

스크리너 결과로 가상 포트폴리오 시뮬레이션
- 기간별 수익률 (1M, 3M, 6M, 1Y)
- Sharpe Ratio, Max Drawdown
- 동일/시총가중 배분

#### 3.3 차트 패턴 인식 (Week 11-12)

**패턴 감지**: Double Bottom, Head & Shoulders, Cup & Handle 등
**필터 추가**: `pattern` 필터로 패턴 매칭 종목 검색

---

## Part 4: 수정 대상 파일 요약

### Backend (serverless/)
| 파일 | Phase | 변경 내용 |
|------|-------|----------|
| `models.py` | 1, 2 | ScreenerAlert, InvestmentThesis, ChainSight |
| `views.py` | 1, 2 | alerts, export, share, chain-sight 엔드포인트 |
| `tasks.py` | 1 | check_screener_alerts 태스크 |
| `services/chain_sight_service.py` | 2 | 관련 종목 발견 (신규) |
| `services/thesis_builder.py` | 2 | 투자 테제 생성 (신규) |
| `services/korea_market_service.py` | 2 | 한국 시장 통합 (신규) |
| `consumers.py` | 3 | AlertConsumer WebSocket |

### Frontend (frontend/)
| 파일 | Phase | 변경 내용 |
|------|-------|----------|
| `app/screener/page.tsx` | 1-3 | 반응형, 새 컴포넌트 통합 |
| `components/screener/AdvancedFilterPanel.tsx` | 1 | 50+ 필터 UI (신규) |
| `components/screener/MobileStockCard.tsx` | 1 | 모바일 카드 (신규) |
| `components/screener/ExportButton.tsx` | 1 | CSV 내보내기 (신규) |
| `components/screener/SharePresetModal.tsx` | 2 | 공유 모달 (신규) |
| `components/screener/ChainSightPanel.tsx` | 2 | DNA 패널 (신규) |
| `components/screener/ThesisBuilder.tsx` | 2 | 테제 빌더 (신규) |
| `hooks/useAlertNotifications.ts` | 3 | WebSocket 알림 (신규) |

---

## Part 5: 마일스톤 및 검증

### 마일스톤

| Milestone | Week | 완료 기준 |
|-----------|------|----------|
| M1 | 4 | Phase 1 완료 - 알림, CSV, 고급 필터, 모바일 |
| M2 | 8 | Phase 2 완료 - 공유, Chain Sight, 테제, 한국 |
| M3 | 12 | Phase 3 완료 - 실시간 알림, 시뮬레이션, 패턴 |

### 검증 방법

```bash
# Phase 1 테스트
cd frontend && npm run build  # 빌드 성공
npm run dev  # 로컬 테스트
# 모바일: Chrome DevTools → 반응형 뷰

# Phase 2 테스트
# 프리셋 공유 → URL 복사 → 새 브라우저에서 열기
# Chain Sight → 필터 적용 후 관련 종목 패널 확인

# Phase 3 테스트
# 알림 설정 → 조건 충족 시 토스트 표시 확인
```

---

## Part 6: 리스크 및 완화

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| LLM Rate Limit (테제/Chain Sight) | 높음 | 적극적 캐싱, 단순 분석 폴백 |
| 모바일 대용량 데이터 성능 | 중간 | 가상 리스트, 지연 로딩, 페이지네이션 |
| 알림 체크 부하 | 높음 | 배치 처리, 우선순위 큐, 사용자별 제한 |
| 차트 패턴 정확도 | 중간 | 신뢰도 점수, 사용자 피드백 루프 |

---

## 다음 단계

1. **Phase 1 시작**: ScreenerAlert 모델 생성
2. **디자인 리뷰**: AdvancedFilterPanel UI 목업
3. **API 설계**: 새 엔드포인트 OpenAPI 스펙 정의

---

## References

- [Finviz Stock Screener](https://finviz.com/screener.ashx)
- [TradingView Screener](https://www.tradingview.com/screener/)
- [Investing.com Stock Screener](https://www.investing.com/stock-screener)
