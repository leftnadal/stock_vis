# SEC β G1.5 — not_found 배타 근본원인 분류 리포트 (SECB-G15-DECOMP-0811)

- 작성: 2026-08-11 (Gate 2 정지 유지 — 조사만)
- 실측: `scripts/sec/grounding_g15_notfound_taxonomy.py` (read-only · 결정론 · **LLM 0콜 · DB 쓰기 0**)
- 성격: **판정·권고 없음. 분류 사실만.** V-B 채점은 디렉터 사이클.

## 선행 산출물과의 관계 (중복 아님 — v2 정련)

- 07-28 `4d0ed3b5` = **1차 분해**(`grounding_g15_decompose.py` + `sec_beta_g15_decomposition_report.md`): raw↔LLM-basis 정규화갭 + dedup + prefix64/24 비-verbatim 렌즈. 출력 not_found **437**.
- 본 리포트 = **배타적 우선순위 분류**(한 건 = 한 태그, ①→⑤). 1차가 하지 않은 **소문자 완화(NORM-MISS) 신규 테스트**를 추가해 V-B(LLM 재추출) 실분모를 code-fixable와 진성 비-verbatim으로 순수 분리. 파일명·태스크 ID 구분(1차 산출물 무접촉).

## STEP 0-4 — not_found 모수 재실측 (실측이 정본)

| 항목 | 실측 | 참조 대비 |
|------|------|----------|
| total evidence | 1,768 | 1차 1,751 (코퍼스 소폭 성장) |
| **not_found (명목)** | **438** (24.8%) | 참조 437 대비 **+1건 (+0.23%)** — ±10% 이내, HALT 아님 |
| strict 분포 | verified 1,289 / normalized_match 41 / not_found 438 / missing_source **0** | — |

- **판정 로직 위치**: `services/sec_pipeline/grounding.py::ground_evidence` — verified(원문 그대로) → normalized_match(NFKC+ASCII 따옴표/대시+공백압축) → not_found. **소문자화 없음** ⟹ NORM-MISS 신규 테스트 여지.
- **grounding source** = 프로덕션 `grounding_backfill.build_source_text` 미러 = `"\n".join(item_1, item_1a, item_7)`.
- **missing_source = 0** (모든 not_found는 원문 소스 보유). **missing_source_section = 0** (구조적: evidence에 섹션 메타 부재 → item 3/8 개별 귀속 불가).

## 배타 분류 집계표 (우선순위 ①→⑤, 한 건 = 한 태그)

| 태그 | 건수 | 명목%(분모 438) | 유니크 기준%(분모 184) |
|------|------|------|------|
| **① DUP-EXTRACT** | **254** | 57.99% | —(중복 제거 대상) |
| **② ITEM-MISSING** | **0** | 0.00% | 0.00% |
| **③ NORM-MISS** | **3** | 0.68% | 1.63% |
| **④ TRUE-NONVERBATIM** | **181** | 41.32% | **98.37%** |
| **⑤ OTHER** | **0** | 0.00% | 0.00% |

- **검산 ✅**: DUP 254 + 대표 184 = 438 (= 모수).
- **dedup 키 = (filing=source_document_id, 정규화 문장)** → 유니크 대표 **184**. (1차 리포트 183은 문장-단독 dedup — 동일 문장이 다른 filing에 존재하면 별건으로 계상해 +1. 지시서 ①의 "(filing, 문장) 쌍" 정의 준수.)
- **① DUP-EXTRACT 처리**: 중복 그룹(size≥2)의 대표 1건만 남기고 나머지(N−1)를 DUP-EXTRACT로 계상. 대표는 ②~⑤ 근본원인 분류로 흐른다(중복이 근본원인을 은폐하지 않게 = V-B 실분모 순수 유지).

## ③ NORM-MISS — 소문자 완화 재대조 매치율 (구제 가능성 정량 근거)

- 유니크 대표 184 중 소문자 완화로 매치 = **3건 (1.63%)** → 대조기에 소문자 완화 추가 시 **V-B 없이 code-fixable**.
- **3건 전부 문장 첫 글자 대문자화 차이**(LLM이 문단 중간 절을 독립 문장으로 추출하며 첫 글자만 대문자화, 원문은 소문자):
  - filing=159 ev=604: evid `S`everal… ↔ src `s`everal… (first-diff@0)
  - filing=79 ev=1183: evid `I`n the U.S.,… ↔ src `i`n the U.S.,… (first-diff@0)
  - filing=202 ev=1597: evid `O`ur Scores segment… ↔ src `o`ur Scores segment… (first-diff@0)
- **함의(사실 진술)**: 소문자 완화의 구제 폭은 **미미(3건)**. NORM-MISS는 근본 동인이 아니다 → 잔여 대부분은 진성 비-verbatim.

## 태그별 대표 사례 (각 2건, filing = source_document_id, 발췌 최소)

- **① DUP-EXTRACT** (중복 그룹 상위 2):
  - filing=34 ×22회: [641] "We market and sell our solutions globally through our field sales and services organizatio…"
  - filing=205 ×15회: [773] "The primary manufacturers of the major components in a commercial MEP system are: Trane, C…"
- **② ITEM-MISSING** (0건): 해당 건 0 — 구조적 부재(섹션 메타 없음·missing_source=0). item 3/8 귀속은 추측이 되어 판정 불가 → 지시서 "추측 분류 금지" 준수로 0 by construction.
- **③ NORM-MISS** (3건):
  - filing=159 [604]: "Several jurisdictions in which we and our franchisees operate, including California, have…"
  - filing=79 [1183]: "In the U.S., most of our products are distributed through wholesalers, and if one of these…"
- **④ TRUE-NONVERBATIM** (181건, V-B 실분모):
  - filing=19 [141]: "Abbott's laboratory facilities, home monitoring services, and durable medical equipment su…"
  - filing=521 [1831]: "Acquisition-related costs included in total expenses include the amortization of intangibl…"
- **⑤ OTHER** (0건).

## 요약 (분류 사실만 — 판정·권고 없음)

- not_found 438(명목) = **중복 계상 254 + 유니크 근본원인 184**.
- 유니크 184 = ITEM-MISSING 0 + **NORM-MISS 3(code-fixable)** + **TRUE-NONVERBATIM 181(V-B 실분모, 98.37%)** + OTHER 0.
- **V-B(LLM 재추출) 실분모 = 181 유니크**. NORM-MISS 구제(대조기 소문자 완화)로 빠지는 건 3건뿐. ITEM-MISSING·OTHER는 0.
- 다음 단계(V-B 부분도입 여부·범위·prompt v2 우선순위) = **디렉터 재판정 사이클**. 본 리포트는 회부 자료.
