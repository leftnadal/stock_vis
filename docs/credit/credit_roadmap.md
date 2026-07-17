# credit_roadmap.md — 크레딧 신호 축 정본 로드맵

> 위치: `docs/credit/credit_roadmap.md` · 이 문서가 크레딧 트랙의 정본이다.
> 단, 계약·규칙의 최종 정본은 코드다 — 이 문서의 규칙 서술이 코드와 어긋나면 코드가 이기고,
> 문서를 코드에 맞춰 고친다 (CAPTION-FIX 원칙, 2026-07-13).
> Claude 프로젝트(sv-credit) 지침서는 이 문서의 요약+포인터이며, 갱신은 이 문서 먼저.

## 1. 철학과 위치

**"bonds speak first."** 크레딧 시장은 주식보다 스트레스를 먼저 반영한다. 이 축은 그 선행
신호를 일일 원장으로 적립하고, 대시보드 최상단에서 의미(해석 문장 + 지표 해설)와 함께
서빙한다. 서비스 플로우 내 위치: Dashboard(시장 흐름) 단계의 매크로 입력. 발견(Chain Sight)
이전에 "오늘 시장의 신용 체온"을 3초 안에 읽게 하는 것이 목적.

## 2. 완료 트랙 (역순)

| 트랙                   | 종결일     | 내용                                                                                         | 최종 커밋 |
| ---------------------- | ---------- | -------------------------------------------------------------------------------------------- | --------- |
| CS-CREDIT-P2-0         | 2026-07-16 | 예약 2키 실현: BB/A 수집(6→8, 재비준 F) + 파생 CCC−BB·BBB−A compute-on-read + 8칩 심각도정렬(결정 g) · **자율가동 확증 07-17**(첫 자동 8키 수집) | 32c0559   |
| CS-CREDIT-CAPTION-FIX  | 2026-07-13 | 리드아웃 밴드 문구를 손글씨 → grading 코드 도출로 교체 (creditGrading.ts 미러 신설)          | 9ffd379   |
| CS-CREDIT-MEANING      | 2026-07-13 | 의미 2층: 규칙 기반 헤드라인(6패턴) + 신호별 리드아웃. 팝오버→리드아웃 전환(overflow 클리핑) | c1bc255   |
| CS-CREDIT-CONSUME      | 2026-07-12 | MacroStrip + GradeChip(제네릭) 홈 삽입, grade 색 토큰 colorSemantics 신설                    | —         |
| credit_signals Phase 1 | 2026-07-10 | FRED 백본, 6키 계약, 일일 07:30 KST 수집→compute→09:00 verify, 3년 백필(~4,680행)            | —         |

## 3. 계약 (코드 포인터)

- **신호 8키** = raw 6(HY_OAS · IG_OAS · BBB_OAS · CCC_OAS · CURVE_10Y2Y · VIX)
  + 파생 2(CCC_MINUS_BB · BBB_MINUS_A, **compute-on-read** — 원장 미적재, 정본
  `compute_derived_signal`). 예약 키 없음(`RESERVED_SIGNAL_KEYS = ()`, P2-0 실현).
  → `apps/credit_signals/` 모델·태스크.
- **grading (signed z, 하방 미발화)**: gray z<1(음수 포함) · yellow 1≤z<2 · orange z≥2(무상한)
  · red = HY_OAS 한정 z≥2 ∧ 값≥800bp(절대 레벨). 정본 `grade_from_z`(백엔드).
  프론트 미러 `frontend/lib/credit/creditGrading.ts` — Z_YELLOW=1 · Z_ORANGE=2 ·
  HY_CRISIS_BP=800 (백엔드 HY_OAS_CRISIS_BP의 미러, 값 동일).
  **백엔드 상수 변경 시 미러 1곳 동기화** (양쪽 주석 존재).
- **의미 1층 헤드라인**: `frontend/lib/credit/creditMeaning.ts` 순수함수, LLM 아님.
  **7패턴**: 기존 6(전부gray안정 / CCC단독=HY내부분화 / HY+CCC=광범위확대 / CURVE단독=금리축 /
  VIX단독=변동성축 / 기타=중립폴백 "관찰 n건") + **CCC_MINUS_BB단독=HY최저신용분화 심화**(P2-0).
  **BBB_MINUS_A 단독 패턴은 의도적 부재**(IG 내부 격차 단독 발화 희소 → 중립 폴백이 소화) — 누락 아님.
- **API**: `/api/credit-signals/strip/` (config/urls.py) — IsAuthenticated,
  {as_of, signals:[{key,name,value,z,grade,spark×30}]}.
- **UI**: MacroStrip.tsx + GradeChip.tsx (onActivate/active optional — TH 밴드 재사용 전제),
  grade 색 토큰 = colorSemantics.ts `grade` 네임스페이스.

## 4. 로드맵

### P2 — 크레딧 확장 (다음 착수)

> 소스 판정: CS-CREDIT-P2-SOURCESPIKE (2026-07-13, 발행사 직결합 범위) 결과로 아래 시퀀스 확정.
> 실측(CS-CREDIT-P2-MEASURE)이 로드맵 초안의 낙관(FMP NAV·만기 데이터 가정)을 교정함.

- **P2-0 예약 2키 실현 (CCC_MINUS_BB · BBB_MINUS_A) — 첫 집행 슬라이스.**
  FRED 동일 소스로 데이터 리스크 0: BB OAS = `BAMLH0A1HYBB`, A OAS = `BAMLC0A3CA`
  (기존 6키와 동일 ICE BofA 계열, 동일 fetcher). 파생 스프레드 = CCC−BB / BBB−A,
  신호화 = 스프레드 robust-z(기존 규약 재사용, red는 HY 한정이라 미발화). 원장은 raw 불변
  — 파생값은 compute-on-read(원장 미적재). 화면 6→8칩 → 스트립 심각도 정렬 동반(아래 결정 g).
- **P2a HYG/LQD 수급 (조건부).** 가격·거래량은 FMP `/stable/quote`(Starter) 즉시.
  현재 NAV는 FMP `/stable/etf/info`로 취득 추정(스파이크 판정 — 라이브 실사 미완).
  **프리미엄/디스카운트·플로우는 iShares 발행사 직결합 필요** — 신규 파서·시계열 모델·
  다운로드 URL 1건 실사가 선행(6c-11 일별 공시로 데이터 존재는 확실, `etf_csv_downloader`
  다운로드 메커니즘 재사용·파서는 신규). FMP는 NAV 이력·플로우 미제공.
- **P2b 차환 절벽 — 파킹.** 발행사 직결합 범위에 만기 도래 분포 소스 없음
  (FMP 채권 엔드포인트 부재, SEC 10-K 구조화 추출 비현실). 필요 시 iShares WAM/듀레이션
  단일 지표로 축소 재정의 가능하나 **진짜 maturity wall 아님(시간축 상실) 명기 필수.**

### P3 — 후보: 회사채 ↔ 개별주 연결

- credit 신호를 Chain Sight 관계축(발행사 노출)으로 연결. **본 프로젝트(Stock-Vis) 협의
  필수** — 트랙 간 통합 사안이므로 여기서 단독 결정 금지.

### 보류 큐

- **CS-CREDIT-INFOPANEL**: ⓘ 확장 패널 — TH 밴드 대시보드 합류 시 재검토.
- **밴드 메타데이터 API 공용화 (미러 철거)**: strip API 응답에 밴드 정의 포함 →
  creditGrading.ts 미러 제거. 발동 조건: 밴드 메타 소비처 2곳 도달(= TH 밴드 합류 시점).

## 5. 결정 이력 (크레딧 축 한정)

| #   | 결정        | 내용                                                                        |
| --- | ----------- | --------------------------------------------------------------------------- |
| B   | 앱 배치     | 전용 `credit_signals` Django 앱 (market_pulse 편입 아님)                    |
| a   | 스트립 인증 | IsAuthenticated 유지 (파생자산 정책)                                        |
| b   | 색 토큰     | colorSemantics.ts grade 네임스페이스 신설 (단일 소스)                       |
| c   | 밀도        | 6칩 전부 + z + 스파크, gray 저채도·비-gray 부상                             |
| D   | 의미 레이어 | D-1 헤드라인 + D-2 리드아웃 채택, D-3 패널 보류                             |
| —   | 문구 도출   | 화면의 규칙 서술은 코드에서 도출, 손글씨 금지                               |
| E   | P2 시퀀스   | 소스 판정 후 P2-0(예약2키·FRED) → P2a(HYG/LQD·iShares 직결합) → P2b 파킹    |
| g   | 스트립 밀도 | 6키 고정 해제 → 8칩 확장 + 심각도 정렬(비-gray 좌측), 칩 폭 불변(TH 무침범) |
| F   | 스코프 재비준 | FRED 6→8종 "고정" 불변규칙 명시 해제 (BB/A 수집, constants docstring 근거) — P2-0 |
| —   | 파생 저장   | compute-on-read 채택 — 원장 raw 순수성, STEP0 정합 0.00%(787=787)로 검증    |

## 6. 교훈 (이 트랙에서 발원)

- UI 슬라이스 마감 조건 = 라이브 렌더 스크린샷 필수 (스코프 테스트 GREEN ≠ 실화면 검증).
- 규칙 문서·화면 카피는 코드에서 도출 — 손글씨 리터럴은 "가짜 문서"가 된다.
- (참고) 신규 beat는 registered 확인 전 enabled 금지 — credit_signals가 회피, TH가 실증.
