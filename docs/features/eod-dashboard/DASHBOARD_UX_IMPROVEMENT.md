# EOD Dashboard UX Improvement v3

## 분석 배경

Investment Advisor + UI/UX Designer 분석 결과를 반영한 개선입니다.

**핵심 문제**:
- 카드 hover shadow가 클릭 가능 외관이지만 CTA 버튼만 동작 → 사용자 혼란
- 시각적 위계 부족 (텍스트 크기 구분 미약)
- Chain Sight Network 아이콘 비기능적
- VIX 레짐 절대값 하드코딩(25) → 매크로 환경 변화에 경직적
- 뉴스 sentiment-시그널 방향 비교 시 "Buy the rumor, sell the news" 함정 미고려

---

## 변경 사항

### P1: 인터랙션 수정

| Before | After |
|--------|-------|
| CTA 버튼만 클릭 가능 | 카드 전체 클릭 가능 |
| 모바일 스크롤 시 카드 오클릭 | touchMove 10px+ 즉시 감지 → 스크롤 판단 |
| Chain Sight 아이콘 비기능적 | `<Link>` → `/stocks/${symbol}?tab=chain-sight` |
| 키보드 접근성 없음 | `role="button"`, `tabIndex={0}`, Enter/Space 지원 |

### P2: 시각적 계층

| 요소 | Before | After |
|------|--------|-------|
| 헤드라인 | `text-base` (16px) | `text-xl` (20px) |
| 시그널 수 | 16px | `text-2xl font-extrabold` (24px) |
| 카드 제목 | `text-sm` (14px) | `text-base` (16px) |
| BullBearBar | `w-16 h-1.5` | `w-24 h-2` + 비율 텍스트 |
| DataFreshnessBadge | 우측 정렬만 | 좌측 "오늘의 시그널" 타이틀 추가 |
| VixChip | 인라인 컴포넌트 | 별도 파일 분리 + elevated 레짐 지원 |

### P3: 사용성

- 교육 팁: 기본 접힘 → 클릭 시 펼침 (ChevronDown 토글)
- ConfidenceBadge: 도트 `w-2`, 간격 `gap-1`, 레이블 텍스트 추가
- 활성 탭: 카테고리 고유 색상 배경
- 정렬 드롭다운 `z-20`, 전환 시 `animate-fadeIn`
- 빈 상태: Inbox 아이콘 + "전체 시그널 보기" 링크
- URL `?category=momentum` 동기화 → 뒤로가기 지원

### P4+P5: 레이아웃

- Chain Sight 진입 "관계 지도 →" 링크
- CTA 배경색 `categoryColor + '1A'` (10%)
- 모바일 바텀시트 드래그 핸들 바

### P6: 백엔드 Dynamic Regime

#### DynamicRegimeCalculator

**Z-score 공식**: `z = (current_vix - rolling_mean) / rolling_std`

| 레짐 | 조건 (우선순위 순) |
|------|------|
| `high_vol` | mean_ratio >= 2.5 (rolling_mean의 2.5배 이상) |
| `high_vol` | z >= 2.0 |
| `elevated` | mean_ratio >= 1.5 AND z >= 0.5 |
| `elevated` | z >= 1.0 |
| `normal` | 그 외 |

- **상대값 하한선**: 절대값(25/35) 대신 rolling_mean 배수 기반 (시대 변화에 적응)
- **lookback_days=60**: 3개월 — 너무 짧으면 노이즈, 너무 길면 구조 변화 미반영
- **절대값 fallback**: 데이터 부족 시에만 사용 (VIX 35+ → high_vol, 25+ → elevated)
- **Redis 캐싱**: TTL 1시간, 키 `vix_regime:YYYY-MM-DD`

#### THRESHOLDS elevated 추가

| 임계값 | normal | elevated | high_vol |
|--------|--------|----------|----------|
| P2_change_pct | 5.0 | 6.0 | 7.0 |
| P3_gap_ratio | 1.03 | 1.04 | 1.05 |
| P4_body_pct | 3.0 | 4.0 | 5.0 |
| P7_bounce_pct | 3.0 | 4.0 | 5.0 |
| V1_vol_ratio | 2.0 | 2.5 | 3.0 |

#### 뉴스 Sentiment 시간적 인과성 보정

| 상황 | 보정 |
|------|------|
| 당일 뉴스 + 방향 일치 | 유지 (buy the rumor 리스크) |
| 당일 뉴스 + 방향 충돌 | 1단계 하향 |
| 7일 뉴스 + 방향 일치 | 1단계 상향 (모멘텀 지속) |
| 7일 뉴스 + 방향 충돌 | 1단계 하향 |

---

#### Sentiment 정규화

`EODNewsEnricher._normalize_sentiment()` — 다양한 형식을 positive/negative/neutral로 통합:

| 입력 | 출력 |
|------|------|
| positive, bullish, up, +, 긍정 | positive |
| negative, bearish, down, -, 부정 | negative |
| neutral, mixed, 0, 중립 | neutral |

---

## 향후 로드맵

1. **sentiment DB 정규화**: `StockNews.sentiment`에 Django choices enum 적용 + 마이그레이션
2. **뉴스 인과성 정밀 보정**: `published_at` 타임스탬프로 장전/장중/장후 구분
3. **Chain Sight DNA 프론트엔드 그래프 시각화**
