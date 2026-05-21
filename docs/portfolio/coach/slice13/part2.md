═══════════════════════════════════════════════════════════════
[슬라이스 13 / Part 2] 작업 지시서
API 엔드포인트 추출 — E2 endpoint (E1 패턴 복제)
═══════════════════════════════════════════════════════════════

■ 위치 / 전제

- 브랜치: slice13, HEAD = Part 1.5 커밋 (28d19c4), working tree clean
- 베이스라인: 회귀 717 passed, IDENTICAL 31/31 PASS
- 누적 비용 $0 (Step 0~Part 1.5 전부 LLM 호출 0)
- 기존 자산: portfolio/api/{**init**,serializers,views,urls}.py 존재
  (Part 1에서 E1용으로 신설). config/urls.py에 include 완료.
- 슬라이스 유형: 표준 슬라이스 → Part 2 회귀 +Δ 예상 +9~13
  (Part 1 E1 단건 +10 선례 기준. ±30% 임계 +6~17)

■ 핵심 설계 원칙 (위반 금지)

1. ADDITIVE — 기존 순수 Django view(E2 진단 카드용), 기존 urls
   라우팅, run_e2_coach service는 한 줄도 수정 금지. 새 DRF endpoint는
   /api/v1/coach/e2/ 경로에 추가만 한다.
2. Pydantic 단일 진실 소스 — E2 입출력 검증 계약은 기존 E2 Pydantic
   스키마가 보유. DRF serializer는 그 위의 얇은 어댑터로만 쓰고,
   검증 로직을 중복 구현하지 말 것.
3. IDENTICAL 31/31 — Part 2는 service·LLM 호출 경로를 안 건드리므로
   해시 불변이어야 한다. 깨지면 즉시 중단·보고.
4. 회귀 contract test는 LLM mock 기반 — Part 2에서 real LLM 호출 0.
5. E1 패턴 답습 — Part 1에서 만든 E1 serializer/view/test 구조를
   그대로 복제. 새로운 설계 패턴을 도입하지 말 것.

───────────────────────────────────────────────────────────────
■ 작업 0 — 사전 사실 확인 (지시서 추정 검증)
───────────────────────────────────────────────────────────────
0-1. E2 Pydantic 스키마 이름 확인

- Part 1 E1 endpoint는 CommentaryInputE1 / E1Output(또는 E1 output
  sub-schema)을 사용. 이에 대응하는 E2 스키마의 정확한 클래스명을
  portfolio/schemas/ 에서 확인 (예: CommentaryInputE2, E2Output 등).
- 확인된 실제 이름을 이후 모든 작업에 사용 (추정 금지).
  0-2. run_e2_coach 시그니처 확인
- run_e2_coach의 인자/반환 타입이 run_e1_coach와 동형인지 확인.
- provider 인자, preset_id/metrics kwarg 유무 확인.
  0-3. 기존 E2 순수 view 경로 확인
- 기존 E2 진단 카드 view가 어느 URL에 노출돼 있는지 확인 (무손상
  대상 식별용). diff 0 검증에 사용.
  ※ 0-1~0-3 결과를 part2_closing.md에 1줄씩 기록.

───────────────────────────────────────────────────────────────
■ 작업 1 — E2 DRF serializer (serializers.py에 추가)
───────────────────────────────────────────────────────────────
1-1. portfolio/api/serializers.py 에 E2용 serializer 추가

- E2 요청용 serializer: 클라이언트 JSON → 검증 → E2 입력 스키마 변환.
- E2 응답용 serializer: run_e2_coach 반환 dict → 응답 JSON.
- 검증은 E2 Pydantic 스키마에 위임 — E1 serializer와 동일한 방식
  (Pydantic ValidationError → DRF ValidationError 변환 → 400).
- E1 serializer 코드 구조를 그대로 복제. 필드별 비즈니스 검증을
  serializer에 중복 구현하지 말 것.

───────────────────────────────────────────────────────────────
■ 작업 2 — E2 API endpoint (views.py + urls.py에 추가)
───────────────────────────────────────────────────────────────
2-1. portfolio/api/views.py 에 E2 coach view 추가

- 처리 흐름 (E1 view와 동형):
  POST JSON → 요청 serializer 검증 → E2 입력 스키마 생성
  → run_e2_coach(input_data, provider="haiku") 호출
  → 반환 dict를 응답 serializer로 직렬화 → 200 응답.
- 에러 처리: 검증 실패 400 / service 예외 500(스택트레이스 미노출)
  / rate limit 429 / upstream 오류 502 — E1 view와 동일 표면.
- 0-2에서 run_e2_coach가 preset_id/metrics kwarg를 받으면, 이번
  Part에서는 전달하지 않음(None) — 기존 동작 유지.
  2-2. portfolio/api/urls.py 에 E2 경로 추가
- 새 경로: POST /api/v1/coach/e2/
- 최종 노출 경로가 정확히 /api/v1/coach/e2/ 가 되도록 확인.
- config/urls.py 는 무수정 (include는 Part 1에서 완료).

───────────────────────────────────────────────────────────────
■ 작업 3 — contract test (회귀 편입)
───────────────────────────────────────────────────────────────
3-1. 신규 파일: portfolio/tests/api/test_e2_endpoint.py

- LLM은 mock (real 호출 0).
- test_e1_endpoint.py 의 10건 구조를 복제, E2용으로 조정:
  · 정상 요청 → 200, 응답이 E2 output 스키마에 부합 (계약 검증)
  · 필수 필드 누락 → 400 / 잘못된 타입 → 400
  · service 예외 → 500 + 스택트레이스 미노출
  · rate limit → 429 / upstream 오류 → 502
- 경로는 모듈 상수로 추출: E2_ENDPOINT = "/api/v1/coach/e2/"
  (Part 1.5에서 E1에 적용한 방식 답습).
- ★ contract test = "E2 응답이 E2 output 계약을 지키는가"를 회귀로
  고정 → 스키마 드리프트 자동 감지.
  3-2. IDENTICAL 31/31 재실행 → PASS 확인 (service/LLM 경로 무수정).

───────────────────────────────────────────────────────────────
■ 작업 4 — 기존 view 무손상 확인
───────────────────────────────────────────────────────────────
4-1. 기존 E2 순수 view(0-3에서 식별)가 Part 2 변경 후에도 git diff 0
임을 확인. 기존 E2 테스트 PASS로 동작 불변 자동 보증.
4-2. #65(기존 순수 view 최종 처리)는 이미 등록됨 — OPEN 유지.
E1~E6 6개 endpoint 마이그레이션 완료 전까지 손대지 않음.
이번 Part에서 신규 부채 등록 사항 없음 (있으면 debts.md §1).

───────────────────────────────────────────────────────────────
■ 작업 5 — 문서 동기화
───────────────────────────────────────────────────────────────
5-1. docs/portfolio/coach/slice13/part2_closing.md 신규 작성

- 작업 0-1~0-3 사실 확인 결과 / 회귀 카운트 / IDENTICAL 상태 /
  신규 endpoint 동작 결과 / contract test 커버리지.
  5-2. kpi_matrix.md §5 베이스라인 갱신 (회귀 717 → Part 2 종결값).

───────────────────────────────────────────────────────────────
■ Part 2 종결 체크리스트
───────────────────────────────────────────────────────────────
□ 회귀 전체 PASS, 카운트 = 717 +9~13 범위 내
□ IDENTICAL 31/31 PASS (service/LLM 경로 무수정)
□ 기존 E2 순수 view 동작 불변 (git diff 0, 기존 테스트 PASS)
□ POST /api/v1/coach/e2/ — 정상 200 / 검증실패 400 / 예외 500
/ rate limit 429 / upstream 502
□ contract test가 E2 output 계약 위반 시 FAIL하도록 동작
□ 작업 0 사실 확인 결과가 part2_closing.md에 기록됨
□ kpi_matrix.md §5 베이스라인 갱신
□ 비용: real LLM 호출 0 → $0

■ 산출물

- 코드(신규): portfolio/tests/api/test_e2_endpoint.py
- 코드(수정): portfolio/api/serializers.py, views.py, urls.py
- 문서: slice13/part2_closing.md 신규, kpi_matrix.md §5 갱신
- 보고: 체크리스트 결과 + 작업 0 사실 확인 + 회귀 카운트 + IDENTICAL

■ 종료 후 커밋
git commit -m "slice13: Part 2 — E2 API endpoint (E1 패턴 복제)"

※ IDENTICAL이 깨지거나 기존 view 동작이 바뀌면 ADDITIVE 위반 — 즉시
중단·보고. Part 1.5 커밋으로 롤백 가능한 상태 유지.
═══════════════════════════════════════════════════════════════
