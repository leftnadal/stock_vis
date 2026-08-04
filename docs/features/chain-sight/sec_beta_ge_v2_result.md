# SEC β G-e — v2 프롬프트 tail 발산 측정 결과 (요약)

**실행:** 2026-08-03 · SECB-GE-EXEC-1 Phase B · gemini-2.5-flash · LLM 5콜(filing당 1)
**원자료:** `var/secb_ge_v2_sample/secb_ge_v2_sample_execute.json` (gitignore, DB 미기록)
**계약:** prod/dev DB 쓰기 **0**(물리 격리 b) · grounding = `ground_evidence_g16`(결정론·LLM 0) · v2 프롬프트 = v1 구조 + R1~R5([`SECB-GE-R1R5-SPEC.md`](./SECB-GE-R1R5-SPEC.md)), `MAX_EVIDENCE_CHARS=300`

## 판정식 (paired, 표본 내)

| | v1 (기존 substrate) | v2 (재추출) |
|---|---|---|
| 총 인용 | 121 | 139 |
| tail (partial_match + not_found) | 86 | **1** |
| **tail율** | **71.07%** | **0.72%** |

> 전역 24.96%는 참고치(tail 편중 표본이므로 직접 비교 무효). paired 표본 기준 tail 발산 **71.07% → 0.72%**.

## filing별 (v1 cites/tail/율 → v2 cites/tail/율, evidence 평균/최대 길이)

| filing | accession | v1 | v2 | ev 평균/최대(자) |
|---|---|---|---|---|
| AKAM | 0001086222-26-000022 | 24/22 (91.7%) | 24/0 (0.0%) | 336 / 351 |
| COR | 0001140859-25-000131 | 28/19 (67.9%) | 46/0 (0.0%) | 325 / 491 |
| CAT | 0000018230-26-000008 | 37/15 (40.5%) | 37/0 (0.0%) | 253 / 369 |
| ISRG | 0001035267-26-000010 | 17/15 (88.2%) | 17/1 (5.9%) | 587 / 646 |
| FIX | 0001104659-26-017530 | 15/15 (100%) | 15/0 (0.0%) | 359 / 359 |

v2 등급 분포 합계: verified 138 / not_found 1 / partial_match 0 / normalized_match 0.

## 방향성 결론 (측정 세션 — pass/fail·배포 없음)

- R1~R5(verbatim copy + 완전 문장 경계 + self-verify)로 **tail 발산이 사실상 소거**(71.07%→0.72%). partial_match(리스트 절단) 410 유형이 v2 표본에서 **0건**.
- ⚠️ **caveat (전량 롤아웃 결정 재료)**: v2 evidence 길이가 R3의 300자 상한을 **상시 초과**(ISRG 평균 587·최대 646자). 모델이 **R2(완전 문장) > R3(300자 캡)** 우선 → verified화는 "더 긴 verbatim 스팬"에 기인. 롤아웃 시 ⑴ evidence_text 길이 팽창 ⑵ v1 "max 300 chars" 의도 위반 ⑶ COR 28→46처럼 인용 수 변동(집합 상이) 을 함께 평가해야 함.
- **전량 배포·substrate 통합은 본 세션 범위 밖 — 별도 결정 사이클.** 본 수치는 방향성 근거로만 제공.

## 무변경 입증

prod 사전/사후 스냅샷 **동일**: total 1768 · deterministic_v1 1751 · prompt_version v1 1768 · v2 **0** · 등급 verified 1273/normalized_match 41/partial_match 410/not_found 27 (실행 전후 불변). DB 쓰기 0.
