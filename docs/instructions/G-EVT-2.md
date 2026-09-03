# G-EVT-2 — Phase 2 진입 프로브 (read-only · 외부 최대 6콜)

전제: EVT Phase 1 완결 계열(4B = main 35a1550b, CORR-3B 종결 3f539a70). 설계 앵커 v1.1 §7 G-EVT-2 그대로.
목적: Phase 2 백로그의 원천 접근성 실측 — ① FMP transcript(P2-iii 어닝 콜 AI 요약) ② M&A(§9 재소환 판단) ③ 어닝 서프라이즈 이력 EP(P2-ii 비용 절감). **구현·모델·수집기 변경 금지. 원장 쓰기 0.**
쓰기 = 0번 게이트 1커밋 + 하네스 기록만. push는 "푸시" 지시 대기.

## §0
0-1. `git fetch origin` → sv-evt-1 재사용, origin/main 기준 새 브랜치 `monorepo/sess-evt-7`. 해시 보고.
0-2. [0번 게이트] `docs/instructions/G-EVT-2.md` 1파일 커밋.
0-3. **예산 확인(하드)**: FMP 금일 사용량·cap(Starter 10,000/day) 실측. 잔여 < 500콜이면 HALT(프로브 연기).
0-4. 프로브 방식: 외부 콜은 **shared FMP client 경유**(규약 — 저수준 `_make_request` 사용 가능, 신규 래퍼 메서드 추가 금지·정식 메서드는 Phase 2 구현 시). foreground 스크립트, 응답 원문은 로그로만(원장 저장 금지).

## STEP 1 — transcript (2콜)
1-1. earning-call-transcript **목록/dates 계열 EP** 1콜(예: AAPL) → HTTP 상태·유료 게이트 징후(402/403/빈 응답+플랜 문구)·필드 목록·행수.
1-2. 가능하면 transcript 본문 EP 1콜(단일 분기) → 본문 존재·길이·언어. 1-1이 게이트 FAIL이면 1-2 생략(콜 절약).
판정 기재: PASS(P2-iii 원천 확보) / FAIL(대체 원천 결정 사이클 필요 — 8-K RSS 병행안 §9).

## STEP 2 — M&A (2콜)
2-1. mergers-acquisitions **latest** 1콜 → 상태·필드(심볼 쌍·발표일·거래가 유무)·행수.
2-2. **search** 1콜(예: symbol=NVDA) → 심볼 기준 조회 가능 여부.
판정 기재: §9 "M&A 이벤트 유형" 재소환 트리거의 ② 조건 충족 여부.

## STEP 3 — 어닝 서프라이즈 이력 (1콜)
3-1. earnings-surprises 계열 EP 1콜(예: NVDA) → 분기 수·필드(actual/estimated/발표일)·과거 커버리지 깊이.
판정 기재: P2-ii(어닝 반응 히스토리)를 자체 축적 대신 이 EP로 대체 가능한지(비용·커버리지 비교 한 줄).

## STEP 4 — 예비 (≤1콜)
캡·게이트 징후가 모호한 EP 1개에 한해 재시도 인가. 그 외 사용 금지.

## 보고 형식
EP별 표: 경로 · HTTP 상태 · 게이트 징후 · 핵심 필드 · 행수/깊이 · 판정. + 예산 소모(전/후) · 콜 수 합계(≤6 입증).
하네스: TASKQUEUE([G-EVT-2] 결과 반영 — P2-iii/P2-ii/M&A 각 PASS·FAIL 표기, 신규율 수렴 추적 항목 유지: 다음 2회 발화 <3% 확인) · PROGRESS. DECISIONS는 기록 없음(프로브는 결정 아님 — 결정은 디렉터 사이클).

## HALT: 0-3 예산 / 콜 6 초과 필요 상황 / 예상 밖 일체.
