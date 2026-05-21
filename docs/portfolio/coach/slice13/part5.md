═══════════════════════════════════════════════════════════════
[슬라이스 13 / Part 5] 작업 지시서
API 엔드포인트 추출 — E4 endpoint (마지막 진입점, 순수 복제)
═══════════════════════════════════════════════════════════════

■ 위치 / 전제

- 브랜치: slice13, HEAD = Part 4 커밋 (54cc47f), working tree clean
- 베이스라인: 회귀 757 passed + 1 skipped, IDENTICAL 31/31 PASS
- 누적 비용 $0 (Step 0~Part 4 전부 LLM 호출 0)
- 기존 자산: portfolio/api/{**init**,serializers,views,urls}.py
  (E1·E2·E3·E5·E6 endpoint 보유). config/urls.py include 완료.
- 슬라이스 유형: 표준 슬라이스, 단건 → Part 5 회귀 +Δ 예상 +9~13
  (E1~E3 단건 +10 선례. 순수 복제. ±30% 임계 +6~17)

■ 사전 점검 결과 (확정 사실 — 재확인 불필요)

- run_e4_coach: 표준 시그니처 존재 (portfolio/services/coach/e4_service.py:19)
  run_e4_coach(input_data: CommentaryInputE4, provider="haiku",
  client=None, max_tokens=2000) -> dict[str, Any]
  · ★ preset_id/metrics kwarg 없음 (다른 진입점과 차이) — 정합화 불필요.
- 입력 스키마: CommentaryInputE4 (commentary_input.py:145, InputBase 편입)
  필드: entry_point="e4", user_question(str), conversation_history(list)
- 출력 스키마: E4Output (commentary_output.py:114, OutputBase 편입)
  base만 사용 — action_items/risk_flags 등 특화 필드 없음.
- 기존 E4 순수 view·URL: 없음 (legacy view 부재 — E4 유일).
- fixture: portfolio_a2.json 의 inputs.e4 (keys: user_question,
  conversation_history) — load_portfolio_a2_raw()로 활용.
- IDENTICAL 31 셋: 20/31이 E4 관련(test_e4_conversation_schema.py 등).

■ 핵심 설계 원칙 (위반 금지)

1. ADDITIVE — run_e4_coach service·E4PromptBuilder·E4 스키마는 한 줄도
   수정 금지. 새 DRF endpoint는 /api/v1/coach/e4/ 경로에 추가만.
2. Pydantic 단일 진실 소스 — 입출력 검증은 CommentaryInputE4 / E4Output
   에 위임. DRF serializer는 얇은 어댑터로만.
3. ★★ IDENTICAL 31/31 — Part 5는 IDENTICAL 보호가 특히 중요.
   31건 중 20건이 E4 관련 → run_e4_coach·E4PromptBuilder·LLM 경로를
   건드리면 즉시 깨진다. 해시 불변 필수. 깨지면 즉시 중단·보고.
4. 회귀 contract test는 LLM mock 기반 — real LLM 호출 0.
5. E1~E3·E5·E6 패턴 순수 복제 — 새 설계 패턴·정합화 작업 없음.

───────────────────────────────────────────────────────────────
■ 작업 1 — E4 DRF serializer (serializers.py에 추가)
───────────────────────────────────────────────────────────────
1-1. portfolio/api/serializers.py 에 E4용 serializer 추가

- 요청용: 클라이언트 JSON → 검증 → CommentaryInputE4 변환.
  핵심 입력 필드 user_question / conversation_history 포함.
  검증은 CommentaryInputE4 에 위임 (다른 serializer와 동일 방식).
- 응답용: run_e4_coach 반환 dict → 응답 JSON. 반환 구조는
  {"output": E4Output.model_dump(), "llm_metadata": {...}} — E1~E3·
  E5·E6 응답 serializer와 동형 처리.
- E5/E6 serializer 구조 그대로 복제.
- ★ preset_id/metrics 필드를 두지 않는다 (run_e4_coach가 받지 않음).

───────────────────────────────────────────────────────────────
■ 작업 2 — E4 API endpoint (views.py + urls.py에 추가)
───────────────────────────────────────────────────────────────
2-1. portfolio/api/views.py 에 E4 coach view 추가

- 처리 흐름 (E1~E3·E5·E6 view와 동형):
  POST JSON → 요청 serializer 검증 → CommentaryInputE4 생성
  → run_e4_coach(input_data, provider="haiku") 호출
  (★ preset_id/metrics 전달 안 함 — 함수가 받지 않음)
  → 반환 dict를 응답 serializer로 직렬화 → 200.
- 에러 처리: 400 / 500(스택트레이스 미노출) / 429 / 502 —
  다른 endpoint와 동일 표면.
  2-2. portfolio/api/urls.py 에 E4 경로 추가
- 새 경로: POST /api/v1/coach/e4/
- config/urls.py 무수정 (include는 Part 1 완료).

───────────────────────────────────────────────────────────────
■ 작업 3 — contract test (회귀 편입)
───────────────────────────────────────────────────────────────
3-1. 신규 파일: portfolio/tests/api/test_e4_endpoint.py

- LLM은 mock (real 호출 0).
- test_e5_endpoint.py 10건 구조 복제, E4용 조정:
  · 정상 요청 → 200, 응답이 E4Output 계약에 부합
  · 필수 필드 누락(user_question 등) → 400 / 잘못된 타입 → 400
  · service 예외 → 500 + 스택트레이스 미노출
  · rate limit → 429 / upstream 오류 → 502
- 경로는 모듈 상수: E4_ENDPOINT = "/api/v1/coach/e4/"
- ★ mock 호출 인자 검증 주의: run_e4_coach 는 preset_id/metrics
  kwarg가 없으므로, 다른 진입점의 "kwarg 미전달 검증"을 그대로
  복사하지 말 것. E4 mock은 (input_data, provider) 만 받는 형태로
  assert — 함수 시그니처에 맞춰 검증.
- ★ contract test = E4Output 계약을 회귀로 고정 → schema drift 감지.
  3-2. IDENTICAL 31/31 재실행 → PASS 확인.
- 31건 중 20건이 E4 관련 — Part 5가 E4 service/LLM 경로를 안
  건드렸음을 이 체크가 직접 보증.

───────────────────────────────────────────────────────────────
■ 작업 4 — 기존 view 무손상 확인 (E4 특이 처리)
───────────────────────────────────────────────────────────────
4-1. ★ E4는 legacy 순수 view가 없음 — 다른 Part의 "git diff 0" 검증이
성립하지 않음. 대신 다음을 확인:
· portfolio/views.py·urls.py 에 coach*e4*\* 함수·E4 legacy 경로가
Part 5에서 신규 추가되지 않았음 (git diff로 두 파일 무변경 확인).
· 즉 Part 5는 portfolio/api/ 와 portfolio/tests/api/ 에만 변경.
4-2. #65(기존 순수 view 최종 처리): Part 5 종결 = E1~E6 6개 endpoint
완료 시점. #65 진입 가능해짐. debts.md §1 의 #65 단서에
"E4는 legacy view 부재 → special case(마이그레이션 대상 아님)"
를 1줄 보강 기록.

───────────────────────────────────────────────────────────────
■ 작업 5 — 문서 동기화
───────────────────────────────────────────────────────────────
5-1. docs/portfolio/coach/slice13/part5_closing.md 신규 작성

- 사전 점검 결과 요약(정합화 0 확정, 인계 메모 부정확 정정),
  회귀 카운트, IDENTICAL(E4 20/31 보호 확인), endpoint 동작,
  contract test 커버리지.
- ★ slice13 종합: E1~E6 6개 endpoint 완료 현황표 + #65 진입 안내.
  5-2. kpi_matrix.md §5 베이스라인 갱신 (757 → Part 5 종결값).
  5-3. debts.md §1 #65 단서 보강 (4-2).

───────────────────────────────────────────────────────────────
■ Part 5 종결 체크리스트
───────────────────────────────────────────────────────────────
□ 회귀 전체 PASS, 카운트 = 757 +9~13 범위 내
□ IDENTICAL 31/31 PASS (★ E4 경로 무수정 — 20/31 carrier 보호)
□ portfolio/views.py·urls.py 무변경 (E4 legacy view 신규 추가 없음)
□ POST /api/v1/coach/e4/ — 200 / 400 / 429 / 500 / 502
□ contract test가 E4Output 계약 위반 시 FAIL
□ E4 mock 검증이 run_e4_coach 실제 시그니처에 맞춰 작성됨
(preset_id/metrics kwarg 미존재 반영)
□ part5_closing.md 신규 (E1~E6 완료 현황 + #65 안내)
□ kpi_matrix.md §5 갱신, debts.md §1 #65 단서 보강
□ 비용: real LLM 호출 0 → $0

■ 산출물

- 코드(신규): portfolio/tests/api/test_e4_endpoint.py
- 코드(수정): portfolio/api/serializers.py, views.py, urls.py
- 문서: slice13/part5_closing.md 신규, kpi_matrix.md §5,
  debts.md §1(#65 단서 보강)
- 보고: 체크리스트 결과 + 회귀 카운트 + IDENTICAL + E1~E6 완료 현황

■ 종료 후 커밋
git commit -m "slice13: Part 5 — E4 API endpoint (마지막 진입점)"

※ IDENTICAL이 깨지면 E4 service/LLM 경로를 건드린 것 — 즉시 중단·보고.
Part 4 커밋(54cc47f)으로 롤백 가능 상태 유지.
═══════════════════════════════════════════════════════════════
