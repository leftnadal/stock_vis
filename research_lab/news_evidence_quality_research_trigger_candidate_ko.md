# Stock_vis 뉴스 Evidence 품질 — Cross-Lab Research Trigger Candidate 한국어 Companion

> **영문 canonical 문서:** [`news_evidence_quality_research_trigger_candidate.md`](news_evidence_quality_research_trigger_candidate.md)  
> 이 문서는 빠른 이해를 돕기 위한 한국어 companion이다. 독립된 Research Authority가 아니다.

**상태:** Working / Research Trigger Candidate  
**버전:** 0.1  
**날짜:** 2026-09-04  
**발견 주체:** Stock_vis Design Lab  
**전달 대상:** Stock_vis Research Lab  
**공식성:** 없음 — Research Knowledge, 승인된 Research Case, Methodology 변경, Product Decision이 아님

## 1. 쉽게 이해하는 요약

Design Lab이 실제 Stock_vis 데이터를 사용해 Company Workspace를 설계하던 중 뉴스 데이터에서 중요한 문제가 보였다.

문제는 단순히 뉴스가 많거나 적다는 것이 아니다.

- NVDA는 raw news와 processed intelligence가 매우 많다.
- 하지만 최신 processed sample에는 NVDA가 주인공으로 보이지 않는 기사들이 여러 개 섞여 있다.
- VRT는 raw news에 회사 인수와 AI 데이터센터 전력 문제처럼 직접 관련성이 높아 보이는 기사가 있다.
- 하지만 processed intelligence는 1건뿐이다.

즉 다음 세 가지가 서로 다를 수 있다.

```text
뉴스가 존재한다
≠
Stock_vis가 처리했다
≠
그 뉴스가 해당 회사의 판단에 실제로 유용하다
```

현재 데이터만으로는 정확한 원인을 알 수 없다. 단순 ticker 연결 오류일 수도 있다. Co-mention을 직접 관련 뉴스처럼 취급했을 수도 있다. Event extraction, ranking, processing coverage에 문제가 있을 수도 있다.

Design Lab은 이 문제를 다음과 같은 Research Trigger Candidate로 전달한다.

> Raw news를 회사와 Claim에 관련된 Evidence로 바꿀 때 어떤 의미 기준과 평가 기준을 적용해야 하는지 Research Lab이 연구할 필요가 있다.

Research Lab은 이 Trigger를 그대로 받을 필요는 없다. 현재 공식 Methodology에 따라 수용, 재구성, 병합, 보류, 기각할 수 있다.

---

## 2. 왜 Design Lab에서 이 문제가 발견됐나

현재 Design Lab은 Company Workspace를 다음 흐름으로 만들고 있다.

```text
무엇이 바뀌었나?
    ↓
그중 무엇이 중요할 수 있나?
    ↓
현재 Investment View의 어느 부분과 관련 있나?
    ↓
어떤 Evidence가 그 해석을 지지하거나 흔드나?
```

뉴스는 이 흐름에서 중요하다.

예를 들어 새 인수, 고객 투자 변화, 경쟁사 가격 변화, 규제 사건은 기존 View를 다시 보게 할 수 있다.

하지만 현재 뉴스 pipeline의 결과를 바로 사용하면 다음 위험이 있다.

- 관련성이 낮은 기사를 중요한 변화처럼 보여줄 수 있다.
- 직접 관련 뉴스가 있는데도 `분석된 뉴스가 없다`고 보일 수 있다.
- 처리된 뉴스 건수를 품질로 오해할 수 있다.
- 약한 뉴스 연결이 사용자의 View를 부당하게 바꿀 수 있다.

따라서 UI를 더 잘 만드는 것만으로 해결할 수 없다. 먼저 Research 수준에서 뉴스 output의 의미를 정리해야 한다.

---

## 3. 확인한 Source Snapshot

이번 관찰은 private working-evidence repository의 실제 Stock_vis DB handoff를 사용했다.

- Repository: `leftnadal/stock_vis_design_handoff`
- Handoff run: `2026-09-03T163602+0900`
- Inspector version: `0.1`
- Inspector implementation commit: `1826fb88580253f9affadbdc152a3b9c746b8155`
- Inspector schema authority ref: `origin/main@eb3cdd85ce5cba4d65137758a2f507ebb70fde8b`
- DB role: `stockvis_design_reader`
- Privacy validation: pass
- Raw integrity validation: pass

주요 자료:

- [Latest manifest](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/manifest.json)
- [NVDA data quality](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/symbols/NVDA/data_quality.json)
- [NVDA news](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/symbols/NVDA/news.json)
- [VRT data quality](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/symbols/VRT/data_quality.json)
- [VRT news](https://github.com/leftnadal/stock_vis_design_handoff/blob/main/latest/symbols/VRT/news.json)

Handoff repository는 Working Evidence 저장소다. Research Knowledge나 공식 Design Knowledge가 아니다.

---

## 4. 실제로 확인한 현상

### 4.1 Coverage 차이

| 종목 | Raw news | Processed intelligence | 초기 관찰 |
| --- | ---: | ---: | --- |
| NVDA | 15,653 | 795 | 두 단계 모두 양이 많음 |
| VRT | 197 | 1 | Raw news는 있지만 processed coverage는 매우 낮음 |

두 종목 모두 Inspector에서 다음 warning이 나온다.

```text
NEWS_INTELLIGENCE_COVERAGE_GAP
Processed intelligence는 raw news의 일부다.
Processed intelligence가 적다고 뉴스가 없는 것은 아니다.
```

### 4.2 NVDA에서 보인 문제

NVDA의 최신 processed intelligence sample에는 제목만 보면 NVDA가 주인공으로 보이지 않는 항목이 여러 개 있다.

예:

- Hasbro 임원 주식 매도 기사
- F5 보안 제품 기사
- AMD 기관보유 변화 기사
- Amazon 기관보유 변화 기사

일부 기사에는 AMD 등 다른 symbol이 co-mention으로 들어 있다. 그러나 왜 이것이 NVDA의 company intelligence로 제공됐는지는 현재 output만으로 명확하지 않다.

가능성은 여러 가지다.

- 잘못된 symbol 연결
- co-mention을 직접 관련성처럼 처리
- 관계 graph를 통한 간접 연결
- 저장은 맞지만 serving query가 잘못됨
- title만 봐서는 실제 본문 관련성을 놓침

현재 단계에서는 어느 설명도 확정하지 않는다.

### 4.3 VRT에서 보인 문제

VRT raw news에는 다음과 같은 직접적인 회사 사건으로 보이는 기사가 있다.

- UtilityInnovation Group 인수 발표
- 약 14.5억 달러 규모 거래 보도
- AI 데이터센터의 time-to-power 문제 완화 목적
- AI 인프라와 전력 병목에 대한 VRT 중심 기사

하지만 processed intelligence는 1건뿐이다.

가능성:

- processing coverage 부족
- 처리 지연
- source별 pipeline 차이
- event extraction 실패
- threshold 문제
- routing 또는 materialization 문제

이 역시 아직 확정되지 않았다.

---

## 5. 현재 자료로 말할 수 있는 것

다음은 비교적 안전하게 말할 수 있다.

1. Raw-news 건수는 Evidence 품질을 뜻하지 않는다.
2. Processed-intelligence 건수도 회사 관련성이나 materiality를 뜻하지 않는다.
3. 처리량이 많아도 관련성 noise가 많을 수 있다.
4. 처리량이 적어도 중요한 raw event가 존재할 수 있다.
5. Availability, processing coverage, relevance, materiality, decision usefulness를 분리해야 한다.

---

## 6. 아직 말할 수 없는 것

다음은 아직 모른다.

- NVDA sample의 모든 간접 기사가 오류인지
- VRT 인수 사건이 모든 투자 관점에서 material한지
- 어느 pipeline stage가 문제인지
- title만으로 relevance를 충분히 판단할 수 있는지
- 현재 전체 pipeline의 precision과 recall이 어느 정도인지
- 한 뉴스가 특정 Claim을 지지하거나 약화하는지
- 모든 회사에 적용되는 하나의 materiality 규칙이 가능한지

따라서 이 문서는 해결책을 확정하지 않는다.

---

## 7. Candidate Research Trigger

### Trigger 성격

- **Failure:** 관련성이 낮아 보이는 item이 processed output에 섞이고, 직접 관련성이 높아 보이는 item은 충분히 처리되지 않을 수 있다.
- **Knowledge Gap:** News relevance, event identity, materiality, Claim bearing에 대한 검증된 semantic contract가 없다.
- **User Need:** Company Workspace는 무엇이 바뀌었고 왜 중요한지 신뢰성 있게 보여줘야 한다.
- **Scale Problem:** 데이터가 많아지면서 건수 중심의 proxy가 실제 semantic failure를 가릴 수 있다.

### Trigger 문장

> 현재 Stock_vis news pipeline은 raw availability, company association, primary subject, event relevance, materiality, Claim-relative bearing을 충분히 구분하지 못할 가능성이 있다. 이 때문에 Research Lab은 news-derived output을 disciplined Evidence로 사용하기 어렵고, Design Lab은 이를 사용자에게 책임 있게 보여주기 어렵다.

---

## 8. Candidate Research Problem

> Stock_vis에는 raw news를 company-relevant, event-structured, materially scoped, Claim-relative Evidence로 바꾸는 충분히 검증된 semantic/evaluation framework가 없다. 그 결과 현재 intelligence record와 count가 시스템이 실제로 무엇을 알고 있는지를 과대 또는 과소 표현할 수 있다.

첫 audit에서 단일 engineering bug로 확인되면 이 Problem은 축소하거나 종료할 수 있다.

---

## 9. Candidate Primary Research Question

> Raw news를 Stock_vis의 company-relevant 및 Claim-relative Evidence로 변환할 때 어떤 semantic contract와 evaluation contract가 필요할까?

### Secondary questions

1. 기사가 올바른 회사와 연결됐는가?
2. 해당 회사가 primary subject인가, secondary subject인가, 단순 co-mention인가?
3. Direct relevance와 indirect/contextual relevance를 어떻게 구분할까?
4. 기사가 보고하는 실제 event는 무엇인가?
5. 새 event인가, 중복인가, 업데이트인가, commentary인가?
6. 어떤 scope에서 material하다고 볼 수 있는가?
7. 구체적인 Claim이 있을 때 support, challenge, qualification, discrimination 중 어떤 bearing을 갖는가?
8. Source와 provenance를 어디까지 보존해야 하는가?
9. 언제 `unknown` 또는 abstention을 사용해야 하는가?
10. Raw coverage와 processed coverage를 어떻게 평가할까?
11. 관련 기업의 뉴스가 다른 회사로 전파될 수 있는 조건은 무엇인가?
12. Intended use마다 어떤 precision/recall 수준이 필요한가?

---

## 10. 조사할 때 분리해야 할 층

다음 구조는 **탐색을 위한 candidate**다. 공식 taxonomy가 아니다.

| 층 | 핵심 질문 | 분리해야 할 것 |
| --- | --- | --- |
| Source identity | 어떤 원문인가? | DB에 있다는 사실 ≠ credible Evidence |
| Entity association | 어떤 회사가 언급됐나? | Mention ≠ relevance |
| Primary subject | 기사의 주인공은 누구인가? | Co-mention ≠ primary subject |
| Relationship context | 관련 회사를 통해 간접 연결됐나? | Graph adjacency ≠ evidential relevance |
| Event extraction | 무엇이 누구에게 언제 발생했나? | Article identity ≠ event identity |
| Novelty / duplicate | 새 정보인가 반복인가? | 기사 수 증가 ≠ 독립 Evidence 증가 |
| Semantic relevance | 회사 이해와 관련 있는가? | Relevance ≠ materiality |
| Materiality | 특정 scope에서 중요한가? | Materiality ≠ 현재 사용자 우선순위 |
| Claim bearing | 특정 Claim에 어떤 영향을 주나? | Bearing은 article 자체 속성이 아니라 관계 |
| Processing state | 얼마나 충분히 처리됐나? | Processing coverage ≠ Evidence quality |
| Product priority | 지금 사용자에게 보여줄까? | 주로 Design Lab 책임 |

이 모든 것을 하나의 `News Quality Score`로 합치지 않는 것이 중요하다.

---

## 11. 가능한 원인들

초기 audit에서 다음을 비교해야 한다.

1. ticker/entity linking false positive
2. co-mention과 direct relevance 혼동
3. primary-subject 분류 실패
4. relation graph propagation의 directness 표시 부족
5. event extraction 또는 event materialization 실패
6. duplicate clustering 실패
7. processing queue 지연 또는 누락
8. source별 ingestion 차이
9. relevance보다 recency를 우선하는 serving
10. underlying data는 맞지만 Company query가 잘못됨
11. title-only 검토의 한계
12. precision보다 coverage를 과도하게 최적화
13. abstention 없이 약한 연결을 강제 분류

첫 단계부터 하나를 정답으로 가정하면 안 된다.

---

## 12. 추천하는 첫 Investigation 방향

최종 Research Design은 Research Lab이 결정한다.

### A. Pipeline map

```text
Raw article
→ source normalization
→ entity/symbol association
→ primary subject
→ event extraction
→ duplicate/update clustering
→ relationship propagation
→ relevance
→ materiality / Claim linkage
→ storage
→ serving/ranking
```

각 stage마다 확인할 것:

- 원래 맡은 의미 역할
- 실제 code가 하는 일
- unknown을 허용하는지
- 어떤 provenance가 사라지는지
- false positive와 false negative가 생기는 경로

### B. Stratified sample

최소한 다음 유형을 섞는다.

- NVDA 같은 high-volume case
- VRT 같은 uneven-coverage case
- ticker ambiguity 또는 sparse news를 드러내는 추가 case

Processed intelligence만 보지 않는다.

- intelligence로 올라간 record
- raw에 남고 올라가지 않은 record

둘 다 포함해야 한다.

### C. Independent annotation

Candidate dimensions:

- entity-link correctness
- primary / secondary / co-mentioned / unrelated
- direct / indirect / contextual relevance
- event identity
- duplicate / update / commentary
- materiality under stated scope
- Claim-relative bearing
- provenance adequacy
- legitimate abstention

Exploratory annotation과 confirmatory evaluation은 구분한다.

### D. Error profile

하나의 accuracy score보다 다음을 구분한다.

- semantic definition gap
- data limitation
- model limitation
- engineering defect
- serving/ranking defect
- unavoidable uncertainty

그 다음에만 `News Evidence Quality Contract` candidate를 제안한다.

---

## 13. 평가할 때 볼 수 있는 기준

Candidate evaluation dimensions:

- entity-link precision/recall
- primary-subject accuracy
- direct-relevance precision/recall
- material-event recall
- duplicate/event-cluster accuracy
- provenance completeness
- abstention calibration
- processed-coverage completeness
- 구체적 Claim이 있을 때 bearing accuracy
- consequence-weighted false positive/false negative
- 회사 유형과 news-volume이 달라도 유지되는지

Intended use를 반드시 구분해야 한다.

```text
Background exploration
≠ Company alert
≠ Investment View revision proposal
≠ Research Evidence admission
```

Click, article count, sentiment volume, engagement는 epistemic quality의 충분한 증거가 아니다.

---

## 14. Lab별 책임

### Research Lab

- company relevance 의미
- direct / indirect relevance
- event와 Evidence identity
- research scope에서의 materiality
- Claim-relative bearing
- source/provenance requirement
- evaluation design
- unknown/abstention 의미

### Engineering / Codex

- pipeline과 code audit
- entity resolution
- primary-subject 분류
- event extraction/clustering
- deduplication
- instrumentation
- confidence propagation
- serving/ranking 구현
- regression monitoring

Engineering은 Research semantics를 구현해야 하며 임의로 다시 정의하면 안 된다.

### Design Lab

- 어떤 valid information을 먼저 보여줄지
- directness, confidence, coverage, provenance 표현
- processing limitation 전달
- event → Evidence → View review interaction
- 사용자의 judgment가 실제로 좋아지는지 평가

### Math Lab

향후 news-derived signal과 시장 결과의 수치 관계를 연구할 수 있다. 그러나 news relevance와 Evidence의 semantic authority는 아니다.

---

## 15. Research가 진행되는 동안 Design Lab이 지킬 임시 Guardrail

1. Processed intelligence 건수를 relevance quality로 쓰지 않는다.
2. Raw coverage와 processed coverage를 분리한다.
3. Raw news가 있는데 processed record가 적다고 `뉴스 없음`이라고 말하지 않는다.
4. News record만으로 user-owned Investment View를 자동 수정하지 않는다.
5. Source와 publication time을 확인할 수 있게 한다.
6. 필요하면 `relevance quality under evaluation`을 표시한다.
7. Direct와 indirect relevance를 가능한 범위에서 구분한다.
8. 약한 관련성에는 강한 분류보다 abstention을 우선한다.
9. Pipeline output을 생성됐다는 이유만으로 Research Knowledge처럼 취급하지 않는다.

따라서 Research 때문에 Company Workspace prototype을 멈출 필요는 없다. 한계를 드러낸 상태로 병렬 진행할 수 있다.

---

## 16. 가능한 Research Output

- 현재 news transformation pipeline map
- error taxonomy
- provenance가 있는 annotated evaluation set
- News Evidence Quality Contract candidate
- intended use별 evaluation result
- engineering remediation requirement
- unresolved alternative와 known limitation
- Problem을 축소, 분할, 종료하는 판단
- 충분히 warranted한 경우에만 후속 Research Claim 또는 Knowledge candidate

어떤 output도 자동으로 Research Knowledge가 되지 않는다.

---

## 17. Research Lab에 요청하는 행동

Design Lab은 Research Lab에 다음을 요청한다.

1. 현재 Research Authority와 비교해 이 handoff를 검토한다.
2. Trigger가 정당하고 material한지 판단한다.
3. 수용, 재구성, 병합, 보류, 기각한다.
4. 수용하면 적절한 Research Case와 Research Design을 만든다.
5. Semantic contract 제안 전에 필요한 추가 Evidence를 결정한다.
6. 단순 기술 bug라면 Research Case를 크게 만들지 않고 Engineering으로 보낸다.
7. Design assumption을 바꿔야 하는 결과가 나오면 Design Lab으로 돌려준다.

Design Lab은 현재 Company Workspace design의 승인을 요청하는 것이 아니다. 위 candidate decomposition을 공식 terminology로 채택해 달라는 요청도 아니다.

---

## 18. 이 Trigger를 축소하거나 종료할 조건

다음이면 broad Research Case가 필요 없을 수 있다.

- 단일 구현 bug로 재현되고 수정 가능
- underlying news model이 아니라 Company query만 문제
- 현재 sample이 corrupted 또는 비대표적
- 실제 intended use가 훨씬 좁음
- 기존 Approved Research Knowledge에 필요한 contract가 이미 있음
- broader research의 epistemic value가 비용보다 낮음

반대로 여러 종목, 여러 stage, 여러 downstream use에서 같은 문제가 확인될 때만 범위를 확대한다.

---

## 19. Design Lab의 현재 Recommendation

**Recommendation:** 이 문제를 legitimate Research Trigger Candidate로 보고, universal framework부터 만들기보다 bounded pipeline/error audit부터 시작한다.  
**Recommendation Strength:** Strong  
**Very Strong이 아닌 이유:** 관찰된 문제는 중요하지만 sample이 제한적이고 root cause가 아직 확인되지 않았다.  
**주요 대안:** entity linking 또는 serving의 좁은 Engineering bug로 바로 처리한다.  
**판정 기준:** 첫 audit에서 localized defect만 확인되면 수정 후 종료한다. Relevance, materiality, event identity, Claim bearing의 의미 충돌이 남으면 Research Case로 계속 진행한다.
