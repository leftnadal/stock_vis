# SEC β G1.5 — not_found 437 분해 리포트 (재판정 준비)

- 작성: 2026-07-28 (Gate 2 정지 유지)
- 실측: `scripts/sec/grounding_g15_decompose.py` (read-only, 결정론, **LLM 0콜, 쓰기 0**)
- 입력: G1 dry-run 기준선 not_found 437(24.96% 명목) > 15% → 분해 후 재판정.

## STEP 0 — 섹션 메타·추출 경계 (결정론 확정)

- **evidence 섹션 메타 없음**: `sec_supply_chain_evidence`에 item/section 컬럼 부재(source_document_id만) → 행별 추측 귀속 금지.
- **추출 입력 경계**: Track A `normalize_section_all`은 **item_1 + item_7만** `_clean_text` 후 LLM 투입(`normalizer.py:56`, item_1a 제외). ⟹ 인용 출처 = 저장 섹션(1/7) 내부 = **missing_source_section = 0 (구조적, 추측 아님)**.

## ① 중복 접기 (정규화 문장 키)

- 전체 1,751 → **유니크 937** (중복률 **46.5%** — 동일 문장이 다관계로 다중 추출).
- not_found 437 → **유니크 182**.
- 잔여 not_found 클러스터 크기 분포: 최대 22개 1클러스터, 대부분 크기 1(109)~5. 소수 대형 클러스터가 명목 카운트를 부풀림.

## ② 섹션 귀속 + 정규화 갭 (동인 분리)

- **missing_source_section = 0** (구조적). **missing_source_doc = 0** (G1 커버리지). → 판정 5종 확장은 **실발생 0** → 마이그 0002 상태 필드(4종, max_length=20) **additive 수정 불요**(참고: `missing_source_section`=22자>20이나 실발생 0이라 moot).
- **정규화 갭 테스트**: grounding source를 raw(item_1+1a+7) → **LLM 실입력 basis**(`normalize_section_all` = 정제 item_1+7)로 교체 재접지 → not_found **437 불변**(verified 1273→1272, normalized 41→42, net 0). ⟹ **정제 갭(HTML 엔티티·공백)은 동인 아님.** 437은 진짜 비-verbatim.

## ③ 잔여 비-verbatim 패턴 (결정론 prefix 분류, 유니크 182)

| 패턴 | 건수 | 비율 | 의미 |
|------|------|------|------|
| prefix64 존재 (tail 발산) | **169** | **92.9%** | 문장 앞 64자 verbatim 존재, 끝에서 절단/mid-word/소편집 |
| prefix24만 존재 (중간 재서술) | 5 | 2.7% | 부분 중첩 |
| prefix24 부재 (합성/전면 재서술) | 8 | 4.4% | 문두조차 원문 부재 |

- **압도적 다수(92.9%)가 "tail 발산"** = LLM이 옳은 문장을 갖고도 끝까지 verbatim 복사 안 함(절단/소편집). = **prompt v2의 "verbatim 강제"가 직접 겨냥하는 대상.**

## 재판정 (임계 15%)

| 기준 | 잔여 순수 not_found율 | 판정 |
|------|----------------------|------|
| 명목(1,751 분모) | 24.96% | > 15% |
| **유니크(937 분모)** | **19.42%** | > 15% |

- 둘 다 > 15% → **V-B 부분도입 결정 사이클 회부** (개정문2 사전 고정 기준).
- **단, 분해가 드러낸 실질**: 잔여의 92.9%는 **prompt v2(verbatim 강제)** 대상(tail 발산)이지 V-B(검증) 대상 아님. **권고**: V-B 이전에 **prompt v2 롤아웃 → 재측정**을 우선. V-B 채택 시 범위 = **잔여 합성/재서술 ~13 유니크 클러스터로 한정**(4.4%+2.7%). 최종 결정은 감독 재판정.

## 부수 확인

- **⑴ 빈 store 61건**: `status=failed, extraction_method=regex` = **regex 추출 실패**(원래 빈 섹션 아님). 어떤 인용도 미참조 → grounding 무해. (수집 실패 재시도는 SEC 파이프라인 별건.)
- **⑵ prompt v2 설계 입력**: v2 "verbatim 강제" 문구의 1순위 표적 = **tail 발산(절단·mid-word 중단·꼬리 소편집)** — 169/182 근거. 문구 취지 "Copy the sentence character-for-character to its end; do not truncate mid-word or drop trailing clauses." 2순위 = 재서술 억제.

## 정지점

**Gate 2 정지 유지.** 재판정 결과(>15%) → **V-B 부분도입 결정 사이클 회부**(본 리포트 = 회부 자료). 감독 결정(prompt v2 우선 vs V-B 범위 확정) 후 Gate 2 사인오프.
