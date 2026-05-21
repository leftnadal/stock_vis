═══════════════════════════════════════════════════════════════
[슬라이스 13 / Part 3] 작업 지시서
API 엔드포인트 추출 — E3 endpoint (preset_id 노출 + metrics 서버 계산)
═══════════════════════════════════════════════════════════════

■ 위치 / 전제

- 브랜치: slice13, HEAD = Part 2 커밋 (50c6313), working tree clean
- 베이스라인: 회귀 727 passed, IDENTICAL 31/31 PASS
- 누적 비용 $0 (Step 0~Part 2 전부 LLM 호출 0)
- 기존 자산: portfolio/api/{**init**,serializers,views,urls}.py 존재
  (E1·E2 endpoint 보유). config/urls.py include 완료.
- 슬라이스 유형: 표준 슬라이스 → Part 3 회귀 +Δ 예상 +11~15
  (E1·E2 단건 +10 + preset_id 검증 contract test 추가분. ±30% 임계 +8~20)

■ 핵심 설계 원칙 (위반 금지)

1. ADDITIVE — 기존 순수 Django view(E3 portfolio-level), 기존 urls
   라우팅, run_e3_coach service는 한 줄도 수정 금지. 새 DRF endpoint는
   /api/v1/coach/e3/ 경로에 추가만 한다.
2. Pydantic 단일 진실 소스 — E3 입출력 검증 계약은 기존 E3 Pydantic
   스키마가 보유. DRF serializer는 얇은 어댑터로만.
3. IDENTICAL 31/31 — service·LLM 호출 경로 무수정 → 해시 불변.
   깨지면 즉시 중단·보고.
4. 회귀 contract test는 LLM mock 기반 — real LLM 호출 0.
5. E1·E2 패턴 답습 — 새 설계 패턴 도입 금지. preset_id/metrics
   처리만 이번 Part의 신규 요소.
6. metrics = 도출값 → 서버 계산. 클라이언트 요청 표면에 metrics
   필드를 노출하지 말 것 (신뢰 경계 보호).

───────────────────────────────────────────────────────────────
■ 작업 0 — 사전 사실 확인 (★ 분기 결정 포함)
───────────────────────────────────────────────────────────────
0-1. E3 Pydantic 스키마 이름 확인

- CommentaryInputE3 / E3Output(또는 E3 output sub-schema)의 정확한
  클래스명을 portfolio/schemas/ 에서 확인. 추정 금지.
  0-2. run_e3_coach 시그니처 확인
- preset_id 인자: 받는 타입(str / enum / int?), 필수 여부.
- metrics 인자: 받는 타입(dict / Pydantic 모델?), 키 7종 이름 확인
  (hhi_concentration, sector_hhi, top3_weight, holding_count,
  portfolio_beta, max_position_weight, avg_correlation).
  0-3. ★★ metrics 서버 계산 경로 확인 — 분기 결정점 ★★
- 보유 종목(holdings)으로부터 portfolio Core 지표 7종을 계산하는
  함수/메서드가 코드베이스에 이미 존재하는가?
  (예: compute_portfolio_metrics, PortfolioMetrics.from_holdings 등.
  E3 service·schema·fixture 생성 경로를 추적해 확인할 것.)
  ┌─ 분기 A: 계산 경로가 존재하고 holdings만으로 7종 산출 가능
  │ → 작업 1~5를 그대로 진행. E3 view에서 그 함수를 호출.
  ├─ 분기 B: 계산 경로가 없거나, 일부 지표만 산출 가능
  │ → 여기서 중단. 작업 1 이후를 진행하지 말 것.
  │ 보고할 것: 어떤 지표가 산출 가능/불가능한지, 누락 지표를
  │ 계산하려면 어떤 입력·로직이 필요한지, 추정 작업 규모(소/중/대).
  │ → 병진+Claude가 "Part 3에 포함 vs 별도 부채"를 재판단한다.
  └─ ※ 분석엔진(#12, Phase 2 위임) 의존이 필요한 경우도 분기 B로
  간주하고 보고 — 분석엔진을 끌어오지 말 것.
  0-4. 기존 E3 순수 view 경로 확인 (무손상 대상 식별, diff 0 검증용).
  0-5. preset_id 검증 소스 확인
- 12개 preset 식별자 목록이 어디서 오는지 (PRESET_SCORERS, PresetSpec,
  enum 등). DRF ChoiceField choices 의 진실 소스로 쓸 것.
  ※ 0-1~0-5 결과를 part3_closing.md §1에 기록. 특히 0-3 분기 결과 명시.

───────────────────────────────────────────────────────────────
■ 작업 1 — E3 DRF serializer (serializers.py에 추가) [분기 A에서만]
───────────────────────────────────────────────────────────────
1-1. portfolio/api/serializers.py 에 E3용 serializer 추가

- E3 요청용 serializer:
  · preset_id — ChoiceField, choices = 0-5에서 확인한 12개 preset
  식별자 (잘못된 값 → 400). 필수 여부는 0-2 결과 따름.
  · holdings 등 E3 입력 필드 — 기존 E3 입력 스키마 위임.
  · ★ metrics 필드는 두지 않는다 (서버 계산).
- E3 응답용 serializer: run_e3_coach 반환 dict → 응답 JSON.
- 검증은 E3 Pydantic 스키마에 위임 (E1·E2 serializer와 동일 방식,
  Pydantic ValidationError → DRF ValidationError → 400).

───────────────────────────────────────────────────────────────
■ 작업 2 — E3 API endpoint (views.py + urls.py에 추가) [분기 A에서만]
───────────────────────────────────────────────────────────────
2-1. portfolio/api/views.py 에 E3 coach view 추가

- 처리 흐름:
  POST JSON → 요청 serializer 검증 → E3 입력 스키마 생성
  → metrics = (0-3에서 확인한 계산 함수)(holdings) ← 서버 계산
  → run_e3_coach(input, provider="haiku",
  preset_id=검증된 값, metrics=metrics)
  → 반환 dict를 응답 serializer로 직렬화 → 200.
- 에러 처리: 검증 실패 400 / 잘못된 preset_id 400 /
  service 예외 500(스택트레이스 미노출) / rate limit 429 /
  upstream 오류 502 — E1·E2 view와 동일 표면.
  2-2. portfolio/api/urls.py 에 E3 경로 추가
- 새 경로: POST /api/v1/coach/e3/
- config/urls.py 무수정 (include는 Part 1 완료).

───────────────────────────────────────────────────────────────
■ 작업 3 — contract test (회귀 편입) [분기 A에서만]
───────────────────────────────────────────────────────────────
3-1. 신규 파일: portfolio/tests/api/test_e3_endpoint.py

- LLM은 mock (real 호출 0).
- test_e2_endpoint.py 구조 복제 + E3 신규 케이스:
  · 정상 요청 → 200, 응답이 E3 output 계약에 부합
  · 필수 필드 누락 → 400 / 잘못된 타입 → 400
  · ★ 잘못된 preset_id (목록 외 값) → 400
  · ★ 정상 요청 시 metrics가 서버에서 계산돼 run_e3_coach에
  전달됨을 검증 (mock 호출 인자 assert)
  · service 예외 500 / rate limit 429 / upstream 502
- 경로는 모듈 상수: E3_ENDPOINT = "/api/v1/coach/e3/"
- ★ contract test = E3 output 계약 + preset_id 검증 + metrics
  서버 계산을 회귀로 고정.
  3-2. IDENTICAL 31/31 재실행 → PASS 확인.

───────────────────────────────────────────────────────────────
■ 작업 4 — 기존 view 무손상 확인 [분기 A에서만]
───────────────────────────────────────────────────────────────
4-1. 기존 E3 순수 view(0-4 식별)가 변경 후에도 git diff 0 임을 확인.
기존 E3 테스트 PASS로 동작 불변 자동 보증.
4-2. #65(기존 순수 view 최종 처리) OPEN 유지 — 6개 endpoint 완료 전
손대지 않음. 이번 Part 신규 부채 없으면 debts.md 무변경.

───────────────────────────────────────────────────────────────
■ 작업 5 — 문서 동기화 [분기 A에서만]
───────────────────────────────────────────────────────────────
5-1. docs/portfolio/coach/slice13/part3_closing.md 신규 작성

- 작업 0-1~0-5 결과(특히 0-3 분기), 회귀 카운트, IDENTICAL,
  endpoint 동작, contract test 커버리지.
  5-2. kpi_matrix.md §5 베이스라인 갱신 (727 → Part 3 종결값).

───────────────────────────────────────────────────────────────
■ Part 3 종결 체크리스트 [분기 A 기준]
───────────────────────────────────────────────────────────────
□ 회귀 전체 PASS, 카운트 = 727 +11~15 범위 내
□ IDENTICAL 31/31 PASS
□ 기존 E3 순수 view 동작 불변 (git diff 0, 기존 테스트 PASS)
□ POST /api/v1/coach/e3/ — 200 / 400(검증·preset_id) / 429 / 500 / 502
□ metrics가 클라이언트 요청 표면에 노출되지 않음 (서버 계산 확인)
□ contract test가 E3 output 계약 위반·preset_id 오류 시 FAIL
□ 작업 0 결과(특히 0-3 분기)가 part3_closing.md §1에 기록
□ kpi_matrix.md §5 갱신
□ 비용: real LLM 호출 0 → $0

■ 산출물 [분기 A]

- 코드(신규): portfolio/tests/api/test_e3_endpoint.py
- 코드(수정): portfolio/api/serializers.py, views.py, urls.py
- 문서: slice13/part3_closing.md 신규, kpi_matrix.md §5 갱신
- 보고: 체크리스트 결과 + 작업 0 전체 + 회귀 카운트 + IDENTICAL

■ 종료 후 커밋 [분기 A]
git commit -m "slice13: Part 3 — E3 API endpoint (preset_id 노출 + metrics 서버 계산)"

※ 분기 B면 작업 1 이후 전부 보류 — 0-3 보고만 가져올 것.
※ IDENTICAL이 깨지거나 기존 view 동작이 바뀌면 ADDITIVE 위반 —
즉시 중단·보고. Part 2 커밋(50c6313)으로 롤백 가능 상태 유지.
═══════════════════════════════════════════════════════════════
