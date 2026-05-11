# Stock-Vis Portfolio Coach — 문서 인덱스

> 최종 갱신: 2026-04-24 v6 (D-0b ~ D-8 작업 지시서 9개 추가)
> 상태: 세션 D 설계 + 모든 구현 지시서 완성. Claude Code가 D-0a부터 순차 실행 가능한 상태.

---

## 1. 폴더 구조

```
docs/portfolio/
├── INDEX.md                                  ← 이 파일
│
├── design/                                   ← 설계 문서 (8개)
│   ├── preset-design-v3.1.md                 ← 프리셋 시스템 설계서 (확정 결정 38개)
│   ├── preset-metrics-matrix.md              ← 12개 프리셋 × 지표 × 계층 매트릭스
│   ├── metric-dictionary-v1.2.md             ← 57개 지표 정의서
│   ├── portfolio-requirements-v0.2.md        ← Portfolio 기능 요구사항
│   ├── service-restructure.md                ← 서비스 아키텍처 재설계
│   │
│   │   ★ 세션 D (2026-04-20) 결과물 ─────────────────────────────────────
│   ├── wallet-portfolio-architecture-v1.md   ← Wallet/Portfolio 데이터 모델 분리
│   ├── return-tracking-design-v1.md          ← 수익률 추적 설계 (RV1~RV4)
│   └── coach-llm-design-v1.md                ← Coach LLM 아키텍처 (E1~E6, B3, D3, PV3)
│
├── reference/                                ← 레퍼런스 (1개, 변경 없이 유지)
│   └── preset-reference.md                   ← 투자 전략 40개 + 포트폴리오 이론 17개
│
├── instructions/                             ← 세션별 작업 지시서 (10개)
│   ├── d-0a-instructions.md                  ← 데이터 모델 리팩토링 (Wallet/Portfolio 재설계)
│   ├── d-0b-instructions.md                  ← Pydantic 스키마 (AnalysisContext 전체)
│   ├── d-1-instructions.md                   ← Tier 0 시스템 프롬프트 (정체성 + PV3 용어)
│   ├── d-2-instructions.md                   ← E1 한 줄 진단 프롬프트
│   ├── d-3-instructions.md                   ← E2 진단 카드 프롬프트 (4요소 JSON)
│   ├── d-4-instructions.md                   ← E3 지표별 한 줄 코멘트
│   ├── d-5-instructions.md                   ← E4 대화 Q&A (Tier 1~3 전체 주입)
│   ├── d-6-instructions.md                   ← E5 조정 파싱 (자연어 → overrides JSON)
│   ├── d-7-instructions.md                   ← E6 조정 후 비교 해설
│   └── d-8-instructions.md                   ← 통합 검증 + E2E 시나리오 테스트
│
├── implementation/                           ← 구현 산출물 (7개)
│   ├── models.py                             ← Django DB 모델 9개 (세션 D에서 리팩토링 예정)
│   └── metrics/definitions/
│       ├── __init__.py
│       ├── metrics.py                        ← 57개 지표 코드 상수
│       ├── presets.py                        ← 12개 프리셋 (applicable_scope 추가 예정)
│       ├── preset_metrics.py                 ← 136개 프리셋-지표 매핑
│       └── versions.py                       ← 버전 번들 (metric_version=1.2)
│
└── archive/                                  ← 이력용 (3개)
    ├── preset-design-v1.md
    ├── preset-design-v2.md
    └── portfolio-requirements-v0.1.md
```

**파일 수 합계**: 29개 (`.md` 23개 + `.py` 6개).

---

## 2. 현재 상태 (2026-04-20 기준)

### 2-1. Metric & Preset

| 항목 | 수량 |
|---|---|
| 총 지표 (Dictionary = 코드) | **57개** |
| MVP 프리셋 | **12개** |
| 프리셋-지표 매핑 | **136개** |

### 2-2. 세션 D 결정 사항

세션 D는 Portfolio Coach LLM 아키텍처 + 데이터 모델 재설계를 다룸. 총 **34개 결정** 확정. §4 참조.

### 2-3. 버전

| 버전 항목 | 현재 |
|---|---|
| metric_version | 1.2 |
| preset_version | 1.0 |
| scoring_version | 1.0 |
| prompt_version | 1.0 (세션 D-1 작성 후 1.1로 bump 예정) |
| universe_version | sp500_v1 |

---

## 3. 2026-04-20 세션 D 완료 작업

### 3-1. 신규 설계 문서 3개

세션 D에서 결정한 34개 사항을 주제별로 분리한 3개 문서로 완전 문서화.

#### `wallet-portfolio-architecture-v1.md`
- Wallet / Portfolio 개념 분리 (컨설턴트 비유)
- I2-a-refined 데이터 모델 (Wallet, WalletHolding, Portfolio 재정의, WalletSnapshot)
- UX 탭 구조 (자산 지갑 / 자산 전략실)
- 전략 저장 정책 (F3), 개별/포트폴리오 전략 (G3), 자산 변경 처리 (H3)
- Saved Analysis 스냅샷 (③)
- 마이그레이션 플랜

#### `return-tracking-design-v1.md`
- 수익률 요구사항 (해석 1 계층, 해석 2-c 기여도)
- R3 하이브리드 (MVP는 avg_cost, Trade는 Phase 2)
- sector/industry 필드 위치 (RV2-b, Stock 모델)
- ReturnCalculator 인터페이스 (RV3-a, 단일 메소드)
- 저장 시점 + 현재 시점 혼합 (RV4-b)
- 2개 독립 스코프 (Portfolio / Wallet, RV1-b)

#### `coach-llm-design-v1.md`
- MVP 진입점 E1~E6 정의
- 4-Tier 컨텍스트 전략 (B3)
- Tier 2.5 Pydantic 스키마 구조
- 대화형 Coach 레벨 1 조정 UX (A2)
- 의사결정 이력 D3 (raw + 추출)
- 사용자 프로필 전략 (Tier 3)
- LLM 혼동 방지 (PV3 + 부분 PV5)
- Wallet 분석 범위 (W2.5, A1)

### 3-2. INDEX.md 업데이트 (이 파일)

- 폴더 구조에 신규 design 문서 3개 추가
- 네이밍 결정 N-8 추가 (Wallet/Portfolio 의미 분리)
- 다음 작업 로드맵 갱신 (세션 D 구현 단계 D-0a~D-8)
- 변경 이력 v4 추가

---

## 4. 확정된 설계 결정 — 전체 목록

### 4-1. 누적 결정 개요

| 출처 | 결정 수 |
|---|---|
| 설계서 v3.1 부록 | 38 |
| Metric Dictionary 공통 결정 (D-1~D-8) | 8 |
| Django 모델 결정 (M-1~M-6) | 6 |
| 네이밍 결정 (N-1~N-8) | 8 |
| **세션 D 결정** | **34** |
| **합계** | **94** |

### 4-2. 세션 D 결정 상세 (34개)

#### 요구사항 범위
| # | 결정 |
|---|---|
| Req-1 | 사후 분석 (시점 A/B 비교) |
| Req-2 | 대화 저장 (질문-답변 스레드) |
| Req-3 | 의사결정 이력 (사용자 프로필) |
| Req-4 | 대화로 레벨 1 프리셋 조정 |

#### 기반
| # | 결정 |
|---|---|
| A2 | MVP = Q&A + 레벨 1 조정 |
| B3 | 4-Tier 계층적 요약 (retrieval 없음) |
| C1 | 수동 저장 기준 사후 분석 |
| D3 | raw + 구조화 Decision 추출 |

#### UX 확인
| # | 결정 |
|---|---|
| 확인1 | 분석 실행: 프리셋 선택 후 즉시 |
| 확인2 | 조정 UX: 확인 카드 → 실행 |
| 확인3 | 조정 범위: 프리셋/종목/비교군 전부 |
| 확인4 | MVP 진입점: E1~E6 |
| 확인5 | 대화 지속성: Saved Analysis에 포함 |

#### UI/UX
| # | 결정 |
|---|---|
| 탭 구조 | 자산 지갑 / 자산 전략실 분리 |
| 재분석 배지 | 제거 |
| Tier 2.5 | β (분석 결과 + 확장 슬롯) |
| 분석 스냅샷 | ③ (Saved=스냅샷, Temp=라이브) |
| Thesis | Y1 (수동 텍스트) |
| 전략실 진입 | A (이전 결과 + 재분석 버튼) |

#### 수익률 추적
| # | 결정 |
|---|---|
| 해석 1 | 섹터/인더스트리/종목 계층 |
| 해석 2 | c (현재 보유 기여도 분해) |
| R | R3 (하이브리드) |
| RV1 | b (Portfolio + Wallet 독립 필드) |
| RV2 | b (Stock 모델에 sector/industry) |
| RV3 | a (ReturnCalculator 단일 메소드) |
| RV4 | b (저장 시점 + 현재 시점) |

#### 분석 스코프
| # | 결정 |
|---|---|
| F3 | 전략 저장: 일회성 + 명명 그룹 |
| G3 | 개별/포트폴리오: applicable_scope 필드 |
| H3 | 자산 변경: 참조 링크 + 자동 필터링 |
| I2-a-refined | 모델: Wallet 신규 + Portfolio 의미 재정의 |

#### LLM 아키텍처
| # | 결정 |
|---|---|
| PV3 | 정의 블록 + 자기설명 필드명 |
| 부분 PV5 | E1~E3, E5~E6 Wallet 최소, E4만 전체 |
| W2.5 | Wallet 분석: 시나리오 A+B (C 제외) |
| A1 | Wallet 시계열: WalletSnapshot (주기 배치 없음) |

### 4-3. 네이밍 결정 (N-1~N-8)

이전 N-1~N-7 유지. 세션 D에서 N-8 추가.

| # | 대상 | 결정 |
|---|---|---|
| N-1~3 | Multi-Factor 합성 | `composite_*` 통일 |
| N-4 | 5번째 팩터 슬롯 | `composite_low_vol` |
| N-5 | 보유 종목 수 | `holding_count` |
| N-6 | 집중도 지표 | `hhi_concentration` + `sector_hhi` |
| N-7 | 상위 종목 비중 | `top3_weight` |
| **N-8** | **Wallet/Portfolio 의미 분리** | **Wallet=자산 지갑, Portfolio=분석 대상 슬라이스** |

---

## 5. 다음 작업 로드맵

### 5-1. 세션 D 구현 단계 (다음 진입)

| 세션 | 작업 | 예상 |
|---|---|---|
| D-0a | 데이터 모델 리팩토링 (models.py: Wallet, WalletHolding, Portfolio 재정의, WalletSnapshot, ChatSession, Message, Decision) | 1.5 세션 |
| D-0b | Tier 2.5 Pydantic 스키마 (AnalysisContext 전체) | 0.5 세션 |
| D-1 | Tier 0 시스템 프롬프트 (정체성 + 정의 블록) | 0.5 세션 |
| D-2 | E1 한 줄 진단 프롬프트 | 0.5 세션 |
| D-3 | E2 진단 카드 프롬프트 (4요소 JSON) | 1 세션 |
| D-4 | E3 지표 코멘트 프롬프트 | 0.5 세션 |
| D-5 | E4 대화 Q&A 프롬프트 | 1 세션 |
| D-6 | E5 조정 파싱 프롬프트 | 1 세션 |
| D-7 | E6 조정 해설 프롬프트 | 0.5 세션 |
| D-8 | 통합 검증 + 예시 시나리오 end-to-end | 1 세션 |

**총 예상**: 약 9~10세션.

### 5-2. D-0a 사전 확인 결과 (2026-04-20 완료)

Stock 모델 확인 완료 — **RV2-b 경로 확정**:
- `stocks/models.py:27` — `sector = CharField(max_length=100, blank=True, null=True)` ✅
- `stocks/models.py:26` — `industry = CharField(max_length=100, blank=True, null=True)` ✅
- 인덱스: `Index(["sector"])`, `Index(["industry"])`, `Index(["symbol", "sector"])` 복합 인덱스 모두 존재

**결론**:
- Stock 모델 수정 작업 **불필요**
- WalletHolding에 sector/industry 캐시 필드 추가 **금지** (RV2-a 폴백 배제)
- WalletHolding은 Stock FK로 sector/industry 조회하는 RV2-b 그대로 진행

### 5-3. MVP 준비 단계 (세션 D 이후)

- 비교군 정책 상세화 (산업 분류 fallback)
- 강점/약점 선정 알고리즘 상세
- API 설계 (REST 엔드포인트)
- UI 와이어프레임

### 5-4. Phase 2+ (MVP 이후)

- 진입점 E7~E12 추가 (사후 비교, Decision 추출, 프로필 생성, Portfolio 후보 추천, Watchlist 제안, 모니터링 지표 추천)
- 조정 레벨 2/3 (세션 스코프 → 영구 커스텀 프리셋)
- Trade 모델 도입 (정밀 수익률, 세금 계산)
- PortfolioSnapshot 일별 배치
- Chain Sight / Thesis Layer 2 연결
- 대화형 Coach 확장 (Watchlist/모니터링 대화)
- Russell 3000 유니버스 확장
- 행동 편향 분석 (BPT, Phase 3)

---

## 6. 핵심 문서 안내

### 처음 읽을 순서

1. **`design/preset-design-v3.1.md`** — 전체 Coach 철학, 설계 결정 38개
2. **`design/wallet-portfolio-architecture-v1.md`** — Wallet/Portfolio 데이터 모델 (세션 D)
3. **`design/return-tracking-design-v1.md`** — 수익률 추적 설계 (세션 D)
4. **`design/coach-llm-design-v1.md`** — Coach LLM 아키텍처 (세션 D)
5. **`design/metric-dictionary-v1.2.md`** — 57개 지표 정의
6. **`design/preset-metrics-matrix.md`** — 12개 프리셋 상세

### 목적별 참조

| 목적 | 문서 |
|---|---|
| 특정 지표 산식·FMP 필드 | metric-dictionary-v1.2.md |
| 프리셋 철학과 진단 카드 예시 | preset-metrics-matrix.md |
| Wallet과 Portfolio 관계 | wallet-portfolio-architecture-v1.md |
| 수익률 분해 로직 | return-tracking-design-v1.md |
| LLM 진입점/프롬프트 전략 | coach-llm-design-v1.md |
| 대화/의사결정 이력 구조 | coach-llm-design-v1.md §5-6 |
| DB 스키마 현재 구현 | implementation/models.py |
| Portfolio 기능 스펙 | portfolio-requirements-v0.2.md |
| 서비스 플로우 | service-restructure.md |
| 설계 결정 배경 | preset-design-v3.1.md 부록 + 각 세션 D 문서 §확정 결정 |
| D-0a 모델 리팩토링 작업 지시 | instructions/d-0a-instructions.md |
| D-0b Pydantic 스키마 작성 지시 | instructions/d-0b-instructions.md |
| D-1 Tier 0 시스템 프롬프트 작성 지시 | instructions/d-1-instructions.md |
| D-2~D-7 E1~E6 프롬프트 작성 지시 | instructions/d-2~d-7-instructions.md |
| D-8 통합 검증 + E2E 테스트 지시 | instructions/d-8-instructions.md |

---

## 7. Git 커밋 권장 구조 (세션 D 완료 시점)

```bash
# Commit 1: 세션 D 설계 문서 3개 추가
git add docs/portfolio/design/wallet-portfolio-architecture-v1.md
git add docs/portfolio/design/return-tracking-design-v1.md
git add docs/portfolio/design/coach-llm-design-v1.md
git commit -m "docs(session-d): Add 3 design documents — Wallet/Portfolio architecture, return tracking, Coach LLM"

# Commit 2: INDEX.md v4 업데이트
git add docs/portfolio/INDEX.md
git commit -m "docs: update INDEX.md v4 with session D results"

# ---- 이후 D-0a, D-0b 등 진행 시 ----
# Commit 3: models.py 리팩토링 (세션 D-0a)
git add docs/portfolio/implementation/models.py
git commit -m "refactor(models): introduce Wallet/Portfolio separation — session D-0a"

# (이후 D-1, D-2, ... 각 프롬프트 추가 시 개별 커밋)
```

---

## 8. 변경 이력

| 날짜 | 버전 | 변경 |
|---|---|---|
| 2026-04-24 | v6 | D-0b ~ D-8 작업 지시서 9개 추가 (instructions/d-0b ~ d-8). Claude Code가 D-0a 완료 후 순차 실행 가능. 파일 수 20→29 |
| 2026-04-20 | v5 | D-0a 작업 지시서 추가 (`instructions/d-0a-instructions.md`). Stock 모델 확인 결과 반영 (RV2-b 확정). 파일 수 19→20 |
| 2026-04-20 | v4 | 세션 D 완료. 설계 문서 3개 추가 (wallet-portfolio-architecture-v1, return-tracking-design-v1, coach-llm-design-v1). 설계 결정 34개 추가 (총 94개). 네이밍 결정 N-8 추가. 다음 작업 로드맵 D-0a~D-8 정의 |
| 2026-04-20 | v3.1 | Dictionary ↔ 코드 동기화 완료. 지표 53→57개, 매핑 126→136개, metric_version 1.0→1.2. Piotroski 서브 9개 Dictionary 통합. 파일명 v1.1→v1.2 |
| 2026-04-18 | v2 | 파일 16개 실물 분석 + 대화 이력 교차 검증. 누락 파일 2건 정정. 네이밍 결정 7건 확정. 동기화 액션 플랜 20건 작성 |
| 2026-04-18 | v1 | 초판 (대화 기반 추정) |
