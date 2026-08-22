# Stock_vis Design Lab Agent Protocol

> **한국어 Companion 문서**  
> 원문: [`agent_protocol.md`](agent_protocol.md)  
> 이 문서는 영어 원문의 의미를 빠르게 검토하기 위한 한국어 companion이다. 독립적인 authority를 만들지 않으며, 의미 차이가 있을 경우 영어 원문을 기준으로 해소한다.

**Status:** Working  
**Version:** 0.1  
**Last Updated:** 2026-08-20  
**Owner:** Stock_vis Design Lab  
**Operational Use:** 2026-08-20 Project Owner가 working bootstrap baseline으로 운영 사용 승인

## 1. Purpose

이 protocol은 Design Lab Lead가 Design Lab을 고정적이고 관료적인 agent 조직으로 만들지 않으면서 specialist agent perspective를 어떻게 구성하고 사용하는지를 정의한다.

목적은 agent 수를 최대화하는 것이 아니다. 하나의 Design Problem을 잘 탐색하고, 설계하고, 비판하고, 통합하는 데 필요한 **최소한의 서로 다른 관점**을 확보하는 것이다.

## 2. 언제 Specialist Agent를 사용하는가

단순하고 local한 작업은 Lead가 직접 처리할 수 있다.

다음 중 하나 이상이 필요할 때 Specialist Agent가 특히 유용하다.

- 서로 다른 domain 또는 user perspective
- 폭넓은 research 또는 benchmarking
- 복수의 plausible design alternative
- IA, interaction, visualization, content, accessibility, prototype 같은 specialized work
- independent critique 또는 adversarial review
- persona 또는 scenario stress-test
- Research Lab consistency review
- Lead의 탐색 범위가 너무 일찍 좁아지는 것을 막기 위한 parallel exploration

Agent 사용 자체가 목적이 아니라 exploration과 judgment의 질을 높이기 위한 수단이다.

## 3. Dynamic Composition

Design Lab은 permanent roster의 specialist agent를 요구하지 않는다.

Lead가 문제에 맞춰 task-specific role을 구성한다. 유용한 기본 질문은 세 가지 기능 중 무엇이 필요한지 보는 것이다.

### Explore

관련 reality, user behavior, constraint, prior art, benchmark, possibility, alternative framing을 발견한다.

임시 역할의 예: User Research, Product Strategy, Competitive Research, Domain Research, Persona Simulation.

### Design

문제를 structure, interaction, representation, content, prototype 또는 기타 design artifact로 번역한다.

임시 역할의 예: Information Architecture, Interaction Design, Visualization, UX Writing, Visual Design, Design System, Prototype.

### Challenge

현재 framing이나 proposal이 실패할 이유를 찾는다.

임시 역할의 예: Design Critic, Accessibility Review, Adversarial Persona, Research Liaison, Consistency Review, Failure-Mode Analysis.

이 명칭들은 기능적 보조도구이며 영구적으로 governance되는 job title이 아니다.

## 4. Minimum Useful Team

Lead는 의미 있게 다른 관점을 제공하는 가장 작은 team을 선호한다.

Agent 수가 많다고 confidence가 자동으로 높아지지 않는다. 중복 agent는 false consensus, 높은 synthesis cost, 반복 reasoning을 만들 수 있다.

Low-consequence task에는 하나의 specialist perspective만으로 충분할 수 있다. 주요 architectural 또는 semantic work에서는 proposal과 critique를 분리하여 독립적으로 challenge하는 것을 기본적으로 고려한다.

## 5. Agent Task Brief

Specialist Agent는 전체 Design Lab을 다시 해석하지 않고도 독립적으로 일할 수 있을 만큼의 context를 받아야 한다.

유용한 brief에는 필요에 따라 다음을 포함한다.

- **Problem** — 무엇을 이해하거나 설계하거나 challenge해야 하는가
- **Context** — 필요한 최소 Stock_vis / Research / Design / user / product context
- **Goal** — agent가 만들어야 할 구체적인 결과
- **Constraints** — approved Purpose, Principles, authority boundaries, scope limits, requirements
- **Authority References** — semantic precision이 필요한 경우 관련 `research_lab/` 또는 `design_lab/` source
- **Expected Output** — Lead synthesis에 유용한 결과의 형식과 깊이

이미 authority가 존재하는 공식 Research 또는 Design 개념에 대해 agent가 새로운 의미를 만들어서는 안 된다.

## 6. Output Contract

Agent output은 synthesis할 수 있을 만큼 간결하고 challenge할 수 있을 만큼 명시적이어야 한다.

유용한 항목은 다음과 같다.

- Key Findings
- Evidence / Observations
- Alternatives
- Risks / Failure Modes
- Recommendation
- Confidence or Uncertainty
- Open Questions

모든 task가 모든 항목을 요구하지는 않는다. Lead는 template 완성을 강제하기보다 task에 맞춰 contract를 조정할 수 있다.

## 7. Exploration과 Critique

중요한 작업에서는 proposal을 만든 agent 또는 perspective만이 그 proposal을 평가하도록 두지 않는다.

유용한 pattern은 다음과 같다.

```text
Explore
→ Design / formulate alternatives
→ independent Challenge
→ Lead synthesis
```

Critique는 필요에 따라 assumption, missing evidence, user failure mode, accessibility, Research consistency, long-term dependency, alternative explanation을 공격적으로 검토한다.

목적은 disagreement 자체가 아니다. Commitment 전에 confirmation bias를 줄이고 consequential weakness를 노출하는 것이다.

## 8. Persona와 Synthetic Stress Test

Persona simulation은 서로 다른 goal, experience level, portfolio context, attention constraint, decision situation에서 design model이 실패하는지를 탐색하는 데 사용할 수 있다.

Synthetic persona는 exploratory instrument이지 user evidence가 아니다.

따라서 synthetic persona test의 finding은 real user observation, stronger evidence, repeated design validation 등으로 뒷받침되기 전까지 hypothesis 또는 failure candidate로 취급한다.

## 9. Research Liaison

Task가 Research Knowledge에 material하게 의존하거나 Research 의미를 변경할 위험이 있다면, Lead는 비싼 rework를 피할 수 있도록 충분히 이른 단계에 Research consistency check를 포함해야 한다.

Research Liaison은 Research 개념을 재정의하지 않는다. 관련 Research authority와 Design interpretation의 정합성을 확인하고 conflict 또는 Research Trigger Candidate를 surface한다.

## 10. Agent Authority

> **Agent output is input, not authority.**

Agent agreement는 evidence, validation, approval과 동일하지 않다.

Design Lab Lead가 agent output을 비교하고, disagreement를 해소하거나 보존하고, higher-level constraint를 확인하고, 최종 synthesis를 만드는 책임을 가진다.

Consequential decision은 Operating Model의 Decision Tier와 escalation rule을 따른다.

## 11. Protocol Evolution

Agent composition, task brief, output contract, critique timing, synthesis 방식이 반복적으로 friction을 만든다면 Design Lab Evolution process를 통해 protocol을 수정한다.

일회성 inconvenience는 즉시 영구 규칙을 만들기보다 local하게 처리하는 것을 기본으로 한다.
