# SEC β G-e — prompt v2 범위 정의서 (감독 승인 대상)

> 발행: 실행 세션 2026-08-01 · **문서 산출물(LLM 미호출)**. G-e는 첫 LLM 호출 단계 —
> **본 정의서 감독 승인 후에만 착수**. 승인 전 어떤 LLM 호출·재추출도 금지.
> 근거: Gate 2 사인오프 요청서 §2 item4 + G-d 제거(D-SECB-GATE2-AMEND-1) 후속.

## 배경
- G-c로 grounding 데이터 기록 완료: 1751 = verified 1273 / normalized 41 / **partial_match 410** / not_found 27 (marker `deterministic_v1`). 전량 `prompt_version='v1'` 추출본.
- partial_match 410 = 접두 verbatim + tail 발산(경쟁사/공급사 리스트 절단, §3 입증). **121 distinct filings** 산출.
- prompt v2 표적 = **tail 발산 방지**(verbatim exact sentence 강제, 리스트 절단 금지 — G1.5 부수② 초안).

## ⒜ prompt v2 적용 대상
- **기본 = 신규 추출 경로 전용**: 향후 filing 추출이 v2 사용(기존 substrate 무변경).
- **효과 측정용 재추출 표본**(기존 1751 **무접촉**): partial_match 산출 121 filings 중 **대표 표본 N**.
  - 표본 선정(제안): partial_match rows 상위 filing(경쟁사 리스트 유형 집중). **N ≈ 5**(방향성 측정 충분).
  - 기록 방식: 재추출분은 **`prompt_version='v2'` 태그로 신규 행**(기존 v1 행 UPDATE 0, shadow).
  - **비용**: N filings × 문서당 1 LLM 호출(gemini-2.5-flash, JSON 파싱). N=5 → **~5 calls**(저비용). 정확 N·filing은 G-e STEP 0(read-only, partial_match 분포)에서 확정.
- ★미결(감독): 표본 크기 N·선정 기준 확정. v2 재추출을 substrate에 **통합할지**는 별도 결정(현 범위 = 측정 표본만).

## ⒝ tail 발산 방지 효과 측정 방법
- 동일 표본 filing의 **v1 추출본 vs v2 재추출본** 대조.
- 각 인용에 결정론 `ground_evidence_g16` 적용 → 지표:
  - **verified 비율 ↑ / (partial_match + not_found) 비율 ↓** = tail 발산 감소.
- 판정: v2 표본의 (partial+nf) 비율이 v1 대비 유의 감소 → v2 효과 확인. (표본이라 통계 엄밀성 제한 — **방향성 확인** 목적, 전량 롤아웃은 후속 결정.)
- LLM 0 계약 불변: **grounding 판정은 여전히 V-A 결정론**(ground_evidence_g16). LLM은 **추출**에만(G-e = 추출 재실행, grounding 아님).

## ⒞ 기존 1,751건 무접촉 확증
- v2 재추출 = **신규 행/별도 `prompt_version='v2'` 태그**만. 기존 1751 `prompt_version='v1'`·grounding 기록 **UPDATE 0**.
- 검증 쿼리(재추출 前후 대조):
  - `SELECT count(*) FROM sec_supply_chain_evidence WHERE prompt_version='v1'` = **1751 불변**.
  - grounding_status 재기록 0 = `count FILTER (grounding_method='deterministic_v1')` **1751 불변**.
- 롤백: v2 표본 행 = `WHERE prompt_version='v2'` 식별·삭제(기존 substrate 무영향).

## G-e 착수 조건(정의서 승인 후)
1. 감독이 본 정의서 ⒜⒝⒞ + 표본 N·v2 프롬프트 문구 승인.
2. G-e STEP 0(read-only): 표본 filing 확정, 비용 재산정.
3. v2 재추출(첫 LLM) → v1/v2 대조 측정 → 보고.
4. **전량 롤아웃·substrate 통합은 별도 감독 결정**(본 범위 밖).

**현재 불변: LLM 0(본 정의서 미호출)·기존 1751 무접촉·G-e 미착수.**
