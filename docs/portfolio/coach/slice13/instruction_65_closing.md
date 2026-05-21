# Claude Code 작업 지시서 — #65 closing (legacy view 처리 마감)

## 목적

#65 mini-slice(legacy view 5건 제거)를 공식 마감한다. 코드 변경 없음 —
문서 갱신·부채 등록만. 이 작업이 끝나면 #65 close, Slice 13 완전 종결.
LLM 무접촉 — 비용 $0.

## git 기준

- 분기 기준: `#65 — 작업 지시서 docs` HEAD `4c2fcc9`
- closing은 단일 doc 커밋

## 제약 (중요)

- **코드 파일 일절 수정 금지.** 이 작업은 문서 갱신 + 부채 등록만.
- 회귀·IDENTICAL 재검증 불필요(#65 작업에서 이미 완료). closing은 기록 작업.
- "제거 후보 보존" 목록의 legacy 전용 의존 코드(`run_e*`·`build_e*_prompt`·
  `parse_e*`·`E*Request/Response`·`OneLineDiagnosis` 등)는 **이번 작업에서
  건드리지 않는다.** #67로 분리해 등록만 한다.

## 작업 항목

### 1. kpi_matrix §5 갱신

- `docs/portfolio/coach/slice13/kpi_matrix.md`(또는 해당 파일)의 §5에
  #65 결과를 반영: legacy view 5건 제거 완료, 6 진입점 단일화,
  회귀 767→730(−37), IDENTICAL 31/31 유지.

### 2. slice13 종합 보고서에 #65 결과 추가

- `docs/portfolio/coach/slice13/slice13_closing.md`(기존, 커밋 `3e59bca`)에
  #65 mini-slice 결과를 **추가 섹션**으로 덧붙인다(기존 내용 보존, append).
- 포함 내용:
  - #65 처리 방식 = **제거**. 당초 wrapper 추천이었으나 E1 pilot에서
    legacy view가 mock 데모 endpoint이고 new API가 프로덕션 API로
    입력·prompt·schema가 본질적으로 다름이 판명 → 재평가 후 제거로 전환.
  - E1~E3·E5·E6 legacy view 전부 호출처 0건(경로 A = dead code) → 삭제.
    E4는 legacy view 부재 special case.
  - 커밋: E1 `4eba9fb` / E2 `fc39d23` / E3 `3e3ad6b` / E5 `2bde79e` /
    E6 `1983a99` / doc `4c2fcc9`.
  - 회귀 767→730(−37 = 삭제한 legacy view 테스트 5+7+9+7+9 합과 정확히 일치),
    IDENTICAL 31/31 유지, 6 API 60/60, 비용 $0.
  - 결과: 6개 진단 입구가 `/api/v1/coach/eN/` 단일 진입점으로 단일화,
    이중 입구(drift 원천) 소멸.
- **간결 우선**: 추가 섹션은 결정 보존 포맷(상세 서술 과잉 금지).

### 3. 부채 등록 — `debts.md` 갱신

- **#65 close 기록**: legacy view 5건 처리 완료로 close.
- **#67 신규 등록** (가칭): legacy 전용 의존 코드 후속 정리.
  - 내용: legacy view는 제거됐으나 그 view들이 쓰던 옛 보조 코드
    (`run_e*`·`build_e*_prompt`·`parse_e*`·`E*Request/Response`·
    `OneLineDiagnosis` 등)가 `scripts/validation/` 및 `test_e*_service.py`,
    `schemas/__init__.py:__all__`에 아직 쓰여 보존됨.
  - 제안 방향: ① `scripts/validation/`을 archived/legacy로 분류
    (슬라이스 1~6 검증용 — 운영 무관) → ② archive 후 legacy 의존 코드
    일괄 제거 검토 → ③ `services/__init__.py:__all__` 정리.
  - 성격: **비위험·개선성 부채.** 보존된 코드는 검증 스크립트가 실제로
    쓰는 live code이므로 dead code가 아니며, 방치해도 깨지지 않음.
  - PS 1.0 (분석 중심, 코드 변경은 후속). 향후 슬라이스 Step 0 후보.
- **#67에 누적 보존 목록 첨부** (중요 — 재조사 비용 절감):
  E5·E6 회신에 포함된 "누적 제거 후보 보존 목록"(Service 함수 5건 /
  Prompt builders 5건 / Parsers 3건 / Schemas)을 #67 항목 본문 또는
  별도 첨부로 그대로 보존한다. 나중에 #67을 열 때 재조사 없이 출발 가능하도록.

### 4. 미커밋 사항 확인

- working tree에 untracked/미커밋 항목이 없는지 확인.
  (지시서 파일 2건은 `4c2fcc9`에서 이미 커밋됨.)

## 완료 기준

- kpi_matrix §5, slice13_closing.md, debts.md 갱신 완료.
- #65 close 기록, #67 등록(누적 보존 목록 첨부 포함).
- 단일 doc 커밋(메시지 예: `#65 closing — legacy view 처리 마감 + #67 등록`).
- working tree clean, 비용 $0.

## 회신에 포함할 것

- 갱신한 문서 목록.
- #67 등록 확인(누적 보존 목록 첨부 여부).
- 커밋 해시.
- Slice 13 + #65 최종 종합(누적 회귀·커밋 수·IDENTICAL·비용).
