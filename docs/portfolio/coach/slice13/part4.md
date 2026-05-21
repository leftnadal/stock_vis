═══════════════════════════════════════════════════════════════
[슬라이스 13 / Part 4] 작업 지시서
API 엔드포인트 추출 — E5+E6 endpoint 묶음 (E1~E3 패턴 순수 복제)
═══════════════════════════════════════════════════════════════

■ 위치 / 전제

- 브랜치: slice13, HEAD = Part 3 커밋 (ae0a9e1), working tree clean
- 베이스라인: 회귀 737 passed, IDENTICAL 31/31 PASS
- 누적 비용 $0 (Step 0~Part 3 전부 LLM 호출 0)
- 기존 자산: portfolio/api/{**init**,serializers,views,urls}.py 존재
  (E1·E2·E3 endpoint 보유). config/urls.py include 완료.
- 슬라이스 유형: 표준 슬라이스, 2진입점 묶음
  → Part 4 회귀 +Δ 예상 +18~22 (E1~E3 단건 +10 ×2)
  → ★ 표준 범위(+9~15) 초과는 의도된 묶음의 정상 결과.
  KPI 평가는 ±30% 임계(+6~20) 기준 — 종결 문서에 단서 기록.

■ 핵심 설계 원칙 (위반 금지)

1. ADDITIVE — 기존 순수 Django view(E5 조정 파싱·E6 코멘트), 기존
   urls 라우팅, run_e5_coach / run_e6_coach service는 한 줄도 수정
   금지. 새 DRF endpoint는 /api/v1/coach/e5/, /api/v1/coach/e6/
   경로에 추가만.
2. Pydantic 단일 진실 소스 — 입출력 검증은 E5·E6 Pydantic 스키마에
   위임. DRF serializer는 얇은 어댑터로만.
3. IDENTICAL 31/31 — service·LLM 경로 무수정 → 해시 불변.
   깨지면 즉시 중단·보고.
4. 회귀 contract test는 LLM mock 기반 — real LLM 호출 0.
5. E1~E3 패턴 순수 복제 — 새 설계 패턴 도입 금지. E5·E6 각각
   E1~E3 endpoint와 동형 구조.
6. E5·E6 둘 다 preset_id/metrics 등 선택 kwarg가 있어도 이번
   Part에서는 전달하지 않음(기본값) — E1~E3와 동일하게 코멘트/
   파싱 본 기능만 노출.

───────────────────────────────────────────────────────────────
■ 작업 0 — 사전 사실 확인 (지시서 추정 검증)
───────────────────────────────────────────────────────────────
0-1. E5 Pydantic 스키마 확인

- 입력 스키마(예: CommentaryInputE5 또는 E5 전용 입력 모델)의
  정확한 클래스명과 핵심 필드를 portfolio/schemas/ 에서 확인.
- ★ E5는 TimeSeriesContext(#27)를 쓰는 유일한 진입점 — 입력
  스키마에 시계열 컨텍스트 필드가 포함되는지 확인.
- 출력 스키마 클래스명 확인.
  0-2. E6 Pydantic 스키마 확인
- E6(income preset 코멘트) 입력/출력 스키마 클래스명·핵심 필드 확인.
  0-3. run_e5_coach / run_e6_coach 시그니처 확인
- 각 함수의 인자/반환 타입이 run_e1~e3_coach와 동형인지 확인.
- provider 인자, 선택 kwarg(preset_id/metrics 등) 유무 확인.
  0-4. 기존 E5·E6 순수 view 경로 확인
- 각 진입점의 기존 순수 view 함수명·URL 확인 (무손상 대상 식별,
  diff 0 검증용). 신규 경로 /api/v1/coach/e5|e6/ 와 충돌 없음 확인.
  ※ 0-1~0-4 결과를 part4_closing.md §1에 기록. 추정 금지.

───────────────────────────────────────────────────────────────
■ 작업 1 — E5·E6 DRF serializer (serializers.py에 추가)
───────────────────────────────────────────────────────────────
1-1. portfolio/api/serializers.py 에 E5용 serializer 추가

- 요청용: 클라이언트 JSON → 검증 → E5 입력 스키마 변환
  (0-1에서 확인한 실제 클래스명 사용).
- 응답용: run_e5_coach 반환 dict → 응답 JSON.
- 검증은 Pydantic 위임 (ValidationError → DRF ValidationError → 400).
- E3 serializer 구조 그대로 복제.
  1-2. portfolio/api/serializers.py 에 E6용 serializer 추가
- 1-1과 동일 방식, E6 스키마(0-2) 기준.

───────────────────────────────────────────────────────────────
■ 작업 2 — E5·E6 API endpoint (views.py + urls.py에 추가)
───────────────────────────────────────────────────────────────
2-1. portfolio/api/views.py 에 E5 coach view 추가

- 처리 흐름 (E1~E3 view와 동형):
  POST JSON → 요청 serializer 검증 → E5 입력 스키마 생성
  → run_e5_coach(input_data, provider="haiku") 호출
  (선택 kwarg 전달 안 함)
  → 반환 dict를 응답 serializer로 직렬화 → 200.
- 에러 처리: 400 / 500(스택트레이스 미노출) / 429 / 502 —
  E1~E3 view와 동일 표면.
  2-2. portfolio/api/views.py 에 E6 coach view 추가 (2-1과 동형).
  2-3. portfolio/api/urls.py 에 E5·E6 경로 추가
- 새 경로: POST /api/v1/coach/e5/, POST /api/v1/coach/e6/
- config/urls.py 무수정 (include는 Part 1 완료).

───────────────────────────────────────────────────────────────
■ 작업 3 — contract test (회귀 편입)
───────────────────────────────────────────────────────────────
3-1. 신규 파일: portfolio/tests/api/test_e5_endpoint.py

- LLM은 mock (real 호출 0).
- test_e3_endpoint.py 10건 구조 복제, E5용 조정:
  · 정상 요청 → 200, 응답이 E5 출력 계약에 부합
  · 필수 필드 누락 → 400 / 잘못된 타입 → 400
  · service 예외 → 500 + 스택트레이스 미노출
  · rate limit → 429 / upstream 오류 → 502
- 경로는 모듈 상수: E5_ENDPOINT = "/api/v1/coach/e5/"
  3-2. 신규 파일: portfolio/tests/api/test_e6_endpoint.py
- 3-1과 동일 방식, E6 기준. 상수 E6_ENDPOINT = "/api/v1/coach/e6/"
- ★ contract test = E5·E6 출력 계약을 회귀로 고정 → schema drift 감지.
  3-3. IDENTICAL 31/31 재실행 → PASS 확인.

───────────────────────────────────────────────────────────────
■ 작업 4 — 기존 view 무손상 확인
───────────────────────────────────────────────────────────────
4-1. 기존 E5·E6 순수 view(0-4 식별)가 변경 후에도 git diff 0 임을
확인. 기존 E5·E6 테스트 PASS로 동작 불변 자동 보증.
4-2. #65(기존 순수 view 최종 처리) OPEN 유지 — Part 5(E4) 종결 =
6개 endpoint 완료 시점에 결정. 이번 Part 신규 부채 없음.

───────────────────────────────────────────────────────────────
■ 작업 5 — 문서 동기화
───────────────────────────────────────────────────────────────
5-1. docs/portfolio/coach/slice13/part4_closing.md 신규 작성

- 작업 0-1~0-4 결과 / 회귀 카운트 / IDENTICAL / endpoint 동작 /
  contract test 커버리지.
- ★ KPI 단서 명기: "Part 4는 E5·E6 2진입점 묶음 → 회귀 +Δ가
  표준 범위(+9~15)를 초과함은 의도된 결과. ±30% 임계(+6~20)
  기준으로 평가하며 PASS."
  5-2. kpi_matrix.md §5 베이스라인 갱신 (737 → Part 4 종결값).

───────────────────────────────────────────────────────────────
■ Part 4 종결 체크리스트
───────────────────────────────────────────────────────────────
□ 회귀 전체 PASS, 카운트 = 737 +18~22 범위 내
(±30% 임계 +6~20 기준 평가 — 표준 범위 초과는 정상)
□ IDENTICAL 31/31 PASS
□ 기존 E5·E6 순수 view 동작 불변 (git diff 0, 기존 테스트 PASS)
□ POST /api/v1/coach/e5/ — 200 / 400 / 429 / 500 / 502
□ POST /api/v1/coach/e6/ — 200 / 400 / 429 / 500 / 502
□ contract test가 E5·E6 출력 계약 위반 시 FAIL
□ 작업 0 결과가 part4_closing.md §1에 기록
□ part4_closing.md KPI 단서 명기, kpi_matrix.md §5 갱신
□ 비용: real LLM 호출 0 → $0

■ 산출물

- 코드(신규): portfolio/tests/api/test_e5_endpoint.py,
  portfolio/tests/api/test_e6_endpoint.py
- 코드(수정): portfolio/api/serializers.py, views.py, urls.py
- 문서: slice13/part4_closing.md 신규, kpi_matrix.md §5 갱신
- 보고: 체크리스트 결과 + 작업 0 + 회귀 카운트 + IDENTICAL

■ 종료 후 커밋
git commit -m "slice13: Part 4 — E5+E6 API endpoint (E1~E3 패턴 복제)"

※ IDENTICAL이 깨지거나 기존 view 동작이 바뀌면 ADDITIVE 위반 —
즉시 중단·보고. Part 3 커밋(ae0a9e1)으로 롤백 가능 상태 유지.
═══════════════════════════════════════════════════════════════
