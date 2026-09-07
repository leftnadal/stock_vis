# Stock_vis Research Lab 연구 후보 등록부 — 한국어 Companion

> **영문 canonical 문서:** [`research_candidate_registry.md`](research_candidate_registry.md)  
> 이 문서는 빠른 이해를 돕기 위한 한국어 companion이다.

**상태:** Working / Operational Registry  
**버전:** 0.1  
**최종 수정:** 2026-09-04  
**Owner:** Stock_vis Research Lab  
**공식성:** 없음 — 운영 인덱스이며 Research Knowledge, 승인된 Research Case, Methodology, 우선순위 확정 또는 시작 시점 확정이 아님  
**기준 역할:** 연구 후보의 현재 발견·보존·처리 상태를 관리한다. 후보의 구체적 내용은 연결된 후보 문서가 기준이다.

## 1. 목적

이 등록부는 중요할 가능성이 있어 잊지 않고 보존해야 하지만, 아직 활성 Research Case로 진행하지 않는 Research Trigger Candidate와 잠재적 연구 경로를 관리한다.

정당한 Trigger라도 곧바로 연구를 시작할 만큼 충분히 검증되거나, 범위가 정리되거나, 실행 가능하거나, 시기적으로 적절하지 않을 수 있다. 이런 후보를 채팅이나 단독 handoff 문서에만 남기면 잊힐 위험이 있다. 반대로 모두를 `Backlog`나 `Roadmap`이라고 부르면 이미 승인·우선순위화·일정 확정된 과제처럼 오해될 수 있다.

따라서 이 등록부는 필요한 범위에서 다음을 기록한다.

- 후보의 출처 문서
- 현재 운영상 처리 상태
- Research Case 개설 여부
- 보존·보류·병합·종료 이유
- 다시 검토해야 하는 조건
- 연구 시작 전까지 필요한 임시 제약 또는 guardrail

## 2. 해석과 경계

등록부에 포함됐다는 것은 해당 후보를 인식했고 추후 검토를 위해 의도적으로 보존한다는 뜻이다. 다음을 의미하지 않는다.

- 제안된 Research Problem이 검증되었다.
- 승인된 Research Case로 수용되었다.
- 후보 문서의 분해 구조나 용어가 공식 채택되었다.
- 연구 일정과 자원이 배정되었다.
- 현재 진행 중인 작업보다 높은 우선순위를 갖는다.
- 후보의 결론이 Research Knowledge가 되었다.

연결된 후보 문서는 후보의 구체적 내용과 관찰 근거를 보관하는 기준 문서다. 이 등록부는 후보의 현재 보존 및 처리 상태를 관리하는 운영상 기준 문서다.

v0.1의 처리 상태 표현은 운영을 위한 서술적 표현이다. 고정된 Research Methodology lifecycle 용어, 식별자 체계, 숫자 우선순위, 처리 기한 또는 자동화 state machine을 새로 확정하지 않는다.

향후 활성화하려면 당시 최신 Research Methodology에 따른 재검토, 관련 Authority Source 확인, 기초 Evidence의 재현 가능성과 대표성 점검, 필요 시 비례적인 Research Design이 선행되어야 한다.

## 3. 현재 연구 후보 목록

| 연구 후보 | 발견 주체 | 현재 처리 | Research Case 상태 | 재검토 / 활성화 조건 | 후보 기준 문서 |
| --- | --- | --- | --- | --- | --- |
| 뉴스 Evidence 품질과 Processing Coverage | Stock_vis Design Lab | 보존하며 추후 Research Lab 재검토로 보류 | 미개설·미승인 | 서브에이전트 자동화와 Lab·cross-Lab 운영이 재현 가능한 제한적 audit을 수행할 만큼 안정되고, news pipeline과 Evidence handoff를 충분히 추적·감사할 수 있을 때 재검토 | [English](news_evidence_quality_research_trigger_candidate.md) · [한국어](news_evidence_quality_research_trigger_candidate_ko.md) |

## 4. 후보 상세 — 뉴스 Evidence 품질과 Processing Coverage

**등록일:** 2026-09-04  
**발견 맥락:** NVDA / VRT 실제 데이터를 사용한 Company Workspace 설계  
**관련 Trigger 유형:** Failure, Knowledge Gap, User Need  
**중요도 해석:** 중요한 연구 후보이나 현재 연구 우선순위는 아님  
**Project Owner 처리 지시:** 후보를 보존하고, 서브에이전트 자동화와 Lab 운영이 충분히 안정된 뒤 연구 여부를 다시 검토  
**인식론적 의미:** 없음 — 이 처리는 broad Research Problem을 검증하거나 Research Case를 승인한 것이 아님

### 4.1 왜 보존하는가

Design Lab은 서로 반대 방향의 실패 가능성을 발견했다.

- processed volume이 많아도 해당 회사와의 실제 관련성이 불명확한 항목이 섞일 수 있다.
- 중요한 raw company event가 있어도 processed coverage는 매우 낮을 수 있다.

이 문제는 raw availability, processing coverage, company relevance, materiality, decision usefulness를 서로 같은 것으로 오해하게 만들 수 있으므로 Research·Engineering·Design 모두에 영향을 줄 수 있다. 또한 후보 문서에는 연구 전까지 피해를 줄일 수 있는 임시 Design guardrail이 포함되어 있다.

### 4.2 왜 지금은 보류하는가

현재 표본만으로는 원인이 제한된 Engineering bug인지, serving/query 문제인지, 데이터 한계인지, 더 넓은 semantic·evaluation gap인지 확정할 수 없다. 제한적인 audit 전에 보편적 framework부터 만들면 성급한 구조화가 될 위험이 있다.

좋은 audit을 위해서는 Evidence handoff의 재현성, pipeline 관찰 가능성, 안정된 cross-Lab 책임 경계, provenance를 보존하고 초기 해석을 비판하며 Engineering 수정과 Research 문제를 구분할 수 있는 서브에이전트 운영 성숙도가 필요하다.

### 4.3 다시 검토할 조건

다음 중 하나 이상이 충족되면 이 후보를 다시 검토한다.

1. 서브에이전트 자동화와 Research Lab 운영 절차가 제한적이고 재현 가능한 audit을 수행·보존할 만큼 안정된다.
2. Cross-Lab handoff, provenance, data snapshot과 관련 news-pipeline stage를 충분히 접근·추적·감사할 수 있다.
3. 최신 회사·표본에서도 relevance와 coverage의 불일치가 반복된다.
4. 이 문제가 Company Workspace, Research Evidence 사용 또는 Engineering 품질 관리의 중요한 장애물이 된다.
5. 좁은 Engineering audit 이후에도 company association, event identity, materiality, Claim-relative bearing 또는 abstention에 관한 의미 문제가 남는다.

이는 **재검토 조건**이지 자동 연구 시작 명령이 아니다. 재검토 결과는 재구성, 병합, 계속 보류, 좁은 Engineering 수정 또는 종료일 수도 있다.

### 4.4 재활성화 후 첫 작업

첫 작업은 보편적인 News Evidence framework 작성이 아니라, 후보 문서가 권고한 **범위를 제한한 pipeline·error audit**이어야 한다.

Audit은 다음 순서로 진행하는 것이 적절하다.

1. processed record와 unprocessed raw record를 모두 포함한 최신 층화 표본으로 현상을 재현한다.
2. provenance를 보존하면서 관련 pipeline·serving stage를 그린다.
3. 제한된 Engineering, data, ranking, semantic-definition failure를 구분한다.
4. 실제 Research Problem이 남는지 판단한다.
5. 필요성이 확인된 경우에만 승인된 Research Case, Question, Research Design을 만든다.

### 4.5 연구 전 임시 Guardrail

재검토 전까지 다음을 지킨다.

- raw-news 건수를 Evidence 품질로 해석하지 않는다.
- processed-intelligence 건수를 회사 관련성, materiality 또는 decision usefulness로 해석하지 않는다.
- raw availability와 processing coverage를 구분한다.
- processed coverage가 적다는 이유만으로 `뉴스가 없다`고 말하지 않는다.
- 하나의 news record만으로 사용자가 소유한 Investment View를 자동 수정하지 않는다.
- 중요한 경우 source, publication time, provenance, relevance limitation과 정당한 abstention을 보존한다.

## 5. 의존 문서와 관련 Authority

이 등록부와 현재 후보는 다음 문서와 정합성을 유지해야 한다.

- [Research Methodology](01_methodology/research_methodology.md)
- [Evaluation Methodology](02_evaluation/evaluation_methodology.md)
- [Operational Record Specification](01_methodology/operational_record_specification.md)
- [Sub-Agent Research Operating Model — Candidate](01_methodology/subagent_research_operating_model_candidate.md)
- [News Evidence Quality Research Trigger Candidate](news_evidence_quality_research_trigger_candidate.md)

향후 실제 연구 활동은 승인된 Methodology가 지배한다. Sub-Agent Research Operating Model은 아직 experimental candidate이며, 이 등록부가 새로 만든 공식 선행 조건이 아니라 실제 연구를 잘 수행하기 위한 준비도 의존성이다.

## 6. 유지 규칙

새 후보를 등록할 때는 최소한 추적 가능한 출처 문서, 현재 처리 상태, Research Case 상태, 보존 또는 보류 이유, 재검토 조건을 남긴다.

후보가 활성화·재구성·병합·재보류·종료되면 중요한 이력을 지우지 않고 등록부를 갱신한다. Research Case가 개설된 뒤의 자세한 연구 상태는 해당 Research Case record에서 관리하며, 이 등록부가 Research Case를 대체하지 않도록 한다.

## 7. Change Log

### 0.1 — 2026-09-04

- 비규범적 운영 인덱스로 Research Candidate Registry를 생성했다.
- Design Lab이 발견한 뉴스 Evidence 품질과 Processing Coverage 후보를 등록했다.
- 서브에이전트 자동화와 Lab 운영이 충분히 안정된 뒤 연구를 재검토하라는 Project Owner의 지시를 기록했다.
- Research Case 또는 보편적 News Evidence framework를 승인하지 않은 상태에서, 조건 기반 재검토·bounded-audit-first 원칙·임시 guardrail을 명시했다.
