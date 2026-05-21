# Claude Code 작업 지시서 — #65: E2·E3 legacy view 제거

## 목적

legacy view `coach_e2_diagnostic_card`·`coach_e3_metric_comment`를 E1 pilot에서
검증된 절차로 처리한다. 호출처 조사 → 경로 A(호출처 없음)면 제거,
경로 B(호출처 발견)면 해당 endpoint만 중단·보고.

## git 기준

- 분기 기준: `#65 pilot` HEAD `4eba9fb`
- E2·E3 각각 별도 커밋 (다단계 슬라이스 커밋 패턴)

## 제약

- 호출처 조사 통과 전 삭제 금지.
- new API endpoint(`/api/v1/coach/e2/`, `/api/v1/coach/e3/`)와
  Slice 13 산출물 무변경.
- E5·E6은 이번 범위 밖.
- E2와 E3은 독립 처리 — 한쪽이 경로 B여도 다른 쪽은 경로 A면 정상 진행.
- LLM 무접촉 — $0.

## 작업 절차 (E2, E3 각각 동일하게 반복)

### Step 1 — 호출처 전수 조사 (E1 pilot에서 검증된 grep 범위 그대로)

1. 함수 심볼(`coach_e2_diagnostic_card` / `coach_e3_metric_comment`) grep
   — 정의·등록 외 직접 호출.
2. URL 경로 문자열 + URL name grep (`reverse()`, `{% url %}` 포함).
3. 템플릿(`.html`), 프론트엔드 JS/TS, management command·admin·내부 스크립트.
4. 대상 legacy view 전용 테스트의 위치·개수.

### Step 2 — 분기 판정

- **경로 A** (production 호출 0건): Step 3 진행.
- **경로 B** (호출처 발견): 해당 endpoint 중단, 호출처 목록(파일·라인·용도) 보고.
  다른 endpoint는 계속.

### Step 3 — 제거 (경로 A일 때만)

1. 대상 view 함수 삭제, 관련 import 정리.
2. `urls.py`에서 해당 URL 패턴 제거 + 사유 주석.
3. 해당 view 전용 테스트 삭제.
4. **legacy 전용 의존 코드 추가 조사** (E1 pilot 핵심 교훈): 대상 view가 쓰던
   옛 prompt builder(`build_e2_prompt`·`build_e3_prompt` 류)·output schema·
   service 함수가 다른 곳(특히 `scripts/validation/`)에서도 쓰이는지 grep.
   - 다른 곳에서 쓰이면 → **보존**, 보고에만 기재.
   - 어디서도 안 쓰이지만 `__all__` 노출 등 외부 import 가능성이 있으면
     → **"제거 후보"로 보고만, 보존.**
   - 확실히 어디서도 안 쓰이고 노출도 없을 때만 제거.

### Step 4 — 검증 (E2·E3 통합)

- 전체 회귀: 762 기준에서 삭제한 테스트 수만큼 감소, 그 외 FAIL 0건.
- IDENTICAL 31/31 PASS — 깨지면 즉시 중단·보고.
  E2/E3 관련 IDENTICAL 영향 여부 명시.
- new API `/api/v1/coach/e2/`·`/api/v1/coach/e3/` 정상 동작 확인.

## 완료 기준

- 경로 A endpoint: view·URL·전용 테스트 제거, 입구 단일화, 회귀·IDENTICAL PASS.
- 경로 B endpoint: 코드 변경 0, 호출처 목록 보고.
- E2·E3 각각 별도 커밋(경로 A인 것만). 메시지 예: `#65 — E2 legacy view 제거`.
- working tree clean, 비용 $0.

## 회신에 포함할 것

- E2·E3 각각의 호출처 조사 결과와 경로 A/B 판정.
- 경로 A: 삭제 항목, 회귀 증분, IDENTICAL 결과, 커밋 해시, "제거 후보 보존" 목록.
- 경로 B: 발견된 호출처 목록.
