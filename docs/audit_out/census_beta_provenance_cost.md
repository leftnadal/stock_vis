# β provenance 비용 census — News Intel / Chain Sight

> 목적: 증거에 β(2-pass grounded provenance)를 **모든 텍스트 추출 관계에 적용(①)**할 때의 실제 LLM 지출을 range가 아닌 확정 숫자로 좁힌다.
> 측정: repo + dev DB 전수(census). M5만 분포 샘플.
> 봉인일: 2026-07-02 / HEAD 3c74073 / 커밋 94f082c / **dev DB 기준**.
> 비용 공식: 월 β콜 = (β 문서/일) × 2 pass × 30. 콜당 단가 = 입력토큰×단가 + 출력토큰×단가 (Sonnet 5 도입가 $2/$10 per Mtok, 배치 50% off, 9월 이후 표준가 ×~1.8).

---

## §0. 선결 개념

- **P1 — β 대상 = 텍스트 추출 근거만.** β는 pass-1에서 native citations로 원문 문장을 grounding → **텍스트(뉴스·SEC 공시)를 LLM이 추출한 관계에만** 적용 가능. `PRICE_CORRELATED`·`CO_MENTIONED` 등 시장/통계 파생 관계는 인용 대상이 없어 제외. `PEER_OF`(FMP peer/industry 구조 데이터, `has_llm_source=0`)도 문장 인용 대상 없음 → β 불가.
- **P2 — β 청구 단위 = LLM 추출 "콜" (evidence row 아님).** 한 추출 컨텍스트마다 2콜(pass-1 grounding + pass-2 structured). 실측 결과 **문서(기사/공시)당 1콜**로 관계 N개를 한꺼번에 뽑음 → 콜 수 = 문서 수 × 2.

---

## §1. M1 — β 대상 스코프 + 추출 콜 단위 (가중 0.26)

**콜 granularity 판정 = 문서당 1콜** (관계당 아님):
- SEC: `services/sec_pipeline/extractor.py:35-95` — `filter_paragraphs(max=15)`를 합쳐 문서당 단일 `generate_content`, `{"relationships":[...]}` 리스트 반환. 청크 루프 없음.
- 뉴스: `services/serverless/services/llm_relation_extractor.py:374-418` — 기사 본문(≤5000자) 단일 호출, `relations` 리스트. `extract_batch`도 문서당 1콜.

**β 대상 (텍스트 추출):**
| 저장소 | 카운트 | 근거 |
|---|---|---|
| SupplyChainEvidence (SEC 10-K) | 1,751 evidence / **351 distinct 문서** | 전수 |
| LLMExtractedRelation (뉴스) | **0행** | 30일 TTL + 미가동 (§7 T2) |
| RelationConfidence 텍스트파생(중복제거 pair) | 270 (COMPETES_WITH 114·SUPPLIES_TO 61·PARTNER_WITH 54·DEPENDS_ON 41) | 전부 `has_supply_chain_source`, `has_llm_source=0` |

**제외 (시장/통계):** RelationConfidence `category='market'` 4,062행 (PRICE_CORRELATED 3,784 + CO_MENTIONED 278).
**β 불가 (구조):** PEER_OF 9,365행 (`has_llm_source=0`, FMP peer/industry).

**콜당 평균 산출 관계 수:** SEC = 1,751 ÷ 351 ≈ **5.0 evidence/콜**. 뉴스 = UNKNOWN(0행).
**현재 β 청구 콜:** SEC 351문서 × 2 = **702콜**로 1,751 evidence 전부 커버. 뉴스 0콜.

---

## §2. M2 — 백필 물량 (일회성, 가중 0.06)

β를 추출 콜 단위(distinct 문서)로 환산:
| 소스 | 콜(distinct 문서) | evidence row |
|---|---|---|
| SEC supply_chain (β 관계 대상) | **351** | 1,751 |
| SEC business_model (사업모델 — 관계 아님, 참고) | 404 | 1,997 |
| Regulatory LLM (weekly) | 17 headlines | 361 |
| 뉴스 LLM | 0 | 0 |

- **β 관계 백필 = SEC supply_chain 351 × 2 pass = 702콜** (일회성). evidence row 1,751 ≠ 콜(콜당 ~5행) — row로 세면 과대추정.
- 도입가 배치 환산 ≈ **$5~10 일회성**(SEC 단락 토큰 미측정, 근사).

---

## §3. M3 — 일일 신규 β 콜량 (가중 0.28, 최우선)

**≈ 0 / 0 / 0 (평균/중앙/피크).** 뉴스 β 미가동, SEC는 월간 배치.
- (a) 타임스탬프: `LLMExtractedRelation` 30일 0행. `SupplyChainEvidence`는 3개 이산 배치일(2026-04-03·05-16·07-01)만 — daily 패턴 아님.
- (b) 인입: NewsArticle ~800/일(평일) 인입되나 β 추출률 0%(daily 09:00은 정규식 매처, LLM 아님).
- (a)(b) 불일치 없음 — 둘 다 뉴스 β=0 수렴.

---

## §4. M4 — 재스코어·리프레시 케이던스 (가중 0.12)

**LLM 재추출 cadence = 0 (월 반복 배수 ≈ 0).**
- `check_stale_and_decay`(토 04:00): status 하향만 = **non-LLM**.
- `update_relation_confidence`(daily 11:00): 규칙 기반 재판정 = **non-LLM**.
- `extract_news_relations`(daily 09:00): 정규식 CO_MENTIONED = **non-LLM**.
- SEC `check_new_filings`(월 1일): **신규 accession만** 트리거, 기존 10-K 재추출 안 함.
- → 기존 증거 LLM 재추출 배치 없음. **과소추정 위험 없음.**

---

## §5. M5 — 콜당 토큰 (가중 0.18, 분포 샘플)

⚠ `ANTHROPIC_API_KEY` **401 무효** → count_tokens 실측 불가. char/token 근사(영문 3.5~4.0).
⚠ 뉴스 **전문 미저장**(title+summary만) → pass-1 실입력은 하한.

| 항목 | 값(tok) | 근거 |
|---|---|---|
| pass-1 입력 p50/p90 | 59~67 / 118~134 | N=500, ⚠요약본(전문 시 650~2000) |
| pass-1 출력 | ~150~400 (추정) | llm_analysis 실측 p90≈254~290 앵커 |
| pass-2 입력 (스키마+span) | ~550~750 | 스키마 실측 1,607 chars≈400~460 + span |
| pass-2 출력 | ~110~370 (1~3관계) | 스키마 직렬화 449~1,301 chars |

---

## §6. M6 — confidence tier 분포 (가중 0.10, ②/① 델타)

- 전체 RelationConfidence(13,697): probable+ 75.9% (단 PEER_OF·PRICE 규칙기반 지배).
- **β 대상(SEC 텍스트) 270건: probable 37 + confirmed 233, hidden/weak/stale 0 → probable+ = 100%.**
- 뉴스 LLM: 0행 → tier 미측정.
- → **② 옵션(probable+만 β)의 절감 효과 ≈ 0** (SEC가 전량 probable+). ①=②.

---

## §종합 — ① 확정 비용

- **현재 월 반복 ≈ $0** (뉴스 β 미가동 + SEC 신규 filing 월 소수). **① = ②**(델타≈0, SEC 100% probable+).
- **백필 일회성 ≈ $5~10** (SEC supply_chain 702 β콜).
- **미래(뉴스 β 켤 때)**: 통과율에 지배 → §7 T1이 실측(7%)으로 좁힘.
- 측정 한계: dev 기준, API키 401, 뉴스 전문 미저장. prod beat 재검증 권장.

<!--
  B-1 봉인 블록 — census 본문(M1~M6)의 연속 섹션(§7).
  봉인일: 2026-07-02 / HEAD 3c74073 / 커밋 94f082c / dev 기준
-->

## §7. 뉴스 β 활성화 조사 (T1·T2) — 2026-07-02

`investigate_news_beta_activation.md` 실행 결과 봉인. census(§1~§6)가 던진 "① 얼마냐"가
"뉴스 β를 켤 것인가"로 바뀐 지점을 닫는 2트랙 조사.

### §7.1 T1 — pre_filter 통과율 dry-run

| 항목 | 값 |
|---|---|
| 인입 / 통과 / 통과율(가중) | 17,660건(30일) / 1,234건 / **6.99%** |
| 일별 통과율 평균·중앙·피크 | 5.95% · 5.48% · 10.94% |
| 게이트 | `relation_hints≥1 AND company_mentions≥2` (고정 정규식, percentile 아님, 커밋 94f082c) |
| β 문서/일 | 평일 ~56 (하한 48 / 피크 87) |
| 월 β콜 | 56 × 2pass × 30 ≈ **3,360** |
| 월 비용 | 도입가 배치 $7~9 / non-배치 $13~17 / 9월 표준가 $25~31 |

검증 경고(리포트 자체 명시, 확인 완료):
- ⓐ 룰 입력 = **title+summary** = 본문 대비 **하한**. 전문 저장 시 통과율·토큰 재측정 필요.
- ⓑ NewsEntity에 `headline`/`content`/`published_at` 필드 부재 → 실호출 시 **AttributeError crash**(배선 결함).
- ⓒ 현 코드는 `_call_llm` **1콜** — 2-pass grounded provenance 미구현.

### §7.2 T2 — 미배선 사유 (git 이력)

| 항목 | 값 |
|---|---|
| 상태 | 처음부터 미연결 |
| 사유 | 배선 드리프트(#28식 순수 침묵실패) — `config/celery.py` 어떤 커밋에도 LLM task **0건** |
| 과거 실패 흔적 | **없음** (disable / quality / cost / hallucination 커밋 0건) |
| 정규식(Phase 6B CO_MENTIONED)과의 관계 | 무관·독립·상호보완 (β 대체가 아님) |

→ "모르는 이유를 밟고 켜는" 위험은 없음. 단 "켜기"의 성격이 바뀜(§7.3).

### §7.3 판정 — 비용(켤 가치) × 안전(켜도 됨) 2축 (독립 채점)

- **① 켤 가치(비용) = ✅ 장벽 아님.** 통과율 7% = census 최저 시나리오(10%)보다 낮음. 월 $10~30대. M4 재스코어 0이라 반복 배수 없음.
- **② 켜도 됨(안전) = ⚠ 조건부.** "위험해서"가 아니라 **"켤 스위치가 아직 없어서".** T2로 침묵실패 위험은 소거됐으나, census가 드러낸 진실은 **"켜기 = beat 등록"이 아니라 "켜기 = 3층 신규 구축":**
  1. **β 2-pass grounded provenance 미구현** — 현 `_call_llm` 1콜. native citations 로직 부재. "뉴스 β 켜기" = β 파이프라인 신규 구축.
  2. **NewsEntity 배선 결함** — `headline`/`content`/`published_at` 부재 → AttributeError.
  3. **뉴스 전문 미저장** — title+summary만 저장 → pass-1 grounding 대상(원문 문장) 없음.

### §7.4 결정 기록 (DECISIONS 편입)

채점 차원·가중치 (**weights 합 = 1.00**):

| 차원 | 가중치 | A(뉴스β 구축) | B(SEC β) | C(본진 복귀) |
|---|---|---|---|---|
| moat 실데이터 축적 즉시성 | 0.35 | 0.30 | 0.90 | 0.85 |
| 착수 대비 실현 거리 | 0.25 | 0.20 | 0.80 | 0.90 |
| 침묵실패·유지보수 안전 | 0.20 | 0.40 | 0.75 | 0.85 |
| 본진 궤적 루프 진도 | 0.10 | 0.20 | 0.50 | 1.00 |
| 운영 비용 (월 $) | 0.10 | 0.80 | 0.80 | 0.90 |
| **가중 합** | **1.00** | **0.335** | **0.795** | **0.8825** |

- 순위: **C 0.8825 > B 0.795 > A 0.335.** 마진 C−B = **+0.088**, B−A = +0.460.
- **결정: C 채택** — census 봉인 후 #28 본진(궤적→상향 학습 루프) 복귀.
- **예약:** B(SEC β provenance 강화)를 **#28 Gate 2 통과 직후 다음 β 트랙**으로. 커밋 전 확인 1점: SEC β 2-pass가 "강화"(base 이미 생산 중)인가 "신규"(1콜만)인가.
- **파킹:** A(뉴스 β 3층)는 **전문 저장 후 통과율·토큰 재측정** 조건부 보류. 현재는 요약본 하한이라 착수 가치 판단 자체가 불완전.
- **결정 근거(핵심):** 세 레인 중 **소급 재구성 불가는 #28 궤적뿐.** β 증거는 원문 잔존으로 재추출 가능하나, 궤적 스냅샷은 beat 미가동일 = 영구 공백. moat 정의("temporal trajectories, none reconstructable retroactively")에 직결.

### §7.5 근거 스냅샷 (재조사 방지)

- ① 현재 월 <$1, 백필 $5~10 일회성, **①=②(델타≈0)** — SEC supply_chain 351문서 / 1,751 evidence, 100% probable+.
- 뉴스 β(`LLMExtractedRelation`) = **0행·미가동**. daily 09:00 = 정규식 CO_MENTIONED(비-LLM). PEER_OF 9,365 = FMP 구조데이터(β 불가).
- M4 재스코어 = 0 (과소추정 위험 없음).
- 미래 시나리오(뉴스 β 켤 때): 통과율 10/30/50% → 도입가 월 $25/$73/$122. **T1이 이 표를 실측 1값(7%)으로 좁힘.**
- 메모: 룰 입력 = 요약본(하한). ROADMAP "$5/월"은 Gemini 1콜 기준(β=Sonnet 2-pass면 상향). 커밋 94f082c / HEAD 3c74073 / dev.

---
*봉인 종료 — §7. 복귀 지점: 이 조사는 닫힘. 다음 세션은 #28 beat 등록에서 출발.*
