# Stock-Vis 1차 검증 기능 구현 설계서

> **문서 버전:** v1.4 (v1.3 + Recharts ComposedChart 구현 확정, 모바일 Accordion UX, interest_coverage 판정 강화)  
> **작성일:** 2026-03-30  
> **서비스 플로우 위치:** Dashboard → Chain Sight → Node Monitoring → **1차 검증** → Thesis Control → Portfolio  
> **설계 원칙:** 정량 지표 중심 · 한글 우선(영어 병기) · 1인 개발 운영 가능 · batch-first · peer 상대 위치 중심

---

## 1. 네비게이션 재설계

### 1.1 현재 → 변경

```
[현재]
overview | balance sheet | income statement | cashflow | other fundamental | news | chain_sight

[변경 — 2-depth 구조]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  기본정보          │       뉴스        │   분석 및 검증
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ▼ 하위 탭 (L2)    │   (하위 탭 없음)   │   ▼ 하위 탭 (L2)
 · Overview        │                   │   · 1차 검증 (재무 체질)
 · Balance Sheet   │                   │   · Chain Sight (관계 탐색)
 · Income Statement│                   │   · (향후: Thesis Control)
 · Cash Flow       │                   │
 · 기타 펀더멘탈    │                   │
```

### 1.2 프론트엔드 라우팅

```
/stock/:symbol                        → 기본정보/Overview (기본 랜딩)
/stock/:symbol?tab=balance-sheet       → 기본정보/Balance Sheet
/stock/:symbol?tab=income-statement    → 기본정보/Income Statement
/stock/:symbol?tab=cashflow            → 기본정보/Cash Flow
/stock/:symbol?tab=other-fundamental   → 기본정보/기타 펀더멘탈
/stock/:symbol?tab=news                → 뉴스
/stock/:symbol?tab=validation          → 분석 및 검증/1차 검증
/stock/:symbol?tab=chainsight          → 분석 및 검증/Chain Sight
```

### 1.3 네비게이션 UI 컴포넌트

```
┌─────────────────────────────────────────────────────────────┐
│  AAPL · Apple Inc. · $198.45 (+1.23%)                       │
├─────────────────────────────────────────────────────────────┤
│  [기본정보]          [뉴스]          [분석 및 검증]          │  ← L1 (Primary Tab)
├─────────────────────────────────────────────────────────────┤
│  Overview  Balance Sheet  Income Statement  Cash Flow  기타  │  ← L2 (Secondary Tab, 기본정보 선택 시)
└─────────────────────────────────────────────────────────────┘

│  [기본정보]          [뉴스]          [분석 및 검증]          │  ← L1
├─────────────────────────────────────────────────────────────┤
│  1차 검증 (재무 체질)             Chain Sight (관계 탐색)    │  ← L2 (분석 및 검증 선택 시)
└─────────────────────────────────────────────────────────────┘
```

**L1 탭 디자인:** Pill 스타일, 선택 시 배경색 변경  
**L2 탭 디자인:** Underline 스타일, 선택 시 하단 보더

---

## 2. 1차 검증 — 페이지 구조 설계

### 2.1 전체 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ ① 종합 요약 카드 (Signal Summary)                           │
│   7개 카테고리 신호등 (green/yellow/red) + 한줄 요약          │
├─────────────────────────────────────────────────────────────┤
│ ② Peer 정보 바 (Peer Context Bar)                           │
│   "비교 대상: Software-Application 업종 내 유사 규모 24개"    │
│   peer 신뢰도 badge (High/Medium/Low)                       │
├────────────────────────┬────────────────────────────────────┤
│ ③ 카테고리별 상세       │ ④ 카테고리 네비게이션 (Sticky)      │
│   (메인 콘텐츠 영역)    │   · 수익성                         │
│                        │   · 성장성                         │
│   스크롤 기반으로       │   · 재무구조                       │
│   각 카테고리 섹션이    │   · 현금흐름                       │
│   순서대로 표시         │   · 운영효율                       │
│                        │   · 희석/주주가치                   │
│                        │   · 밸류에이션                      │
├────────────────────────┴────────────────────────────────────┤
│ ⑤ 산업 위치 요약 (Industry Position)                        │
│   업종 내 주요 지표 순위 + 산업 리더 대비 비교                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 모바일 레이아웃

```
┌───────────────────────────┐
│ ① 종합 요약 카드           │
│   (7개 신호등 가로 스크롤)   │
├───────────────────────────┤
│ ② Peer 정보 (축약)        │
├───────────────────────────┤
│ ③ 카테고리 필터            │
│   [수익성] [성장성] [재무..] │
│   (가로 스크롤 Chip)       │
├───────────────────────────┤
│ ④ 선택된 카테고리 상세      │
│   지표 카드 Accordion 나열  │
│                           │
│   ┌─ 매출총이익률 ────┐    │
│   │ 🟢 45.2% (상위19%)│    │  ← 접힌 상태 (기본)
│   └───────────────────┘    │
│   ┌─ 영업이익률 (펼침) ┐    │
│   │ 🟢 33.1% (상위12%)│    │  ← 펼친 상태
│   │ [막대 차트]        │    │
│   │ 해석 텍스트...     │    │
│   └───────────────────┘    │
│   ┌─ 순이익률 ────────┐    │
│   │ 🟢 26.8% (상위15%)│    │  ← 접힌 상태
│   └───────────────────┘    │
├───────────────────────────┤
│ ⑤ 산업 위치 (축약)         │
└───────────────────────────┘
```

**모바일 지표 카드 Accordion 규칙:**

- **접힌 상태 (기본):** 신호등 아이콘 + 지표명 + 현재값 + percentile 한줄
- **펼친 상태 (탭 시):** 차트 + peer benchmark 수치 + 해석 텍스트
- 한 번에 1개만 펼쳐짐 (다른 카드 탭하면 이전 카드 접힘)
- 데스크톱에서는 Accordion 없이 전체 펼침 (기존 레이아웃 유지)

---

## 3. 각 섹션 상세 설계

### 3.1 ① 종합 요약 카드 (Signal Summary)

DB 소스: `category_signal` 테이블

```
┌─────────────────────────────────────────────────────────────┐
│                    AAPL 재무 체질 진단                        │
│                                                             │
│  🟢 수익성    🟢 성장성    🟢 재무구조    🟢 현금흐름          │
│                                                             │
│  🟡 운영효율  🟢 희석/주주  🟡 밸류에이션                     │
│                                                             │
│  ─── 한줄 요약 ───                                           │
│  "높은 수익성과 안정적 현금흐름. 밸류에이션 부담 존재."        │
└─────────────────────────────────────────────────────────────┘
```

**신호등 기준 (percentile 기반으로 통일):**

카테고리 신호등과 지표 막대 색상을 동일한 기준으로 통일하여 사용자 혼란을 방지한다.

- 🟢 Green: 카테고리 내 지표들의 평균 percentile ≥ 65 (양호)
- 🟡 Yellow: 35 ≤ 평균 percentile < 65 (주의)
- 🔴 Red: 평균 percentile < 35 (경고)
- ⚪ Gray: 데이터 부족 또는 특수 산업으로 해석 제한

**category_signal 점수 계산 규칙:**

```python
def calculate_category_signal(symbol, category, fiscal_year):
    """
    카테고리 신호 = 소속 지표들의 percentile_rank 균등 가중 평균 기반 판정.

    1. null 지표 처리:
       - 해당 기업에 적용 불가한 지표(흑자 기업의 cash_runway,
         서비스 기업의 inventory 등)는 분모에서 제외
       - 분모가 0이면 (모든 지표 null) → signal = 'gray'

    2. 특수 산업 처리:
       - industry_classification.handling_mode == 'special'인 경우:
         해당 카테고리의 signal = 'gray' + reason에 산업 특성 고지
         (예: "금융업 특성상 일반 해석과 다를 수 있습니다")

    3. 점수 계산:
       valid_metrics = [m for m in category_metrics
                        if m.percentile_rank is not None
                        and m.value_status == 'normal']
       if len(valid_metrics) == 0:
           return signal='gray', reason='데이터 부족'
       score = mean([m.percentile_rank for m in valid_metrics])
       # score 범위: 0~100 (percentile 평균이므로 자연스럽게 0~100)
       # score는 내부 계산용으로만 저장, UI에서는 신호등만 표시

    4. 신호등:
       if score >= 65: signal = 'green'
       elif score >= 35: signal = 'yellow'
       else: signal = 'red'

    5. signal_reason 생성 (rule-based):
       green_count = len([m for m in valid_metrics if m.percentile_rank >= 65])
       reason = f"{len(valid_metrics)}개 지표 중 {green_count}개 업종 상위 35%"
    """
```

**⚠️ 균등 가중을 선택한 이유:**

- 가중치 차등화는 "왜 이 지표가 더 중요한가"에 대한 도메인 판단이 필요한데, 이는 산업별로 다름
- MVP에서 임의 가중치를 주면 나중에 바꾸기 어려움
- 균등 가중 + percentile 기반이면 산업 특성이 자연스럽게 반영됨 (peer가 기준이므로)
- 향후 사용자 피드백으로 가중치 조정 여지를 남김

**한줄 요약 생성 (Phase 1: Rule-based Only):**

```python
def generate_summary_text(category_signals):
    """
    Phase 1에서는 rule-based 템플릿만 사용.
    Phase 2에서 LLM 배치 캐싱 + fallback 구조 도입 검토.
    """
    green_cats = [c for c in category_signals if c.signal == 'green']
    red_cats = [c for c in category_signals if c.signal == 'red']
    gray_cats = [c for c in category_signals if c.signal == 'gray']

    parts = []

    # 강점 언급
    if len(green_cats) >= 2:
        top2 = sorted(green_cats, key=lambda c: c.score, reverse=True)[:2]
        parts.append(f"높은 {top2[0].display_name}과(와) {top2[1].display_name}")
    elif len(green_cats) == 1:
        parts.append(f"{green_cats[0].display_name}이(가) 강점")

    # 약점 언급
    if red_cats:
        parts.append(f"{red_cats[0].display_name} 부분 주의 필요")

    # 해석 제한 언급
    if gray_cats:
        parts.append(f"{len(gray_cats)}개 카테고리 해석 제한")

    # 조합
    if len(green_cats) >= 5:
        return "전반적으로 양호한 재무 체질. " + ". ".join(parts) + "."
    elif len(red_cats) >= 2:
        return ". ".join(parts) + ". 심층 분석 권장."
    elif not green_cats and not red_cats:
        return "대부분 지표가 중립 구간. 뚜렷한 강점/약점 없음."
    else:
        return ". ".join(parts) + "."
```

### 3.2 ② Peer 정보 바 (Peer Context Bar)

DB 소스: `peer_list_cache`, `industry_classification`

```
┌─────────────────────────────────────────────────────────────┐
│  📊 비교 기준: Software - Application 업종 내 유사 규모 24개  │
│  비교 신뢰도: 🟢 높음   |  데이터 기준: 2025 FY              │
│  규모 기준: Large Cap (±1 단계 포함)                          │
│  ⓘ 과거 연도 차트도 현재 peer 기준으로 계산됩니다             │
│                                                             │
│  [peer 목록 보기 ▼]                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ MSFT · CRM · ADBE · NOW · INTU · WDAY ...          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Peer 선정 구조 (Phase 1: Industry + Size Bucket):**

```python
# Size Bucket 분류
def assign_market_cap_bucket(market_cap):
    """
    S&P 500은 대부분 large/mega이므로 분포가 단순.
    """
    if market_cap >= 200_000_000_000:   # $200B+
        return 'mega'
    elif market_cap >= 10_000_000_000:  # $10B+
        return 'large'
    elif market_cap >= 2_000_000_000:   # $2B+
        return 'mid'
    else:
        return 'small'

def get_adjacent_buckets(bucket):
    """같은 bucket + 인접 ±1 bucket 허용"""
    order = ['small', 'mid', 'large', 'mega']
    idx = order.index(bucket)
    return order[max(0, idx-1):min(len(order), idx+2)]

# Peer 선정 알고리즘
def select_peers(target_symbol):
    """
    Phase 1: industry + size bucket 기반 peer 선정.
    Phase 2 (Chain Sight 연계 후): business_model_tag 기반 strict/broad 분류 추가.
    """
    target = Company.objects.get(symbol=target_symbol)

    # Step 1: 같은 industry + 같은/인접 size bucket
    peers = Company.objects.filter(
        industry=target.industry,
        market_cap_bucket__in=get_adjacent_buckets(target.market_cap_bucket),
        is_active=True,
    ).exclude(symbol=target_symbol)

    benchmark_basis = 'industry_size'

    # Step 2: 부족하면 size bucket 조건 완화
    if peers.count() < 8:
        peers = Company.objects.filter(
            industry=target.industry,
            is_active=True,
        ).exclude(symbol=target_symbol)
        benchmark_basis = 'industry'

    # Step 3: 그래도 부족하면 sector fallback
    if peers.count() < 5:
        peers = Company.objects.filter(
            sector=target.sector,
            is_active=True,
        ).exclude(symbol=target_symbol)
        benchmark_basis = 'sector'

    return peers, benchmark_basis
```

**Peer 신뢰도 기준:**

- 🟢 높음 (High): peer ≥ 15개, benchmark_basis가 industry_size
- 🟡 보통 (Medium): 8 ≤ peer < 15, 또는 size 완화 사용
- 🔴 낮음 (Low): peer < 8, sector fallback 사용 중임을 표시

**Phase 2 확장 구조 (Chain Sight 연계):**

- Chain Sight 재구축 시 Neo4j에 기업 속성 태깅 (10-K 파싱 기반 business_model_tag)
- Louvain 커뮤니티 탐지로 "재무적 유사 기업 클러스터" 자동 생성
- 이 클러스터를 strict peer로 활용, 기존 industry 기반은 broad peer로 전환
- `peer_list_cache.peer_tier` 필드에 strict/broad/industry 값 할당
- **Phase 1에서는 peer_tier를 nullable로 미리 추가해두되 전부 null**

**Peer 시간 변동 한계:**

- 5년 차트의 peer band(p25/median/p75)는 **현재 시점의 peer 구성**으로 과거 데이터도 계산한다.
- 이유: peer 이력(과거 peer 그룹)을 관리하면 복잡도가 급증하고, 1인 개발에서 감당 불가.
- 한계: 2020년에 상장하지 않았던 종목이 현재 peer에 포함되면, 해당 연도 benchmark에 해당 종목은 null → 자동 제외.
- UI 고지: Peer 정보 바에 "과거 연도 차트도 현재 peer 기준으로 계산됩니다" 문구 표시.

### 3.3 ③ 카테고리별 상세 — 지표 카드

DB 소스: `company_metric_snapshot`, `company_metric_latest`, `company_benchmark_delta`, `metric_definition`

#### 지표 카드 단일 레이아웃:

```
┌─────────────────────────────────────────────────────────────┐
│ 🟢 매출총이익률 (Gross Margin)                               │
│                                                             │
│     현재값: 45.2%          업종 중앙값: 38.7%                 │
│     순위: 24개 중 5위       백분위: 81%                      │
│     비교 기준: industry_size | 신뢰도: 높음                   │
│                                                             │
│     ┌─ 5년 추세 + Peer 비교 (막대 차트) ──────────────┐      │
│     │                                                 │      │
│     │   ┬─ p75                                        │      │
│     │   │       ┬─ p75                                │      │
│     │  ██  ╂   ██  ╂    ██  ╂   ██  ╂   ██  ╂       │      │
│     │  ██  │   ██  │    ██  │   ██  │   ██  │        │      │
│     │  ██  ┴─ p25  ██  ┴    ██  ┴   ██  ┴   ██  ┴   │      │
│     │  ██       ██        ██       ██       ██        │      │
│     │ 2020    2021      2022     2023     2024        │      │
│     │                                                 │      │
│     │  ██ = 이 기업    ╂ = peer 중앙값                 │      │
│     │  ┬┴ = peer p25~p75 범위                         │      │
│     └─────────────────────────────────────────────────┘      │
│                                                             │
│     해석: peer 상위 19%에 위치하며 최근 3년 개선 추세.        │
│     (높을수록 좋은 지표)                                      │
└─────────────────────────────────────────────────────────────┘
```

**value_status에 따른 지표 카드 표시 분기:**

```
value_status = 'normal'          → 정상 렌더링 (차트 + 해석)
value_status = 'not_applicable'  → "해당 없음" + 사유 표시 (차트 없음)
value_status = 'missing'         → "데이터 누락" 표시
value_status = 'unstable'        → 정상 렌더링 + ⚠️ "값 변동이 크므로 해석 주의" 경고
value_status = 'low_confidence'  → 정상 렌더링 + ⚠️ "비교 표본 부족" 경고
```

#### 차트 유형: Grouped Bar Chart + Peer Range Overlay

- X축: fiscal_year (최근 5년)
- Y축: 지표 값
- **이 기업 값**: 컬러 막대 (강조색, 연도별 1개씩)
- **Peer 중앙값**: 각 막대 위에 가로선 마커 (─)
- **Peer p25~p75**: 각 연도에 세로 범위 표시 (Error bar 스타일, ┬┴)
- hover 시 구체적 수치 표시 (이 기업 값, median, p25, p75)
- 막대 색상: signal에 따라 green/yellow/red 그라데이션 (해당 연도 peer 대비 위치 기반)

#### 해석 텍스트 생성 (Phase 1: Rule-based Only):

```python
def generate_metric_interpretation(metric_def, latest, benchmark_delta, trend, value_status):
    """
    Phase 1: Rule-based 해석만 사용.
    Phase 2: LLM 배치 캐싱 도입 검토 (validation_ai_cache 테이블).
    """
    # value_status가 normal이 아니면 특수 메시지
    if value_status == 'not_applicable':
        return metric_def.not_applicable_reason  # e.g. "흑자 기업에 해당하지 않는 지표"
    if value_status == 'missing':
        return "데이터가 제공되지 않아 비교할 수 없습니다."

    parts = []

    # 1. 상대 위치
    pct = benchmark_delta.percentile_rank
    if pct >= 75:
        parts.append(f"peer 상위 {100 - pct:.0f}%에 위치")
    elif pct <= 25:
        parts.append(f"peer 하위 {pct:.0f}%에 위치")
    else:
        parts.append("업종 중앙값 수준")

    # 2. 추세
    if trend == "improving":
        parts.append("최근 3년간 개선 추세")
    elif trend == "declining":
        parts.append("최근 3년간 하락 추세")
    else:
        parts.append("최근 3년간 안정적")

    # 3. benchmark 신뢰도 경고
    if benchmark_delta.benchmark_confidence == 'low':
        parts.append("비교 표본이 적어 해석에 주의 필요")

    # 4. value_status 경고
    if value_status == 'unstable':
        parts.append("값 변동이 크므로 추세 해석에 주의")

    # 5. 방향성 안내
    direction = "높을수록" if metric_def.higher_is_better else "낮을수록"
    parts.append(f"({direction} 좋은 지표)")

    return ". ".join(parts) + "."
```

### 3.4 ④ 카테고리 네비게이션 (Sticky Sidebar)

7개 카테고리를 사이드바로 표시. 스크롤 위치에 따라 활성 카테고리 하이라이트.

```
┌──────────────────┐
│ 📋 카테고리       │
│ ───────────────  │
│ 🟢 수익성  (5)   │  ← 카테고리명 + 신호등 + 지표 수
│ 🟢 성장성  (4)   │
│ 🟢 재무구조 (6)  │  ← 현재 스크롤 위치 (bold)
│ 🟢 현금흐름 (6)  │
│ 🟡 운영효율 (6)  │
│ 🟢 희석    (4)   │
│ 🟡 밸류에이션(3) │
└──────────────────┘
```

### 3.5 ⑤ 산업 위치 요약 (Industry Position)

DB 소스: `company_benchmark_delta`, `industry_metric_benchmark`, `peer_metric_benchmark`

이 섹션의 핵심 질문: **"이 기업은 속한 산업에서 어떤 위치인가?"**

```
┌─────────────────────────────────────────────────────────────┐
│                    산업 내 경쟁력 요약                        │
│                                                             │
│  ┌─ 핵심 지표 순위 ────────────────────────────────────┐     │
│  │                                                    │     │
│  │  매출 성장률     ██████████████████░░░   8위/24     │     │
│  │  영업이익률     ████████████████████░   5위/24      │     │
│  │  ROE           ██████████████████████  3위/24      │     │
│  │  FCF 마진      █████████████████░░░░   11위/24     │     │
│  │  부채비율      ██████████████████████  2위/24      │     │
│  │                                                    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                             │
│  ┌─ 업종 1위 기업 대비 (카테고리별 대표 지표) ────────┐       │
│  │                                                    │     │
│  │  업종 1위: MSFT (Microsoft)                        │     │
│  │                                                    │     │
│  │  ─── 요약 (기본 노출 — 대표 6개) ───                │     │
│  │  지표              AAPL       MSFT     격차        │     │
│  │  영업이익률        33.1%      44.2%   -11.1%p     │     │
│  │  매출 성장률        8.2%      12.4%    -4.2%p     │     │
│  │  부채비율           0.18x      0.25x    우위 ✅    │     │
│  │  FCF 마진          22.3%      30.1%    -7.8%p     │     │
│  │  총자산회전율       1.08x      0.52x    우위 ✅    │     │
│  │  주주수익률          4.5%       2.1%    우위 ✅    │     │
│  │                                                    │     │
│  │  [상세 16개 더 보기 ▼]                              │     │
│  │                                                    │     │
│  │  ──── 종합 ────                                    │     │
│  │  💡 22개 비교 지표 중 7개에서 업종 1위보다 우위.     │     │
│  │     강점: 운영효율, 희석/주주가치, 밸류에이션         │     │
│  │     약점: 수익성(마진 격차), 성장성(FCF 성장 부진)    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                             │
│  ┌─ 경쟁력 요약 (Rule-based) ────────────────────────┐       │
│  │  22개 비교 지표 중 7개 우위.                        │     │
│  │  강점: 운영효율, 희석/주주가치.                      │     │
│  │  약점: 수익성(마진 격차), 성장성(FCF 성장 부진).     │     │
│  └────────────────────────────────────────────────────┘     │
│                                                             │
│  ┌─ 성장 추세 비교 ──────────────────────────────────┐       │
│  │  이 기업의 매출 성장률: 가속 중 (5% → 6% → 8%)     │     │
│  │  업종 중앙값 성장률:   감속 중 (10% → 8% → 7%)     │     │
│  │  → 업종 대비 상대적 성장 모멘텀: 양호 ↑             │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

**업종 1위 선정 기준:**

- `peer_metric_benchmark`에서 market_cap 기준 peer 내 1위 (= 대장주)
- **자기 자신이 대장주인 경우:** market_cap 2위와 비교. 표시: "업종 2위: {symbol} ({name})"
- **peer가 2개 미만인 경우:** 이 섹션 비표시 ("비교 대상 부족")

**비교 지표 구성 (22개 — 요약/상세 분리 표시):**

**요약 (기본 노출 — 카테고리별 대표 1개씩, 6개):**

- 영업이익률 (수익성 대표)
- 매출 성장률 (성장성 대표)
- 부채비율 (재무구조 대표)
- FCF 마진 (현금흐름 대표)
- 총자산회전율 (운영효율 대표)
- 주주수익률 (희석/주주가치 대표)

**상세 (접기/펼치기 — 나머지 16개):**

- 수익성: gross_margin, roe, roic
- 성장성: operating_income_growth, fcf_growth_yoy
- 재무구조: current_ratio, interest_coverage
- 현금흐름: ocf_to_net_income, accruals_ratio
- 운영효율: dso, sga_to_revenue
- 희석/주주가치: dilution_3y_cum, sbc_to_revenue
- 밸류에이션: pe_ratio, ev_to_ebitda, fcf_yield

**"우위" 판정 기준:**

- higher_is_better 지표: 이 기업 > 대장주 → 우위 ✅
- higher_is_better가 아닌 지표: 이 기업 < 대장주 → 우위 ✅
- 종합 카운트: "22개 중 N개에서 우위"

**경쟁력 요약 (Phase 1: Rule-based):**

```python
def generate_leader_summary(advantages, disadvantages):
    """
    Phase 1: Rule-based.
    Phase 2: LLM 배치 캐싱 도입 검토.
    """
    parts = [f"22개 비교 지표 중 {len(advantages)}개 우위."]

    if advantages:
        adv_cats = list(set(a['category'] for a in advantages))
        parts.append(f"강점: {', '.join(adv_cats[:3])}.")

    if disadvantages:
        dis_cats = list(set(d['category'] for d in disadvantages))
        parts.append(f"약점: {', '.join(dis_cats[:3])}.")

    return " ".join(parts)
```

**성장 추세 비교:**

- 자사 3년 매출 성장률 추세 vs 업종 median 3년 추세
- 추세 방향: 가속 / 유지 / 감속 / 역성장
- Rule-based 판단 (CAGR이 아닌 연도별 방향 변화)

---

## 4. 7개 카테고리 × 34개 지표 — 프론트엔드 표시 명세

### 4.1 수익성 (Profitability) — 5개

| 순서 | 표시명         | 영어 병기        | 단위 | 높을수록 좋음 | 차트 |
| ---- | -------------- | ---------------- | ---- | ------------- | ---- |
| 1    | 매출총이익률   | Gross Margin     | %    | ✅            | Bar  |
| 2    | 영업이익률     | Operating Margin | %    | ✅            | Bar  |
| 3    | 순이익률       | Net Margin       | %    | ✅            | Bar  |
| 4    | 자기자본이익률 | ROE              | %    | ✅            | Bar  |
| 5    | 투하자본이익률 | ROIC             | %    | ✅            | Bar  |

**카테고리 설명 (UI 상단에 표시):**

> "기업이 매출에서 얼마나 효율적으로 이익을 만들어내는지 보여줍니다. 마진이 높고 안정적일수록 가격 결정력과 비용 효율이 뛰어난 기업입니다."

### 4.2 성장성 (Growth) — 4개

| 순서 | 표시명            | 영어 병기               | 단위 | 높을수록 좋음 | 차트     |
| ---- | ----------------- | ----------------------- | ---- | ------------- | -------- |
| 1    | 매출 성장률 (YoY) | Revenue Growth          | %    | ✅            | Bar      |
| 2    | 영업이익 성장률   | Operating Income Growth | %    | ✅            | Bar      |
| 3    | FCF 성장률        | FCF Growth              | %    | ✅            | Bar      |
| 4    | 매출성장 vs 업종  | Rev Growth vs Industry  | %p   | ✅            | 단독 Bar |

**카테고리 설명:**

> "기업의 성장 속도를 보여줍니다. 단순 성장률뿐 아니라 업종 평균 대비 얼마나 빠르게 성장하는지도 함께 확인합니다."

### 4.3 재무구조 / 생존 (Financial Structure) — 6개

| 순서 | 표시명         | 영어 병기          | 단위 | 높을수록 좋음 | 차트               |
| ---- | -------------- | ------------------ | ---- | ------------- | ------------------ |
| 1    | 부채비율       | Debt to Equity     | 배   | ❌            | Bar                |
| 2    | 유동비율       | Current Ratio      | 배   | ✅            | Bar                |
| 3    | 이자보상배율   | Interest Coverage  | 배   | ✅            | Bar                |
| 4    | 순부채/EBITDA  | Net Debt to EBITDA | 배   | ❌            | Bar                |
| 5    | 현금 소진 연수 | Cash Runway        | 년   | ✅            | 단독 (적자 기업만) |
| 6    | 단기부채 비중  | Short-term Debt %  | %    | ❌            | Bar                |

**카테고리 설명:**

> "기업이 위기 상황에서 생존할 수 있는지 평가합니다. 부채 수준, 현금 보유, 이자 지급 능력 등 재무 안정성의 핵심 지표입니다."

**특수 처리:**

- `cash_runway_years`: 흑자 기업은 value_status='not_applicable' → "해당 없음 (흑자 기업)" 표시
- `interest_coverage`: 무차입 기업은 value_status='not_applicable' → "해당 없음 (무차입)" 표시
- `interest_coverage`: 값이 극단적으로 변동 (-500x → +200x)인 경우 value_status='unstable'

**⚠️ 특수 산업 처리 (handling_mode='special'):**

- 금융업(은행/보험): debt_to_equity 해석 제한 표시 "금융업 특성상 일반 기업과 다른 기준이 적용됩니다"
- REIT: FCF 계열 지표 해석 제한
- Phase 1에서는 고지문 표시만, Phase 2에서 산업별 대체 지표 도입 검토

### 4.4 현금흐름의 질 (Cash Flow Quality) — 6개

| 순서 | 표시명                    | 영어 병기         | 단위 | 높을수록 좋음 | 차트      |
| ---- | ------------------------- | ----------------- | ---- | ------------- | --------- |
| 1    | FCF 마진                  | FCF Margin        | %    | ✅            | Bar       |
| 2    | 이익의 질 (영업CF/순이익) | OCF to Net Income | 배   | ✅            | Bar       |
| 3    | Capex 부담률              | Capex to OCF      | %    | ❌            | Bar       |
| 4    | 발생액 비율               | Accruals Ratio    | %    | ❌            | Bar       |
| 5    | FCF 전환율                | FCF Conversion    | %    | ✅            | Bar       |
| 6    | 영업CF 추세 (3년)         | OCF Trend 3Y      | %    | ✅            | 단독 Line |

**카테고리 설명:**

> "회계상 이익이 아니라 실제 현금 창출 능력을 평가합니다. 발생액 비율이 높으면 이익의 질이 낮을 수 있고, FCF 전환율이 높으면 실제 현금으로 잘 바뀌는 이익입니다."

### 4.5 운영 효율성 (Operational Efficiency) — 6개

| 순서 | 표시명                 | 영어 병기                 | 단위 | 높을수록 좋음 | 차트 |
| ---- | ---------------------- | ------------------------- | ---- | ------------- | ---- |
| 1    | 매출채권 회전일수      | Days Sales Outstanding    | 일   | ❌            | Bar  |
| 2    | AR/매출 비율           | AR to Revenue             | %    | ❌            | Bar  |
| 3    | 재고자산 회전일수      | Inventory Turnover Days   | 일   | ❌            | Bar  |
| 4    | 재고 vs 매출 성장 격차 | Inventory vs Sales Growth | %p   | ❌            | Bar  |
| 5    | 판관비/매출            | SGA to Revenue            | %    | ❌            | Bar  |
| 6    | 총자산회전율           | Asset Turnover            | 배   | ✅            | Bar  |

**카테고리 설명:**

> "기업이 자산과 자원을 얼마나 효율적으로 활용하는지 보여줍니다. 매출채권이 빠르게 회수되고, 재고가 과잉 축적되지 않는 것이 건강한 운영의 신호입니다."

**특수 처리:**

- `inventory_turnover_days`, `inventory_vs_sales_growth`: 서비스 기업(재고 없음)은 value_status='not_applicable' → "해당 없음 (서비스 기업)" 표시

### 4.6 희석 / 주주가치 (Dilution & Shareholder) — 4개

| 순서 | 표시명            | 영어 병기              | 단위 | 높을수록 좋음 | 차트 |
| ---- | ----------------- | ---------------------- | ---- | ------------- | ---- |
| 1    | 3년 누적 희석률   | 3Y Cumulative Dilution | %    | ❌            | Bar  |
| 2    | 주식보상비/매출   | SBC to Revenue         | %    | ❌            | Bar  |
| 3    | 자사주매입 수익률 | Buyback Yield          | %    | ✅            | Bar  |
| 4    | 주주수익률        | Shareholder Yield      | %    | ✅            | Bar  |

**카테고리 설명:**

> "기업이 주주 가치를 보호하는지 확인합니다. 주식 희석은 기존 주주의 지분을 줄이고, 자사주 매입은 주주에게 현금을 돌려주는 행위입니다. 특히 테크 기업의 SBC(주식보상비용) 규모를 주시해야 합니다."

### 4.7 밸류에이션 (Valuation) — 3개 (보조)

| 순서 | 표시명    | 영어 병기         | 단위 | 높을수록 좋음 | 차트 |
| ---- | --------- | ----------------- | ---- | ------------- | ---- |
| 1    | PER       | Price to Earnings | 배   | ❌            | Bar  |
| 2    | EV/EBITDA | EV to EBITDA      | 배   | ❌            | Bar  |
| 3    | FCF Yield | FCF Yield         | %    | ✅            | Bar  |

**카테고리 설명:**

> "현재 주가가 기업 가치 대비 얼마나 비싼지 보여줍니다. 참고용 보조 지표이며, 밸류에이션만으로 투자 판단을 내리기는 어렵습니다."

**UI 차별화:** 보조 카테고리로 표시 (접혀 있다가 펼치기 가능, 색상 톤 다운)

---

## 5. 백엔드 API 설계

### 5.1 엔드포인트 구조

```
# 1차 검증 메인 데이터 (한 번 호출로 전체 로드)
GET /api/v1/validation/{symbol}/summary/
→ 종합 요약 + peer 정보 + 산업 위치

# 카테고리별 상세 (lazy load)
GET /api/v1/validation/{symbol}/metrics/?category=profitability  (기본값: 첫 카테고리)
GET /api/v1/validation/{symbol}/metrics/?category=growth
GET /api/v1/validation/{symbol}/metrics/?category=all  (전체 — 데스크톱 초기 로드용)
→ 지표별 현재값 + 5년 시계열 + peer band + 해석

# 산업 리더 비교
GET /api/v1/validation/{symbol}/leader-comparison/
→ 업종 대장주 vs 이 기업 핵심 지표 비교
```

**API 응답 크기 제어:**

- `category=all`: ~80~120KB (34개 지표 × 5년 시계열 + peer band + 해석 텍스트). 데스크톱 초기 로드에서만 사용.
- `category={single}`: ~10~20KB (4~6개 지표). 모바일 및 lazy load 기본값.
- 프론트엔드 전략: 데스크톱은 `category=all` 1회 호출, 모바일은 카테고리 Chip 선택 시 개별 호출.

### 5.2 API 응답 구조

#### `/api/v1/validation/{symbol}/summary/`

```json
{
	"symbol": "AAPL",
	"company_name": "Apple Inc.",
	"data_fiscal_year": 2025,
	"data_freshness": "2026-03-15T00:00:00Z",

	"category_signals": [
		{
			"category": "profitability",
			"display_name": "수익성",
			"display_name_en": "Profitability",
			"signal": "green",
			"description": "기업이 매출에서 얼마나 효율적으로 이익을 만들어내는지 보여줍니다.",
			"metric_count": 5,
			"signal_reason": "5개 지표 중 4개 업종 상위 35%"
		}
	],

	"summary_text": "높은 수익성과 안정적 현금흐름. 밸류에이션 부담 존재.",
	"summary_source": "rule",

	"peer_info": {
		"industry": "Software - Application",
		"peer_count": 24,
		"confidence": "high",
		"benchmark_basis": "industry_size",
		"size_bucket": "large",
		"basis_description": "Software - Application 업종 내 유사 규모 기업",
		"top_peers": ["MSFT", "CRM", "ADBE", "NOW", "INTU"],
		"industry_leader": {
			"symbol": "MSFT",
			"name": "Microsoft Corporation",
			"market_cap": 3100000000000
		}
	},

	"industry_position": {
		"ranks": [
			{
				"metric": "revenue_growth_yoy",
				"display_name": "매출 성장률",
				"rank": 8,
				"total": 24,
				"value": 0.082
			},
			{
				"metric": "operating_margin",
				"display_name": "영업이익률",
				"rank": 5,
				"total": 24,
				"value": 0.331
			}
		]
	}
}
```

#### `/api/v1/validation/{symbol}/metrics/?category=all`

```json
{
	"symbol": "AAPL",
	"categories": [
		{
			"category": "profitability",
			"display_name": "수익성",
			"display_name_en": "Profitability",
			"signal": "green",
			"description": "기업이 매출에서 얼마나 효율적으로 이익을 만들어내는지...",
			"metrics": [
				{
					"metric_code": "gross_margin",
					"display_name": "매출총이익률",
					"display_name_en": "Gross Margin",
					"unit": "ratio",
					"higher_is_better": true,

					"current": {
						"value": 0.452,
						"fiscal_year": 2025,
						"value_status": "normal"
					},

					"benchmark": {
						"basis": "industry_size",
						"confidence": "high",
						"median": 0.387,
						"p25": 0.321,
						"p75": 0.441,
						"percentile_rank": 81.2,
						"rank": 5,
						"total": 24
					},

					"history": [
						{
							"fiscal_year": 2021,
							"company_value": 0.418,
							"peer_median": 0.372,
							"peer_p25": 0.305,
							"peer_p75": 0.425
						},
						{
							"fiscal_year": 2022,
							"company_value": 0.432,
							"peer_median": 0.38,
							"peer_p25": 0.312,
							"peer_p75": 0.43
						},
						{
							"fiscal_year": 2023,
							"company_value": 0.441,
							"peer_median": 0.383,
							"peer_p25": 0.315,
							"peer_p75": 0.435
						},
						{
							"fiscal_year": 2024,
							"company_value": 0.448,
							"peer_median": 0.385,
							"peer_p25": 0.318,
							"peer_p75": 0.438
						},
						{
							"fiscal_year": 2025,
							"company_value": 0.452,
							"peer_median": 0.387,
							"peer_p25": 0.321,
							"peer_p75": 0.441
						}
					],

					"trend": "improving",
					"interpretation": "peer 상위 19%에 위치하며 최근 3년 개선 추세. (높을수록 좋은 지표).",
					"interpretation_source": "rule"
				}
			]
		}
	]
}
```

### 5.3 Django View 구조

```python
# validation/api/views.py

class ValidationSummaryView(APIView):
    """1차 검증 종합 요약 API"""

    def get(self, request, symbol):
        # 1. category_signal 조회 (7개 카테고리)
        # 2. peer_list_cache 조회 (benchmark_basis, confidence 포함)
        # 3. industry_metric_benchmark 조회
        # 4. rule-based 한줄 요약 생성
        # 5. 산업 내 순위 계산
        pass

class ValidationMetricsView(APIView):
    """카테고리별 지표 상세 API"""

    def get(self, request, symbol):
        category = request.query_params.get('category', 'profitability')
        # 1. metric_definition 조회 (지표 메타)
        # 2. company_metric_snapshot 조회 (가용 연도, 최대 5년) — value_status 포함
        # 3. company_benchmark_delta 조회 (peer band) — benchmark_basis, confidence 포함
        # 4. rule-based 해석 텍스트 생성
        pass

class LeaderComparisonView(APIView):
    """업종 리더 대비 비교 API"""

    def get(self, request, symbol):
        # 1. peer 내 market_cap 1위 조회
        # 2. 카테고리별 대표 지표 22개 비교
        # 3. 우위/열위 카운트 + 강점/약점 카테고리 판별
        # 4. rule-based 경쟁력 요약 생성
        # 5. 성장 추세 비교
        pass
```

### 5.4 URL 설정

```python
# validation/api/urls.py

urlpatterns = [
    path('<str:symbol>/summary/', ValidationSummaryView.as_view(), name='validation-summary'),
    path('<str:symbol>/metrics/', ValidationMetricsView.as_view(), name='validation-metrics'),
    path('<str:symbol>/leader-comparison/', LeaderComparisonView.as_view(), name='validation-leader'),
]

# config/urls.py
urlpatterns += [
    path('api/v1/validation/', include('validation.api.urls')),
]
```

---

## 6. 배치 파이프라인 설계

### 6.1 데이터 흐름

```
                                     [FMP API]
                                         │
                                    (주 1회 배치)
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Celery Beat: Weekly Batch                     │
│                                                                  │
│  ※ 실행 방식: chain(Task1 → Task2 → Task3 → Task3.5 → Task4     │
│               → Task5 → Task6)                                   │
│  ※ Task간 순차 보장 (chain), Task 내 종목별 병렬 가능 (group)     │
│  ※ Worker pool: prefork, Neo4j driver import 없음 (SIGSEGV 안전) │
│                                                                  │
│  Task 1: fetch_annual_financials                                 │
│  → FMP income-statement, balance-sheet, cash-flow-statement      │
│  → company_metric_snapshot에 원값 저장                            │
│                                                                  │
│  Task 2: calculate_derived_metrics                               │
│  → snapshot 원값으로 33개 지표 계산 (rev_growth_vs_industry 제외)  │
│  → company_metric_snapshot 업데이트 (계산 필드)                    │
│  → company_metric_latest 갱신                                     │
│  → ⭐ value_status 판정 (normal/not_applicable/missing/unstable)  │
│                                                                  │
│  Task 3: calculate_benchmarks                                    │
│  → ⭐ peer 선정: industry + size bucket 기반 (select_peers 함수)  │
│  → peer_metric_benchmark, industry_metric_benchmark 계산          │
│  → company_benchmark_delta 계산 (회사 vs peer/industry)           │
│  → ⭐ benchmark_basis, benchmark_confidence 필드 함께 저장         │
│                                                                  │
│  Task 3.5: calculate_relative_metrics  ← ⚠️ Task 3 이후 실행     │
│  → rev_growth_vs_industry = 자사 매출 성장률 - industry median    │
│  → Task 3에서 계산된 industry_metric_benchmark 참조 (순환 해소)    │
│  → company_metric_snapshot + benchmark_delta 업데이트              │
│                                                                  │
│  Task 4: calculate_category_signals                              │
│  → benchmark_delta + metric_definition 기반                       │
│  → ⭐ category_signal 계산 (green/yellow/red/gray 신호등)         │
│  → value_status가 normal인 지표만 신호 계산에 포함                │
│  → handling_mode='special' 산업은 해당 카테고리 gray 처리          │
│                                                                  │
│  Task 5: update_peer_list_cache                                  │
│  → ⭐ industry + size bucket 기반 peer 목록 갱신                  │
│  → peer 수 + benchmark_basis 기반 confidence 계산                 │
│  → peer_tier는 null (Phase 2에서 Chain Sight 연계 시 활성화)      │
│                                                                  │
│  ──────────────── 모두 완료 후 ────────────────                   │
│                                                                  │
│  Task 6: log_batch_run                                           │
│  → batch_job_run 테이블에 실행 결과 기록                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 배치 스케줄

```python
# config/celery.py

CELERY_BEAT_SCHEDULE = {
    'validation-weekly-batch': {
        'task': 'validation.tasks.run_weekly_validation_batch',
        'schedule': crontab(day_of_week='sunday', hour=2, minute=0),  # 일요일 새벽 2시
        'kwargs': {'universe': 'sp500'}  # S&P 500 먼저
    },
}
```

**Celery 실행 코드:**

```python
# validation/tasks.py
from celery import chain

def run_weekly_validation_batch(universe='sp500'):
    """주간 배치 오케스트레이터. Task간 순차 보장."""
    symbols = get_universe_symbols(universe)

    pipeline = chain(
        fetch_all_financials.s(symbols),
        calculate_all_derived_metrics.s(),       # rev_growth_vs_industry 제외, value_status 판정
        calculate_all_benchmarks.s(),             # industry + size bucket peer
        calculate_relative_metrics.s(),           # Task 3 결과 참조
        calculate_all_category_signals.s(),       # ⭐ category_score → category_signal
        update_all_peer_list_caches.s(),
        log_batch_run.s(universe),
    )
    pipeline.apply_async()
```

### 6.3 FMP API 호출 전략

```
S&P 500 = 503개 종목
FMP Starter 플랜: 300 calls/min, 10,000 calls/day

종목당 필요 API 호출:
  - income-statement (annual, limit=5)  → 1 call
  - balance-sheet-statement (annual)    → 1 call
  - cash-flow-statement (annual)        → 1 call
  - key-metrics (annual)                → 1 call
  - profile (company info)              → 1 call (변경 시에만)
  합계: 4~5 calls/종목

503 × 4 = 2,012 calls → 일일 한도 10,000 내 여유
503 × 4 / 300 = ~7분 (rate limit 기준)

실행 전략:
  - 일요일 새벽 배치 1회
  - 실패 시 재시도 3회 (exponential backoff)
  - 종목별 독립 실행 (한 종목 실패해도 나머지 계속)
```

**⚠️ FMP 연간 이력 제한 확인 필요:**

- FMP Starter 플랜에서 `limit` 파라미터로 연간 재무제표 최대 반환 건수가 제한될 수 있음.
- 확인 필요: `GET /income-statement/AAPL?period=annual&limit=5`로 실제 5년 반환되는지 테스트.
- 만약 3~4년만 반환되는 경우: 차트 X축을 가용 데이터 연도에 맞게 동적 조정 (최소 3년).

---

## 7. 데이터 모델 변경 사항

### 7.1 테이블명 변경

| 기존 (v1.2)      | 변경 (v1.3)       | 이유                                             |
| ---------------- | ----------------- | ------------------------------------------------ |
| `category_score` | `category_signal` | 숫자 점수보다 신호등 상태가 핵심이므로 이름 일치 |

### 7.2 `company_metric_snapshot`에 추가 필드

```python
class CompanyMetricSnapshot(models.Model):
    # ... 기존 필드 ...

    # ⭐ v1.3 추가
    value_status = models.CharField(
        max_length=20,
        choices=[
            ('normal', '정상'),
            ('missing', '데이터 누락'),
            ('not_applicable', '해당 없음'),
            ('unstable', '값 불안정'),
            ('low_confidence', '신뢰도 낮음'),
        ],
        default='normal',
        help_text="배치에서 판정. 프론트에서 표시 분기 기준."
    )
    exclusion_reason = models.CharField(
        max_length=100, blank=True, default='',
        help_text="not_applicable/unstable일 때 사유. e.g. '흑자 기업', '값 변동 과대'"
    )
```

**value_status 판정 로직 (Task 2에서 실행):**

```python
def determine_value_status(metric_code, value, company_info):
    """배치 시점에 value_status 판정."""

    # not_applicable 판정
    if metric_code == 'cash_runway_years' and company_info.is_profitable:
        return 'not_applicable', '흑자 기업'
    if metric_code == 'interest_coverage' and company_info.total_debt == 0:
        return 'not_applicable', '무차입 기업'
    if metric_code == 'interest_coverage' and interest_expense == 0:
        return 'not_applicable', '이자비용 없음'
    if metric_code == 'interest_coverage' and interest_expense is None:
        return 'missing', '이자비용 데이터 미제공'
    if metric_code in ('inventory_turnover_days', 'inventory_vs_sales_growth') \
       and company_info.inventory == 0:
        return 'not_applicable', '서비스 기업 (재고 없음)'

    # missing 판정
    if value is None:
        return 'missing', '데이터 미제공'

    # unstable 판정 (이전 연도 대비 극단적 변동)
    if metric_code == 'interest_coverage':
        # 이전 값 대비 부호 반전 + 절대값 10배 이상 변동
        if prev_value and ((value > 0) != (prev_value > 0)) and abs(value) > abs(prev_value) * 10:
            return 'unstable', '값 변동 과대'

    return 'normal', ''
```

### 7.3 `company_benchmark_delta`에 추가 필드

```python
class CompanyBenchmarkDelta(models.Model):
    # ... 기존 필드 ...

    # ⭐ v1.3 추가
    benchmark_basis = models.CharField(
        max_length=20,
        choices=[
            ('industry_size', '업종+규모'),     # Phase 1 기본
            ('industry', '업종 전체'),           # size 완화 fallback
            ('sector', '섹터 전체'),             # 최종 fallback
            # Phase 2 추가 예정:
            # ('strict_peer', 'Strict Peer'),
            # ('broad_peer', 'Broad Peer'),
        ],
        default='industry_size',
    )
    benchmark_confidence = models.CharField(
        max_length=10,
        choices=[
            ('high', '높음'),
            ('medium', '보통'),
            ('low', '낮음'),
            ('limited', '제한적'),
        ],
        default='high',
    )
```

### 7.4 `peer_list_cache`에 추가 필드

```python
class PeerListCache(models.Model):
    # ... 기존 필드 ...

    # ⭐ v1.3 추가
    benchmark_basis = models.CharField(max_length=20, default='industry_size')
    size_bucket = models.CharField(
        max_length=10,
        choices=[('mega', 'Mega'), ('large', 'Large'), ('mid', 'Mid'), ('small', 'Small')],
        null=True, blank=True,
    )
    peer_tier = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="Phase 2: Chain Sight 연계 시 strict/broad/industry 값 할당. Phase 1에서는 null."
    )
```

### 7.5 `industry_classification`에 추가 필드

```python
class IndustryClassification(models.Model):
    # ... 기존 필드 ...

    # ⭐ v1.3 추가
    handling_mode = models.CharField(
        max_length=10,
        choices=[
            ('standard', '일반'),
            ('special', '특수 산업'),
        ],
        default='standard',
        help_text="special: 금융/보험/REIT/유틸리티 등. 일부 카테고리 해석 제한 표시."
    )
```

**handling_mode='special' 대상 (Phase 1 초기 시딩):**

- Banks, Insurance, REIT, Utilities
- 이 산업의 기업은 재무구조 카테고리에서 gray 신호 + 고지문 표시

### 7.6 `category_signal` 테이블 (기존 category_score 대체)

```python
class CategorySignal(models.Model):
    """
    카테고리별 종합 신호. category_score에서 이름 변경.
    score는 내부 계산용으로 유지하되, UI에서는 signal만 표시.
    """
    symbol = models.CharField(max_length=20, db_index=True)
    category = models.CharField(max_length=30)
    fiscal_year = models.IntegerField()

    signal = models.CharField(
        max_length=10,
        choices=[('green', '양호'), ('yellow', '주의'), ('red', '경고'), ('gray', '해석 제한')],
    )
    score = models.FloatField(
        null=True, blank=True,
        help_text="내부 계산용. percentile 균등 평균. UI 미노출."
    )
    signal_reason = models.CharField(max_length=200)
    metric_count = models.IntegerField(help_text="이 카테고리의 총 지표 수")
    valid_metric_count = models.IntegerField(help_text="score 계산에 사용된 지표 수")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'category_signal'
        unique_together = ('symbol', 'category', 'fiscal_year')
```

---

## 8. LLM 활용 전략 (Phase 2 이후 검토)

### 8.1 Phase 1: Rule-based Only

Phase 1에서는 모든 해석 텍스트를 rule-based로 생성한다.
LLM 배치 캐싱은 Phase 1 구현 완료 후, 실제 데이터와 UI를 확인한 뒤에 도입 여부를 결정한다.

**이유:**

- peer/benchmark 설계가 핵심이고, LLM은 그 위에 얹는 보조 레이어
- rule-based 해석만으로도 사용자에게 충분한 정보 제공 가능
- LLM 배치 인프라(Gemini API 연동, sanity check, idempotency) 구축 비용을 Phase 1에서 분리

### 8.2 Phase 2 LLM 도입 시 구조 (참고용)

Phase 2에서 LLM을 도입할 경우, 아래 구조를 따른다.

**`validation_ai_cache` 테이블:**

```python
class ValidationAICache(models.Model):
    """Phase 2에서 추가. LLM 생성 텍스트 캐시."""
    CACHE_TYPES = [
        ('company_summary', '종합 요약'),
        ('metric_interpretation', '지표 해석'),
        ('leader_analysis', '대장주 경쟁력 분석'),
    ]
    symbol = models.CharField(max_length=20, db_index=True)
    cache_type = models.CharField(max_length=30, choices=CACHE_TYPES)
    cache_key = models.CharField(max_length=50, default='')
    content = models.TextField()
    fiscal_year = models.IntegerField()
    model_version = models.CharField(max_length=50, default='gemini-2.5-flash')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'validation_ai_cache'
        unique_together = ('symbol', 'cache_type', 'cache_key')
```

**도입 시 배치 파이프라인에 Task 추가:**

- Task 6.5: generate_ai_texts (LLM 배치) → validation_ai_cache 저장
- API View에서: 캐시 있으면 AI 텍스트, 없으면 기존 rule-based fallback
- 사용자 경험 무변경 (텍스트 품질만 향상)

### 8.3 Rule-based 해석 미사용 영역 (전부 순수 계산)

| 기능                                | 방식                                                |
| ----------------------------------- | --------------------------------------------------- |
| 신호등 판정 (green/yellow/red/gray) | percentile 기반 + value_status 필터                 |
| 추세 판단 (가속/감속/유지)          | 3년 값 방향 비교                                    |
| 산업 순위                           | SQL 정렬 + 백분위 계산                              |
| 카테고리 신호                       | 소속 지표 percentile_rank 균등 평균 (normal 지표만) |
| value_status 판정                   | 하드코딩 규칙 (metric_code별)                       |
| null 처리 메시지                    | 하드코딩 ("해당 없음 (흑자 기업)" 등)               |
| 특수 산업 고지                      | handling_mode 기반                                  |

---

## 9. 프론트엔드 구현 계획

### 9.1 컴포넌트 구조

```
src/
├── components/
│   └── stock-detail/
│       ├── StockDetailLayout.tsx          # 전체 레이아웃 + L1/L2 탭
│       ├── PrimaryTabNav.tsx              # L1: 기본정보 | 뉴스 | 분석 및 검증
│       ├── SecondaryTabNav.tsx            # L2: 각 L1 하위 탭
│       │
│       ├── fundamentals/                  # 기본정보 탭 하위 (기존 유지)
│       │   ├── OverviewTab.tsx
│       │   ├── BalanceSheetTab.tsx
│       │   ├── IncomeStatementTab.tsx
│       │   ├── CashFlowTab.tsx
│       │   └── OtherFundamentalTab.tsx
│       │
│       ├── news/                          # 뉴스 탭 (기존 유지)
│       │   └── NewsTab.tsx
│       │
│       └── analysis/                      # 분석 및 검증 탭
│           ├── ValidationTab.tsx           # 1차 검증 메인 컴포넌트
│           ├── ChainSightTab.tsx           # Chain Sight (기존 이동)
│           │
│           └── validation/                # 1차 검증 하위 컴포넌트
│               ├── SignalSummaryCard.tsx   # ① 종합 요약
│               ├── PeerContextBar.tsx     # ② Peer 정보 (benchmark_basis 표시)
│               ├── CategorySection.tsx    # ③ 카테고리 섹션 (반복)
│               ├── MetricCard.tsx         # 개별 지표 카드 (value_status 분기)
│               ├── MetricBarChart.tsx     # 막대 차트 (Recharts)
│               ├── CategorySidebar.tsx    # ④ 사이드바 네비
│               ├── IndustryPosition.tsx   # ⑤ 산업 위치
│               └── LeaderComparison.tsx   # 업종 리더 비교
│
├── hooks/
│   └── useValidation.ts                   # TanStack Query hooks
│
└── types/
    └── validation.ts                      # TypeScript 타입 정의
```

### 9.2 TanStack Query 훅

```typescript
// hooks/useValidation.ts

export function useValidationSummary(symbol: string) {
	return useQuery({
		queryKey: ["validation", "summary", symbol],
		queryFn: () => fetchValidationSummary(symbol),
		staleTime: 1000 * 60 * 60, // 1시간 (배치 데이터이므로 자주 안 변함)
		gcTime: 1000 * 60 * 60 * 24, // 24시간 캐시
	});
}

export function useValidationMetrics(symbol: string, category?: string) {
	return useQuery({
		queryKey: ["validation", "metrics", symbol, category],
		queryFn: () => fetchValidationMetrics(symbol, category),
		staleTime: 1000 * 60 * 60,
	});
}

export function useLeaderComparison(symbol: string) {
	return useQuery({
		queryKey: ["validation", "leader", symbol],
		queryFn: () => fetchLeaderComparison(symbol),
		staleTime: 1000 * 60 * 60,
	});
}
```

### 9.3 차트 라이브러리

**Recharts** 사용. `ComposedChart`로 Bar + Scatter + ErrorBar 조합.

```typescript
// validation/MetricBarChart.tsx

import { ComposedChart, Bar, Scatter, XAxis, YAxis, CartesianGrid,
         Tooltip, Legend, Cell, ErrorBar, ResponsiveContainer } from 'recharts';

interface MetricBarChartProps {
  history: ChartDataPoint[];
  unit: string;
  higherIsBetter: boolean;
}

interface ChartDataPoint {
  fiscal_year: number;
  company_value: number;
  peer_median: number;
  peer_p25: number;
  peer_p75: number;
  // ErrorBar용 계산 필드 (데이터 가공 시 추가)
  errorY: [number, number]; // [median - p25, p75 - median]
}

/**
 * 막대 색상 결정 — higher_is_better에 따라 로직 반전
 */
function getSignalColor(
  value: number, p25: number, p75: number, higherIsBetter: boolean
): string {
  if (higherIsBetter) {
    if (value >= p75) return 'var(--color-green)';
    if (value <= p25) return 'var(--color-red)';
    return 'var(--color-yellow)';
  } else {
    if (value <= p25) return 'var(--color-green)';
    if (value >= p75) return 'var(--color-red)';
    return 'var(--color-yellow)';
  }
}

/**
 * 구현 구조:
 * - ComposedChart: Bar + Scatter + ErrorBar 조합
 * - Bar: 이 기업 값 (색상은 peer 대비 위치에 따라 green/yellow/red)
 * - Scatter (shape=dash): peer 중앙값 가로선 마커
 * - ErrorBar on Scatter: peer p25~p75 범위 세로선
 *
 * 이 방식은 커스텀 SVG 오버레이 없이 Recharts 내장 컴포넌트만으로 구현 가능.
 */
export function MetricBarChart({ history, unit, higherIsBetter }: MetricBarChartProps) {
  // ErrorBar용 데이터 가공
  const chartData = history.map(d => ({
    ...d,
    errorY: [d.peer_median - d.peer_p25, d.peer_p75 - d.peer_median] as [number, number],
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={chartData} barCategoryGap="25%">
        <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
        <XAxis dataKey="fiscal_year" />
        <YAxis tickFormatter={(v) => formatMetricValue(v, unit)} />

        {/* 이 기업 값 막대 */}
        <Bar dataKey="company_value" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {chartData.map((entry, index) => (
            <Cell
              key={index}
              fill={getSignalColor(entry.company_value, entry.peer_p25, entry.peer_p75, higherIsBetter)}
            />
          ))}
        </Bar>

        {/* peer 중앙값 마커 + p25-p75 범위 */}
        <Scatter dataKey="peer_median" shape="dash" fill="var(--color-muted)">
          <ErrorBar dataKey="errorY" width={12} strokeWidth={1.5} stroke="var(--color-muted)" />
        </Scatter>

        <Tooltip content={<MetricTooltip unit={unit} />} />
        <Legend
          payload={[
            { value: '이 기업', type: 'rect', color: 'var(--color-primary)' },
            { value: 'peer 중앙값', type: 'plainline', color: 'var(--color-muted)' },
            { value: 'peer p25~p75', type: 'plainline', color: 'var(--color-muted)' },
          ]}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
```

---

## 10. 구현 우선순위 및 일정

### Phase 1: 기반 (1~2주)

```
□ 네비게이션 재설계 (L1/L2 탭 구조)
  - PrimaryTabNav, SecondaryTabNav 컴포넌트
  - 라우팅 (query param 방식)
  - 기존 탭 내용 이동 (breaking change 없이)

□ Django validation 앱 API 기본 세팅
  - URL 구조, ViewSet 등록
  - Serializer 기본 틀

□ DB 마이그레이션
  - category_signal 테이블 (category_score 대체)
  - company_metric_snapshot에 value_status, exclusion_reason 추가
  - company_benchmark_delta에 benchmark_basis, benchmark_confidence 추가
  - peer_list_cache에 benchmark_basis, size_bucket, peer_tier(nullable) 추가
  - industry_classification에 handling_mode 추가
```

### Phase 2: 배치 + 데이터 (2~3주)

```
□ metric_definition 초기 데이터 로딩 (34개 지표 seed)
□ industry_classification handling_mode 초기 시딩 (금융/보험/REIT/유틸리티 = special)
□ Celery Task 1: FMP 연간 재무제표 수집
□ Celery Task 2: 33개 지표 계산 + value_status 판정
□ Celery Task 3: peer 선정 (industry + size bucket) + benchmark 계산 + benchmark_basis/confidence 저장
□ Celery Task 3.5: 상대 지표 계산
□ Celery Task 4: category_signal 계산 (gray 포함)
□ Celery Task 5: peer_list_cache 갱신
□ Celery Task 6: batch_job_run 로깅
□ S&P 500 대상 첫 배치 실행 및 검증
□ FMP Starter 플랜 5년 이력 반환 확인 테스트
```

### Phase 3: 프론트엔드 (2~3주)

```
□ ValidationTab 메인 컴포넌트
□ SignalSummaryCard (종합 요약 — 신호등 + rule-based 한줄 요약)
□ PeerContextBar (benchmark_basis, size_bucket, confidence 표시)
□ CategorySection + MetricCard (value_status 분기 렌더링)
□ MetricBarChart (Recharts ComposedChart — Bar + Scatter + ErrorBar)
□ CategorySidebar (Sticky)
□ IndustryPosition + LeaderComparison (rule-based 요약)
□ 반응형 (모바일: Accordion 지표 카드 + 카테고리 Chip 필터)
```

### Phase 4: 연결 및 폴리시 (1주)

```
□ Chain Sight 탭 이동 (분석 및 검증 하위로)
□ 로딩 상태, 에러 처리, 빈 데이터 처리
□ 데이터 없는 지표의 graceful fallback (value_status 기반)
□ 특수 산업 고지문 표시 (handling_mode='special')
□ 성능 최적화 (TanStack Query 캐싱)
□ 데이터 기준일 표시, 새로고침 안내
```

### Phase 5: LLM 도입 검토 (Phase 4 완료 후)

```
□ Phase 1~4 결과물 검토: rule-based 해석 품질 평가
□ LLM 도입 결정 시:
  - validation_ai_cache 테이블 마이그레이션
  - Gemini 2.5 Flash 배치 생성 Task 추가
  - sanity check + idempotency 로직
  - 3종 텍스트: company_summary, metric_interpretation, leader_analysis

□ Chain Sight 재구축 연계 (별도 프로젝트):
  - business_model_tag 기반 strict/broad peer 분류
  - peer_list_cache.peer_tier 활성화
  - benchmark_basis에 strict_peer, broad_peer 추가
```

**Empty State UI 정의 (반드시 구현):**

```
[Case 1: 배치 미실행 — 종목 데이터가 전혀 없음]
┌─────────────────────────────────────────┐
│  📊 재무 분석 데이터 준비 중             │
│                                         │
│  이 종목의 분석 데이터는 아직            │
│  준비되지 않았습니다.                    │
│  매주 일요일에 자동 업데이트됩니다.       │
│                                         │
│  기본정보 탭에서 재무제표 원본을          │
│  확인할 수 있습니다.                     │
│  [기본정보 보기 →]                       │
└─────────────────────────────────────────┘

[Case 2: 부분 데이터 — 일부 카테고리만 계산됨]
→ 데이터 있는 카테고리는 정상 표시
→ 없는 카테고리: "이 카테고리의 데이터는 아직 준비 중입니다"
→ 종합 요약: 가용 카테고리만으로 계산 + "N개 카테고리 기준"

[Case 3: 개별 지표 null / 특수 상태]
→ value_status에 따른 분기 표시 (섹션 3.3 참조)
→ not_applicable: "이 기업에 해당하지 않는 지표입니다" + exclusion_reason
→ unstable: 차트 표시 + ⚠️ 경고
→ low_confidence: 차트 표시 + ⚠️ "비교 표본 부족"

[Case 4: S&P 500 외 종목]
┌─────────────────────────────────────────┐
│  ⓘ S&P 500 외 종목                      │
│                                         │
│  현재 1차 검증은 S&P 500 종목을          │
│  대상으로 제공됩니다.                    │
│  향후 대상 범위를 확대할 예정입니다.      │
└─────────────────────────────────────────┘

[Case 5: 특수 산업 (handling_mode='special')]
→ 해당 카테고리 신호등 = gray
→ "금융업(또는 REIT/유틸리티) 특성상 일반 기업과 다른 기준이 적용됩니다"
→ 데이터는 표시하되 신호등 판정은 보류
```

**예상 총 기간: 6~9주 (1인 개발 기준, LLM 제외)**

---

## 11. 핵심 설계 결정 요약

| 결정 사항             | 선택                                                          | 이유                                                              |
| --------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------- |
| 데이터 업데이트 방식  | 주 1회 배치                                                   | 연간 재무제표 기반, 실시간 불필요                                 |
| 해석 텍스트 (Phase 1) | Rule-based only                                               | LLM 인프라 비용 분리, 충분한 정보 제공 가능                       |
| 해석 텍스트 (Phase 2) | LLM 배치 캐싱 + Rule-based fallback 검토                      | Phase 1 결과 확인 후 결정                                         |
| 차트 유형             | ComposedChart (Bar + Scatter + ErrorBar)                      | Recharts 내장 컴포넌트만으로 peer range 구현, SVG 오버레이 불필요 |
| 신호등 기준           | percentile 기반 통일 (≥65 green, 35~65 yellow, <35 red, gray) | 카테고리/지표 간 기준 일관성                                      |
| 카테고리 신호         | signal 중심 (score는 내부 계산용)                             | UI에서 숫자보다 상태가 직관적                                     |
| 테이블명              | `category_signal` (기존 category_score에서 변경)              | 역할과 이름 일치                                                  |
| peer 선정 (Phase 1)   | industry + size bucket                                        | 단순하면서 효과적, 1인 개발 적합                                  |
| peer 선정 (Phase 2)   | Chain Sight 연계 strict/broad/industry 3단계                  | 10-K 파싱 + 커뮤니티 탐지로 자동화                                |
| size bucket           | mega/large/mid/small (market_cap 기준)                        | 규모 왜곡 방지                                                    |
| value_status          | normal/missing/not_applicable/unstable/low_confidence         | 프론트 분기 로직 단순화, 배치에서 미리 판정                       |
| benchmark_basis       | industry_size/industry/sector (Phase 1)                       | 어떤 기준으로 비교했는지 투명하게 표시                            |
| 특수 산업             | handling_mode='special' 플래그                                | 금융/REIT 등 오해 방지, Phase 1은 고지문만                        |
| 대장주 비교           | 1:1 비교 (market_cap 기준 peer 내 1위)                        | 직관적 UX 가치 유지                                               |
| 대장주 자기 자신      | market_cap 2위와 비교, peer 2개 미만이면 비표시               | edge case 대응                                                    |
| 밸류에이션            | 보조 카테고리 (접힘)                                          | 단독 판단 위험, 참고용으로만                                      |
| 모바일                | 카테고리 Chip + Accordion 지표 카드                           | 스크롤 압박 방지, 접힌 상태에서 핵심 정보만 노출                  |
| API 분할              | summary + metrics (카테고리별 lazy load)                      | 모바일 ~15KB/카테고리, 데스크톱만 all 사용                        |
| Task 실행 순서        | Celery `chain()` 순차 보장                                    | Task 3.5(상대 지표)가 Task 3(벤치마크) 의존                       |

---

## 12. 리스크 및 대응

| 리스크                    | 영향                         | 대응                                                                     |
| ------------------------- | ---------------------------- | ------------------------------------------------------------------------ |
| FMP API 장애              | 배치 실패                    | 재시도 3회 + 이전 데이터 유지 (stale but available)                      |
| FMP 연간 이력 제한        | 5년 차트 불가                | 가용 연도에 맞게 동적 조정 (최소 3년), 배치 전 테스트                    |
| peer 수 부족 (niche 산업) | benchmark 신뢰도 저하        | size bucket 완화 → industry fallback → sector fallback + confidence 표시 |
| 지표 계산 오류            | 잘못된 신호등                | unit test + 배치 후 sanity check (이상치 로그)                           |
| 재무제표 데이터 gap       | 특정 연도 누락               | value_status='missing' + 차트에서 빈 구간 표시                           |
| 극단적 지표 변동          | 잘못된 해석                  | value_status='unstable' + ⚠️ 경고 표시                                   |
| 프론트 렌더링 성능        | 34개 차트 동시 로드          | 카테고리별 lazy render (IntersectionObserver)                            |
| 특수 산업 오해석          | 금융주 재무구조 빨간불       | handling_mode='special' → gray 신호 + 고지문                             |
| peer 시간 변동            | 과거 연도 benchmark 부정확   | 현재 peer 기준 계산 + UI 고지                                            |
| 자기가 대장주             | 자기 자신과 비교             | market_cap 2위와 비교, 2개 미만이면 비표시                               |
| size bucket 경계 기업     | bucket 간 이동으로 peer 변동 | ±1 bucket 허용으로 완화, 배치 간 급변 방지                               |

---

## 부록 A. v1.2 → v1.3 변경 이력

| 항목              | v1.2                        | v1.3                                      | 변경 이유                                |
| ----------------- | --------------------------- | ----------------------------------------- | ---------------------------------------- |
| Peer 선정         | industry 기반 단순 그룹     | industry + size bucket + fallback 체계    | 규모 왜곡 방지, benchmark 신뢰도 향상    |
| value_status      | 없음 (null만 체크)          | 5단계 상태 (normal~low_confidence)        | 프론트 분기 단순화, unstable 케이스 대응 |
| benchmark_basis   | benchmark_type: "peer" 정도 | industry_size/industry/sector 명시        | 비교 기준 투명성 확보                    |
| 특수 산업         | 없음                        | handling_mode='special' 플래그            | 금융/REIT 오해석 방지                    |
| 테이블명          | category_score              | category_signal                           | 역할과 이름 일치                         |
| LLM               | Phase 1 배치 캐싱 포함      | Phase 1 제외, Phase 2 검토                | 핵심(peer/benchmark)에 집중, LLM은 이후  |
| Phase 2 peer 확장 | 미정                        | Chain Sight 연계 (10-K 파싱 + 클러스터링) | 중복 시스템 방지, 자동 태깅              |
| 배치 Task         | 7개 (LLM 포함)              | 6개 (LLM Task 제거)                       | Phase 1 범위 축소                        |

## 부록 B. v1.3 → v1.4 변경 이력

| 항목              | v1.3                           | v1.4                                          | 변경 이유                                   |
| ----------------- | ------------------------------ | --------------------------------------------- | ------------------------------------------- |
| 차트 구현         | BarChart + "구현 시 확정 필요" | ComposedChart (Bar + Scatter + ErrorBar) 확정 | 커스텀 SVG 불필요, Recharts 내장만으로 구현 |
| 모바일 UX         | 지표 카드 세로 나열            | Accordion (접힌 상태 기본, 탭 시 펼침)        | 34개 지표 스크롤 압박 방지                  |
| interest_coverage | total_debt==0만 체크           | interestExpense 0 vs null 구분 추가           | FMP 데이터 정합성 강화                      |
