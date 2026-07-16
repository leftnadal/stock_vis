# SLICE 20A 지시서 — Coach 화면 1부: REST 표면 + 권유 읽기 (admin 입력 지름길)

> **배치 위치:** `docs/portfolio/coach/slice20a/SLICE20A_INSTRUCTION.md` — 실행 세션이므로 세션 시작 전 repo 배치 필수.
>
> **세션 종류:** 실행 세션. 설계 결정은 2026-07-16 디렉터·사용자 사이클에서 닫혔다(§4 — D1 자동 확정 마진 1.10, D2·D3 사용자 확정). 이 세션은 결정을 다시 열지 않는다. 단 STEP 0가 전제를 깨면 HALT(§7).
>
> **왜 이 슬라이스인가:** 19c까지 엔진은 완성됐지만 UI 진입점이 0이다 — `run_advisory`는 파이썬 함수일 뿐 REST가 없고, coach E1~E6 화면은 dead-end다. 20a는 그 엔진을 병진이 매일 읽을 수 있는 화면으로 만든다. 입력(wallet·watchlist·손잡이 조작)은 20b로 미루고, 당분간 Django admin을 입력 지름길로 쓴다(1인 도그푸딩). 사용 루프: admin에 보유 입력 → [지금 진단] → My 탭에서 갭·모드·BUY/TRIM/탐험 권유 읽기.
>
> **base:** `origin/main = dbe0986`, pytest 637 green (19c 랜딩 시점 — 재측정 대상). vitest·tsc 기준선은 STEP 0 실측이 baseline.
> **LLM 비용:** REST+화면 — LLM 호출 0.

## 0. DoD
1. AdvisoryRun `trigger` 필드 가산(`auto`/`manual`, D2) — mig 0006 가산만.
2. nightly advisory 자동 기록(`trigger=auto`). beat 코드 정의까지만(DB 등록=prod 후보).
3. REST 표면(`apps/portfolio`, DRF 얇은 어댑터): GET 최신 권유 / GET 자산 요약+갭·모드 / GET 손잡이 읽기전용 / POST 수동 진단(`trigger=manual`). 전부 user 스코프. spectacular 반영.
4. My 탭 권유 읽기 화면: 요약 스트립 + 권유 리스트(BUY/HOLD/TRIM·레인 구분·근거) + 예상수익률 빈 슬롯 placeholder + 손잡이 읽기전용 + [지금 진단]. E1~E6 연결 안 함(20b).
5. admin 입력 지름길: WalletHolding·WatchlistItem·CashBalance·UserGoal(+Wallet) 등록(미등록만 가산).
6. 테스트: REST 4종 user 스코프·trigger·수동 실행(pytest) + 화면 렌더·빈/에러 상태(vitest+MSW).
7. codegen 최신화, tsc strict clean, drift 0.
8. 회귀: pytest 637→종료 깨짐 0. vitest·tsc baseline 유지. 아키텍처·동결 0. `--check` clean(0006 외 재생성 0).

## 1. 절대 규칙 (넘으면 HALT)
- 메모리 신뢰 금지(STEP 0 재측정).
- **계약 v3 가산 전용 진화(D0 헌법)**: 기존 필드 의미·형태 변경 금지. 이번 가산 = trigger·REST 봉투뿐.
- **유령 필드 화면 노출 금지**: analyst_*·forward_pe 등 writer 없는 필드 금지. 예상수익률=빈 슬롯 placeholder만(가짜 값·프록시 금지).
- **손잡이 쓰기 금지(20a)**: REST에 손잡이 PUT/PATCH 없음. 엔진 자동 조정 코드 금지(주권).
- 한 방향 규칙: apps/portfolio(+프론트 하우스 구조 실측). shared 역참조 금지.
- 행위보존: 엔진 로직 무변경. trigger 가산·nightly 외 기존 모델·마이그레이션 재생성 0. 기존 pytest·vitest 깨짐=회귀=HALT.
- prod 미적용 유지(mig 0006 dev만).
- 결정 재오픈 금지(§4 닫힘).

## 4. 닫힌 결정 (Part A 기록)
- **D0** 계약 가산 전용 진화(신규 원칙).
- **D1** 스코프 분할(자동 확정 1.10): 20a=REST+읽기화면+admin / 20b=손잡이·입력UI·E1~E6.
- **D2** 실행 트리거=혼합(4.60): nightly auto + 수동 manual. 사후분석은 auto만 표본.
- **D3** 손잡이 UI=슬라이더 직접 노출(도그푸딩 우선). 실행 20b, 20a는 읽기전용.
- mgmt 인라인 관례 명문화: 실행=repo 배치 필수 / mgmt=인라인 허용.

## 5. 실행 계획
- **A** 결정 선행 기록(DECISIONS §4 + TASKQUEUE).
- **B** 백엔드: trigger 가산(mig 0006) + nightly advisory 태스크(trigger=auto, beat 코드정의) + admin 등록.
- **C** REST 표면: 조회 3 + 수동 POST, user 스코프, spectacular + pytest.
- **D** 프론트: codegen + My 탭 화면(요약·권유·빈슬롯·손잡이·[지금 진단]) + 빈/에러 상태 + vitest.
- **E** 닫기: 전체 pytest+vitest+tsc+`--check`+health+아키텍처. 닫기 보고(§6).

## 7. HALT 트리거
baseline red / REST 표면 이미 존재(재사용 전환 보고) / `--check` 0006 외 재생성 / 엔진·기존 admin·기존 계약 필드 변경 필요 / 손잡이 쓰기·자동조정 필요 / 유령 필드 노출 필요 / 프론트 하우스 패턴 실측 불가 / shared 역참조·prod 필요.

## 8. 다음 (범위 밖)
20a 랜딩 mgmt → 20b(손잡이 슬라이더·입력 UI·E1~E6 연결) → SIGNAL-FORWARD-INFRA(예측 정본, 빈 슬롯 채움).
