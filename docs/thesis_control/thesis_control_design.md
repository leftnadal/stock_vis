# Thesis Control (가설 통제실) — 설계 문서

> 버전: 1.0  
> 작성일: 2026-02-27  
> 상태: 설계 단계

---

## 1. 개요

### 1.1 컨셉

Thesis Control은 투자자가 시장에 대한 가설을 세우고, AI가 추천한 지표를 통해 가설의 흐름을 모니터링하는 기능이다. 영화 빅쇼트에서 마이클 버리가 여러 지표를 관측하며 최종 결정을 내리는 과정에서 영감을 받았다.

핵심 가치: **"예측이 아니라 관찰, 숫자가 아니라 흐름, 판단의 주체는 항상 사용자"**

### 1.2 Stock-Vis 내 위치

| 기능                         | 역할                                | 단계 |
| ---------------------------- | ----------------------------------- | ---- |
| **Chain Sight**              | 종목 간 관계 탐색 + Node Monitoring | 발견 |
| **Thesis Control**           | 가설 설정 → 지표 추적 → 모니터링    | 판단 |
| **Portfolio Planner** (가제) | 포트폴리오 설계/관리                | 실행 |

사용자 여정: **발견 → 판단 → 실행**

### 1.3 핵심 설계 원칙

1. **엄지 우선**: 모든 조작은 한 손 엄지로 가능. 탭 > 스와이프 > 선택 > 타이핑 순서. 타이핑은 사용자의 고유한 생각을 입력할 때만.
2. **느낌 전달**: 명확한 숫자(67.3%)가 아니라 방향성(화살표), 색상(빨강/파랑), 흐름(그래프 선)으로 "내 가설이 맞아가고 있는 느낌" 또는 "다르게 움직이는 느낌"을 전달.
3. **자연스러운 학습**: 초보자도 가설을 세우고 지표를 보면서 자연스럽게 투자 분석 역량을 키움. 강제 교육 없이, [근거] 버튼으로 궁금할 때만 깊이를 탐색.
4. **AI는 조산사**: AI가 답을 주는 게 아니라 사용자의 생각을 끌어내고 정리하고 관련 데이터를 연결해주는 역할.

---

## 2. 사용자 플로우

### 2.1 전체 흐름

```
[진입] Thesis Control 첫 화면
  ↓
[가설 설립] AI 대화형 플로우 (탭 기반)
  ↓
[지표 설정] AI 자동 추천 + 사용자 커스텀
  ↓
[모니터링] 관제실 대시보드 (카드/히트맵/그래프 뷰)
  ↓
[변화 감지] 푸시 알림 → 재방문
  ↓
[가설 마감] 복기 및 아카이브
```

### 2.2 첫 화면

```
┌─────────────────────────────────┐
│  Thesis Control                 │
│  가설 통제실                     │
│                                 │
│  ─── 관제 중 ───                │
│  📌 KOSPI 하락 | 지지 중 🟧     │
│  📌 2차전지 반등 | 약화 중 🟦    │
│                                 │
│  ─── 오늘의 변화 ───            │
│  🔔 "KOSPI 하락" 가설에 변화!    │
│     외국인 순매도 전환 감지       │
│     [확인하기]                   │
│                                 │
│  ─── 새로운 가설 ───            │
│  [💬 내 생각] [📰 오늘 이슈]     │
│  [🔥 인기 가설] [📋 템플릿]      │
│  [🔗 Chain Sight에서]           │
└─────────────────────────────────┘
```

**세 구역:**

- 관제 중: 기존 가설 상태 한눈에 확인
- 오늘의 변화: 어젯밤 사이의 변화 (매일 다른 내용 → 재방문 동기)
- 새로운 가설: 5가지 진입점

### 2.3 가설 설립 — 5가지 진입 경로

#### 경로 1: 📰 오늘 이슈 (메인 경로)

매일 내용이 바뀌어 재방문 동기를 제공하는 가장 핵심적인 진입점.

```
사용자: [📰 오늘 이슈] 👆

AI: "오늘의 시장 이슈예요.

    🇰🇷 국내
    📰 코스피 2,800 돌파, 6거래일 연속 상승  [이걸로 시작]
    📰 삼성전자 HBM3E 양산 본격화          [이걸로 시작]

    🌍 글로벌
    📰 미 연준 3월 FOMC 금리 동결 전망      [이걸로 시작]
    📰 원/달러 환율 1,380원대 하락          [이걸로 시작]

    🔥 화제
    📰 엔비디아 실적 발표 앞두고 변동성 확대  [이걸로 시작]"
```

```
사용자: "코스피 2,800 돌파" [이걸로 시작] 👆

AI: "코스피가 계속 오르고 있네요.
    이 흐름이 어떻게 될 것 같아요?"

    [계속 오른다] [곧 꺾인다] [잘 모르겠어]
```

```
사용자: [곧 꺾인다] 👆

AI: "왜 그렇게 생각하세요?
    여러 개 골라도 돼요."

    [선거/정치 기대감 소멸] [기업 실적 부진]
    [외국인 매도 전환] [글로벌 리스크]
    [과열/거품] [수급 변화]
    [✏️ 다른 이유]
```

```
사용자: [선거/정치 기대감 소멸] [외국인 매도 전환] 👆👆

AI: "선거 쪽을 좀 더 구체적으로 물어볼게요.
    어떤 이벤트를 생각하고 있어요?"

    [6월 지방선거] [정권 정책 변화] [기타 정치 이벤트]
    [딱히 특정 이벤트는 아니야]
```

```
사용자: [6월 지방선거] 👆

AI: "그리고 외국인 매도 전환은
    어떤 맥락에서 생각하고 있어요?"

    [미국 시장으로 자금 회귀] [환율 부담]
    [한국 시장 매력 감소] [잘 모르겠어, 그냥 느낌]
```

```
사용자: [미국 시장으로 자금 회귀] 👆

AI: "좋아요, 정리해볼게요.

    📌 가설: KOSPI 하락

    전제 1: 6월 지방선거 이후 정치 기대감 소멸
    전제 2: 미국 시장으로 외국인 자금 회귀

    어때요?"

    [좋아, 이대로 가자] [수정할 부분 있어] [전제 추가할래]
```

```
사용자: [좋아, 이대로 가자] 👆

AI: "하나만 더요.
    대략 언제쯤, 얼마나 빠질 것 같아요?"

    시점: [선거 직후] [하반기 중] [연말쯤] [모르겠어]
    강도: [살짝 조정] [꽤 빠진다] [크게 빠진다] [모르겠어]
```

```
사용자: [하반기 중] [꽤 빠진다] 👆👆

AI: "가설 등록 완료! 🎯

    📌 KOSPI 하락
    📉 Bearish | 하반기 중 | 꽤 빠진다

    전제:
    · 6월 지방선거 후 정치 기대감 소멸
    · 미국 시장으로 외국인 자금 회귀

    AI가 관련 지표 3개를 자동으로 달았어요.
    · 외국인 순매수 추이              [근거]
    · 원/달러 환율                    [근거]
    · S&P500 vs KOSPI 상관관계       [근거]

    지표는 언제든 수정할 수 있어요."

    [관제실 보기] [지표 수정하기] [알림 설정]
```

**경로 1 통계: 탭 8~10회, 타이핑 0회, 소요시간 1분**

#### 경로 2: 💬 내 생각 (확신 있는 사용자)

```
사용자: [💬 내 생각] 👆

AI: "편하게 써주세요.
    한 줄이어도 좋고, 길게 써도 돼요."

    [텍스트 입력창]
```

```
사용자: "코스피가 선거 끝나면 빠질 것 같아.
       지금 오르는 게 실적이 아니라 기대감이거든." ⌨️

AI: "정리해볼게요.

    📌 가설: KOSPI 하락

    전제 1: 현재 상승은 실적이 아닌 기대감에 의존
    전제 2: 선거 종료 시 기대감 소멸

    그리고 하나 더 생각해볼 게 있는데요.
    '실적이 아니라 기대감'이라는 건
    실적이 상승을 뒷받침 못한다는 의미이기도 해요.
    이것도 추적할까요?"

    [응, 추가해줘] [아니, 이대로 충분해]
```

```
사용자: [응, 추가해줘] 👆

AI: "가설 등록 완료! 🎯
    (... 지표 자동 설정 ...)"

    [관제실 보기] [지표 수정하기] [알림 설정]
```

**경로 2 통계: 탭 3~4회, 타이핑 1회, 소요시간 1~2분**

#### 경로 3: 🔥 인기 가설 (초보자 / 구경)

```
사용자: [🔥 인기 가설] 👆

AI: "이번 주 인기 가설이에요.

    🥇 코스피 3,000 연내 돌파
       1,240명 추적 중
       지지 ████████░░
       [구경하기] [나도 추적]

    🥈 2차전지 하반기 반등
       890명 추적 중
       지지 █████░░░░░
       [구경하기] [나도 추적]

    🥉 반도체 슈퍼사이클 재개
       760명 추적 중
       지지 ██████░░░░
       [구경하기] [나도 추적]"
```

```
사용자: 코스피 3,000 [구경하기] 👆

AI: "이 가설의 구조예요.

    📌 코스피 3,000 연내 돌파
    📈 Bullish | 2026년 내

    전제:
    · 기업 실적 회복세 지속         [근거]
    · 외국인 매수 기조 유지         [근거]
    · 글로벌 금리 인하 사이클 시작   [근거]

    추적 지표:
    · KOSPI EPS 추이        ↗ 지지  [근거]
    · 외국인 순매수          ↑ 지지  [근거]
    · 미국 기준금리          → 중립  [근거]

    어떠세요?"

    [나도 추적할래] [내 방식으로 수정] [다른 거 볼래]
```

[내 방식으로 수정] 선택 시:

```
AI: "어떤 부분을 바꾸고 싶어요?

    전제:
    ✅ 기업 실적 회복세 지속     [빼기]
    ✅ 외국인 매수 기조 유지     [빼기]
    ✅ 글로벌 금리 인하 시작     [빼기]
    [+ 전제 추가하기]

    방향:
    [📈 상승 그대로] [📉 반대로 하락으로]"
```

**경로 3 통계: 탭 3~4회, 타이핑 0회, 소요시간 30초**

#### 경로 4: 📋 템플릿

```
사용자: [📋 템플릿] 👆

AI: "어떤 유형의 가설을 세울까요?

    [📅 이벤트형] '어떤 이벤트 이후 무엇이 변한다'
    [📊 추세형] '현재 흐름이 계속된다 / 꺾인다'
    [⚖️ 비교형] 'A가 B보다 더 잘한다 / 못한다'
    [🔄 괴리형] 'A와 B의 차이가 좁혀진다 / 벌어진다'"
```

```
사용자: [📅 이벤트형] 👆

AI: "어떤 이벤트를 생각하고 있어요?

    최근 예정된 이벤트:
    [3월 FOMC] [삼성전자 실적발표]
    [6월 지방선거] [하반기 금리결정]
    [✏️ 직접 입력]"
```

```
사용자: [6월 지방선거] 👆

AI: "지방선거 이후 어떤 변화를 예상해요?

    [코스피 상승] [코스피 하락]
    [특정 섹터 수혜] [특정 섹터 타격]
    [환율 변동] [정책 변화]"
```

이후 대화형 플로우 → 가설 카드 생성

#### 경로 5: 🔗 Chain Sight에서

Chain Sight 화면에서 직접 진입:

```
[Chain Sight에서 삼성전자 노드를 보고 있는 중]

사용자: 삼성전자 노드 탭 → [📌 가설 세우기] 👆

→ Thesis Control 채팅이 열리면서:

AI: "삼성전자에 대한 가설을 세워볼까요?

    최근 삼성전자 관련 이슈:
    📰 HBM3E 양산 본격화
    📰 파운드리 수율 개선
    📰 KOSPI 지수 기여도 25% 돌파

    [이 이슈에서 시작] [내 생각이 있어]"
```

역방향도 지원: Thesis Control에서 가설 등록 완료 후 "Chain Sight에서 관련 종목 보기" 제안

#### 경로 분기: 잘 모르겠어 (양쪽 추적)

```
AI: "코스피가 계속 오르고 있네요.
    이 흐름이 어떻게 될 것 같아요?"

    [계속 오른다] [곧 꺾인다] [잘 모르겠어]
```

```
사용자: [잘 모르겠어] 👆

AI: "그러면 양쪽 다 추적해볼까요?

    가설 A: 📈 KOSPI 상승 지속
    가설 B: 📉 KOSPI 조정 임박

    둘 다 만들어두면 시장이 어느 쪽으로
    기우는지 비교하면서 볼 수 있어요."

    [둘 다 만들어줘] [하나만 고를래]
```

### 2.4 초보자 대응 — [근거] 시스템

모든 플로우에서 모르는 용어/개념이 나왔을 때, 흐름을 끊지 않으면서 학습할 수 있는 구조.

**버튼/선택지 롱프레스 → 용어 설명 팝업**

```
사용자: [수급 변화] 꾹 👆 (롱프레스)

┌─────────────────────────────────┐
│ 📖 수급 변화란?                   │
│ 주식을 사는 사람(매수)과 파는      │
│ 사람(매도)의 힘 균형이 바뀌는 걸   │
│ 말해요.                          │
│              [닫기]              │
└─────────────────────────────────┘
```

**전제 텍스트 탭 → 맥락 설명**

```
사용자: "전제 2: 미국 시장으로 외국인 자금 회귀" 탭 👆

AI: "외국인 투자자들은 여러 나라에 돈을
    나눠서 투자해요. 미국 시장이 더 매력적이면
    한국에서 돈을 빼서 미국으로 옮기는데,
    이때 한국 주식을 팔게 되니까
    코스피가 빠질 수 있어요."

    [이해했어] [좀 더 자세히]
```

**지표 옆 [근거] 탭 → 가설과의 연결 설명**

```
사용자: 외국인 순매수 옆 [근거] 👆

AI: "당신의 전제가 '외국인 자금 회귀'잖아요.
    외국인이 실제로 한국 주식을 팔고 있는지를
    매일 확인할 수 있는 지표예요.

    이 숫자가 마이너스(순매도)로 전환되면
    당신의 가설을 지지하는 신호가 됩니다."

    [이해했어]
```

**핵심:** 단순 용어 사전이 아니라 "네 가설과 왜 관련되는지"를 설명. 설명 후 원래 흐름으로 즉시 복귀. 3~4줄 이내 짧게, [좀 더 자세히]로 깊이 조절.

### 2.5 가설 설립 완료 → 지표 설정 분기

```
AI: "가설 등록 완료! 🎯
    AI가 추천 지표 3개를 자동으로 달아둘까요?
    나중에 수정할 수 있어요."

    [좋아, 일단 달아줘] → 자동 설정 → 모니터링 즉시 시작
    [내가 직접 고를래]  → 지표 설정 화면
    [나중에 할게]       → 가설만 저장
```

"좋아, 일단 달아줘"가 핵심 경로. 가설 세우기만 하면 즉시 살아있는 대시보드를 볼 수 있음.

---

## 3. 모니터링 단계

### 3.1 관제실 첫 화면

숫자가 아니라 "분위기"가 먼저 느껴지는 설계:

```
┌─────────────────────────────────┐
│  📌 KOSPI 하락                   │
│  등록: 2/25 | 32일째 관제 중      │
│                                 │
│          ◐                      │
│       전체 흐름                   │
│    내 가설 쪽으로 기울고 있어요     │
│                                 │
│  ┌────┐ ┌────┐ ┌────┐          │
│  │ 🟥 │ │ 🟧 │ │ 🟦 │          │
│  │ ↗  │ │ →  │ │ ↘  │          │
│  │외국인│ │환율 │ │S&P │          │
│  └────┘ └────┘ └────┘          │
│                                 │
│  최근 변화:                      │
│  "외국인 순매도 3일째 지속 중"     │
└─────────────────────────────────┘
```

### 3.2 전체 흐름 아이콘 (Moon Phase 메타포)

```
◉ 강하게 기울고 있어요        (진한 빨강)
◐ 기울고 있어요              (빨강)
◑ 아직 판단하기 이른 상태예요   (회색)
◐ 반대쪽으로 기울고 있어요     (파랑)
◉ 강하게 반대쪽이에요         (진한 파랑)
```

### 3.3 화살표 시스템

각 지표 카드에 표시되는 방향 화살표:

| 각도 | 화살표 | 의미        | 색상         |
| ---- | ------ | ----------- | ------------ |
| 0°   | ↑      | 강하게 지지 | 진한 빨강 🟥 |
| 45°  | ↗      | 지지하는 편 | 빨강/주황 🟧 |
| 90°  | →      | 중립        | 회색 ⬜      |
| 135° | ↘      | 약화하는 편 | 연한 파랑 🟦 |
| 180° | ↓      | 강하게 반박 | 진한 파랑 🟪 |

색상은 각도에 따라 그라데이션으로 연속 표현.

### 3.4 세 가지 뷰

화면 상단에서 탭 한번으로 전환:

```
[카드뷰] [히트맵] [그래프]
```

**카드뷰** — 개별 지표를 하나씩 자세히

```
┌──────────────────┐
│    ↗             │
│  외국인 순매수     │
│  지지하는 중 🟥    │
└──────────────────┘
```

**히트맵** — 전체를 한눈에 색으로 (Finviz 스타일)

```
┌───────┬───────┬───────┐
│ 🟥🟥  │ 🟧    │ ⬜    │
│외국인  │ 기관   │ 환율  │
├───────┼───────┼───────┤
│ 🟥    │ 🟦    │ 🟧    │
│정치    │ S&P   │ PER   │
└───────┴───────┴───────┘
빨간색 많을수록 가설 지지 흐름
```

**그래프뷰** — 시간 흐름을 선으로

```
지지 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
      ___
     /   \  ----___
─────────────────────── 중립
         \___/
반박 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─

── 외국인  ── 환율  ── S&P
```

Y축에 숫자 없음. "지지 / 중립 / 반박"만 표시. 선의 흐름으로 느끼는 구조.

### 3.5 모바일 제스처

| 제스처            | 동작                                 |
| ----------------- | ------------------------------------ |
| **탭**            | 지표 간단 해석 / 뷰 전환 / 버튼 선택 |
| **롱프레스**      | 지표 상세 차트                       |
| **좌우 스와이프** | 지표 간 이동 / 가설 간 이동          |
| **상하 스와이프** | 시간 범위 조절 (1주 ↔ 1개월 ↔ 3개월) |
| **쉐이크**        | 전체 요약 새로고침                   |

모든 화면에서:

- [근거] 탭 → 왜 이런 상태인지 설명
- [일단 지켜볼래] → 부담 없이 변화 알림 넘기기

### 3.6 지표 탭 시 해석

```
사용자: 외국인 순매수 카드 탭 👆

  외국인 순매수
  ↗ 지지하는 중

  매수세가 줄고 있지만
  아직 순매도 전환은 아니에요.
  전환되면 당신의 가설을
  강하게 지지하는 신호예요.

  3일 전 ↑ → 오늘 ↗
  (살짝 약해지는 중)

  [근거] [더 자세히]
```

숫자 대신 자연어 해석 + 화살표 변화로 방향 전달.

### 3.7 변화 감지 알림

```
푸시: "📌 KOSPI 하락 가설에 변화!
      외국인 순매수가 순매도로 전환"
      [확인하기]
```

확인 시:

```
AI: "외국인 순매수가 순매도로 전환됐어요.

    이 지표의 화살표가 바뀌었어요.
    ↗ (지지) → ↑ (강하게 지지)

    당신의 전제 '외국인 매도 전환'과
    일치하는 움직임이에요."

    [자세히 보기] [다른 지표도 확인]
```

반대 방향 변화 시:

```
AI: "환율이 예상과 다르게 움직이고 있어요.

    ↗ (지지) → ↘ (약화)

    외국인 자금 회귀를 전제로 했는데,
    환율 하락은 오히려 외국인 매수
    환경이 좋아지는 신호일 수 있어요.

    이 전제를 다시 생각해볼까요?"

    [전제 유지할래] [전제 수정할래] [일단 지켜볼래]
```

### 3.8 시간 경과에 따른 경험

**1주차:** "아직 데이터가 쌓이는 중이에요." → ◑ 회색

**2~3주차:** "지표들이 방향을 잡아가고 있어요." → ◐ 기울기 시작

**1~2개월차:** 전체 흐름 요약 + 변곡점 안내

**가설 시점 도래 시:**

```
AI: "당신이 예상한 시점이 다가왔어요.

    📌 KOSPI 하락 — 하반기 중

    이 가설을 어떻게 할까요?"

    [맞았어, 가설 마감] [좀 더 지켜볼래] [수정해서 연장]
```

### 3.9 가설 마감 — 복기

```
AI: "가설을 마감합니다.

    📌 KOSPI 하락 — 67일간 관제
    결과: 가설 방향과 일치 ✅

    가장 유용했던 지표:
    · 외국인 순매수 (초반부터 지지)

    예상과 달랐던 부분:
    · 환율은 반대로 움직였지만
      결과에 큰 영향은 없었어요

    이 경험이 기록으로 남았어요."

    [새 가설 세우기] [관제실로 돌아가기]
```

정확도 %가 아니라, "어떤 지표가 유용했고 어떤 건 아니었는지"를 정성적으로 전달. 가설 아카이브가 쌓이면서 사용자가 자기 투자 성향을 자연스럽게 파악.

---

## 4. 데이터 모델

### 4.1 새 Django 앱: thesis/

```
thesis/
├── models/
│   ├── __init__.py
│   ├── thesis.py          # Thesis, ThesisPremise
│   ├── indicator.py       # ThesisIndicator, IndicatorReading
│   ├── monitoring.py      # ThesisSnapshot, ThesisAlert
│   └── community.py       # ThesisFollow, PopularThesis
├── services/
│   ├── __init__.py
│   ├── thesis_builder.py      # 가설 구조화 (LLM 대화)
│   ├── indicator_matcher.py   # 전제→지표 매칭
│   ├── arrow_calculator.py    # 화살표 각도 계산
│   ├── monitoring_engine.py   # 모니터링 + 변화 감지
│   ├── news_connector.py      # 뉴스→가설 연결
│   └── summary_generator.py   # 상태 요약 생성 (LLM)
├── tasks/
│   ├── __init__.py
│   ├── daily_monitoring.py    # 일별 지표 업데이트
│   ├── alert_check.py         # 변화 감지 + 알림
│   └── news_scan.py           # 관련 뉴스 스캔
├── views/
│   ├── __init__.py
│   ├── thesis_views.py
│   ├── monitoring_views.py
│   └── community_views.py
├── serializers/
├── urls.py
└── admin.py
```

### 4.2 모델 상세

#### Thesis (가설)

```python
class Thesis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='theses')

    # 가설 내용
    title = models.CharField(max_length=200)          # "KOSPI 하락"
    description = models.TextField(blank=True)         # 원본 자연어 입력
    direction = models.CharField(max_length=10,        # bearish / bullish / neutral
        choices=[('bearish', 'Bearish'), ('bullish', 'Bullish'), ('neutral', 'Neutral')]
    )
    target = models.CharField(max_length=100)          # "KOSPI", "삼성전자", "2차전지 섹터"
    target_type = models.CharField(max_length=20,      # index / stock / sector / macro
        choices=[('index','Index'), ('stock','Stock'), ('sector','Sector'), ('macro','Macro')]
    )

    # 시점/강도 (nullable — "모르겠어" 선택 시)
    expected_timeframe = models.CharField(max_length=50, blank=True)   # "하반기 중"
    expected_magnitude = models.CharField(max_length=50, blank=True)   # "꽤 빠진다"
    target_date_start = models.DateField(null=True, blank=True)
    target_date_end = models.DateField(null=True, blank=True)

    # 가설 유형
    thesis_type = models.CharField(max_length=20,      # event / trend / comparison / divergence
        choices=[
            ('event', 'Event-driven'),
            ('trend', 'Trend'),
            ('comparison', 'Comparison'),
            ('divergence', 'Divergence'),
            ('custom', 'Custom')
        ]
    )

    # 진입 경로
    entry_source = models.CharField(max_length=20,     # news / free_input / popular / template / chainsight
        choices=[
            ('news', 'Today Issue'),
            ('free_input', 'Free Input'),
            ('popular', 'Popular Thesis'),
            ('template', 'Template'),
            ('chainsight', 'Chain Sight')
        ]
    )
    source_news = models.ForeignKey('news.NewsArticle', null=True, blank=True, on_delete=models.SET_NULL)
    copied_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    # 상태
    status = models.CharField(max_length=20, default='active',
        choices=[
            ('setting_up', 'Setting Up'),
            ('active', 'Active'),
            ('paused', 'Paused'),
            ('closed_correct', 'Closed - Correct'),
            ('closed_incorrect', 'Closed - Incorrect'),
            ('closed_neutral', 'Closed - Neutral'),
        ]
    )

    # 전체 흐름 점수 (화살표 계산용, 내부 사용)
    overall_score = models.FloatField(default=0.0)     # -1.0 (강한 반박) ~ 1.0 (강한 지지)
    overall_label = models.CharField(max_length=50, default='아직 이른 상태')

    # 태그
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    category = models.CharField(max_length=20, blank=True)  # macro / sector / event / supply

    # 알림 설정
    alert_preference = models.CharField(max_length=20, default='on_change',
        choices=[('daily', 'Daily'), ('on_change', 'On Change'), ('weekly', 'Weekly'), ('off', 'Off')]
    )

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]
```

#### ThesisPremise (전제)

```python
class ThesisPremise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='premises')

    content = models.TextField()                       # "6월 지방선거 이후 정치 기대감 소멸"
    extraction_level = models.CharField(max_length=20,  # explicit / implicit / ai_suggested
        choices=[
            ('explicit', 'User Stated'),               # 사용자가 직접 말한 것
            ('implicit', 'Implied'),                    # 사용자 말에서 추론
            ('ai_suggested', 'AI Suggested'),           # AI가 추가 제안
        ]
    )

    # 전제 상태 (사용자 선택)
    is_active = models.BooleanField(default=True)      # 사용자가 빼기로 한 경우 False

    # 전제별 현재 상태 (모니터링 결과)
    current_score = models.FloatField(default=0.0)     # -1.0 ~ 1.0
    current_label = models.CharField(max_length=50, default='추적 전')

    # 근거 설명 (LLM 생성)
    explanation = models.TextField(blank=True)          # [근거] 탭 시 보여줄 내용

    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
```

#### ThesisIndicator (지표)

```python
class ThesisIndicator(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='indicators')
    premise = models.ForeignKey(ThesisPremise, on_delete=models.CASCADE,
                                related_name='indicators', null=True, blank=True)

    # 지표 정의
    name = models.CharField(max_length=100)            # "외국인 순매수 추이"
    indicator_type = models.CharField(max_length=30,
        choices=[
            ('market_data', 'Market Data'),            # 주가, 수급, 거래량
            ('macro', 'Macro Economic'),               # 금리, 환율, VIX
            ('sentiment', 'News Sentiment'),           # 뉴스 감성분석
            ('technical', 'Technical'),                # RSI, MACD 등
            ('fundamental', 'Fundamental'),            # PER, EPS 등
            ('custom', 'Custom'),                      # 사용자 정의
        ]
    )

    # 데이터 소스 연결
    data_source = models.CharField(max_length=50)      # "fmp_foreign_flow", "macro_vix", etc.
    data_params = models.JSONField(default=dict)       # {"symbol": "KOSPI", "metric": "net_foreign"}

    # 방향 정의: 이 지표가 올라가면 가설을 지지하는가 반박하는가
    support_direction = models.CharField(max_length=10,  # positive = 올라가면 지지, negative = 올라가면 반박
        choices=[('positive', 'Positive'), ('negative', 'Negative')]
    )

    # 현재 상태
    current_arrow_degree = models.FloatField(default=90.0)  # 0=강한지지, 90=중립, 180=강한반박
    current_label = models.CharField(max_length=50, default='중립')
    current_color = models.CharField(max_length=10, default='gray')  # red/orange/gray/lightblue/blue

    # 근거 설명 (LLM 생성)
    rationale = models.TextField(blank=True)           # "이 지표가 붙은 이유" ([근거])
    context_explanation = models.TextField(blank=True)  # 현재 상태 해석

    # 메타
    is_ai_recommended = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
```

#### IndicatorReading (지표 읽기값 — 시계열)

```python
class IndicatorReading(models.Model):
    indicator = models.ForeignKey(ThesisIndicator, on_delete=models.CASCADE,
                                  related_name='readings')

    date = models.DateField()
    raw_value = models.FloatField()                    # 원본 값 (내부 계산용)
    normalized_score = models.FloatField()             # -1.0 ~ 1.0 (화살표 계산용)
    arrow_degree = models.FloatField()                 # 0 ~ 180
    label = models.CharField(max_length=50)
    color = models.CharField(max_length=10)

    class Meta:
        unique_together = ['indicator', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['indicator', '-date']),
        ]
```

#### ThesisSnapshot (일별 스냅샷)

```python
class ThesisSnapshot(models.Model):
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='snapshots')

    date = models.DateField()
    overall_score = models.FloatField()                # 그날의 전체 점수
    overall_label = models.CharField(max_length=50)
    indicator_scores = models.JSONField()              # {"indicator_uuid": {"score": 0.5, "arrow": 45, ...}}

    # 주요 변화 기록
    notable_changes = models.JSONField(default=list)   # [{"indicator": "외국인", "from": 45, "to": 20, ...}]
    ai_summary = models.TextField(blank=True)          # AI 요약 (쉐이크 시 표시)

    class Meta:
        unique_together = ['thesis', 'date']
        ordering = ['-date']
```

#### ThesisAlert (알림)

```python
class ThesisAlert(models.Model):
    thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='alerts')
    indicator = models.ForeignKey(ThesisIndicator, on_delete=models.CASCADE,
                                  null=True, blank=True)

    alert_type = models.CharField(max_length=30,
        choices=[
            ('indicator_change', 'Indicator Direction Change'),  # 화살표 방향 변경
            ('threshold_cross', 'Threshold Crossed'),            # 지지↔반박 전환
            ('news_event', 'Related News Event'),                # 관련 뉴스 발생
            ('target_date', 'Target Date Approaching'),          # 예상 시점 임박
            ('daily_summary', 'Daily Summary'),                  # 일일 요약
        ]
    )

    title = models.CharField(max_length=200)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    is_pushed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
```

#### 커뮤니티 모델

```python
class ThesisFollow(models.Model):
    """인기 가설 따라하기"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='followers')
    user_thesis = models.ForeignKey(Thesis, on_delete=models.CASCADE, related_name='followed_from')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'original_thesis']


class PopularThesisCache(models.Model):
    """인기 가설 캐시 (주기적 갱신)"""
    thesis = models.OneToOneField(Thesis, on_delete=models.CASCADE)
    follower_count = models.PositiveIntegerField(default=0)
    support_ratio = models.FloatField(default=0.5)     # 지지 비율 (히트맵 바 표시용)
    rank = models.PositiveIntegerField(default=0)
    cached_at = models.DateTimeField(auto_now=True)
```

### 4.3 모델 관계도

```
User
  └── Thesis (1:N)
        ├── ThesisPremise (1:N)
        │     └── ThesisIndicator (1:N)
        │           └── IndicatorReading (1:N, 시계열)
        ├── ThesisIndicator (1:N, premise 없이도 가능)
        ├── ThesisSnapshot (1:N, 일별)
        ├── ThesisAlert (1:N)
        └── ThesisFollow (N:M via follow)

NewsArticle ←── Thesis.source_news (진입 뉴스)
Stock/MarketIndex ←── ThesisIndicator.data_params (데이터 소스)
EconomicIndicator ←── ThesisIndicator.data_params (거시지표)
```

### 4.4 Neo4j 그래프 모델

PostgreSQL과 별도로, 가설 간 관계를 Neo4j에 저장:

```
(Thesis: KOSPI 하락) --[HAS_PREMISE]--> (Premise: 선거 기대감 소멸)
                     --[HAS_PREMISE]--> (Premise: 외국인 매도 전환)
                     --[TRACKED_BY]--> (Indicator: 외국인 순매수)
                     --[TRIGGERED_BY]--> (News: 코스피 2800 돌파)
                     --[SIMILAR_TO]--> (Thesis: 2018 선거 후 조정)
                     --[OPPOSITE_OF]--> (Thesis: KOSPI 3000 돌파)

(Premise: 외국인 매도 전환) --[MONITORED_BY]--> (Indicator: 외국인 순매수)
                           --[RELATED_TO]--> (Indicator: 원/달러 환율)

(Indicator: 외국인 순매수) --[CORRELATES_WITH]--> (Indicator: 원/달러 환율)
```

**활용:**

- 가설 연결 제안: "기존 가설과 관련된 새 가설이 있어요"
- 지표 추천: "이 전제를 가진 다른 사용자들은 이 지표도 추적해요"
- Chain Sight 연동: 가설의 대상 종목을 Chain Sight 그래프에 매핑

---

## 5. 인프라 아키텍처

### 5.1 4-Layer 구조

```
Layer 1: 데이터 수집 (Data Collection)
  ├── 시장 데이터: FMP, Alpha Vantage (가격, 수급, 지표)
  ├── 뉴스 데이터: Finnhub, Marketaux (국내외 뉴스)
  ├── 거시경제: FRED API (금리, 환율, VIX 등)
  ├── 이벤트 캘린더: FOMC, 실적발표, 선거 등
  └── → 정규화 + 임베딩 → 벡터 DB 저장

Layer 2: 지식 가공 (Knowledge Processing)
  ├── 뉴스 → 영향 종목/섹터, 방향성, 관련 가설 매칭
  ├── 시장 데이터 → 의미 해석, 과거 패턴 비교
  └── → 미리 가공하여 Redis 캐싱 (즉시 제공)

Layer 3: 에이전트 (Agent Layer)
  ├── 가설 구조화 에이전트: 사용자 입력 → 구조화된 가설
  ├── 지표 매칭 에이전트: 전제 → 관련 지표 탐색
  ├── 모니터링 에이전트: 지표 변화 감지 + 화살표 계산
  └── 해석 에이전트: [근거] 설명, 변화 맥락 해석

Layer 4: 분석 엔진 (Deep Analysis)
  ├── 과거 유사 상황 검색 (벡터 유사도)
  ├── 여러 소스 종합 분석 (긴 컨텍스트)
  └── → 필요할 때만 가동 (비용 효율)
```

### 5.2 기존 앱 활용 매핑

| Thesis Control 기능 | 기존 앱         | 활용 방식                                  |
| ------------------- | --------------- | ------------------------------------------ |
| 오늘 이슈 진입      | news/           | NewsArticle + DailyNewsKeyword             |
| 뉴스 센티먼트 지표  | news/           | SentimentHistory, Intelligence Pipeline v3 |
| 시장 데이터 지표    | stocks/         | DailyPrice, Stock                          |
| 거시경제 지표       | macro/          | EconomicIndicator, IndicatorValue          |
| 기술적 지표         | analysis/       | TechnicalIndicators (RSI, MACD 등)         |
| 수급 데이터         | serverless/     | MarketMover, InstitutionalHolding          |
| Chain Sight 연동    | serverless/     | Chain Sight 6개 레이어                     |
| 사용자 관리         | users/          | User, JWT 인증                             |
| 스케줄링            | config/         | Celery Beat                                |
| 그래프 관계         | graph_analysis/ | Neo4j 연동                                 |

### 5.3 새 Celery 태스크

| 태스크                        | 주기                | 역할                                |
| ----------------------------- | ------------------- | ----------------------------------- |
| `update_indicator_readings`   | 장 마감 후 18:00 ET | 모든 active 가설의 지표 값 업데이트 |
| `calculate_arrow_degrees`     | 18:15 ET            | 화살표 각도 재계산                  |
| `create_daily_snapshots`      | 18:30 ET            | 일별 스냅샷 생성                    |
| `check_thesis_alerts`         | 18:45 ET            | 변화 감지 → 알림 생성               |
| `scan_thesis_news`            | 2시간마다           | 활성 가설 관련 뉴스 스캔            |
| `update_popular_thesis_cache` | 매일 08:00          | 인기 가설 캐시 갱신                 |
| `prepare_daily_issues`        | 매일 07:00          | 오늘의 이슈 카드 준비               |
| `generate_thesis_summaries`   | 매일 07:30          | AI 일일 요약 생성                   |

### 5.4 화살표 각도 계산 로직

```python
# arrow_calculator.py 핵심 로직

def calculate_arrow_degree(indicator, readings, thesis_direction):
    """
    지표 데이터를 화살표 각도(0~180)로 변환

    0°   = 강하게 지지 (↑)
    45°  = 지지하는 편 (↗)
    90°  = 중립 (→)
    135° = 약화하는 편 (↘)
    180° = 강하게 반박 (↓)
    """

    # Step 1: 원본 데이터를 정규화 (-1 ~ 1)
    #   - 정량 지표: z-score 기반 (이동평균 대비 편차)
    #   - 정성 지표: LLM 센티먼트 스코어
    normalized = normalize_reading(indicator, readings)

    # Step 2: 가설 방향에 맞춰 부호 조정
    #   - support_direction이 positive이고 값이 올라가면 → 지지
    #   - support_direction이 negative이고 값이 올라가면 → 반박
    if indicator.support_direction == 'negative':
        normalized = -normalized

    # Step 3: -1~1 스코어를 0~180 각도로 변환
    #   - 1.0 → 0° (강한 지지)
    #   - 0.0 → 90° (중립)
    #   - -1.0 → 180° (강한 반박)
    degree = 90 - (normalized * 90)

    # Step 4: 색상 결정
    color = score_to_color(degree)

    # Step 5: 라벨 결정
    label = degree_to_label(degree)

    return degree, color, label
```

### 5.5 LLM 사용 포인트와 비용 관리

| 사용 포인트              | 빈도             | 모델             | 비용 영향   |
| ------------------------ | ---------------- | ---------------- | ----------- |
| 가설 구조화 대화         | 가설 생성 시 1회 | Gemini 2.5 Flash | 낮음        |
| 전제 추출/제안           | 가설 생성 시 1회 | Gemini 2.5 Flash | 낮음        |
| 지표 매칭/추천           | 가설 생성 시 1회 | Gemini 2.5 Flash | 낮음        |
| [근거] 설명 생성         | 사용자 요청 시   | Gemini 2.5 Flash | 낮음 (캐싱) |
| 뉴스→가설 관련성 판단    | 2시간마다        | Gemini 2.5 Flash | **중간**    |
| 일일 상태 요약           | 매일 1회/가설    | Gemini 2.5 Flash | 중간        |
| 깊은 분석 (과거 비교 등) | 사용자 요청 시   | Gemini 2.5 Flash | 높음 (희귀) |

**비용 절감 전략:**

- [근거] 설명은 한번 생성 후 캐싱. 지표 상태가 크게 바뀔 때만 재생성.
- 뉴스 스캔은 활성 가설과 관련된 키워드에 매칭되는 것만 LLM 분석.
- 일일 요약은 지표 변화가 있는 가설만 생성.
- 깊은 분석은 사용자가 명시적으로 요청할 때만.

---

## 6. API 설계

### 6.1 엔드포인트

```
/api/v1/thesis/

# 가설 CRUD
POST   /                        # 가설 생성
GET    /                        # 내 가설 목록
GET    /{id}/                   # 가설 상세
PATCH  /{id}/                   # 가설 수정
POST   /{id}/close/             # 가설 마감

# 가설 설립 대화
POST   /conversation/start/     # 대화 시작 (진입 경로별)
POST   /conversation/respond/   # 사용자 선택/입력에 AI 응답

# 전제
GET    /{id}/premises/          # 전제 목록
POST   /{id}/premises/          # 전제 추가
PATCH  /{id}/premises/{pid}/    # 전제 수정/비활성화
DELETE /{id}/premises/{pid}/    # 전제 삭제

# 지표
GET    /{id}/indicators/        # 지표 목록
POST   /{id}/indicators/auto/   # AI 자동 지표 추천
POST   /{id}/indicators/        # 지표 수동 추가
PATCH  /{id}/indicators/{iid}/  # 지표 수정
DELETE /{id}/indicators/{iid}/  # 지표 삭제

# 모니터링
GET    /{id}/dashboard/         # 관제실 데이터 (카드/히트맵/그래프 뷰)
GET    /{id}/snapshots/         # 스냅샷 히스토리 (그래프뷰용)
GET    /{id}/summary/           # AI 현재 상태 요약 (쉐이크)

# 지표 상세
GET    /{id}/indicators/{iid}/readings/     # 지표 시계열 (상세 차트)
GET    /{id}/indicators/{iid}/explanation/   # [근거] 설명

# 알림
GET    /alerts/                 # 내 알림 목록
PATCH  /alerts/{aid}/read/      # 읽음 처리

# 오늘 이슈
GET    /daily-issues/           # 오늘의 시장 이슈 목록

# 커뮤니티
GET    /popular/                # 인기 가설 목록
POST   /popular/{id}/follow/    # 인기 가설 따라하기
GET    /popular/{id}/detail/    # 인기 가설 상세 (구경하기)

# 템플릿
GET    /templates/              # 가설 템플릿 목록
GET    /templates/{type}/       # 유형별 선택지
```

### 6.2 주요 응답 형태

**관제실 대시보드 (GET /{id}/dashboard/)**

```json
{
	"thesis": {
		"id": "uuid",
		"title": "KOSPI 하락",
		"direction": "bearish",
		"status": "active",
		"days_active": 32,
		"overall_score": 0.35,
		"overall_label": "내 가설 쪽으로 기울고 있어요",
		"overall_phase": "waxing",
		"recent_change": "외국인 순매도 3일째 지속 중"
	},
	"indicators": [
		{
			"id": "uuid",
			"name": "외국인 순매수 추이",
			"arrow_degree": 30,
			"color": "red",
			"label": "지지하는 중",
			"previous_degree": 45,
			"trend": "strengthening",
			"premise_name": "외국인 매도 전환"
		},
		{
			"id": "uuid",
			"name": "원/달러 환율",
			"arrow_degree": 90,
			"color": "gray",
			"label": "중립",
			"previous_degree": 85,
			"trend": "stable",
			"premise_name": "외국인 매도 전환"
		}
	],
	"heatmap": {
		"rows": 2,
		"cols": 3,
		"cells": [
			{ "name": "외국인", "color": "#e74c3c", "degree": 30 },
			{ "name": "환율", "color": "#95a5a6", "degree": 90 },
			{ "name": "S&P", "color": "#3498db", "degree": 135 }
		]
	}
}
```

**대화 응답 (POST /conversation/respond/)**

```json
{
	"message": "왜 그렇게 생각하세요?\n여러 개 골라도 돼요.",
	"buttons": [
		{
			"id": "election",
			"label": "선거/정치 기대감 소멸",
			"long_press_hint": true
		},
		{ "id": "earnings", "label": "기업 실적 부진", "long_press_hint": true },
		{ "id": "foreign", "label": "외국인 매도 전환", "long_press_hint": true },
		{ "id": "global", "label": "글로벌 리스크", "long_press_hint": true },
		{ "id": "overheat", "label": "과열/거품", "long_press_hint": true },
		{ "id": "supply", "label": "수급 변화", "long_press_hint": true },
		{ "id": "custom", "label": "✏️ 다른 이유", "type": "text_input" }
	],
	"selection_mode": "multi",
	"long_press_explanations": {
		"election": "선거 등 정치 이벤트로 인한 기대감이 사라지면서 시장이 조정받는 것을 말해요.",
		"supply": "주식을 사는 사람(매수)과 파는 사람(매도)의 힘 균형이 바뀌는 걸 말해요."
	},
	"conversation_state": "awaiting_reason",
	"step": 3,
	"total_steps": 6
}
```

---

## 7. 구현 단계 (Phase)

### Phase 1: 기반 구조 (MVP)

**목표:** 가설을 세우고 기본 모니터링이 되는 최소 구조

- thesis/ 앱 생성 + 모델 마이그레이션
- 가설 CRUD API
- 대화형 가설 구조화 (LLM 연동) — 경로 1, 2만
- 정량 지표 3~5종 (외국인 순매수, 환율, VIX, KOSPI PER, 기관 수급)
- 화살표 각도 계산 엔진
- 관제실 대시보드 API (카드뷰만)
- 일별 지표 업데이트 Celery 태스크

### Phase 2: 모니터링 강화

**목표:** 풍부한 모니터링 경험

- 히트맵, 그래프 뷰 API
- 스냅샷 히스토리
- 변화 감지 + 알림 시스템
- AI 일일 요약 생성
- [근거] 설명 시스템 + 캐싱
- 뉴스 센티먼트 지표 연동 (news/ 앱)
- 오늘 이슈 진입 (daily-issues API)

### Phase 3: 커뮤니티 + 고도화

**목표:** 재미와 네트워크 효과

- 인기 가설 시스템
- 가설 따라하기/수정
- 템플릿 시스템
- Chain Sight 연동
- 가설 마감 + 복기 시스템
- Neo4j 가설 관계 그래프
- 가설 아카이브 + 학습 이력

### Phase 4: 지능화

**목표:** AI가 점점 더 똑똑해지는 구조

- 투자 지식 그래프 (Neo4j) 확장
- 과거 유사 상황 검색 (벡터 유사도)
- 지표 추천 정확도 개선 (사용자 피드백 루프)
- 가설 간 연결 자동 발견
- 반대 가설 자동 생성

---

## 8. 기술 스택 요약

| 구분      | 기술                  | 용도                                     |
| --------- | --------------------- | ---------------------------------------- |
| 기존 유지 | Django 5.1.7 + DRF    | 백엔드 프레임워크                        |
| 기존 유지 | PostgreSQL            | 가설, 지표, 스냅샷 저장                  |
| 기존 유지 | Redis                 | 캐싱 ([근거] 설명, 오늘 이슈, 인기 가설) |
| 기존 유지 | Celery + Beat         | 일별 지표 업데이트, 알림 체크            |
| 기존 유지 | Neo4j                 | 가설-전제-지표 관계, 가설 간 연결        |
| 기존 유지 | Gemini 2.5 Flash      | 가설 구조화, [근거] 설명, 요약           |
| 기존 유지 | Finnhub/Marketaux     | 뉴스 소스 (가설 관련 뉴스)               |
| 기존 유지 | FMP/FRED              | 시장/거시 데이터 (지표 값)               |
| 신규 검토 | 벡터 DB (pgvector 등) | 유사 상황 검색, 뉴스 임베딩 (Phase 4)    |

---

## 9. 리스크 및 고려사항

### 9.1 규제 리스크

- "예측"이 아니라 "가설 탐색", "모니터링 도구"로 용어 일관 유지
- 확률/정확도 숫자를 제공하지 않음 → 방향성, 느낌으로 전달
- 투자 판단 책임이 사용자에게 있음을 명확히

### 9.2 확인 편향(Confirmation Bias)

- 반대 가설 자동 생성 (Phase 4)
- 반박 지표도 동등하게 표시
- 가설 마감 시 "예상과 달랐던 부분" 명시

### 9.3 LLM 비용

- [근거] 설명 캐싱으로 중복 호출 방지
- 뉴스 스캔은 키워드 매칭 후 관련된 것만 LLM 분석
- 일일 요약은 변화가 있는 가설만 생성

### 9.4 데이터 한계

- 한국 시장(KOSPI, KOSDAQ) 데이터는 FMP 커버리지 확인 필요
- 외국인/기관 수급 데이터 소스 별도 확보 필요
- 뉴스 센티먼트의 정확도 한계 → "참고 지표"로 위치

---

## 부록: 용어 정리

| 용어                  | 설명                                         |
| --------------------- | -------------------------------------------- |
| 가설 (Thesis)         | 사용자가 세운 시장 예측/판단                 |
| 전제 (Premise)        | 가설을 지탱하는 하위 논리                    |
| 지표 (Indicator)      | 전제를 추적하는 데이터 포인트                |
| 화살표 (Arrow)        | 지표의 가설 지지/반박 정도를 방향으로 표현   |
| 관제실 (Control Room) | 가설 모니터링 대시보드                       |
| 근거 (Rationale)      | 지표가 왜 붙었는지, 현재 왜 이 상태인지 설명 |
| 스냅샷 (Snapshot)     | 특정 일자의 가설 전체 상태 기록              |
