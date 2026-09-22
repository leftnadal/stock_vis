# Working Record — Judgment–Outcome–Learning Feedback Loop / Checkpoint 16

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-20  
**Topic:** Judgment–Outcome–Learning Feedback Loop  
**Keywords:** synthetic prior record, real record, mechanism isolation, ecological validity, retrieval separation, prior experience, 합성 기록, 실제 기록, 메커니즘 분리, 실제성, 검색 분리  
**Prior Record:** [Checkpoint 14](2026-09-20_judgment-outcome-learning-feedback-loop_14.md)  
**Official Authority:** `leftnadal/stock_vis`, `main/research_lab/`  
**Record Basis:** 사용자의 “좋아 다시 집중하자” 요청, 현재 파일럿 설계 맥락, LongMemEval 및 Reflexion 관련 공개 논문, AI의 단계적 실험 설계 제안. 실행 결과가 아니다.

## Current Question

첫 prior-record utility 파일럿에서 실제 StockVis 과거 기록을 사용할지, 통제된 합성 과거 기록을 사용할지 결정할 필요가 있다. 이 선택은 실험이 무엇을 분리해 말할 수 있는지를 좌우한다.

## Proposal — Synthetic-First, Then Real Records

첫 단계에서는 통제된 합성 prior record를 직접 제공하는 조건을 사용해 “과거 경험을 읽고 현재 상황에 맞게 적용하는 능력”을 분리해 본다. retrieval, indexing, record discoverability, historical formatting, 실제 기록의 불완전성은 첫 단계의 원인에서 제외한다.

두 번째 단계에서 실제 StockVis Working Record를 사전에 선정하여 같은 유형의 과제에 제공한다. 여기서는 실제 기록의 구조·불완전성·맥락 차이 속에서도 transfer가 유지되는지 본다. 여전히 자동 retrieval은 분리한다.

세 번째 단계에서만 INDEX/search/retrieval까지 포함한 end-to-end memory workflow를 비교한다.

이 순서는 아래처럼 주장 범위를 단계적으로 확장한다.

1. **Controlled utilization:** 관련 기록이 제공됐을 때 현재 판단에 적절히 사용할 수 있는가.
2. **Ecological utilization:** 실제 StockVis 기록을 제공해도 그 효과·오적용 패턴이 유지되는가.
3. **Retrieval-inclusive system:** 필요한 기록을 실제로 찾고 전달하는 전체 시스템에서도 이득이 유지되는가.

첫 단계가 실패하면 retrieval 시스템부터 복잡하게 만들 이유가 줄어든다. 첫 단계 성공만으로 실제 memory system의 효용을 주장하지 않는다.

## Synthetic Record Design Boundary

합성 기록을 “입력을 먼저 확인하라” 같은 교훈 한 문장으로 만들지 않는다. 그런 문구는 목표 행동을 직접 노출해 instruction-following을 memory transfer처럼 보이게 할 수 있다.

대신 현실적인 mini record로 구성하는 것을 제안한다.

- 당시 문제와 목적
- 당시 확인된 사실 / 미확인
- 선택한 행동과 이유
- 실제 실행 후 관찰
- 사후 재평가
- 어디까지 일반화할 수 있는지 / 적용 조건
- 당시 unresolved point

현재 문제에 대한 정답 행동을 명령문으로 적지 않는다. 모델이 과거 구조와 현재 조건을 비교해 relevance와 applicability를 판단해야 한다.

동일한 합성 prior record를 적용 필요 / 이미 해소 / 현재 확인 불가의 세 상황에 공통으로 제공하면, “기억을 받았는가”가 아니라 “언제 적용하고 언제 제한하는가”를 볼 수 있다. 다만 이 기록이 이미 개발에 노출되면 held-out evidence로 부르지 않는다.

## Academic Analogy, Not Adoption

Reflexion은 언어적 피드백을 episodic memory에 저장해 이후 시도에 사용하는 접근을 보였지만, StockVis의 연구판단 전이 문제와 동일하지 않다. LongMemEval은 장기기억 시스템을 indexing, retrieval, reading 단계로 분해하고 retrieval 결과 사용 능력과 전체 memory pipeline을 구분해 평가한다. 이 분해는 StockVis에서도 retrieval confound를 뒤로 미루고 utilization을 먼저 보는 논리적 참고가 된다.

StockVis는 QA 기억 회상이 아니라 과거 판단 경험이 “다음 연구 행동”의 적절성을 바꾸는지를 보므로 별도 평가 기준이 필요하다.

## Alternative

처음부터 실제 StockVis Working Record를 쓰면 실제성은 높지만, 기록의 길이·표현·누락·현재 문제와의 유사도·선정 편향이 동시에 들어가므로 결과가 나쁠 때 “경험 적용 실패”와 “record quality 문제”를 분리하기 어렵다.

반대로 합성 기록만 쓰면 통제는 강하지만 실제 기록 활용을 입증하지 못한다. 따라서 synthetic-only가 아니라 synthetic-first → real-record transfer 순서를 추천한다.

## Scope / Next

다음 설계 단계는 첫 합성 prior record의 구체 문안과 세 현재 상황의 입력을 서로 독립적으로 검토해 정답 누수와 적용 조건 편향을 줄이는 것이다. 모델·반복·비용·evaluator 실행은 아직 시작하지 않는다.

이번 제안은 공식 Methodology, memory architecture, Research Work 범위 또는 실제 호출을 변경하지 않는다.

## Sources

- Wu et al., LongMemEval, ICLR 2025: https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html
- Shinn et al., Reflexion, NeurIPS 2023: https://papers.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html
