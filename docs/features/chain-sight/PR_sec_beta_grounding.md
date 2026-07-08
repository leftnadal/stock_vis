# PR 지시서: SEC β — evidence grounding 검증 (self-reported → verified)

- 작성: 2026-07-02
- 승인: 사용자 (결정 ②-A: 지시서 선행 작성 / 결정 ③: 검증 방식 V-A)
- 근거: SEC β 2-pass 사전확인 (2026-07-02, 강화형·상 근접 판정)
- 트랙: Chain Sight — 증거 provenance β (뉴스 β 파킹, SEC β가 차기 트랙)

> **보관 메모 (2026-07-02):** 본 문서는 실행 잠금(§0) 하의 **리드타임 준비물**로 repo에 영속화됨.
> census `docs/audit_out/census_beta_provenance_cost.md` §7.4 각주가 이 경로를 참조한다.
> 잠금 체인 충족 전에는 실행하지 않는다. 실행 세션은 §1 프리플라이트부터 진입한다.
> (잠금 상태 최종 확인 2026-07-02: 4개 중 0개 충족 — Gate 2 미종결·궤적 미달·D2 미착수·main 미통합.)

---

## 0. 실행 트리거 — 잠금 (이 절이 최우선)

**본 지시서는 아래 조건이 전부 충족되기 전에는 실행하지 않는다.**

```
#28 Gate 2 종결(verify [OK]) → 궤적 ≥5틱 → 상향 D2 완료(flag-on 실발화+whipsaw+튜닝)
→ pair 브랜치 main 통합(17커밋+D2 한 단위) → [본 지시서 실행 가능]
```

- 지시서가 먼저 존재하는 것은 준비 리드타임 활용이며, 체인을 앞지르는 실행 권한이 아니다.
- 실행 세션은 착수 전 반드시 §1 프리플라이트를 통과시켜야 한다.

## 1. 프리플라이트 — 착수 직전 재확인 4점 (전제 드리프트 방지)

작성 시점(07-02)과 실행 시점 사이에 D2·main 통합이 끼므로, 아래를 재확인한다.
하나라도 불일치하면 **착수 중단 → 불일치 내용을 사용자에게 보고 → 재판정**.

- [ ] **P-1**: `services/sec_pipeline/extractor.py` — 문서당 단일 `generate_content` 구조 유지
      (작성 시점 기준 호출부 70-74행 부근). 청크 루프/2-pass가 이미 생겼다면 범위 재산정.
- [ ] **P-2**: `services/sec_pipeline/models.py` — `evidence_text`(TextField),
      `system_confidence`, `confidence_grade`, `prompt_version` 필드 무변경.
- [ ] **P-3**: `prompt_version` 현행값 = `v1` 확인 + `sec_supply_chain_evidence` 행수 재실측
      (07-02 기준 1,751 — 증가는 정상, 감소는 플래그).
- [ ] **P-4 (신규 확인점 — 사전확인 미조사 항목)**: **원문 텍스트 소스 존재 확인.**
      grounding 매칭에는 추출 당시의 10-K 원문 텍스트가 필요하다. filing 원문(또는 추출에
      사용된 텍스트)이 로컬/DB에 보존돼 있는지 확인. 보존돼 있지 않으면 EDGAR 재fetch가
      범위에 추가되므로(레이트리밋·버전 불일치 리스크) **착수 전 사용자 보고 필수**.

## 2. 목적과 범위 (강화형 판정의 의미)

- 현재: 인용 1,751건은 temperature 0.1 LLM의 **self-reported** "exact sentence" —
  원문에 verbatim 존재하는지 검증된 적 없음.
- 목표: 인용을 **grounding 검증 통과 인용**으로 승격. 신규 구축이 아니라 기존
  추출·필드·인용 substrate 전부 재사용하는 **덧대기**.
- 검증 방식 = **V-A: 결정적 정규화 매칭 (LLM 0콜)**. 2026-07-02 결정 ③,
  퀀트 0.94 (vs V-B LLM 2-pass 0.51, V-C 하이브리드 0.87).
  - V-B(native-citation 2콜)는 채택하지 않음: 비용·비결정성·"검증의 검증" 문제.
  - 조건부 탈출구: §6 Gate 2에서 not_found 비율 > 15%면 V-B 부분 도입 재판정(사용자 결정).

## 3. 구현 — Phase G1: 검증기 + 백필 (flag 무관, read-path 무영향)

### G1-a. 정규화 매처 (순수 함수, 모듈 상수)

- 위치: `services/sec_pipeline/grounding.py` (신규)
- 함수: `ground_evidence(evidence_text: str, source_text: str) -> GroundingResult`
- 정규화 파이프라인 (양쪽 텍스트 동일 적용):
  1. Unicode NFKC 정규화
  2. 스마트 따옴표/대시 → ASCII (`" " ' '` → `"` `'`, `– —` → `-`)
  3. 연속 공백(개행 포함) → 단일 스페이스, strip
- 판정 3단계:
  - `verified` — 정규화 전 원문 그대로 substring 존재
  - `normalized_match` — 정규화 후에만 substring 존재
  - `not_found` — 정규화 후에도 부재
- 임계/상수는 **모듈 상수**로 (하향 :406 하드코딩 / 상향 UPWARD=60·STREAK=3과 동일 규율 —
  정책표 md는 근거 문서지 런타임 소스 아님).

### G1-b. 마이그레이션 (additive-only)

- `sec_supply_chain_evidence`에 필드 3개 추가 (기존 행 무손상 — 상향 D1의
  "additive, 13,697행 무손상" 원칙 동일 적용):
  - `grounding_status` (CharField, choices: verified/normalized_match/not_found, null=True)
  - `grounding_method` (CharField, 초기값 후보 `deterministic_v1`, null=True)
  - `grounded_at` (DateTimeField, null=True)
- null = 미검증 (백필 전 상태). 기존 read-path는 이 필드들을 모름 → 무영향.

### G1-c. 백필 태스크

- `backfill_grounding_task`: 미검증(`grounding_status IS NULL`) evidence 전건 순회,
  P-4에서 확인된 원문 소스와 매칭, 결과 기록.
- `select_for_update(skip_locked=True)` 패턴 준수 (SEC 파이프라인 기존 규율).
- **dry-run 모드 필수**: 쓰기 없이 판정 분포만 리포트 (pair backfill 9,562 dry-run 선례).

## 4. 구현 — Phase G2: 신규 추출 경로 인라인 검증 (flag-gated)

- flag: `SEC_GROUNDING_ENABLED`, **기본 False** (상향 D1 `CHAINSIGHT_UPWARD_LEARNING_ENABLED`
  패턴 동일).
- flag-on 시: extractor 추출 직후 `ground_evidence` 인라인 호출 →
  - `not_found`면 `confidence_grade` 1단계 강등 + grounding_status 기록 (인용 폐기 아님 —
    데이터는 남기고 신뢰만 낮춤).
- `prompt_version` v1 → **v2**: 프롬프트에 verbatim 요구 보강
  ("Copy the sentence character-for-character; do not paraphrase or truncate mid-word" 취지).
  v1/v2 경계 필드는 기존재 — 매칭률 비교(v1 vs v2)가 v2 효과의 정량 지표.

## 5. Gate 1 — 코드 검증 (flag-off)

- [ ] 매처 단위 테스트 4경로 GREEN: verified / normalized_match / not_found / 원문 부재(예외 경로)
- [ ] 마이그레이션 additive 확인: 기존 행수 불변, 기존 필드 무변경 (전/후 카운트 실측)
- [ ] flag-off에서 추출 파이프라인 동작 전/후 동일 (기존 테스트 무손상)
- [ ] 백필 dry-run 실행: 1,751+건 판정 분포 리포트 산출 (쓰기 0건 확인)

## 6. Gate 2 — 실발화 검증

- [ ] 백필 실기록 (dry-run 분포 확인 후): verified/normalized/not_found 분포 실측 보고
- [ ] flag-on 신규 추출 N건(최소 1 filing) 실발화: 인라인 검증 동작 + 강등 경로 확인
- [ ] **분기점**: not_found 비율 > 15% → 착수 중단 아님, V-B 부분 도입 여부를
      사용자 재판정에 회부 (분포 리포트 + 샘플 20건 첨부)
- [ ] 매칭률(v1 기준선) DECISIONS.md 기록 — v2 롤아웃 후 비교 기준

## 7. 범위 밖

- 뉴스 β 일체 (파킹 유지), census 봉인 사실(§7.1–7.3) 재조사, Neo4j 반영 로직 변경,
  V-B(LLM 2-pass) 구현, EDGAR 파이프라인 v2.3 설계 변경.
- 원문 미보존 발견 시(P-4 실패) EDGAR 재fetch를 임의 착수하지 않는다 — 사용자 보고 후 결정.

## 8. 산출물

- 코드: `grounding.py` + 마이그레이션 + 백필 태스크 + v2 프롬프트
- 문서: 백필 분포 리포트 1장, DECISIONS.md 갱신(V-A 채택·기준선 매칭률),
  본 지시서에 Gate 1/2 체크 결과 기입
