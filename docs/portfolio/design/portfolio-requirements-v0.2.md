# Stock-Vis Portfolio 기능 요구사항 설계서

> 문서 버전: v0.2
> 작성일: 2026-04-04
> 상태: 기능 정의 단계
> 변경 이력: v0.1 → v0.2 예비 후보 관리(FR-P105~P108) 추가, 데이터 엔티티 갱신, 구현 순서 확정

---

## 1. 개요

### 1-1. Portfolio의 목적
사용자의 보유 종목과 예비 후보를 통합 관리하고, 투자 판단의 근거를 추적하며, LLM 기반 코칭을 통해 포트폴리오 구조를 개선하는 핵심 기능. Stock-Vis의 사용자 락인 효과를 담당하는 가장 중요한 기능이다.

### 1-2. 핵심 설계 원칙

- **초보자와 전문가 모두 사용 가능:** 프리셋으로 쉽게 시작하되, 전문가는 커스터마이징 가능
- **LLM이 스펙트럼을 연결:** 친절한 설명, 쉬운 프리셋, 전문가도 쓸 수 있는 커스터마이징을 LLM이 중재
- **프리셋 → 개인화 진화:** 초기엔 프리셋 기반 분석 도구, 장기적으론 개인화 포트폴리오 코치
- **판단의 주체는 사용자:** 서비스는 판단을 돕는 코치이지, 대신 판단하지 않음
- **"왜"가 항상 붙어있음:** 모든 보유 종목에 투자 근거(thesis)가 연결됨
- **보유 + 예비 후보 통합 관리:** 매수 전 후보도 포트폴리오 맥락에서 분석

### 1-3. 설계 제약 (1인 개발)

- 관리 부담이 적은 구조 우선 (JSONField 활용, 별도 테이블 최소화)
- 사용자에게 과도한 신뢰를 주어 투자 비난을 받을 요소 배제
- LLM 입출력이 단순한 필드 타입 사용 (숫자, 날짜, Enum, 자유 텍스트)

### 1-4. 타 시스템 연동 관계

| 연동 대상 | 방향 | 내용 |
|---|---|---|
| Thesis Engine | 양방향 | thesis 상태 조회, status 전환 (watching→holding→closed) |
| Chain Sight | 수신 | 관계 변화 시그널, thesis 생성 데이터, Watching→후보 전환 |
| Dashboard | 수신 | 매크로 시나리오 변화 알림 |
| 종목 상세(1차 검증) | 호출 | 개별 종목 클릭 시 1차 검증 페이지 연결 |
| News Intelligence | 수신 | 보유/후보 종목 관련 뉴스 시그널 |
| EOD Screening | 수신 | 일일 스크리닝 결과 중 보유/후보 종목 해당 건 |

---

## 2. 사용자 정의

### 2-1. 사용자 페르소나

**페르소나 A — 입문 투자자**
- 보유 종목 3~5개
- 왜 샀는지 명확하지 않음
- 포트폴리오 분석 경험 없음
- 원하는 것: "내가 가진 게 괜찮은 건지 알고 싶다"

**페르소나 B — 중급 투자자**
- 보유 종목 5~15개
- 나름의 투자 근거가 있지만 체계적이지 않음
- 섹터 분산 정도는 신경 씀
- 원하는 것: "내 포트폴리오 약점이 뭔지, 어떻게 고칠지 알고 싶다"

**페르소나 C — 전문 투자자**
- 보유 종목 10~30개
- thesis 기반 투자
- 비중 관리, 리스크 관리 직접 수행
- 원하는 것: "내 판단 기록을 추적하고, 패턴을 분석하고, 블라인드스팟을 찾고 싶다"

### 2-2. 사용자 단계별 경험 목표

| 단계 | 사용 횟수 | 서비스 인식 | 핵심 가치 |
|---|---|---|---|
| 콜드스타트 | 1회 | "투자 스타일별로 해석해주는 서비스" | 프리셋 기반 즉시 가치 체험 |
| 초기 사용 | 2~5회 | "내 기록을 바탕으로 조언해주네" | 프리셋 + 히스토리 기반 조언 |
| 장기 사용 | 10회+ | "내 투자 방식을 같이 다듬는 코치" | 완전 개인화 코칭 |

---

## 3. 기능 요구사항

### FR-P100: 포트폴리오 입력 및 관리

#### FR-P101: 포트폴리오 생성
- 사용자는 보유 종목과 비중을 직접 입력하여 포트폴리오를 생성할 수 있다.
- 입력 항목: 종목 (ticker/name 검색), 보유 수량, 평균 매수가
- 최소 1개 종목 입력 시 포트폴리오 생성 가능
- 포트폴리오 이름 지정 가능 (기본값: "My Portfolio")

#### FR-P102: 다중 포트폴리오
- 사용자는 여러 개의 포트폴리오를 생성/관리할 수 있다.
- 각 포트폴리오는 독립적으로 분석/코칭됨
- 기본 포트폴리오(primary) 1개 지정 가능

#### FR-P103: 종목 추가/제거/수정
- 기존 포트폴리오에 종목 추가, 제거, 수량/단가 수정 가능
- 종목 제거 시 해당 thesis의 status를 `closed`로 변경
- 수량 변경 시 변경 이력 자동 기록
- 예비 후보에 분할 매수 계획이 있는 종목의 추가 매수 시: 해당 계획의 다음 미완료 회차에 `completed_at`, `actual_price` 자동 기록

#### FR-P104: 포트폴리오 가져오기 (Phase 2)
- CSV/엑셀 파일 업로드를 통한 일괄 입력
- 향후: 증권사 API 연동 (검토 단계)

#### FR-P105: 예비 후보 관리
- 매수 전 관심 종목을 포트폴리오 내 "예비 후보"로 등록/관리
- 보유 종목과 같은 포트폴리오 안에서 관리 (별도 탭이 아닌 구분된 섹션)
- position_type으로 구분: `holding` (보유) / `candidate` (예비 후보) / `sold` (매도 완료)
- Coach는 보유 + 예비 후보를 합쳐서 구조적 분석 가능
  - 예: "NVDA를 매수하면 AI 인프라 thesis 집중도가 32%에서 48%로 올라갑니다"
- Chain Sight Watching에서 "예비 후보로 전환" 시 자동으로 발견 출처 기록

**예비 후보 필드 — 자동 생성 (4개)**

| 필드 | 타입 | 설명 | 생성 시점 |
|---|---|---|---|
| registered_at | datetime | 예비 후보 등록일 | 등록 시 자동 |
| last_reviewed_at | datetime | 마지막 검토일 (종목 상세 열람 시 갱신) | 열람 시 자동 |
| discovery_source | enum | 발견 출처 | 등록 시 선택/자동 |
| price_gap_pct | float | 현재가 대비 목표 매수가 괴리율 | EOD 배치 자동 계산 |

discovery_source 선택지: `chain_sight` / `news` / `screening` / `direct` / `other`

**예비 후보 필드 — 사용자 입력: 기본 (6개)**

| 필드 | 타입 | 설명 | 필수 여부 |
|---|---|---|---|
| target_price | decimal | 목표 매수가 ("이 가격 이하면 매력적") | 선택 |
| target_weight_pct | decimal | 목표 비중 (%) | 선택 |
| buy_deadline | date | 매수 기한 ("이 날까지 안 되면 재검토") | 선택 |
| conviction_score | int (1~5) | 확신도 (사용자 본인의 주관적 점수) | 선택 |
| unresolved_concerns | text | 미해결 우려사항 ("아직 걸리는 것") | 선택 |
| memo | text | 범용 메모 (매수 조건, 참고 링크, 생각 정리 등) | 선택 |

**예비 후보 필드 — 사용자 입력: 추가 (4개)**

| 필드 | 타입 | 설명 | 비고 |
|---|---|---|---|
| split_buy_plan | JSONField | 분할 매수 계획 | 매수 시 해당 회차 자동 업데이트 |
| buy_trigger | JSONField | 매수 트리거 조건 | 타입 태그 + 설명 + 충족 체크박스 |
| invest_priority | int | 투자 고려 순위 | 동순위 허용, 순서 정렬용 |
| related_event | JSONField | 관련 이벤트 일정 | 날짜 + 설명 + 경과 여부 |

**분할 매수 계획 JSONField 구조:**
```json
{
  "rounds": [
    {
      "target_price": 850,
      "weight_pct": 40,
      "completed_at": "2026-04-03",
      "actual_price": 845
    },
    {
      "target_price": 800,
      "weight_pct": 30,
      "completed_at": null,
      "actual_price": null
    }
  ]
}
```
- 매수 시 자동 업데이트: PortfolioHolding 수량 변경의 post_save signal에서 해당 종목의 미완료 회차 중 첫 번째에 completed_at + actual_price 기록
- 순서대로 채움 (가격 매칭 로직 없음, 복잡도 최소화)

**매수 트리거 조건 JSONField 구조:**
```json
{
  "trigger_type": "earnings",
  "description": "Q2 실적 발표 후 매출 성장률 20% 이상 확인",
  "is_met": false
}
```
- trigger_type 선택지: `price` / `earnings` / `indicator` / `macro_event` / `other`
- is_met: 사용자가 수동으로 체크 (자동 추적 없음)
- LLM 활용: Coach가 trigger_type을 읽고 관련 정보 연결 가능
  - 예: "실적 발표 조건을 걸어두셨는데, 다음 주가 Q2 실적입니다"

**관련 이벤트 JSONField 구조:**
```json
{
  "event_date": "2026-06-15",
  "event_description": "Q2 실적 발표",
  "event_passed": false
}
```
- Celery 일일 배치에서 event_date < today이면 event_passed = true로 갱신
- Coach 넛지: "내일 예정된 이벤트가 있는 후보가 있습니다"

#### FR-P106: 예비 후보 → 매수 전환
- 예비 후보를 매수 확정 시 position_type: `candidate` → `holding`으로 전환
- 전환 시 수량, 평균 매수가 입력
- 전환 시 **시뮬레이션 스냅샷 자동 저장** (FR-P108 참조)
- 분할 매수 계획이 있는 경우 해당 회차 자동 업데이트
- thesis status: `watching` → `holding`으로 연동 전환

#### FR-P107: 예비 후보 Coach 연동
- Coach는 보유 종목 + 예비 후보를 합산하여 구조 분석 가능
- Coach 활용 예시:
  - "NVDA를 매수하면 AI 인프라 thesis 집중도가 32%에서 48%로 올라갑니다. 현재 Risk Balanced 모드 기준으로는 과집중입니다."
  - "1순위로 정한 X와 2순위 Y 중에서, 현재 포트폴리오 구조상 Y를 먼저 매수하면 thesis 분산 효과가 더 큽니다."
  - "이 종목 45일째 검토하지 않았습니다. 아직 관심 있으신가요?"
  - "매수 기한이 3일 남았습니다. 조건을 재검토하시겠어요?"
- Coach 역할 한정: 구조적 분석만. "이 종목을 사세요"는 비허용.

#### FR-P108: 매수 확정 시 시뮬레이션 스냅샷
- 예비 후보 → 매수 전환 시, 또는 신규 종목 추가 시 자동 생성
- PortfolioChange 레코드에 `simulation_snapshot` JSONField로 첨부
- 저장 항목 (단순 산술 연산만, 고급 시뮬레이션 제외):
  - 매수 전/후 thesis 집중도 변화
  - 매수 전/후 섹터 비중 변화
- 사후 분석 활용: ChangeOutcome의 실제 결과와 비교하여 시뮬레이션 정확도 피드백 루프 구성
- 탐색적 시뮬레이션(수시 조회)은 저장하지 않음. 매수 확정 시점의 스냅샷만 저장.

```json
{
  "pre_thesis_concentration": {"AI_infra": 32, "Healthcare": 15},
  "post_thesis_concentration": {"AI_infra": 48, "Healthcare": 12},
  "pre_sector_weights": {"Tech": 55, "Healthcare": 15, "Energy": 10},
  "post_sector_weights": {"Tech": 63, "Healthcare": 12, "Energy": 8},
  "simulated_at": "2026-04-03T14:30:00Z"
}
```

---

### FR-P200: 포트폴리오 현황 (Layer 1 — What)

#### FR-P201: 포트폴리오 요약 카드
기본 뷰에서 항상 표시되는 핵심 지표.

| 지표 | 설명 |
|---|---|
| 총 평가금액 | 현재 시가 기준 총액 |
| 총 수익률 | 평균 매수가 대비 현재가 수익률 |
| 일간 변동 | 전일 대비 변화 금액/비율 |
| 최근 1개월 변동성 | 일일 수익률의 표준편차 (연환산) |
| 집중도 점수 | HHI 또는 상위 3종목 비중 합계 |
| 현재 적용 모드 | 프리셋명 또는 "개인화" |

#### FR-P202: 종목별 현황 리스트
- 종목명, 티커, 보유 수량, 현재가, 평가금액, 수익률, 비중(%)
- 수익률 기준 색상 표시 (양/음)
- 정렬: 비중순 (기본), 수익률순, 이름순

#### FR-P203: 비중 분포 시각화
- 섹터별 비중 (파이 차트 또는 트리맵)
- Thesis별 비중 (동일 thesis 태그로 묶인 종목들의 합산 비중)
  - 예: "AI 인프라" thesis에 NVDA 18% + AMD 8% + TSMC 6% = 32%
- 상위 리스크 노출 표시

#### FR-P204: 포트폴리오 한 줄 진단
- LLM이 현재 포트폴리오 상태를 한 문장으로 요약
- 예: "종목 수는 9개지만 실제로는 AI 인프라 thesis에 집중되어 있습니다."
- 페이지 로드 시 자동 생성, 1일 1회 갱신 (또는 포트폴리오 변경 시)

#### FR-P205: 예비 후보 현황 섹션
- 보유 종목 리스트 하단에 "예비 후보" 섹션 구분 표시
- 표시 항목: 종목명, 티커, 목표 매수가, 현재가, 괴리율, 확신도, 투자 고려 순위
- 정렬: 투자 고려 순위순 (기본), 확신도순, 괴리율순
- 매수 기한 임박 종목 하이라이트
- 장기 미검토 종목 표시 (마지막 검토일 기준 30일 이상)

---

### FR-P300: 투자 근거 추적 (Layer 2 — Why)

#### FR-P301: 종목별 Thesis 연결
- 보유 종목 클릭 시 해당 종목의 thesis 정보 펼침 표시
- 표시 항목:
  - Thesis 제목 (예: "AI 인프라 확장")
  - Thesis 건강도 점수 (Thesis Engine 출력)
  - 전제(premise) 목록 및 각 전제의 유효성 상태
  - 전제 유효성 변화 추이 (최근 30일 미니 차트)
- Thesis가 없는 종목: "투자 근거 미설정" 표시 + 설정 유도 버튼

#### FR-P302: Thesis 건강도 요약 뷰
- 전체 보유 종목의 thesis 건강도를 한눈에 보는 뷰
- 건강도 기준 신호등 표시:
  - 녹색: 건강도 70% 이상 (전제 대부분 유효)
  - 황색: 건강도 40~70% (일부 전제 약화)
  - 적색: 건강도 40% 미만 (thesis 재검토 필요)
- 정렬: 건강도 낮은 순 (주의 필요 종목 우선)

#### FR-P303: Thesis 미설정 종목 관리
- Thesis 없이 보유 중인 종목 목록 별도 표시
- "투자 근거를 설정하면 더 정확한 코칭을 받을 수 있습니다" 안내
- 간편 Thesis 설정: LLM이 종목 특성 기반으로 thesis 초안 제안
  - 사용자가 수정/확인 후 저장

---

### FR-P400: 변화 신호 (Layer 3 — What's Changing)

#### FR-P401: Chain Sight 변화 신호
- Chain Sight에서 보유/후보 종목 관련 관계 변화 감지 시 표시
- 예: "TSMC 공급망에 새로운 리스크 노드 감지됨 → NVDA thesis에 영향 가능"
- 신호 유형:
  - 관계 추가/제거
  - 관련 노드의 급격한 가격 변동
  - 클러스터 구조 변화

#### FR-P402: 매크로 시나리오 영향 신호
- Dashboard의 매크로 thesis 상태 변화가 보유/후보 종목에 미치는 영향 표시
- 예: "지정학 리스크 확대 시나리오 → 당신의 포트폴리오 중 민감 종목: XOM, LMT"
- 매크로 시나리오와 종목 간 연결은 섹터/태그 기반 매핑

#### FR-P403: 뉴스 시그널
- News Intelligence Pipeline에서 보유/후보 종목 관련 주요 뉴스 감지 시 표시
- 중요도/긴급도 기준 필터링
- thesis 전제와 관련된 뉴스 우선 표시

#### FR-P404: 1차 검증 지표 변화
- 보유/후보 종목의 1차 검증 지표 중 유의미한 변화 감지 시 표시
- 예: 부채비율 급증, 매출 성장률 둔화 등
- 변화 임계값 기준 알림 (기본값 제공, 사용자 커스터마이징 가능 — Phase 2)

---

### FR-P500: Coach (LLM 포트폴리오 코치)

#### FR-P501: 프리셋 기반 진단
- 사용자가 선택한 프리셋 관점으로 포트폴리오 분석
- 프리셋 목록:

| 프리셋 | 핵심 철학 | 진단 관점 |
|---|---|---|
| Quality Value | 저평가 우량주 중심 | 밸류에이션 과열, 퀄리티 점수 |
| Growth Compounder | 고성장 복리 수익 | 성장 지속성, thesis 견고성 |
| Risk Balanced | 리스크 조절 우선 | 변동성, 집중도, 상관관계 |
| Dividend | 배당 수익 중심 | 배당 지속성, 배당성장률 |
| Trend Leader | 모멘텀/추세 추종 | 가격 추세, 거래량, 상대강도 |

- 각 프리셋은 진단 시 다른 지표 가중치를 적용
- 여러 프리셋을 동시에 적용하여 비교 가능 (Phase 2)

#### FR-P502: 진단 카드 (MVP 핵심)
- 프리셋 기반 분석 결과를 카드 형태로 표시
- 카드당 내용:
  - 진단 요약 문장 (LLM 생성)
  - 수정 제안 (유지/축소/보완)
  - 제안 이유 설명
  - 적용/무시 버튼
- 카드 수: 상위 3개 (가장 임팩트 큰 제안)

#### FR-P503: Coach 역할 범위
- Coach는 포트폴리오 **전체의 구조적 균형**을 판단
  - 허용: thesis 중복도, 섹터 편중, 변동성 분포, 리스크 노출 분석
  - 허용: 비중 조절 제안 (축소/확대/유지)
  - 허용: 기존 보유 종목 간 교체 제안
  - 허용: 예비 후보 매수 시 포트폴리오 구조 영향 분석
  - 허용: 예비 후보 간 매수 순서 구조적 분석 (투자 고려 순위 참조)
  - 허용: 장기 미검토/기한 임박 후보에 대한 넛지
  - 비허용: 새 종목 매수 추천 (종목 추천기가 아님)
  - 비허용: 개별 종목의 매수/매도 타이밍 판단
  - 비허용: "이 종목을 사세요" 류의 직접적 매수 권유

#### FR-P504: 대화형 코치 (Phase 2)
- 진단 카드에서 시작하여 대화형으로 확장
- 사용자가 질문/반론 시 LLM이 응답
- 대화 맥락:
  - 현재 포트폴리오 상태 (보유 + 예비 후보)
  - 적용 중인 프리셋
  - 과거 판단 기록 (History)
  - thesis 건강도
  - 예비 후보의 미해결 우려사항 및 매수 트리거 상태
- 예시 대화:
  - 사용자: "NVDA 비중을 왜 줄여야 해?"
  - Coach: "NVDA 자체의 문제가 아니라, AI 인프라 thesis에 전체 포트폴리오의 42%가 집중되어 있어 구조적 리스크가 높습니다. 과거 기록상 thesis 편중도가 40%를 넘었을 때 변동성이 1.8배 높았습니다."
  - 사용자: "예비 후보 중에 뭘 먼저 사는 게 좋을까?"
  - Coach: "1순위인 LLY와 2순위인 UNH 중에서, 현재 포트폴리오 구조상 LLY를 매수하면 Healthcare thesis가 생겨 AI 인프라 편중이 완화됩니다. 구조적 분산 효과는 LLY가 더 큽니다."

#### FR-P505: 수정안 비교
- Coach가 제안한 수정안을 적용했을 때의 예상 변화 시뮬레이션
- 비교 항목:
  - 수정 전/후 비중 분포
  - 수정 전/후 thesis 편중도
  - 수정 전/후 예상 변동성
  - 수정 전/후 프리셋 적합도 점수
- 보수적/균형/공격적 3가지 수정안 제공

#### FR-P506: 개인화 코칭 (Phase 3)
- History 데이터 축적 후 활성화
- 개인화 요소:
  - 과거 판단 패턴 인식 (조기 익절, 늦은 손절 등)
  - 프리셋 vs 실제 행동 차이 분석
  - 사용자 성향에 맞는 수정 강도 조절
  - 예비 후보 관리 패턴 분석 (후보 등록 후 평균 매수 전환 기간, 확신도별 매수 성과 등)
- 개인화 우선 모드: 프리셋 조언과 개인화 조언이 충돌 시 개인화 우선
- 예: "버핏형 프리셋은 축소를 권하지만, 당신은 좋은 성장주를 너무 빨리 줄였을 때 성과가 더 나빴습니다."

---

### FR-P600: History (판단 이력)

#### FR-P601: 포트폴리오 스냅샷 자동 저장
- 포트폴리오 변경 시 자동으로 변경 전 상태 스냅샷 저장
- 저장 항목:
  - 스냅샷 일시
  - 전체 종목 구성 및 비중
  - 총 평가금액
  - 전체 thesis 건강도
  - 적용 중인 프리셋/모드
  - 예비 후보 목록 및 상태

#### FR-P602: 변경 기록 카드
- 타임라인 UI로 표시
- 카드당 내용:
  - 날짜
  - 변경 내용 (어떤 종목을 얼마나 변경했는지)
  - 변경 이유 (사용자 입력 또는 Coach 제안 채택 시 자동 기록)
  - 당시 적용 모드/프리셋
  - 당시 시장 상황 요약 (자동 생성)
  - 사용자 메모 (선택 입력)
  - 시뮬레이션 스냅샷 (FR-P108, 매수 시)
- 변경 이유 입력 유도: "왜 이렇게 바꾸셨나요?" 프롬프트
  - 입력하지 않으면 "이유 미기록"으로 저장
  - Coach 제안 채택 시 자동으로 이유 연결

#### FR-P603: 사후 성과 추적
- 각 변경 기록에 사후 성과 자동 연결
- 추적 기간: 변경 후 7일 / 30일 / 90일
- 추적 항목:
  - 변경 종목의 이후 수익률
  - 포트폴리오 전체 수익률 변화
  - 변동성 변화
  - 시장(벤치마크) 대비 성과
  - 시뮬레이션 예상 vs 실제 결과 비교 (시뮬레이션 스냅샷이 있는 경우)
- 예: "2026-04-03 NVDA 축소 판단 → 30일 후: 변동성 감소, 절대수익 소폭 감소, 시장대비 -1.2%"

#### FR-P604: 변경 기록 검색/필터
- 기간별 필터 (최근 1주/1개월/3개월/전체)
- 종목별 필터
- 변경 유형별 필터 (추가/제거/비중변경/후보→매수 전환)
- Coach 제안 채택 여부 필터

---

### FR-P700: Review (사후 분석)

#### FR-P701: 월간 복기 리포트
- 매월 자동 생성 (해당 월 데이터 기준)
- 리포트 내용:
  - 이번 달 총 변경 횟수
  - 변경의 평균 성과
  - 가장 좋았던 판단 (+ 왜 좋았는지)
  - 가장 아쉬웠던 판단 (+ 왜 아쉬웠는지)
  - 포트폴리오 전체 성과 요약
  - 예비 후보 관리 요약 (신규 등록, 매수 전환, 만료/제거)

#### FR-P702: 반복 패턴 분석 (Phase 2)
- History 데이터 축적 후 활성화 (최소 3개월)
- 분석 패턴 예시:
  - 이익 조기 실현 빈도
  - Thesis 중복 과소 인식
  - 하락장 대응 지연
  - 수익 구간에서의 과도한 비중 확대
  - 손실 구간에서의 방치
  - 예비 후보 장기 방치 빈도
  - 확신도 높은 후보의 매수 성과 vs 낮은 후보의 매수 성과
- LLM이 패턴을 자연어로 설명
- 예: "최근 3개월간 하락 후 뒤늦게 방어 전환하는 패턴이 반복되었습니다."

#### FR-P703: 프리셋 적합도 분석 (Phase 2)
- 사용자의 실제 행동 패턴과 각 프리셋의 권고를 비교
- 어떤 프리셋의 조언을 따랐을 때 성과가 좋았는지 분석
- 예: "당신은 Growth Compounder 성향이 강하지만, 실제 성과는 Risk Balanced 수정안에서 더 안정적이었습니다."

#### FR-P704: 다음 기간 개선 포인트
- 복기 리포트 기반으로 다음 달 개선 포인트 3개 자동 생성
- 예:
  - "thesis 중복도 40% 이하로 유지"
  - "비중 변경 시 30일 이상 관찰 후 결정"
  - "방어 전환은 VIX 25 도달 시 선제 실행"

---

### FR-P800: Style (프리셋 및 투자 스타일 관리)

> MVP 단계에서는 Portfolio 내 섹션으로 포함. Phase 3에서 별도 탭 분리 검토.

#### FR-P801: 프리셋 선택 및 적용
- 프리셋 모드 목록 표시 (FR-P501 참조)
- 프리셋 선택 시 해당 관점으로 진단/코칭 전환
- 프리셋별 핵심 철학 설명 제공

#### FR-P802: 내 투자 스타일 추정
- History/Review 데이터 기반으로 사용자의 실제 투자 스타일 자동 추정
- 현재 가장 가까운 프리셋 2개 표시
- 실제 성과상 가장 잘 맞는 프리셋 1개 표시

#### FR-P803: 프리셋별 해석 비교 (Phase 2)
- 동일 포트폴리오를 여러 프리셋 관점으로 동시 분석
- 프리셋별로 "이 포트폴리오의 문제점/강점" 차이 표시
- 프리셋 전환 시 예상 수정안 미리보기

#### FR-P804: 목표 및 리스크 설정
- 투자 기간: 단기(<1년) / 중기(1~3년) / 장기(3년+)
- 우선 목표: 수익률 / 안정성 / 균형
- 변동성 허용: 낮음 / 중간 / 높음
- 이 설정값은 Coach 진단에 반영

---

### FR-P900: 온보딩 (콜드스타트 해결)

#### FR-P901: 포트폴리오 초기 입력
- 최소 진입 장벽: 1개 종목만 입력해도 시작 가능
- 입력 UI: 종목 검색 + 수량 + 매수가
- "나중에 추가하기" 허용
- 예비 후보도 온보딩 시 등록 가능 ("관심 있는 종목도 추가해보세요")

#### FR-P902: 온보딩 질문 (짧고 핵심적)
- 질문 수: 최대 4개
- 질문 항목:
  1. 투자 기간: 단기 / 중기 / 장기
  2. 우선 목표: 수익률 / 안정성 / 균형
  3. 변동성 허용: 낮음 / 중간 / 높음
  4. 관심 스타일: 가치 / 성장 / 균형 / 배당 / 잘 모르겠음
- "잘 모르겠음" 선택 시에도 기본 프리셋(Risk Balanced) 자동 적용

#### FR-P903: 프리셋 추천
- 온보딩 답변 기반으로 적합 프리셋 2~3개 제안
- 예: "당신에게는 Growth Compounder와 Risk Balanced가 먼저 적합해 보입니다."
- 사용자가 하나 선택하면 즉시 진단 시작

#### FR-P904: 첫 진단 결과
- 선택한 프리셋 기준 즉시 분석 결과 표시
- 내용:
  - 현재 포트폴리오 요약
  - 선택한 프리셋 기준 문제점/강점
  - 간단 수정 제안 3개
  - "Coach와 대화 시작" 버튼 (Phase 2에서 활성화)
- 이 단계에서 사용자가 **즉시 가치를 체험**해야 함

---

## 4. 비기능 요구사항

### NFR-P01: 성능
- 포트폴리오 현황 페이지 로드: 2초 이내
- 진단 카드 생성 (LLM): 5초 이내
- 한 줄 진단 생성: 3초 이내
- 스냅샷 저장: 비동기, 사용자 대기 없음
- 시뮬레이션 스냅샷 생성: 1초 이내 (단순 산술)

### NFR-P02: 데이터 갱신
- 종목 가격: EOD 기준 (장중 실시간은 Phase 3 이후 검토)
- Thesis 건강도: 1일 1회 (Thesis Engine 배치 스케줄)
- 한 줄 진단: 1일 1회 또는 포트폴리오 변경 시
- 매크로 시나리오 신호: 1일 1회
- 예비 후보 괴리율: EOD 배치 자동 계산
- 관련 이벤트 경과 체크: 1일 1회 Celery 배치

### NFR-P03: 스케일
- 사용자당 포트폴리오: 최대 10개
- 포트폴리오당 보유 종목: 최대 50개
- 포트폴리오당 예비 후보: 최대 20개
- History 보관 기간: 무제한
- 스냅샷 보관: 무제한

### NFR-P04: LLM 사용 정책
- 진단 카드 / 한 줄 진단 / 수정안 생성에 LLM 사용
- LLM 호출 결과는 캐싱 (동일 포트폴리오 구성에 대해 1일간 유효)
- LLM 실패 시 fallback: 규칙 기반 진단 텍스트 표시
- LLM 응답에 면책 문구 포함: "이 분석은 투자 조언이 아니며 참고용입니다"
- 예비 후보 관련 LLM 입력: 모든 필드를 단순 나열 (숫자/날짜/Enum/텍스트)

### NFR-P05: 보안/프라이버시
- 포트폴리오 데이터는 사용자 본인만 접근 가능
- LLM에 전송되는 데이터: 종목/비중/thesis 요약 (개인 식별 정보 미포함)
- 포트폴리오 삭제 시 관련 데이터 완전 삭제

---

## 5. 데이터 엔티티

### 핵심 엔티티 관계

```
User
 └── Portfolio (1:N)
      ├── PortfolioHolding (1:N)
      │    ├── Stock (N:1)
      │    ├── Thesis (1:1, nullable) — Thesis Engine 연동
      │    └── position_type: holding | candidate | sold
      │         └── [candidate 전용 필드들]
      ├── PortfolioSnapshot (1:N)
      ├── PortfolioChange (1:N)
      │    ├── ChangeDetail (1:N)
      │    ├── ChangeOutcome (1:1, 사후 성과)
      │    └── simulation_snapshot (JSONField)
      ├── CoachDiagnosis (1:N)
      └── ReviewReport (1:N)

Portfolio
 └── PortfolioPreset (N:1)
      └── Preset

User
 └── UserStyle (1:1)
      └── OnboardingAnswer
```

### 주요 엔티티 필드

**Portfolio**
- id, user_id, name, is_primary, preset_id, created_at, updated_at

**PortfolioHolding**
- id, portfolio_id, stock_id
- position_type: `holding` | `candidate` | `sold` (enum)
- **공통 필드:**
  - thesis_id (nullable, FK → Thesis Engine)
  - added_at
- **holding 전용:**
  - quantity, avg_cost
- **candidate 전용 — 자동 생성:**
  - registered_at, last_reviewed_at, discovery_source (enum), price_gap_pct
- **candidate 전용 — 사용자 입력:**
  - target_price, target_weight_pct, buy_deadline, conviction_score (1~5)
  - unresolved_concerns (text), memo (text)
  - split_buy_plan (JSONField), buy_trigger (JSONField)
  - invest_priority (int), related_event (JSONField)
- **sold 전용:**
  - sold_at, sold_price, sold_reason

**PortfolioSnapshot**
- id, portfolio_id, snapshot_date, total_value, total_return, volatility_30d
- concentration_score, holdings_json, thesis_health_json, candidates_json

**PortfolioChange**
- id, portfolio_id, changed_at
- change_type: `add` | `remove` | `rebalance` | `candidate_to_holding`
- reason_text, reason_source (user_input/coach_suggestion)
- coach_diagnosis_id (nullable), market_context_summary, user_memo
- simulation_snapshot (JSONField, nullable)

**ChangeDetail**
- id, change_id, stock_id, field (quantity/avg_cost/position_type), old_value, new_value

**ChangeOutcome**
- id, change_id, evaluated_at, period_days (7/30/90)
- portfolio_return, benchmark_return, volatility_change
- simulation_accuracy (JSONField, nullable — 시뮬레이션 있는 경우 예상 vs 실제)

**CoachDiagnosis**
- id, portfolio_id, preset_id, diagnosed_at
- summary_text, suggestions_json
- includes_candidates (boolean — 예비 후보 포함 분석 여부)
- applied (boolean)

**ReviewReport**
- id, portfolio_id, period_type (monthly/quarterly), period_start, period_end
- report_json, generated_at

**Preset**
- id, name, description, philosophy, indicator_weights_json

**UserStyle**
- id, user_id, investment_horizon, priority_goal, volatility_tolerance
- estimated_style, closest_presets_json, updated_at

---

## 6. Thesis Engine 연동 인터페이스

### 6-1. Portfolio → Thesis Engine 호출

```
# 보유 종목의 thesis 상태 조회
GET /api/thesis/?scope=stock&status=holding&portfolio_id={id}

# 예비 후보의 thesis 상태 조회
GET /api/thesis/?scope=stock&status=watching&portfolio_id={id}

# thesis status 전환
PATCH /api/thesis/{thesis_id}/
  { "status": "holding" }  # watching → holding (매수 시)
  { "status": "closed" }   # holding → closed (매도 시)

# thesis 건강도 배치 조회 (Portfolio 요약용)
GET /api/thesis/health-summary/?portfolio_id={id}
```

### 6-2. Thesis Engine → Portfolio 알림 (이벤트 기반)

```
# thesis 건강도 변화 이벤트
Event: thesis.health_changed
Payload: { thesis_id, stock_id, old_health, new_health, changed_premises }

# premise 유효성 변화 이벤트
Event: thesis.premise_invalidated
Payload: { thesis_id, premise_id, stock_id, reason }
```

### 6-3. Thesis 모델 scope 확장

기존 Thesis 모델에 추가할 필드:
```python
class Thesis(models.Model):
    # 기존 필드 유지
    scope = models.CharField(choices=[('macro','Macro'),('stock','Stock')], default='stock')
    status = models.CharField(choices=[('watching','Watching'),('holding','Holding'),('closed','Closed')], default='watching')
    portfolio_id = models.ForeignKey('Portfolio', null=True, blank=True)
```

---

## 7. 구현 순서

### Sprint 1 — 기반 구조 (2주)
> 목표: 데이터 모델 + 기본 CRUD가 작동하는 상태

| 순서 | ID | 기능 | 이유 |
|---|---|---|---|
| 1 | - | DB 모델 생성 | Portfolio, PortfolioHolding, Preset, UserStyle 모델 |
| 2 | - | API 엔드포인트 기본 CRUD | serializer + viewset |
| 3 | FR-P101 | 포트폴리오 생성 | 모든 기능의 전제 조건 |
| 4 | FR-P103 | 종목 추가/제거/수정 | 포트폴리오 데이터 입력의 핵심 |
| 5 | FR-P804 | 목표 및 리스크 설정 | UserStyle 모델, 프리셋 추천의 전제 |
| 6 | - | Preset 시드 데이터 | 5개 프리셋 기본 데이터 투입 |

### Sprint 2 — 온보딩 + 현황 뷰 (2주)
> 목표: 사용자가 들어와서 첫 가치를 체험하는 플로우 완성

| 순서 | ID | 기능 | 이유 |
|---|---|---|---|
| 7 | FR-P901 | 포트폴리오 초기 입력 UI | 온보딩 첫 화면 |
| 8 | FR-P902 | 온보딩 질문 | 프리셋 추천을 위한 입력 |
| 9 | FR-P903 | 프리셋 추천 | 온보딩 답변 → 프리셋 매칭 로직 |
| 10 | FR-P801 | 프리셋 선택 및 적용 | 선택한 프리셋 저장/전환 |
| 11 | FR-P201 | 포트폴리오 요약 카드 | 메인 화면 상단 |
| 12 | FR-P202 | 종목별 현황 리스트 | 메인 화면 중단 |
| 13 | FR-P203 | 비중 분포 시각화 | 섹터/thesis 비중 차트 |

### Sprint 3 — Coach MVP + 첫 진단 (2주)
> 목표: LLM 기반 진단이 작동하여 "이 서비스 쓸만하다" 확인

| 순서 | ID | 기능 | 이유 |
|---|---|---|---|
| 14 | FR-P501 | 프리셋 기반 진단 | Coach 핵심 로직 (프리셋별 가중치 적용) |
| 15 | FR-P204 | 포트폴리오 한 줄 진단 | LLM 연동 첫 기능, 가장 가벼운 LLM 호출 |
| 16 | FR-P502 | 진단 카드 (상위 3개) | Coach MVP 핵심 산출물 |
| 17 | FR-P904 | 첫 진단 결과 | 온보딩 → 진단 플로우 연결 완성 |

**--- 여기까지가 MVP (6주) ---**

### Sprint 4 — 예비 후보 기본 (2주)
> 목표: 예비 후보 등록/관리/현황 표시

| 순서 | ID | 기능 | 이유 |
|---|---|---|---|
| 18 | FR-P105 | 예비 후보 관리 — 기본 필드 | candidate position_type + 자동 생성 4개 + 사용자 입력 기본 6개 |
| 19 | FR-P205 | 예비 후보 현황 섹션 | 보유 종목 아래 후보 리스트 표시 |
| 20 | FR-P106 | 예비 후보 → 매수 전환 | position_type 전환 + 수량/매수가 입력 |

### Sprint 5 — 예비 후보 확장 + History 기초 (2주)
> 목표: 예비 후보 추가 필드 + 판단 기록 시작

| 순서 | ID | 기능 | 이유 |
|---|---|---|---|
| 21 | FR-P105 | 예비 후보 — 추가 필드 4개 | 분할 매수 계획, 매수 트리거, 투자 고려 순위, 관련 이벤트 |
| 22 | FR-P108 | 매수 확정 시 시뮬레이션 스냅샷 | PortfolioChange에 simulation_snapshot 자동 저장 |
| 23 | FR-P103 | 분할 매수 자동 업데이트 | post_save signal로 계획 회차 자동 기록 |
| 24 | FR-P601 | 포트폴리오 스냅샷 자동 저장 | 변경 시 pre-change 스냅샷 |
| 25 | FR-P602 | 변경 기록 카드 | 타임라인 UI + 이유 입력 |
| 26 | - | Celery 배치 잡 | 괴리율 계산, 이벤트 경과 체크, 미검토 넛지 |

### Sprint 6 — Coach 후보 연동 + Review 기초 (2주)
> 목표: Coach가 예비 후보를 포함해서 분석, 월간 리포트 시작

| 순서 | ID | 기능 | 이유 |
|---|---|---|---|
| 27 | FR-P107 | 예비 후보 Coach 연동 | Coach LLM 프롬프트에 후보 데이터 포함 |
| 28 | FR-P503 | Coach 역할 범위 적용 | 허용/비허용 경계 프롬프트 엔지니어링 |
| 29 | FR-P701 | 월간 복기 리포트 | Celery 월간 배치 + LLM 리포트 생성 |
| 30 | FR-P603 | 사후 성과 추적 | 7/30/90일 후 ChangeOutcome 자동 생성 |

**--- 여기까지가 핵심 루프 완성 (12주) ---**

### Sprint 7~8 — Phase 2 확장 (4주)

| 순서 | ID | 기능 | 이유 |
|---|---|---|---|
| 31 | FR-P102 | 다중 포트폴리오 | |
| 32 | FR-P104 | CSV 가져오기 | |
| 33 | FR-P301 | 종목별 Thesis 연결 | Thesis Engine 연동 필요 |
| 34 | FR-P302 | Thesis 건강도 요약 뷰 | Thesis Engine 연동 필요 |
| 35 | FR-P303 | Thesis 미설정 종목 관리 | |
| 36 | FR-P504 | 대화형 코치 | LLM 대화형 전환 |
| 37 | FR-P505 | 수정안 비교 | 시뮬레이션 UI |
| 38 | FR-P604 | 변경 기록 검색/필터 | |
| 39 | FR-P702 | 반복 패턴 분석 | 최소 3개월 데이터 필요 |
| 40 | FR-P803 | 프리셋별 해석 비교 | |

### Sprint 9~10 — Phase 2 연동 (4주)

| 순서 | ID | 기능 | 이유 |
|---|---|---|---|
| 41 | FR-P401 | Chain Sight 변화 신호 | Chain Sight v1.2 완료 후 |
| 42 | FR-P402 | 매크로 시나리오 영향 신호 | Dashboard 매크로 Thesis 완료 후 |
| 43 | FR-P403 | 뉴스 시그널 | News Pipeline 연동 |

### Phase 3 — 개인화 (시점 미정)

| ID | 기능 | 선행 조건 |
|---|---|---|
| FR-P404 | 1차 검증 지표 변화 신호 | |
| FR-P506 | 개인화 코칭 | 최소 6개월 History 데이터 |
| FR-P703 | 프리셋 적합도 분석 | |
| FR-P704 | 다음 기간 개선 포인트 | |
| FR-P802 | 내 투자 스타일 추정 | |
| - | Style 별도 탭 분리 | |
| - | History 별도 탭 분리 | |
| - | 장중 실시간 가격 연동 | |

---

## 8. 구현 순서 요약 — 마일스톤

```
Sprint 1~3 (6주)  → MVP 릴리즈
                     포트폴리오 CRUD + 온보딩 + 현황 뷰 + Coach 진단 카드
                     사용자가 "첫 가치"를 체험

Sprint 4~6 (6주)  → 핵심 루프 완성
                     예비 후보 관리 + History + Review + Coach 후보 연동
                     사용자가 "기록이 쌓이는 가치"를 체험

Sprint 7~10 (8주) → Phase 2
                     Thesis 연동 + 대화형 Coach + 외부 시스템 연동
                     사용자가 "연결된 생태계"를 체험

Phase 3 (시점 미정) → 개인화
                     패턴 학습 + 스타일 추정 + 완전 개인화 코칭
                     사용자가 "나만의 코치"를 체험
```

---

## 9. 미결 사항 / 추후 결정 필요

| # | 항목 | 설명 | 결정 시점 |
|---|---|---|---|
| 1 | 프리셋 지표 가중치 구체화 | 각 프리셋별로 어떤 지표에 어떤 가중치를 줄지 | Sprint 3 시작 전 |
| 2 | LLM 프롬프트 설계 | 진단 카드, 한 줄 진단, Coach 대화의 프롬프트 구조 | Sprint 3 |
| 3 | Coach 비중 조절 제안의 구체 수치 | "축소" 제안 시 목표 비중까지 제안할지 방향만 제안할지 | Sprint 3 |
| 4 | 벤치마크 기준 | S&P 500 / 사용자 지정 / 프리셋별 상이 | Sprint 6 |
| 5 | 증권사 API 연동 범위 | 어떤 증권사부터, 어떤 데이터까지 | Phase 2 이후 |
| 6 | 다중 통화 지원 | 한국 주식 + 미국 주식 혼합 포트폴리오 | Phase 2 이후 |
| 7 | Portfolio ↔ Chain Sight thesis 전환 UX | Chain Sight에서 만든 thesis가 Portfolio로 넘어오는 구체 UI 흐름 | Sprint 9 |
| 8 | 예비 후보 → 매수 전환 시 분할매수 자동매칭 엣지케이스 | 계획 외 가격/수량 매수 시 처리 방식 | Sprint 5 |
| 9 | Coach가 예비 후보 분석할 때의 면책 범위 | "구조적 분석"과 "매수 권유"의 구체적 경계선 | Sprint 6 |
| 10 | 자산 유형 확장 로드맵 | MVP는 개별 주식 전용. ETF는 Phase 2 후반~Phase 3에서 ticker 허용으로 자연스럽게 확장 (가격 데이터 구조 동일). 원자재(금/은)는 데이터 소스 확인 후 검토. 채권/파생상품은 사용자 수요 확인 후 검토. Stock 모델에 asset_type enum 추가로 대응 가능 | Phase 2 후반 이후 |
