# SEC β 트랙 — 종결 선언 확정본

**확정:** 2026-08-03 · SECB-GE-EXEC-1 완주 · 디렉터 조건부 종결 승인
**전신:** `sec_beta_closure_prep.md`(초안). 본 문서가 확정본.

---

## 선언

**SEC β (grounding 검증층) 트랙은 Gate 1 → Gate 2 → G-e 로 실질 완결한다.**
grounding 판정은 V-A 결정론(`ground_evidence_g16`, LLM 0콜)으로 확립됐고, prompt v2의 tail 발산 억제 효과가 표본 측정으로 입증됐다. 전량 배포·노출 설계는 **별도 결정 사이클**로 이관한다.

## G-e 측정 결과 (SECB-GE-EXEC-1 Phase B, 2026-08-03)

**paired 표본(5 filings·인용≥8 중 tail 상위, 3단 키):**

| | v1 (기존 substrate) | v2 (재추출) |
|---|---|---|
| 총 인용 | 121 | **139** |
| tail (partial_match+not_found) | 86 | **1** |
| **tail율** | **71.07%** | **0.72%** |

- v2 등급 분포: verified 138 / not_found 1 / partial_match 0 / normalized_match 0.
- LLM 5콜(재추출만)·비용 실측 ~$0.047·DB 쓰기 0(물리 격리 (b)·`var/secb_ge_v2_sample/`).
- prod 사전=사후 동일 입증(1768/1751·v2 0·1273/41/410/27 불변).

**caveat 전문 인용 (전량 롤아웃 결정 재료):**
> "⚠️ v2 evidence 길이가 R3의 300자 상한을 **상시 초과**(ISRG 평균 587·최대 646자). 모델이 **R2(완전 문장) > R3(300자 캡)** 우선 → verified화는 '더 긴 verbatim 스팬'에 기인. 롤아웃 시 ⑴ evidence_text 길이 팽창 ⑵ v1 'max 300 chars' 의도 위반 ⑶ COR 28→46처럼 인용 수 변동(집합 상이) 을 함께 평가해야 함."

`{MAX_EVIDENCE_CHARS}` 치환값 = **300** (v1 프롬프트 L20 역산).

## 트랙 호(弧) 요약

- **Gate 1 (G1/G1.5/G1.6)**: V-A 결정론 grounding 채택 → not_found 437 분해 → G1.6 partial_match(접두≥70% 절단/tail) 신설. 4분포 확립(1751): verified 1273 / normalized_match 41 / partial_match 410 / not_found 27. 잔여 순수 nf 명목 1.54%·유니크 2.03% (≤15%).
- **Gate 2 (개정 B)**: G-a 백업(`secb_pre_gate2_20260801`, 44M) · G-b migrate 0003(additive·no-op DDL) · G-c 백필 1751(marker `deterministic_v1`) · G-d 제거→SECB-EXPOSURE 이관.
- **G-e (prompt v2 측정)**: 위 표 — tail 71.07%→0.72%. 측정 세션(배포 아님).

**핵심 계약(불변)**: grounding = V-A 결정론·LLM 0콜. LLM은 추출에만.

## 잔여 이관 목록

| 트랙 | 성격 | 상태 |
|---|---|---|
| SECB-V2-ROLLOUT | v2 전량 적용 결정(전제 4건) | 🆕 등재 — 결정 사이클 |
| SECB-EXPOSURE | grounding_status 노출 설계(UX·목업 필수) | 디렉터 세션 소관 |
| SECB-REGRESSION-WATCH | 13건 재발 감시 | 상시 감시 |
| SECB-V-B-STANDBY | V-B 부분도입 트리거 대기 | 미발동(nf ≤15%) |
| SECB-GE-OBS-17ROW | v1 1768 vs marker 1751 — 17행 미표기 | 저우선 등재 |
| TH-TRIGGER-FIRED | TH Session 1 개시(corpus unfreeze + TNV 백필) | 🆕 트리거 발화(지시서 디렉터 별도) |
| CN-AUTO-REVIEW 회수 | 병진 별도 세션 | 이관 |

## 산출물 경로
- R1~R5 사양(단일 출처): `SECB-GE-R1R5-SPEC.md` · v2 프롬프트: `services/sec_pipeline/prompts.py` `SUPPLY_CHAIN_EXTRACTION_PROMPT_V2`
- 측정 결과: `sec_beta_ge_v2_result.md` · 원자료: `var/secb_ge_v2_sample/`(gitignore)
- 결정: DECISIONS `D-SECB-GATE-E`(+배달사고 #8)
