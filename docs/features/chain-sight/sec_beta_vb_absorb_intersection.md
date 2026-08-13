# SEC β — V-B → V2 흡수 교집합 실측 부록 (SECB-VB-ABSORB-0811)

- 작성: 2026-08-11 (Gate 2 정지 유지 — 조사만)
- 실측: read-only · 결정론 · LLM 0콜 · DB 쓰기 0. **판정·권고 없음 — 집계·목록만.**
- 목적: G1.5 ④ TRUE-NONVERBATIM 181건이 V2 롤아웃(351 filing)에 자연 흡수되는 범위를 filing·evidence 이중 집계로 확정.

## STEP 0-4 — 181 재확인 (v1 필터, 모집단 안정성)

evidence에 `prompt_version` 컬럼 존재 → **v1 = 1768 / v2 = 18**(V2 롤아웃 §1+§2가 18건 재추출 착수). 181은 v1 모집단 속성이므로 **`prompt_version='v1'` 필터**로 재분류(모집단 변화 ≠ 로직 변화).

| 항목 | v1 필터 재실측 | 참조 |
|------|------|------|
| not_found | 438 | 438 |
| 유니크 대표 (doc,문장) | 184 | 184 |
| DUP-EXTRACT | 254 | 254 |
| ITEM-MISSING / NORM-MISS / **TRUE-NONVERBATIM** / OTHER | 0 / 3 / **181** / 0 | 0 / 3 / **181** / 0 |

- **TRUE-NONVERBATIM = 181 → 참조 일치 ✅** (재실행 결정론 확인, HALT 없음).

## F_v2 정의 소스 (V2 롤아웃 대상 351 filing)

- **하드코딩 목록 아님 = 쿼리 정의**: `DECISIONS.md` D-SECB-V2(:50)·`docs/features/secb/secb_v2_recon_report.md:24` — "롤아웃 대상 = **deterministic_v1 351 distinct filings / 1751행**(재카운트·평균 4.97 cites)".
- 실측 대조: `grounding_method='deterministic_v1'` distinct filings = **351**(참조 정확 일치). 참고: `prompt_version='v1'` distinct filings = **356**(5개 더 많음 = 아래 미접지 straggler).

## Part A — 교집합 실측

### A-1. F_nb (④ 181건 소속 filing)

- **|F_nb| = 128 유니크 filing** (evidence 181건이 128개 filing에 분포).

### A-2. F_nb ∩/− F_v2 (filing·evidence 이중 집계)

| 지표 | filing | evidence(181 중) |
|------|--------|------|
| **\|F_nb ∩ F_v2\|** (V2 배치 자연 재추출) | **127** | **180** |
| **\|F_nb − F_v2\|** (미포함) | **1** | 1 |
| 계 (F_nb) | 128 | 181 |

- **∩ = 127 filing / 180 evidence**: V2 롤아웃 배치가 이 181건 중 **180건을 자연 재추출**(별도 V-B 파이프라인 없이 v2 프롬프트로 재인용). 검산: 127+1=128 filing ✅ / 180+1=181 evidence ✅.

### A-2 차집합 — 미포함 filing 전건

- **미포함 = 1 filing: `[521]` (symbol PAYX)** — V2 대상 추가 후보(추가 여부 = 디렉터 판정, 목록만).
- **왜 F_v2 제외인가(사실)**: filing 521의 해당 evidence(id 1831 "Acquisition-related costs…Paycor…")는 `grounding_method=NULL·grounding_status=NULL` = **미접지 v1 evidence**. F_v2가 `grounding_method='deterministic_v1'`로 정의되므로 제외.
  - 근원: deterministic_v1 백필은 원 1751행 대상 → 이후 코퍼스 성장분 **+17행/5 filing**(513·515·519·521·522, 전부 method=NULL)이 미백필. 이 5개 중 F_nb(181 라이브 재분류)에 드는 건 **521만**(나머지 4는 181 미포함).
  - **정의 민감도(사실)**: F_v2를 `prompt_version='v1'`(356)로 정의하면 521 포함 → 차집합 0. `deterministic_v1`(351) 정의에선 차집합 1. 어느 정의가 롤아웃 이터레이션의 실제 소스인지에 따라 521 커버 여부 결정 — 정의 채택은 디렉터·V2 세션 관할.

## 요약 (집계·목록만)

- ④ 181건 = 128 filing. V2 351 filing과 **∩ 127 filing / 180 evidence**(자연 재추출), **− 1 filing [521] / 1 evidence**(미접지 straggler, V2 대상 추가 후보).
- **커버리지: 181건 중 180건(99.4%)이 V2 롤아웃에 자연 흡수** — 별도 V-B 파이프라인 불요의 정량 근거(판정은 D-SECB-VB-ABSORB / 디렉터).
