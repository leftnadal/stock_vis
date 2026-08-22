# Stock_vis Design Lab Knowledge Lifecycle

> **한국어 Companion 문서**  
> 원문: [`knowledge_lifecycle.md`](knowledge_lifecycle.md)  
> 이 문서는 영어 원문의 의미를 빠르게 검토하기 위한 한국어 companion이다. 독립적인 authority를 만들지 않는다. 영어와 한국어 사이에 의미 차이가 생기면 관련 CEO-approved semantic intent와 authoritative Design / Research decision을 기준으로 두 문서를 다시 정합시킨다.

**Status:** Working  
**Version:** 0.1  
**Source Version:** 0.1  
**Source Synced:** 2026-08-22  
**Last Updated:** 2026-08-22  
**Owner:** Stock_vis Design Lab  
**Use Status:** Active Working Baseline (Project Owner가 운영 사용 허용)

## 1. Purpose

Design Lab은 모든 exploration, preference, temporary solution을 공식 Design Knowledge로 만들지 않으면서 실제 작업에서 학습해야 한다.

이 lifecycle은 working exploration이 reusable knowledge, 더 강한 Design guidance, 또는 명시적인 Decision Record로 발전하는 방식을 정의하고, revision 가능성을 보존하며 premature formalization을 방지한다.

## 2. Authority Boundary

Research Knowledge는 계속 `research_lab/`에서 governance된다.

Design Lab 문서는 Research Knowledge를 참조하고 그 Design implication을 연구할 수 있지만, Research definition을 복제한 뒤 동일 개념에 대한 독립 authority를 암묵적으로 주장해서는 안 된다.

Design Lab knowledge lifecycle은 Design 측 학습을 다룬다. 예를 들면 user experience, information representation, interaction, design interpretation, design method, pattern, failure mode 및 기타 reusable Design knowledge다.

## 3. Minimal Document Status

Bootstrap 단계에서는 더 강한 lifecycle state가 실제로 필요해질 때까지 의도적으로 작은 document-status vocabulary를 사용한다.

- **Working** — 현재 operating 또는 design baseline으로 사용할 수 있지만 추가 작업과 evidence를 통해 의도적으로 수정 가능
- **Approved** — 명시된 scope 안에서 Project Owner가 durable authoritative Design Lab commitment로 명시적으로 승인

Working 문서는 개념 자체가 final Approved Design Knowledge가 아니어도 **운영상 active하게 사용할 수 있다.** Operational permission과 epistemic / governance maturity는 다른 문제다. 혼동을 줄이기 위해 문서 자체가 Approved status가 아닌 경우 operational-use metadata에서는 `Approved`를 status label처럼 사용하지 않는다.

Superseded, Deprecated, Retired 같은 추가 상태는 실제 lifecycle 필요가 생길 때만 도입한다.

## 4. Default Knowledge States

유용한 최소 lifecycle은 다음과 같다.

```text
Exploration
→ Working Finding
→ Reusable Design Knowledge
→ Principle / Standard when justified
```

이들은 maturity state이며 모든 항목이 반드시 순서대로 통과해야 하는 workflow stage가 아니다. Finding은 더 강한 상태로 승격되지 않아도 된다.

### Exploration

Work 중 생성된 idea, hypothesis, alternative, benchmark, persona simulation, prototype result, critique, unresolved question.

Exploration은 true 또는 reusable하다고 가정하지 않는다.

### Working Finding

현재 workstream을 안내하기에 충분히 유용하지만 아직 provisional한 finding.

Working Finding은 작업이 발전하면서 자유롭게 수정할 수 있다.

### Reusable Design Knowledge

하나의 local decision을 넘어 반복 사용 가치가 입증되어 future Design work에서 discoverable하게 만들 가치가 있는 finding.

Promotion은 보통 다음 중 하나 이상의 근거를 가져야 한다.

- 여러 workstream 또는 scenario에서 반복적으로 유용함
- user 또는 usability evidence
- credible external research 또는 established design evidence
- 반복적인 prototype 또는 stress-test support
- 여러 design problem을 설명하는 explanatory value
- 상위 approved Design / Research constraint와 강한 consistency

### Principle / Standard

Meaningful scope 전반에서 durable consistency가 필요하고 local 또는 optional로 남겨두는 비용이 커질 때만 Principle 또는 Standard를 만든다.

그럴듯하게 들린다는 이유만으로 Principle이나 Standard를 만들지 않는다.

## 5. Workstream은 기본 Exploration Container

새 Design Problem은 보통 Foundation, Principle, Standard가 아니라 Workstream에서 시작한다.

Workstream에는 다음이 포함될 수 있다.

- problem framing
- hypothesis
- desk research / benchmarking
- user 또는 persona perspective
- alternatives
- prototypes
- critique
- experiments
- findings
- unresolved questions

다른 곳에서 더 강한 status가 명시적으로 부여되지 않는 한 Workstream content는 기본적으로 Working이다.

첫 실제 Workstream이 필요성을 만들기 전에는 repository에 workstream directory를 미리 만들 필요가 없다.

## 6. Knowledge Promotion

Promotion은 반복이나 agent consensus의 자동 결과가 아니라 의도적인 judgment다.

Working Finding을 승격하기 전에 Lead는 다음을 검토한다.

- 현재 local implementation을 넘어 유용한가?
- 어떤 evidence가 지지하는가?
- valid scope는 무엇인가?
- 무엇이 이 finding을 falsify, narrow, reverse할 수 있는가?
- 기존 Research 또는 Design authority가 이미 이 개념을 governance하고 있는가?
- formalization이 maintenance cost를 감수할 만큼 future work를 실제로 개선하는가?

이 질문에 충분히 답할 수 없다면 Working으로 유지한다.

## 7. Knowledge와 Decision은 다르다

Design Knowledge는 Design Lab이 무엇을 배웠는지를 설명한다.

Design Decision은 특정 context와 authority 아래에서 여러 가능성 중 중요한 선택을 한 기록이다.

예를 들어 사용자가 uncertainty를 해석하는 방식에 대한 reusable finding은 Design Knowledge가 될 수 있지만, 특정 major navigation architecture를 채택하는 것은 Design Decision이다.

Durable downstream dependency를 만드는 consequential decision은 필요가 생길 때 Decision Record로 남긴다. Minor reversible decision은 보통 formal Decision Record를 만들지 않는다.

## 8. Revision과 Retirement

Design Knowledge는 revisable해야 한다.

새 evidence나 반복되는 failure는 다음 중 하나를 정당화할 수 있다.

- **Retain** — 현재 knowledge가 충분함
- **Revise** — substantial continuity를 유지하면서 의미나 guidance를 수정
- **Narrow** — valid scope를 축소
- **Replace** — 더 강한 model 또는 pattern이 기존 knowledge를 대체
- **Retire** — 현재 사용에 더 이상 적합하지 않음

Material semantic change는 중요한 knowledge의 과거 의미를 조용히 덮어쓰지 않고 explicit하고 traceable해야 한다.

Design concept가 cross-Lab이 되거나 governed Research terminology와 겹치기 시작하면 local renaming으로 해결하지 말고 authority boundary를 검토해야 한다.

## 9. Documentation Economy

> **Save what future agents need to know; do not archive every thought.**

가장 가벼우면서 적절한 documentation 수준을 사용한다.

- future value가 거의 없는 temporary exploration은 저장하지 않아도 됨
- 현재 workstream material은 해당 workstream에 둠
- reusable finding은 필요가 생기면 Design Knowledge에 둠
- Lab-wide long-term commitment는 정당화될 때만 Foundation, Principle, Standard, Decision Record에 둠

Documentation은 future reasoning과 coordination cost를 줄여야 한다. Maintenance cost가 learning value보다 커지면 구조를 재검토한다.

## 10. Lab Evolution과의 연결

Knowledge Lifecycle은 Design work에 적용되고, `evolution.md`는 Design Lab 자체 Operating System에 대한 학습을 governance한다.

두 시스템은 상호작용할 수 있다. 예를 들어 반복되는 design-process failure는 reusable Design Ops knowledge와 Agent Protocol 또는 Operating Model 변경을 동시에 만들 수 있다.
