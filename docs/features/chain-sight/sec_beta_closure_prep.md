# SEC β 트랙 — 종결 선언 준비 (SECB-GE-EXEC-1 Phase C)

**작성:** 2026-08-03 · worktree `monorepo/sess-secb-ge` · **초안(디렉터 종결 선언 대기)**

---

## 1. 종결 선언문 초안

> **SEC β (grounding 검증층) 트랙은 Gate 1 → Gate 2 → G-e 로 실질 완결한다.** grounding 판정은 V-A 결정론(`ground_evidence_g16`, LLM 0콜)으로 확립됐고, prompt v2의 tail 발산 억제 효과가 방향성 수준에서 입증됐다. 잔여는 전량 배포·노출 설계 등 **별도 결정 사이클**로 이관한다.

**트랙 호(弧) 요약**
- **Gate 1 (G1/G1.5/G1.6)**: V-A 결정론 grounding 채택 → not_found 437 분해 → G1.6 partial_match(접두≥70% 절단/tail) 신설. 4분포 확립 verified 1273 / normalized_match 41 / partial_match 410 / not_found 27 (1751). 잔여 순수 nf 명목 1.54%/유니크 2.03% (≤15%).
- **Gate 2 (개정 B)**: G-a 백업(`secb_pre_gate2_20260801`, 44M) · G-b migrate 0003(choices additive·no-op DDL) · G-c 백필 1751(marker `deterministic_v1`) · G-d 제거→SECB-EXPOSURE 이관(노출 read-path 코드 부재 실측).
- **G-e (prompt v2 측정)**: R1~R5 verbatim 규율 v2 프롬프트로 표본 5 재추출·paired 측정 → **tail율 71.07%→0.72%**. DB 쓰기 0(물리 격리 b). 측정 세션 — 배포 아님.

**핵심 계약(불변)**: grounding = V-A 결정론·LLM 0콜. LLM은 추출에만.

**잔여 이관 목록**
| 트랙 | 성격 | 상태 |
|---|---|---|
| SECB-EXPOSURE | grounding_status 노출 설계(소비자 UX 결정·목업 필수) | 디렉터 세션 소관 — 실행 세션 선제 구축 금지(γ) |
| SECB-REGRESSION-WATCH | 13건(attention6+leadership7) 재발 감시 | 상시 감시(재실패 시 HALT+traceback) |
| SECB-V-B-STANDBY | V-B 부분도입(합성/재서술) 트리거 대기 | 미발동(잔여 nf ≤15%) |
| SECB-PROMPT-V2 롤아웃 | v2 전량 배포·substrate 통합 | 별도 결정(재료 = G-e 결과 + 300자 초과 caveat) |
| SECB-GE-OBS-17ROW | v1 1768 vs marker 1751 — 17행 grounded 미표기 | 저우선 등재만 |
| CN-AUTO-REVIEW 회수 | 병진 별도 세션 | 이관 |

## 2. 삭제 후보 회부 (목록 보고만 — 실행 금지, 파괴적 = 병진 수동)

- **`monorepo/sess-secb-land`** (브랜치 + worktree `~/worktrees/sv-secb-land`, detached `e42d1641`)
- **`monorepo/sess-secb-g16`** (브랜치 + worktree `~/worktrees/sv-secb-g16` `18874db6`; 원격 `origin/monorepo/sess-secb-g16` 별도 판단)
- (참고·비후보) `sess-secb-kickoff`(`~/worktrees/sv-secb` `4d0ed3b5`)·`sess-secb-gate2-amend`·`sess-secb-progress` — 디렉터 확인 후 별도 회부.
- ⚠️ 본 세션 worktree `~/worktrees/sv-secb-ge`는 랜딩·병합 확정 후 회부(현 미push).

## 3. TH 트리거 발화 문안 (SEC β 종결이 선행 조건)

> **[TH Session 1 개시 조건]** SEC β 트랙 종결 선언 확정 시, Theme Heat corpus **unfreeze** + ThemeTermOverride 재산출 트랙(TNV) **백필 개시**(대상 창 = 2026-07-12 → 현재, 50일+). Session 1 범위 = corpus unfreeze 게이트 통과 확인 → TNV 백필 1차 창 실행 → heat 재산출 파급 검증. ⚠️ ThemeTermOverride 215(ovr_v1) **재적재 금지**(기존 override 트랙 계약). 발화 전제 = SEC β G-e 종결(본 세션) + 디렉터 명시 개시 승인.

## 4. 소비 처리 반영
- `SECB-PROMPT-V2` → ✅ 소비 완료(G-e). `SECB-GE-R1R5-SPEC.md`·정의서 개정본 = 단일 출처.
- DECISIONS: `D-SECB-GATE-E` + 배달사고 #8 등재. TASKQUEUE: `SECB-GE-OBS-17ROW` 신설.
