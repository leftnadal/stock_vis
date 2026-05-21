═══════════════════════════════════════════════════════════════
[슬라이스 13 / Part 3 v2] 작업 지시서
API 엔드포인트 추출 — E3 endpoint (코멘트 노출, E1·E2 패턴 순수 복제)
═══════════════════════════════════════════════════════════════

■ 위치 / 전제

- 브랜치: slice13, HEAD = Part 2 커밋 (50c6313), working tree clean
- 베이스라인: 회귀 727 passed, IDENTICAL 31/31 PASS
- 누적 비용 $0 (Step 0~Part 2 전부 LLM 호출 0)
- 기존 자산: portfolio/api/{**init**,serializers,views,urls}.py 존재
  (E1·E2 endpoint 보유). config/urls.py include 완료.
- 슬라이스 유형: 표준 슬라이스 → Part 3 회귀 +Δ 예상 +9~13
  (E1·E2 단건 +10 선례. 순수 복제. ±30% 임계 +6~17)

■ 작업 0 결과 (확정 사실 — 재확인 불필요)

- E3 입력 스키마: CommentaryInputE3
  (portfolio/schemas/commentary_input.py:136)
  · concentration_metrics: dict[str, Any] — 입력 스키마의 일부.
  클라이언트가 보내는 코멘트 생성용 입력. 별도 서버 계산 불필요.
- E3 출력 스키마: E3Output (portfolio/schemas/commentary_output.py:107)
- run_e3_coach 시그니처:
  run_e3_coach(input_data, provider="haiku", client=None,
  max_tokens=2000, \*, preset_id=None, metrics=None)
  · preset_id/metrics 는 선택 인자 — 이번 Part에서는 전달하지 않음.
- 기존 E3 순수 view: coach_e3_metric_comment (portfolio/views.py:248),
  URL /api/coach/e3/metric-comment/ — 신규 경로와 충돌 없음.
- preset 식별자 진실 소스: PRESET_ID_TO_CATEGORY
  (portfolio/services/scoring/**init**.py) — 이번 Part 미사용(#66).

■ 핵심 설계 원칙 (위반 금지)

1. ADDITIVE — 기존 순수 view(coach_e3_metric_comment), 기존 urls
   라우팅, run_e3_coach service는 한 줄도 수정 금지. 새 DRF endpoint는
   /api/v1/coach/e3/ 경로에 추가만.
2. Pydantic 단일 진실 소스 — 입출력 검증은 CommentaryInputE3 /
   E3Output 에 위임. DRF serializer는 얇은 어댑터로만.
3. IDENTICAL 31/31 — service·LLM 경로 무수정 → 해시 불변.
   깨지면 즉시 중단·보고.
4. 회귀 contract test는 LLM mock 기반 — real LLM 호출 0.
5. E1·E2 패턴 순수 복제 — 새 설계 패턴·신규 계산 모듈 도입 금지.
6. preset_id / metrics kwarg 를 endpoint에 노출하지 않는다.
   run_e3_coach 호출 시 둘 다 전달하지 않음(기본값 None).
   → 이 기능은 #66 부채로 분리 (작업 5).

───────────────────────────────────────────────────────────────
■ 작업 1 — E3 DRF serializer (serializers.py에 추가)
───────────────────────────────────────────────────────────────
1-1. portfolio/api/serializers.py 에 E3용 serializer 추가

- E3 요청용 serializer: 클라이언트 JSON → 검증 → CommentaryInputE3
  변환. concentration_metrics 를 포함한 모든 입력 필드는 기존
  CommentaryInputE3 스키마에 위임 (E2 serializer와 동일 방식).
- ★ preset_id / metrics 필드를 두지 않는다.
- E3 응답용 serializer: run_e3_coach 반환 dict(E3Output) → 응답 JSON.
- 검증은 Pydantic 위임 (ValidationError → DRF ValidationError → 400).
- E2 serializer 코드 구조를 그대로 복제.

───────────────────────────────────────────────────────────────
■ 작업 2 — E3 API endpoint (views.py + urls.py에 추가)
───────────────────────────────────────────────────────────────
2-1. portfolio/api/views.py 에 E3 coach view 추가

- 처리 흐름 (E1·E2 view와 동형):
  POST JSON → 요청 serializer 검증 → CommentaryInputE3 생성
  → run_e3_coach(input_data, provider="haiku") 호출
  (preset_id / metrics 인자 전달 안 함)
  → 반환 dict를 응답 serializer로 직렬화 → 200.
- 에러 처리: 검증 실패 400 / service 예외 500(스택트레이스 미노출)
  / rate limit 429 / upstream 오류 502 — E1·E2 view와 동일 표면.
  2-2. portfolio/api/urls.py 에 E3 경로 추가
- 새 경로: POST /api/v1/coach/e3/
- config/urls.py 무수정 (include는 Part 1 완료).

───────────────────────────────────────────────────────────────
■ 작업 3 — contract test (회귀 편입)
───────────────────────────────────────────────────────────────
3-1. 신규 파일: portfolio/tests/api/test_e3_endpoint.py

- LLM은 mock (real 호출 0).
- test_e2_endpoint.py 10건 구조를 복제, E3용으로 조정:
  · 정상 요청 → 200, 응답이 E3Output 계약에 부합
  · 필수 필드 누락 → 400 / 잘못된 타입 → 400
  · service 예외 → 500 + 스택트레이스 미노출
  · rate limit → 429 / upstream 오류 → 502
- 경로는 모듈 상수: E3_ENDPOINT = "/api/v1/coach/e3/"
- ★ contract test = E3Output 계약을 회귀로 고정 → schema drift 감지.
  3-2. IDENTICAL 31/31 재실행 → PASS 확인.

───────────────────────────────────────────────────────────────
■ 작업 4 — 기존 view 무손상 확인
───────────────────────────────────────────────────────────────
4-1. 기존 coach_e3_metric_comment view가 변경 후에도 git diff 0 임을
확인. 기존 E3 테스트 PASS로 동작 불변 자동 보증.

───────────────────────────────────────────────────────────────
■ 작업 5 — #66 신규 부채 등록 (★ 이번 Part 유일한 신규 요소)
───────────────────────────────────────────────────────────────
5-1. debts.md §1 에 #66 등록:

- 제목: "E3 endpoint preset 점수 기능 API 노출
  (preset_id + metrics optional 필드)"
- 내용: run_e3_coach 의 preset_id / metrics kwarg 를 E3 endpoint
  요청 표면에 optional 필드로 노출 → ScoringEngine 점수 기반 진단
  제공.
- ★ 선행조건: 분석엔진 #12 (Phase 2). metrics 정규화 7종 중 3종
  (sector_hhi / portfolio_beta / avg_correlation)이 외부 데이터
  (수익률 시계열·섹터 라벨)에 의존 → 분석엔진 없이는 서버·클라
  모두 산출 불가. ScoringEngine은 7종 완비를 전제.
- 처리 시점: 분석엔진 #12 완성 후. 그때 preset_id / metrics 를
  optional 필드로 ADDITIVE 추가 → 기존 E3 클라이언트 무손상
  (breaking change 아님).
- PS: 2.0 (Phase 2 블록).
  5-2. #65(기존 순수 view 최종 처리) OPEN 유지 — 6개 endpoint 완료 전
  손대지 않음.

───────────────────────────────────────────────────────────────
■ 작업 6 — 문서 동기화
───────────────────────────────────────────────────────────────
6-1. docs/portfolio/coach/slice13/part3_closing.md 신규 작성

- 작업 0 분기 B 결과 요약(metrics 두 종류 구분, 분석엔진 의존 3종),
  옵션 A 선정 근거, 회귀 카운트, IDENTICAL, endpoint 동작,
  contract test 커버리지, #66 등록 사실.
  6-2. kpi_matrix.md §5 베이스라인 갱신 (727 → Part 3 종결값).

───────────────────────────────────────────────────────────────
■ Part 3 종결 체크리스트
───────────────────────────────────────────────────────────────
□ 회귀 전체 PASS, 카운트 = 727 +9~13 범위 내
□ IDENTICAL 31/31 PASS
□ 기존 coach_e3_metric_comment view 동작 불변 (git diff 0, 기존 테스트 PASS)
□ POST /api/v1/coach/e3/ — 200 / 400 / 429 / 500 / 502
□ endpoint 요청 표면에 preset_id / metrics 필드 없음 (#66로 분리됨)
□ contract test가 E3Output 계약 위반 시 FAIL
□ #66 debts.md §1 등록 (분석엔진 #12 선행조건 명시)
□ part3_closing.md 신규, kpi_matrix.md §5 갱신
□ 비용: real LLM 호출 0 → $0

■ 산출물

- 코드(신규): portfolio/tests/api/test_e3_endpoint.py
- 코드(수정): portfolio/api/serializers.py, views.py, urls.py
- 문서: debts.md §1(#66 등록), slice13/part3_closing.md 신규,
  kpi_matrix.md §5 갱신
- 보고: 체크리스트 결과 + 회귀 카운트 + IDENTICAL + #66 등록 확인

■ 종료 후 커밋
git commit -m "slice13: Part 3 — E3 API endpoint (코멘트 노출, preset 점수는 #66)"

※ IDENTICAL이 깨지거나 기존 view 동작이 바뀌면 ADDITIVE 위반 —
즉시 중단·보고. Part 2 커밋(50c6313)으로 롤백 가능 상태 유지.
═══════════════════════════════════════════════════════════════
