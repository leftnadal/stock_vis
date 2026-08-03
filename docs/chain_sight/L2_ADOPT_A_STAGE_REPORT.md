# L2-ADOPT — A단계 리포트 (Peer LLM 태그 채택 + 판정기 거부권)

> 트랙: ⑳-3 / D-L2-SOURCE 결정 2. 브랜치 `monorepo/sess-l2-adopt` (base origin/main `34a171dd`).
> 확정 결정: **LLM 태그 기본 + grounded ≤0.2 자동 기각 → 업종 버킷 폴백.** 프롬프트 ㉯(회사명+industry),
> claim 영어 출력. 하·상이 구획 "추정" 라벨.
> **A단계 = 무비용(신규 LLM 호출 0). B단계(전량 태깅) = 병진님 견적 승인 후 별도 투입.**

---

## STEP 0 — 정찰 (READ ONLY, 쓰기 0)

`scratchpad/step0_recon.py` (read-only) 실측. dev=prod 공유 DB(stock_vis) — 쓰기 없음.

### ⑴ PEER_OF distinct 무방향 쌍 (실호출 규모의 분모)

| 항목 | 값 |
|------|----|
| PEER_OF raw 엣지(전체) | 9,365 |
| rejected 제외 | 9,365 |
| self-loop(a==b) | 0 |
| **★distinct 무방향 쌍** | **9,365** |
| 양방향 중복률 (raw/distinct) | **1.000x** |

> ETF 중복 버그 전례(양방향 이중계상) **해당 없음** — PEER_OF는 쌍당 단일 정규행으로 저장(a<b 정렬).
> 9,365 = 실호출 규모의 분모.

### ⑵ 쌍 기준 mcap tercile · industry_same 분포

- 쌍 등장 distinct 심볼 = 544
- 층화 모집단(양끝 mcap+industry 보유 쌍) = 9,192 / tercile 경계 t1=16.99B, t2=33.75B

| tercile\industry | 동일 | 상이 |
|---|---|---|
| 상 | 609 | 2,471 |
| 중 | 635 | 2,433 |
| 하 | 546 | **2,498** |

- 전체 distinct 쌍 industry_same: **동일 1,790 / 상이 7,402 / 미상(결측) 173**
- **★"추정" 라벨 대상 (하·상이 구획) = 2,498쌍** — 실험상 최저 접지(avg 0.718)·최고 과신(0.40), "소형주 위험"

### ⑶ FMP desc·industry 커버리지 (쌍 기준 — 결측 쌍 = 버킷 폴백 대상)

| 커버리지 | 심볼 기준 | 쌍 기준(양끝) |
|---|---|---|
| mcap | 531/544 (97.6%) | 9,311/9,365 (99.4%) |
| industry | 521/544 (95.8%) | 9,192/9,365 (98.2%) |
| description | 519/544 (95.4%) | 9,161/9,365 (97.8%) |

- **★태깅 가능 쌍 (industry+desc 양끝 보유) = 9,161/9,365 (97.8%)**
- **버킷 폴백(결측) 쌍 = 204** (2.2%)

### ⑷ LLM 래퍼 · L1 파이프라인 훅

- 래퍼 `apps/market_pulse/llm/client.py`: `generate_with_circuit` (동기, model=`gemini-2.5-flash`)
- 서킷 `gemini`: failure_threshold=5, recovery_seconds=60. 배치 rate = **4.2s sleep** (free 15 RPM 여유)
- L1 훅 = `apps/chain_sight/tasks/domain_tasks.py::tag_relation_domain_task` (SEC 유입 이벤트 구동, beat 미사용).
  코어 = `services/domain_tagging.py::tag_one` (커맨드·훅 공유 단일 소스). **PEER_OF는 대상 아님**(SEC_RELATION_TYPES 밖) → L2 경로 신설 삽입점.

### ⑸ 스키마 게이트 — **PASS (마이그레이션 불요)**

| 항목 | 값 | 판정 |
|------|----|----|
| `relation_domain` choices 제약 | **None** | PEER 태그 기록 가능 |
| `relation_domain` max_length | 80 | 태그 길이 여유 |
| PEER_OF 중 domain_review_status 有 | 0 | 백지 |
| PEER_OF 중 domain_machine_check 有 | 0 | 백지 |
| PEER_OF 중 relation_domain 有 | 0 | 백지 |
| SEC verdict(review有·mc無) 270 재확인 | **270** | PEER_OF와 타입 분리 → **무접촉 보장** |

> 결론: `relation_domain`(승인본, 미접촉)·`relation_domain_draft`(초안)·`domain_machine_check`(JSON: 거부권·추정 flag 수납)·
> `domain_review_status`(채택=auto / 거부권=pending — A3에서 'rejected' soft-drop 회피 교정) 전부 재사용
> → **신규 마이그레이션 없음, HALT 없음.**

---

## A1 — 거부권 임계 0.2 재집계 (무비용, LLM 0)

기존 실험 240쌍(`outputs/peer_experiment/peer_experiment_judged.csv`)에 **고정 거부권 0.2** 적용.
`peer_adjudicator.veto(grounded_ratio)`: grounded ≤ 0.2 → 기각(버킷 폴백), None(접지 불가) → 보수적 기각.

- 실험의 과신 플래그는 동적 gr_q1(**0.667**) 기준 → 저정밀(플래그 ~23-25%, 실제 오류 ~10%만).
- 프로덕션 거부권은 **고정 0.2** → 고정밀·저재현.

### 거부권 발동 결과

| 지표 | 값 |
|------|----|
| **거부권 발동** | **1 / 240 (0.4%)** |
| 채택(LLM 태그 유지) | 239 / 240 (99.6%) |

구획별 기각률:

| 구획 | veto / n | 비율 |
|---|---|---|
| 상·동일 | 0/40 | 0.0% |
| 상·상이 | 0/40 | 0.0% |
| 중·동일 | 0/40 | 0.0% |
| 중·상이 | 0/40 | 0.0% |
| **하·동일** | **1/40** | **2.5%** |
| 하·상이 | 0/40 | 0.0% |

### 기각 목록 (거부권 발동 쌍)

| 쌍 | 구획 | LLM 태그 | grounded | reason |
|---|---|---|---|---|
| **CRM ↔ MTCH** | 하·동일·㉯ | 구독형 클라우드 소프트웨어 서비스 | **0.0** | low_grounding |

> **★CRM↔MTCH 포함 확인** — 인간 검수 WRONG 판정(Salesforce B2B CRM vs Match Group B2C 데이팅,
> "구독형 SaaS"는 표면적 공통점) 1건과 **정확히 일치**. 거부권이 유일한 명백한 오류를 포착.

### B단계 예상 기각률 근거

- 표본 기각률 0.4% → 태깅 가능 9,161쌍 기준 **예상 거부권 발동 ~37쌍** (버킷 폴백).
- 추가로 커버리지 결측 204쌍도 버킷 폴백 → **총 폴백 예상 ~241쌍 (2.6%)**.
- 나머지 ~8,920쌍(95%+)은 LLM 태그 채택. 그중 하·상이 2,498쌍은 "추정" 라벨.

---

## A3 — 파일럿 dry-run (신규 LLM 호출 0) + 마인드맵 노출 경로

### ⑴ 파이프라인 dry-run (실험 ㉯ 120쌍 재사용)

`tag_peer_domains --pilot-csv peer_experiment_judged.csv` — 기존 실험 ㉯(variant B) 120쌍을
A2 파이프라인 판정(ground_claim→veto→추정라벨)에 태움. **신규 LLM 호출 0**.

| 지표 | 값 |
|------|----|
| ㉯ 대상 | 120쌍 |
| **채택(adopt)** | **119 (99.2%)** |
| **거부권(veto)** | **1 (0.8%)** — CRM↔MTCH(하·동일) |
| **추정 라벨(하·상이)** | **20** |
| claim 없음 | 0 |

→ 전 경로(채택·거부권 폴백·추정 라벨) 실측 검증. 결과 `outputs/peer_domain_tagging/pilot_120.csv`.

### ⑵ ego API·마인드맵 노출 경로 (S3-MINDMAP 개정 — additive)

**ego API** (`ego_views.py`): PEER 엣지에 `peer_domain`(채택 태그)·`peer_domain_estimate`(추정) additive 노출.
- 노출 조건: `domain_machine_check.source == 'L2-ADOPT'` ∧ `domain_review_status == 'auto'` → `relation_domain_draft`.
- 거부권(status='pending')·미태깅 → `peer_domain=null`.

**★soft-drop 교정**: 거부권 status를 **'rejected' 아닌 'pending'**으로 기록.
ego 메인 쿼리가 `domain_review_status='rejected'`를 soft-drop(엣지 은닉)하므로, 거부권으로 PEER 관계
자체가 사라지면 안 됨(거부권 = "태그 기각·버킷 폴백"이지 "관계 은닉" 아님).

**FE** (`egoMindmap.ts`): L2 하위그룹 키를 **`peer_domain`(llm_tag) 우선 → `industry_bucket` 폴백 → 미분류**로 개정.
계약(`shared-types.ts` EgoEdge)에 `peer_domain`·`peer_domain_estimate` optional additive.

### 검증
- backend ego API pytest **38 passed**
- FE 마인드맵 회귀 vitest **12 passed** (기존 9 + L2-ADOPT 3: llm_tag 우선·버킷 폴백·추정 라벨)
- tsc `--noEmit` **0 errors**
