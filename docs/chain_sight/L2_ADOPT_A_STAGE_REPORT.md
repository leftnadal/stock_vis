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

---

## A4 — B단계 견적표 (착수 게이트 재료)

### 규모 (STEP 0 실측)

| 항목 | 값 |
|------|----|
| PEER distinct 무방향 쌍 | 9,365 |
| 태깅 가능(industry+desc 양끝) = **LLM 호출 대상** | **9,161** |
| 커버리지 결측(호출 불요, 즉시 버킷 폴백) | 204 |

> 쌍당 LLM 호출 1회(㉯). 이미 태깅된 쌍은 idempotent skip(재개 안전). 결측 204쌍은 호출 없이 버킷 폴백.

### 콜당 소요·토큰 (240콜 실험 앵커 — 신규 호출 0)

| 항목 | 추정 | 근거 |
|------|------|------|
| 입력 토큰/콜 | ~270 | ㉯ 프롬프트 실측(system 235 + user 33) |
| 출력 토큰/콜 | ~160 | domain_tag + rationale JSON |
| 콜당 wall time | ~6s | 240콜 sweep(4.2s throttle + ~1.5-2s 지연) 앵커 |

### 무료 티어 (Gemini 2.5 Flash Free) — 비용 $0, 분할 일정

| 항목 | 값 |
|------|----|
| 한도 | **15 RPM · 1,500 RPD** (CLAUDE.md 외부 API) |
| 일 배치 | 1,500쌍 (RPD 상한) |
| **분할 일수** | **7일** (9,161 ÷ 1,500 = 6.1 → 6일×1,500 + 1일×161) |
| 일 wall time | ~2.5시간/일 (1,500 × ~6s) |
| **비용** | **$0** |
| 실행 | `tag_peer_domains --apply --limit 1500` 일 1회(idempotent 재개) |

### 유료 티어 (Gemini 2.5 Flash Paid) — 단일 세션

| 항목 | 값 |
|------|----|
| 한도 | Tier1 ~1,000 RPM · ~10,000 RPD (RPD 여유 1회 완주) |
| 단가(추정) | 입력 $0.30/1M · 출력 $2.50/1M |
| 콜당 비용 | ~270×$0.30/1M + ~160×$2.50/1M ≈ **$0.00048** |
| **총 비용(9,161콜)** | **≈ $4.4** (전량 9,365 기준 ≈ $4.5) |
| 완주 시간 | ~1일 이내(throttle 완화 시 1-2시간) |

> ⚠️ 단가·토큰은 **추정**(SEC β G-e 실측 앵커 $0.0094/콜은 대형 프롬프트 기준 — Peer는 ~1/20 규모).
> B단계 착수 직후 **소량 마이크로배치(5-10콜)로 실단가·실지연 확정** 권장(그 시점부터 비용 발생 = 게이트 이후).

### 제공자 (래퍼 지원)

- 현 래퍼 `generate_with_circuit` = **google.genai(Gemini) 전용** (CB `gemini`, model=`gemini-2.5-flash`).
- Gemini 외 제공자(OpenAI/Anthropic 등) **미배선** → 추가 시 래퍼 확장 필요(본 트랙 밖).
- **결론: Gemini 무료(7일 분할·$0) vs 유료(단일 세션·~$4.4) 2안.**

### 권장 (게이트 상신)

| 방식 | 소요 | 비용 | 적합 |
|------|------|------|------|
| **무료 7일 분할** | 7일(일 2.5h) | **$0** | 비용 0 우선, 시간 여유 |
| **유료 단일 세션** | ~1일 | ~$4.4 | 즉시 완주 우선 |

> B단계 착수(비용 발생)·`--apply`(prod 태그 기록)·머지·배포는 **병진님 승인 게이트**.

---

# B단계 (L2-FULL-SWEEP) — 전량 태깅 실행 (병진님 승인 2026-08-03)

## 실행 요약

- 유료 단일 세션, `--apply` prod 기록, thinking_budget=512(D-L2-THINKING-BUDGET).
- detached 프로세스(nohup) + Monitor 진척 감시(1000 마일스톤·완료·死). 재개 안전(콜당 즉시 DB 커밋).
- 배치 무중단 완주: json_fail 0 · circuit_fail 0.

## P2 실단가 게이트 (마이크로배치)

| 항목 | 실측 |
|------|------|
| 콜당 비용 | **$0.00050515** (in ~289tok · out ~167tok) |
| 전량 환산 | **~$4.67** (게이트 2×=$8.8 → **통과**) |
| 지연(thinking 512) | ~3,974ms/콜 |

## P3 전량 최종 분포 (distinct 9,365쌍)

| 지표 | 값 |
|------|----|
| **채택**(태그+거부권통과) | **5,928 (63.3%)** |
| **거부권 발동** | **68 (0.73%)** — low_grounding 67 / no_claim 1 |
| 빈 태그 → 버킷 폴백 | 3,389 (36.2%, 대부분 타산업) |
| **추정 라벨** | **2,511 (26.8%)** — 기대 2,498 정합 |
| status | auto 9,297 / pending 68 |
| 채택 태그종 | 3,063종 |
| json_fail / circuit_fail | 0 / 0 |

### 총비용 실측
- 배치 invocation(8,876콜) **$4.4837** + 선행(파일럿 청크 469 + 마이크로/진단 ~32) ~$0.26 → **총 ≈ $4.74**.
- 추정 $4.4 대비 근접, 게이트 2×($8.8) 이내.

### 구획별 거부권률 (A1 정합 확인)

| 구획 | veto/n | 비율 |
|---|---|---|
| 하·상이 | 7/2,511 | 0.3% (A1 0% 정합) |
| 상·동일 | 3/604 | 0.5% |
| 중·상이 | 7/2,454 | 0.3% |
| **상·미상** | 17/82 | **20.7%** |
| ·미상(tercile 결측) | 21/54 | 38.9% |

> 거부권은 **industry 결측(미상) 쌍 + 제네릭 태그 메가캡**(AMZN↔MSFT "클라우드 컴퓨팅" gr 0.167,
> AMD↔AVGO "반도체" gr 0.042)에 집중 — 서술 광범위해 구체 claim 미접지. A1이 우려한 하·상이(소형·타산업)
> 셀은 예측대로 거의 0. veto가 억지·제네릭 태그를 정상 필터.

## P4 검증 (ego 서빙 라이브)

- **채택 표본**: peer_domain = DB llm_tag 정확 노출(MRK↔SOLV "의료기기 및 헬스케어 솔루션" estimate=True 등).
- **거부권 표본**: 전부 **엣지 미은닉 + peer_domain=null(버킷 폴백) + status=pending**
  (ASML↔NVDA 폴백버킷="반도체·메모리" 실증) → soft-drop 교정 라이브 작동.

## 견적 교훈 (A4 시간 과낙관)

A4의 "유료 1-2시간"은 **실 지연(thinking 기본 ON 8.8s) 미반영**. thinking_budget 조정(512→4s)으로
완주 ~11h. 교훈: 배치 견적은 **모델 thinking 지연을 반영**해야 함(비용은 정확했으나 시간 과낙관).

## 대사 (Reconciliation, PRE-DEPLOY-FIX 2026-08-05)

> **DB(RelationConfidence)가 정본, `summary.json`은 실행 세그먼트 evidence.**

**⑴ 상호배타 파티션 등식** (정본):
```
채택(draft有·비veto) 5,928 + 거부권(veto) 68 + 빈태그·미거부권(draft無·비veto) 3,369 = 9,365 (= distinct)
```
- 기보고 "빈 태그 3,389"는 draft無 **전체**(거부권 발동 중 draft無 20건 포함)라 거부권(68)과 **20건 겹침**(비배타).
  → 채택+거부권+빈태그(전 draft無) = 9,385 = 9,365 **+20**(겹침, 이중처리 아님).
- 서빙상 **버킷 폴백 총 = 거부권 68 + 빈태그·미거부권 3,369 = 3,437**, llm_tag 노출 = 채택 5,928.

**⑵ 세그먼트 대사 등식**:
```
DB 전수 9,365 = summary.json(최종 invocation) 8,876 + 선행 세그먼트 489
              (선행 489 = 마이크로배치 20 + 파일럿 청크 469)
```

**⑶ 이중처리 무**: raw 태깅 행 9,365 = distinct 쌍 9,365(차이 0), 2+ 방향행 이중기록 0 → 각 쌍 정확히 1회 처리·과금.
추정 라벨 2,511은 파티션과 독립인 additive 플래그.
