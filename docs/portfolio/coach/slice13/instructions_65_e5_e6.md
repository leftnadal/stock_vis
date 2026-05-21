# Claude Code 작업 지시서 — #65: E5·E6 legacy view 제거

## 목적

legacy view `coach_e5_adjustment`·`coach_e6_comparison`를 E1~E3에서 검증된
절차로 처리한다. 호출처 조사 → 경로 A(호출처 없음)면 제거, 경로 B(호출처 발견)면
해당 endpoint만 중단·보고. **이로써 #65의 legacy view 처리가 완료된다**
(E4는 legacy 부재 — 대상 아님).

## git 기준

- 분기 기준: `#65 — E3 legacy view 제거` HEAD `3e3ad6b`
- E5·E6 각각 별도 커밋 (다단계 슬라이스 커밋 패턴)

## 제약

- 호출처 조사 통과 전 삭제 금지.
- new API endpoint(`/api/v1/coach/e5/`, `/api/v1/coach/e6/`)와
  Slice 13 산출물 무변경.
- E5와 E6은 독립 처리 — 한쪽이 경로 B여도 다른 쪽은 경로 A면 정상 진행.
- LLM 무접촉 — $0.

## 작업 절차 (E5, E6 각각 동일하게 반복)

### Step 1 — 호출처 전수 조사 (E1~E3에서 검증된 grep 범위 그대로)

1. 함수 심볼(`coach_e5_adjustment` / `coach_e6_comparison`) grep
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
4. **legacy 전용 의존 코드 추가 조사** (E1~E3 일관 교훈): 대상 view가 쓰던
   옛 prompt builder(`build_e5_prompt`·`build_e6_prompt` 류)·output schema·
   service 함수(`run_e5`·`run_e6` 류)·parser가 다른 곳(특히 `scripts/validation/`,
   `test_e*_service.py`, `schemas/__init__.py` **all**)에서도 쓰이는지 grep.
   - 다른 곳에서 쓰이면 → **보존**, 보고에만 기재.
   - 어디서도 안 쓰이지만 `__all__` 노출 등 외부 import 가능성이 있으면
     → **"제거 후보"로 보고만, 보존.**
   - 확실히 어디서도 안 쓰이고 노출도 없을 때만 제거.

### Step 4 — 검증 (E5·E6 통합)

- 전체 회귀: 746 기준에서 삭제한 테스트 수만큼 감소, 그 외 FAIL 0건.
- IDENTICAL 31/31 PASS — 깨지면 즉시 중단·보고.
  E5/E6 관련 IDENTICAL 영향 여부 명시(이름에 e5/e6이 들어가도 legacy view와
  무관한 테스트는 별개로 가려낼 것 — E3에서 scoring 통합 테스트를 가려낸 선례 참고).
- new API `/api/v1/coach/e5/`·`/api/v1/coach/e6/` 정상 동작 확인.

## 미커밋 지시서 파일 처리

- 이번 지시서 `instruction_65_e5_e6.md`와 직전 `instruction_65_e2_e3.md`(untracked
  상태로 남아 있음)를 **별도 doc 커밋 하나로 묶는다.** 코드 커밋(E5·E6 제거)에는
  섞지 않는다 — 코드 커밋은 코드만 유지.
- doc 커밋 위치: `docs/portfolio/coach/slice13/` 경로. 메시지 예: `#65 — 작업 지시서 docs`.

## 완료 기준

- 경로 A endpoint: view·URL·전용 테스트 제거, 입구 단일화, 회귀·IDENTICAL PASS.
- 경로 B endpoint: 코드 변경 0, 호출처 목록 보고.
- E5·E6 각각 별도 커밋(경로 A인 것만). 메시지 예: `#65 — E5 legacy view 제거`.
- 지시서 파일 2건 별도 doc 커밋.
- working tree clean, 비용 $0.

## 회신에 포함할 것

- E5·E6 각각의 호출처 조사 결과와 경로 A/B 판정.
- 경로 A: 삭제 항목, 회귀 증분, IDENTICAL 결과, 커밋 해시, "제거 후보 보존" 목록.
- 경로 B: 발견된 호출처 목록.
- #65 종료 판정: E5·E6 처리 후 legacy view 5건(E1~E3·E5·E6)이 모두 처리됐는지,
  #65를 close 가능한 상태인지 명시.
- **누적 "제거 후보 보존" 목록 총괄**: E1~E6 전체에서 보존된 legacy 전용
  의존 코드(run_e*, build_e*\_prompt, parse_e*, E*Request/Response 등)를 한데 모아
  보고. (#65 종료 후 별도 정리 검토용 — 이번 작업에서는 건드리지 않음.)
