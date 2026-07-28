# 개정문 1: SEC β G1 — 소스 커버리지 사전 대조 + 임계 사전 고정 + maxfail 교훈

- 발행: 감독 세션, 2026-07-28
- 선행: 커버 `sec_beta_kickoff_cover_directive.md`, 실체 명세 `docs/features/chain-sight/PR_sec_beta_grounding.md`(`9df14f6`). 원 명세 미수정(발행 보존).
- 성격: G1 착수 승인 + 3건 개정 편입. V-A 결정론·**LLM 0콜** 계약 불변.

## 개정 ① — 소스 커버리지 사전 대조 (G1 STEP 0 추가) + 판정 4종

매칭 실행 전, 인용 1,751 ↔ 원문 store 조인 검사로 **모든 인용의 출처 문서가 raw store에 존재하는지** 확인한다. 누락 인용은 **`missing_source`로 별도 판정 — `not_found`와 합산 금지.**

- 이유: "소스가 없어 못 찾은 것(missing_source)"과 "소스가 있는데 원문에 없는 것(not_found=진짜 접지 실패)"은 의미가 다르며, 섞이면 15% 임계가 오염된다.
- **판정 체계 = verified / normalized_match / not_found / missing_source (4종).**
- G1 STEP 0 실측(2026-07-28): evidence 1,751 = source_row_present 1,751 · source_row_missing **0** · evidence_on_empty_store **0** → **missing_source 후보 = 0**(빈 store 61건은 어떤 인용도 미참조). 코드는 missing_source를 처리하되 본 코호트 실발생 0.

## 개정 ② — 임계 사전 고정 (dry-run 분포 보기 전 커밋에 박음)

분포를 본 뒤 기준을 정하는 **사후 합리화 금지.** 판정 기준을 dry-run 실행 전에 확정:

- **`not_found`(순수) > 15% → V-B 부분 도입 사용자 재판정 회부**(진행 차단, 분포+샘플 20건 첨부). missing_source는 분모/분자에서 제외.
- **`missing_source` > 0 → 건수·문서 목록 보고**(회부 사안, **진행 차단은 아님**).
- not_found 비율 정의 = `not_found / (verified + normalized_match + not_found)` (missing_source 제외).

## 개정 ③ — common-bugs 신규 (#70)

"pytest default maxfail=5 조기정지는 부분 실패 수를 전체로 오인시킨다 — 실패 수 인용 전 전수 실행(`--maxfail` 상향 또는 해제)으로 확정할 것." (07-28 킥오프에서 5→13 사례.)

## 매처 규율 (불변)

- 정규화 매처(NFKC + 스마트따옴표/대시 ASCII + 연속공백 단일화)는 **단위 테스트 동반 커밋** — 유니코드 대시(– —)·스마트 따옴표(" " ' ')·말줄임(…) 등 **EDGAR 원문 특이 케이스 포함**.

## 게이트별 사인오프 (불변)

- **Gate 1 = flag-off**: additive 마이그 3필드 + 매처 4경로 테스트 + dry-run 분포 보고. 여기서 정지.
- **Gate 2**(백필 실기록·flag-on 1 filing)는 **Gate 1 dry-run 분포 보고를 감독이 비준한 후** 착수. 사인오프 없이 Gate 2 진입 금지.
