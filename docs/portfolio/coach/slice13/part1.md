═══════════════════════════════════════════════════════════════
[슬라이스 13 / Part 1] 작업 지시서
API 엔드포인트 추출 — DRF serializer + 첫 endpoint(E1) + contract test
═══════════════════════════════════════════════════════════════

■ 위치 / 전제

- 브랜치: slice13 (Step 0b 커밋 위, working tree clean 확인됨)
- 베이스라인: 회귀 707 passed + 1 skipped, IDENTICAL 31/31 PASS
- DRF는 이미 설치·INSTALLED_APPS 등록됨 (rest_framework, drf_spectacular)
- 슬라이스 유형: 표준 슬라이스 → 회귀 +Δ 기대 +9~15 (KPI 10, ±30% 임계 +6~20)

■ 핵심 설계 원칙 (위반 금지)

1. ADDITIVE — 기존 순수 Django view(coach/e1/garp/ 등)·urls 라우팅·
   run_e1_coach service는 한 줄도 수정 금지. 새 DRF endpoint는 별도
   경로(/api/coach/e1/)에 추가만 한다.
2. Pydantic 단일 진실 소스 — 입출력 검증 계약은 기존 CommentaryInputE1
   /E1Output(Pydantic)이 보유. DRF serializer는 그 위의 얇은 어댑터로만
   쓰고, 검증 로직을 중복 구현하지 말 것.
3. IDENTICAL 31/31 — Part 1은 service 로직·LLM 호출 경로를 안 건드리므로
   해시 불변이어야 한다. 깨지면 즉시 중단·보고.
4. 회귀 contract test는 LLM mock 기반 — Part 1에서 real LLM 호출 0.

───────────────────────────────────────────────────────────────
■ 사전 작업 — 문서 동기화 (Step 0a/0b 반영 누락분)
───────────────────────────────────────────────────────────────
S1-0a. kpi_matrix.md §5 KPI 기준선 갱신

- 현재 §5가 "Slice 11 종결 → Slice 12 진입" 상태로 정체.
- Slice 12 종결값 + Slice 13 Step 0a/0b 결과로 갱신:
  · 회귀: 707 passed + 1 skipped (Step 0b 종결)
  · 누적 cost: docs 출처값 기재 + "ledger 부재로 미검증(#63)" 단서
  · IDENTICAL: 31/31 PASS
- §6에 슬라이스 13 유형 = "표준 슬라이스" 사전 등록.

S1-0b. debts.md §4·§5 갱신

- §4 부채 변화 요약을 Slice 13 Step 0a/0b 기준으로 갱신
  (close: #62 / 신규: #61 #63 #64 / 잔여: #51 fit-close·#59 E5).
- §5 진입점 사전 등록을 Slice 14 기준으로 교체
  (현재 Slice 13 시점 내용이 만료됨).

───────────────────────────────────────────────────────────────
■ 작업 1 — DRF serializer (Pydantic 어댑터)
───────────────────────────────────────────────────────────────
1-1. 신규 파일: portfolio/api/serializers.py (portfolio/api/ 패키지 신설)

- E1 요청용 serializer: 클라이언트 JSON → 검증 → CommentaryInputE1 변환.
- E1 응답용 serializer: run_e1_coach 반환 dict(E1Output) → 응답 JSON.
- 검증은 Pydantic CommentaryInputE1에 위임:
  DRF serializer.validate() 내에서 Pydantic 모델 생성 시도 →
  ValidationError를 DRF ValidationError로 변환해 400 응답으로 흐르게.
- DRF serializer 자체에 필드별 비즈니스 검증을 중복 구현하지 말 것.

───────────────────────────────────────────────────────────────
■ 작업 2 — 첫 API endpoint (E1)
───────────────────────────────────────────────────────────────
2-1. 신규 파일: portfolio/api/views.py

- E1 coach API view (DRF APIView 또는 함수 기반 @api_view).
- 처리 흐름:
  POST 요청 JSON → 요청 serializer 검증 → CommentaryInputE1 생성
  → run_e1_coach(input_data, provider="haiku") 호출
  → 반환 dict를 응답 serializer로 직렬화 → 200 응답.
- 에러 처리:
  · 검증 실패 → 400 + 에러 상세
  · service 예외 → 500 + 표준 에러 형식 (스택트레이스 노출 금지)
- run_e1_coach 호출 시 Step 0a에서 추가된 preset_id/metrics kwarg는
  이번 Part에서는 전달하지 않음(None) — 기존 동작과 동일하게 유지.

2-2. 신규 파일: portfolio/api/urls.py + config/urls.py 라우팅

- 새 경로: POST /api/coach/e1/ (기존 coach/e1/garp/ 와 별개)
- config/urls.py에 portfolio.api.urls include 1줄 추가
  (기존 portfolio/urls.py 라우팅은 무수정).

───────────────────────────────────────────────────────────────
■ 작업 3 — contract test (회귀 편입)
───────────────────────────────────────────────────────────────
3-1. 신규 파일: portfolio/tests/api/test_e1_endpoint.py

- LLM은 mock (Part 1 real 호출 0).
- 검증 항목:
  · 정상 요청 → 200, 응답이 E1Output 스키마에 부합 (계약 검증)
  · 필수 필드 누락 → 400
  · 잘못된 타입 → 400
  · service 예외 시 → 500 + 스택트레이스 미노출
- ★ contract test = "API 응답이 OutputBase/E1Output 계약을 지키는가"를
  회귀로 고정 → 향후 스키마 드리프트 자동 감지.

3-2. IDENTICAL 체크포인트

- IDENTICAL 31 테스트 재실행 → 31/31 PASS 확인.
- service·LLM 경로 무수정이므로 해시 불변이어야 함.

───────────────────────────────────────────────────────────────
■ 작업 4 — 기존 view 무손상 확인 & 부채 등록
───────────────────────────────────────────────────────────────
4-1. 기존 coach/e1/garp/ 순수 view가 Part 1 변경 후에도 동일 동작함을
기존 테스트로 확인 (회귀 PASS로 자동 보증).

4-2. 신규 부채 등록: debts.md §1

- #65 기존 순수 Django view 최종 처리 (PS 1.5, 슬라이스 13 후반 Part)
  단서: "E1~E6 전부 DRF endpoint로 노출 완료 후, 순수 view 유지/
  제거/wrapper화 결정. 6개 endpoint 마이그레이션 완료가 선행조건."

───────────────────────────────────────────────────────────────
■ Part 1 종결 체크리스트
───────────────────────────────────────────────────────────────
□ 회귀 전체 PASS, 카운트 = 707 +9~15 범위 내 (표준 슬라이스)
□ IDENTICAL 31/31 PASS (service/LLM 경로 무수정)
□ 기존 coach/e1/garp/ view 동작 불변 (기존 테스트 PASS)
□ POST /api/coach/e1/ — 정상 200 / 검증실패 400 / 예외 500
□ contract test가 E1Output 계약 위반 시 FAIL하도록 동작
□ kpi_matrix.md §5/§6, debts.md §4/§5 동기화 완료
□ #65 신규 등록
□ 비용: real LLM 호출 0 → $0

■ 산출물

- 코드(신규): portfolio/api/**init**.py, serializers.py, views.py, urls.py
  portfolio/tests/api/test_e1_endpoint.py
- 코드(수정): config/urls.py (include 1줄)
- 문서: kpi_matrix.md, debts.md 갱신 + slice13/part1_closing.md
- 보고: 체크리스트 결과 + 회귀 카운트 + IDENTICAL 상태 + 신규 endpoint 동작

■ 종료 후 커밋
git commit -m "slice13: Part 1 — E1 API endpoint (DRF serializer + contract test)"

※ IDENTICAL이 깨지거나 기존 view 동작이 바뀌면 ADDITIVE 위반 — 즉시
중단·보고. Step 0b 커밋으로 롤백 가능한 상태 유지.
═══════════════════════════════════════════════════════════════
