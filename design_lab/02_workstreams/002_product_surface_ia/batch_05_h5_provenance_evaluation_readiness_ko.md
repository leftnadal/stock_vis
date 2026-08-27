# Workstream 002 — Batch 05: H5 Architectural Provenance & Evaluation Readiness

> **한국어 Companion 문서**  
> 원문: [`batch_05_h5_provenance_evaluation_readiness.md`](batch_05_h5_provenance_evaluation_readiness.md)  
> 이 문서는 영어 canonical document의 빠른 검토를 위한 한국어 companion이며 독립 authority를 만들지 않는다.

**Source Synced:** 2026-08-28  
**Status:** Working / Evaluation-Readiness Baseline  
**Date:** 2026-08-28  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream-local evaluation frame; Approved Product IA / Design Principle / Lab-wide Evaluation Methodology 아님

## 1. 왜 이 Batch가 필요한가

Batch 04에서 **H5 — Stable Semantic Spaces + Adaptive Reasoning Canvas**가 현재 가장 강한 IA hypothesis로 나왔다. 그런데 CEO feedback을 통해 평가 준비의 중요한 약점이 확인됐다.

> 합성된 architecture는 겉으로 보이는 component와 scenario 장점만 기록했다고 충분히 평가 가능한 것이 아니다. 나중에 H5를 수정하려면 **각 요소가 어디에서 왔는지, 어떤 더 깊은 철학 / 인지 문제를 해결하려는지, source domain에서 무엇은 의도적으로 가져오지 않았는지, 어떤 evidence가 나오면 유지·축소·교체·삭제할지를 추적할 수 있어야 한다.**

따라서 screen-level convergence를 더 진행하기 전에 architectural genealogy와 falsifiable evaluation frame을 먼저 만든다.

### 현재 판단

이 문제 제기는 타당하다. Batch 04는 **divergent prototype comparison**에는 충분했지만, **깊은 causal evaluation 또는 향후 architecture revision**을 하기에는 부족했다.

**Recommendation Strength: Very Strong**

H5는 component별 provenance, counter-hypothesis, failure signal이 명확해지기 전에는 Product IA 방향으로 승격하면 안 된다.

---

## 2. 여기서 사용하는 Evaluation Philosophy

이 Workstream은 Research Lab의 Evaluation Methodology를 Design governance로 복사하지 않는다. 다만 현재 Approved Research methodology에서 다음 discipline을 Design에 맞게 가져온다.

- 평가에는 target, version, purpose, scope, evidence, challenge, limitation, re-evaluation trigger가 있어야 한다.
- 평가는 하나의 score가 아니라 structured characterization이어야 한다.
- uncertainty와 unassessed 영역을 숨기지 않는다.
- preferred interpretation은 competing alternative와 effective challenge를 받아야 한다.
- exploratory discovery는 confirmation이 아니다.
- 평가 기준과 이전 평가 자체도 수정 가능해야 한다.

관련 내부 문서:

- `research_lab/01_methodology/research_methodology.md`
- `research_lab/02_evaluation/evaluation_methodology.md`
- `design_lab/01_operating_system/knowledge_lifecycle.md`

Design으로 옮기면 핵심은 다음이다.

> **H5의 material component는 모두 rationale부터 testable design hypothesis와 reversal condition까지 추적 가능해야 한다.**

---

## 3. Architectural Genealogy Chain

H5는 flat feature list 대신 다음 chain으로 추적한다.

```text
Deep Principle / Philosophy
        ↓
Recurring Cognitive / Decision Problem
        ↓
Source-domain Pattern
        ↓
Transfer Boundary
(무엇은 가져오면 안 되는가)
        ↓
Stock_vis Design Hypothesis
        ↓
H5 Component / Behavior
        ↓
Expected User Effect
        ↓
Counter-hypothesis
        ↓
Observable Failure Signal
        ↓
Retain / Revise / Narrow / Replace / Remove
```

Consequential한 H5 변경에는 최소한 이 reasoning trace가 필요하다.

---

## 4. H5 뒤에 있는 더 깊은 Principle Family

### P1 — Reality / Evidence가 Model을 바꿀 수 있어야 한다

**주요 뿌리**
- Stock_vis Research Lab Scientific Philosophy / Research Methodology
- mental model을 필요하지만 위험한 도구로 보고 계속 challenge하는 intelligence-analysis tradition

**핵심 생각**

Model은 Reality에 의해 수정될 수 있을 때만 유용하다. 정보가 많아진다고 자동으로 판단이 좋아지는 것이 아니며, 정보를 해석하는 frame 자체도 challenge 가능해야 한다.

**H5 implication**
- Evidence, alternative, uncertainty, provenance, revision history는 장식이 아니다.
- System Synthesis를 절대적인 product truth처럼 보이게 하면 안 된다.
- 새 evidence가 현재 Investment View와 미래 assumption을 다시 검토하게 연결되어야 한다.

### P2 — Attention은 희소하고, 좋은 Action 전에 Situation Awareness가 필요하다

**주요 뿌리**
- bounded rationality / limited attention
- Human Factors의 Situation Awareness: 관련 signal 인지 → 의미 이해 → 미래 상태 projection
- incident / operations triage

**핵심 생각**

사용자는 모든 정보를 처리할 수 없다. 좋은 system은 중요한 변화를 발견하고, 그것의 의미를 context에서 이해하며, 행동 전에 미래 영향을 생각할 수 있게 도와야 한다.

**H5 implication**
- Orientation은 단순 Dashboard label이 아니라 독립적인 cognitive function이다.
- Triage는 raw activity가 아니라 maintained View에 영향을 줄 가능성으로 attention을 배분해야 한다.
- adaptive depth는 material uncertainty를 숨기지 않으면서 불필요한 processing을 줄일 때만 정당화된다.

### P3 — Competing Explanation이 Premature Closure를 막는다

**주요 뿌리**
- 임상 differential diagnosis / diagnostic uncertainty
- Analysis of Competing Hypotheses / intelligence analysis
- Research Lab의 competing explanation, contrary evidence, discriminative value

**핵심 생각**

Preferred explanation과 compatible한 evidence라고 해서 강한 evidence는 아니다. Alternative와도 똑같이 compatible하다면 구별 능력이 낮다. 좋은 reasoning은 **어떤 evidence가 실제로 alternative들을 구분하는가**를 묻는다.

**H5 implication**
- ambiguous / high-consequence 상황에서 Differential / competing-scenario lens는 단순 장식이 아니다.
- `다른 설명은 무엇인가?`, `무엇을 보면 둘을 구별할 수 있나?`를 지원해야 한다.
- 하나의 System narrative가 coherent하다는 이유만으로 default truth가 되면 안 된다.

### P4 — Stable Semantic Coordinate가 Cognitive Reorientation을 줄인다

**주요 뿌리**
- IA / wayfinding / predictable interaction
- object-centered operational system
- Research Lab process–object separation과 Design Lab semantic boundary

**핵심 생각**

Content는 변해도 사용자가 자신의 semantic location을 이해하는 좌표는 안정적이어야 한다. Adaptive system이 object / scope / location cue 없이 계속 바뀌면 사용자는 매번 다시 배워야 한다.

**H5 implication**
- `Scope`, `Mode`, active `Question`, provenance, return path가 필요할 때 명확히 보여야 한다.
- Stable space는 transient feature가 아니라 durable semantic responsibility를 가져야 한다.
- News, AI, Evidence, Scenario, Relationship, History는 정말 독립된 persistent meaning이 있을 때만 별도 top-level destination이 된다.

### P5 — Adaptation은 Human Work를 강화해야지 Control을 빼앗으면 안 된다

**주요 뿌리**
- mixed-initiative HCI
- DL-DR-0001 Human–AI Authority Boundary
- uncertainty, predictability, user control, intervention timing을 중시하는 adaptive-interface 연구

**핵심 생각**

Automation은 실제 가치를 더하면서도 사용자가 이해할 수 있는 control을 유지하고, system이 user goal을 확실히 모른다는 사실을 존중할 때 유용하다.

**H5 implication**
- Adaptive Reasoning Canvas가 관련 lens를 조합할 수 있지만 semantic ownership이나 user Judgment를 조용히 바꾸면 안 된다.
- Adaptation은 반복 사용하면서 예측하고 복구할 수 있어야 한다.
- unconstrained generated UI보다 fixed shell + adaptive canvas가 우선한다.

### P6 — Expectation은 시간에 따라 수정되는 Object다

**주요 뿌리**
- forecasting / calibration / revision workflow
- Research Lab predictive claim boundary
- decision postmortem / expectation-vs-reality discipline

**핵심 생각**

Forward belief는 conditional하고 time-stamped된 expectation으로 보고, revise / reaffirm / stale / reality comparison이 가능해야 한다.

**H5 implication**
- Current View / Change / Future Scenario / Outcome-Learning이 서로 연결되어야 한다.
- `검토 후 유지`와 `오랫동안 검토하지 않음`을 구분한다.
- forecast probability, Research credibility, user conviction, investment attractiveness를 섞지 않는다.

### P7 — Understanding / View와 Decision Context는 다른 의미다

**주요 뿌리**
- Approved Research semantic boundary + DL-DR-0002

```text
Understanding
+ Decision Context
→ Judgment
→ Decision
→ Action
```

**핵심 생각**

Company-level Understanding / Investment View와 portfolio-specific Judgment는 같은 object가 아니다.

**H5 implication**
- Decision Context는 distinct semantic responsibility가 필요하다.
- portfolio, valuation, alternatives, horizon, opportunity cost, constraint가 company truth를 조용히 바꾸면 안 된다.
- comparison은 Investment View를 input으로 사용하지만 그것을 overwrite하지 않는다.

---

## 5. H5 Component Genealogy Matrix

| H5 component | 바로 해결하려는 문제 | 주요 뿌리 | Source-domain pattern | 가져오면 안 되는 것 | 핵심 hypothesis | 주요 failure signal |
|---|---|---|---|---|---|---|
| **Orientation** | 제한된 attention 배분 | P2, P1 | portfolio monitoring + incident triage + situation awareness | incident urgency / 공포감 | 모든 것을 열지 않고도 지금 검토할 대상을 찾을 수 있다 | salient noise를 쫓거나 Quiet를 `안전 확정`으로 이해하거나 결국 전부 열어봄 |
| **Investment Workspace** | 회사에 대한 지속적인 view 유지 | P1, P4, P7 | company research hub + persistent object view | enterprise ontology를 그대로 노출하거나 pre-context state를 Judgment라고 부르기 | continuity가 change 해석과 이해를 개선 | 관리 업무가 되거나 anchoring을 만들거나 research가 중복됨 |
| **Explore** | commitment 전에 question/theme/relationship investigation 보존 | P1, P3, P4 | investigation case + object/link exploration | 모든 deep feature를 담는 catch-all 또는 두 번째 Research Lab | 회사 밖 inquiry를 why/provenance와 함께 유지 | Investment와 Explore 경계를 예측 못하고 duplication 증가 |
| **Decision Context** | View와 portfolio-specific constraint 결합 | P7, P1 | portfolio allocation / contextual decision support | 자동 recommendation / execution rule | context를 명시하면 company truth를 훼손하지 않고 Judgment가 명확해진다 | company view와 recommendation을 사용자가 구분 못함 |
| **Adaptive Reasoning Canvas** | 현재 문제에 필요한 reasoning lens 조합 | P5, P2, P4 | mixed-initiative UI + contextual AI | unconstrained generated UI | 불필요한 navigation을 줄이면서 orientation 유지 | 어디에 정보가 있을지 예측 못하거나 AI hierarchy가 정답처럼 느껴짐 |
| **Scope / Mode / Question / Return Path** | Adaptation 중 안정된 좌표 제공 | P4, P2 | wayfinding + predictable UI + situation awareness | 반드시 최종 top-nav label일 필요는 없음 | explicit coordinate가 location awareness와 interruption recovery를 개선 | 사용자가 현재 위치/작업/복귀 경로를 설명하지 못함 |
| **Differential / Competing View Lens** | premature closure 방지 | P3, P1 | differential diagnosis + ACH | 질병처럼 mutually exclusive라고 가정하거나 fake probability ranking | alternative와 discriminating evidence가 challenge quality를 개선 | complexity만 늘고 구별 evidence는 못 찾으며 system narrative가 계속 지배 |
| **Scenario / Future Lens** | conditional future와 growth-path condition projection | P6, P1 | forecasting + scenario planning | probability를 credibility로 보이게 하기 / deterministic default | future comparison과 revision이 좋아짐 | false precision, stale forecast, prediction=attractiveness 혼동 |
| **Triage → Focused Review** | consequence / ambiguity에 맞춰 깊이 조절 | P2, P5 | incident triage + adaptive review | 모든 signal을 task / approval로 바꾸기 | selective depth가 부담을 줄이고 중요한 건 충분히 검토 | focused review가 inbox workload가 되거나 material issue가 숨겨짐 |
| **Provenance / Lineage** | 현재 state가 왜 존재하는지 보존 | P1, P6, P4 | Research provenance + forecast history + incident timeline | first view를 provenance detail로 과부하 | 변화 이유 추적이 correction / learning에 도움 | 평소 전혀 사용하지 않거나 필요할 때 reasoning 복원이 안 됨 |
| **Human–AI authorship separation** | System Synthesis와 user-owned View 구분 | P5 + DL-DR-0001 | mixed initiative + causal user control | visual simplicity를 위해 semantic authorship 제거 | AI가 더 많은 일을 해도 user belief를 조용히 대체하지 않음 | 사용자가 system synthesis를 자기 생각으로 오인하거나 동의 압박을 느낌 |

---

## 6. Batch 04에서 발견한 Evaluation Readiness Gap

Batch 04는 주로 다음을 비교했다.

- 어떤 architecture가 더 많은 scenario를 처리했나?
- navigation이 어느 쪽이 쉬워 보이나?
- context continuity가 어디서 더 강한가?

이건 **comparative exploration**에는 유용하지만 causal evaluation으로는 부족하다.

이유:

1. H5는 여러 idea의 composition이어서 결과가 좋아도 어떤 component가 기여했는지 모른다.
2. Source-domain assumption이 충분히 명시되지 않아 cargo-cult transfer를 잡기 어렵다.
3. locally attractive한 interaction이 더 깊은 philosophy와 충돌할 수 있다.
4. component dependency가 분리되어 있지 않다.
5. user-visible failure signal을 테스트 전에 충분히 선언하지 않았다.
6. H1 / H2는 architecture challenger였지만 H5 내부 요소를 제거하는 **ablation challenger**가 없었다.

따라서 다음 prototype은 `H5가 좋은가?`보다 **각 component와 interaction mechanism이 실제로 필요한가?**를 봐야 한다.

---

## 7. Workstream-Local Design Evaluation Contract v0.1

Material한 H5 experiment마다 다음을 기록한다.

```text
Evaluation Target + Version
+ Intended Cognitive Job
+ Scope / User Context
+ Parent Principle / Genealogy
+ Design Hypothesis
+ Main Challenger / Counter-hypothesis
+ Expected Observable Effect
+ Material Failure Signal
+ Unassessed Areas
+ Test / Evidence Method
+ Re-evaluation Trigger
→ Structured Design Evaluation Result
```

이것은 **Workstream-local**이다. 아직 permanent Design Lab Evaluation Methodology가 아니다.

다른 Workstream에서도 반복적으로 유용함이 확인되면 기존 Knowledge Lifecycle에 따라 promotion을 검토한다.

---

## 8. H5 Evaluation Dimension

### E1 — Semantic / Authority Integrity

- System Synthesis / My Investment View / Decision Context / Judgment / Decision을 필요한 수준에서 구분하는가?
- Adaptive composition이 Research/System output을 user view로 조용히 promotion하지 않는가?
- Explore가 Research authority를 흉내내지 않는가?

**Hard failure:** DL-DR-0001 또는 DL-DR-0002 위반.

### E2 — Orientation & Wayfinding

- 현재 Scope / Mode / Question / return path를 알 수 있는가?
- interruption 후 경로를 처음부터 재구성하지 않고 resume 가능한가?
- feature 이름을 몰라도 어디로 가야 할지 예상할 수 있는가?

### E3 — Attention Allocation

- Orientation이 불필요한 inspection을 줄이는가?
- 왜 prioritize되었는지 이해 가능한가?
- low priority와 `중요하지 않음이 증명됨`을 구분하는가?

### E4 — Sensemaking / Understanding

- 무엇이 바뀌었고 현재 Investment View에 왜 중요한지 설명할 수 있는가?
- evidence를 affected driver / risk / condition과 연결하는가?
- persistent state가 반복 reconstruction을 줄이면서 anchoring은 지나치게 만들지 않는가?

### E5 — Alternative / Challenge Quality

- ambiguity가 material할 때 plausible alternative를 고려하는가?
- alternative를 실제로 구별하는 evidence를 찾는가?
- Differential이 단순 card 증가가 아니라 premature closure를 줄이는가?

### E6 — Future Reasoning & Calibration

- current state / future scenario / scenario condition / outcome을 구분하는가?
- probability / credibility / attractiveness를 구분하는가?
- stale vs reaffirmed expectation을 이해하는가?

### E7 — Adaptive UI Safety

- adaptation이 실제로 irrelevant navigation / detail을 줄이는가?
- 반복 사용 후 예측 가능한가?
- 특정 lens가 왜 나타났는지 이해 가능한가?
- user control / authorship을 보존하는가?

### E8 — Context Transfer & Continuity

- Explore → Investment 전환에서 question / evidence provenance가 유지되는가?
- Investment → Decision Context 전환에서 company View가 변형되지 않는가?
- duplicate copy가 아니라 coherent reference가 되는가?

### E9 — Cognitive Cost / Complexity Budget

- 추가 lens가 complexity를 감수할 만큼 실제 이득이 있는가?
- 단순 H1보다 material하게 나은가?
- expert flexibility를 위해 novice performance가 무너지는가?

### E10 — Learning / Revision Value

- View가 왜 변했는지 나중에 복원할 수 있는가?
- Reality가 나온 뒤 어떤 assumption / scenario / interpretation이 틀렸는지 찾을 수 있는가?
- History가 archival clutter가 아니라 향후 judgment 개선에 쓰이는가?

---

## 9. Challenger / Ablation Set

`H5 vs H1 vs H2`만 보지 않는다.

### C0 — H1 Minimal Challenger
H5 complexity가 정말 필요한지 확인.

### C1 — H5 Full
Stable spaces + Scope / Mode / Question + adaptive canvas.

### C2 — H5 without explicit Mode
Mode가 orientation을 실제로 개선하는지, 아니면 jargon만 추가하는지 확인.

### C3 — H5 with Fixed Canvas
Semantic space는 같지만 question-driven dynamic lens composition이 없음.

Adaptation 자체가 good conventional IA보다 실제로 이득인지 확인.

### C4 — H5 without explicit Explore space
Theme/question investigation을 Orientation / Investment에서 contextual하게 연다.

Explore가 permanent semantic status를 얻을 가치가 있는지 확인.

### C5 — H5 without Differential lens
Ambiguous case에서 competing-explanation structure가 실제 reasoning을 개선하는지 확인.

모든 variant를 한 번에 구현할 필요는 없다. Material hypothesis 하나를 분리할 수 있는 최소 실험을 사용한다.

---

## 10. Evaluation Ladder

### Stage 0 — Semantic / Authority Preflight
User test 전에:
- Research ↔ Design semantic consistency
- authorship boundary
- component genealogy
- contradiction / duplication audit

### Stage 1 — Expert / Persona Adversarial Walkthrough
서로 다른 사고방식을 의도적으로 사용한다.
- discretionary investor / analyst
- trader / fast-monitoring user
- quant / structured-evidence user
- diagnostic-style reasoner
- novice retail investor
- skeptical Design Critic / Accessibility reviewer

목표는 preference vote가 아니라 structural failure 발견이다.

### Stage 2 — Task-level Prototype Test
- 3-minute morning review
- first-time company understanding
- mixed earnings
- theme investigation
- rotation comparison
- mobile interruption / resume

Visual polish 전에 observable navigation / comprehension failure를 본다.

### Stage 3 — Component Ablation
H5 Full과 targeted removal variant를 비교해 complexity가 값을 하는지 확인한다.

### Stage 4 — Judgment-Support Stress Test
- salient evidence가 misleading
- system과 user disagreement
- 두 explanation이 같은 evidence와 compatible
- material evidence missing
- future scenario stale
- company Understanding은 그대로인데 portfolio context만 변화

목표는 investment return accuracy가 아니라 reasoning quality와 semantic boundary다.

### Stage 5 — Longitudinal / Repeated-use Test
이전 단계가 살아남은 뒤에만 수행.

- Investment View continuity가 수주 단위로도 유용한가?
- alert / Focused Review가 workload가 되는가?
- IA를 사용자가 실제로 학습하는가?
- adaptive composition이 점점 예측 가능해지는가?
- provenance / history가 실제 learning value를 주는가?

---

## 11. Philosophy-Mutation Guard

향후 H5를 수정할 때 change를 다음처럼 나눈다.

### Type A — Representation detail
예: card 순서, icon, local disclosure.

Cognitive job / semantic boundary가 그대로면 delegated modification.

### Type B — Mechanism change
예: explicit Scope를 자동 inference로 교체, Differential 제거, Explore를 Investment에 merge.

반드시 확인:
1. 어떤 H5 hypothesis가 바뀌나?
2. 그 mechanism이 어떤 source principle / cognitive problem을 해결하려 했나?
3. 원래 문제가 이제 중요하지 않은가, 아니면 다른 mechanism이 더 잘 해결하나?
4. 새 failure mode는 무엇인가?
5. 어떤 evaluation을 다시 해야 하나?

### Type C — Philosophy / Authority change
예:
- system prediction이 자동으로 user View가 됨
- Decision Context를 company truth와 merge
- 하나의 model이 `best`라는 이유로 alternative 제거
- Adaptive AI가 stable recovery 없이 navigation을 통제

Approved cross-Lab / Human–AI boundary 또는 Design Purpose에 영향을 줄 수 있으므로 local UI iteration이 아니라 escalation한다.

---

## 12. 현재 Evaluation Readiness 판정

### 이 Batch 전

**H5 promotion evaluation을 하기에는 준비가 충분하지 않았다.**

좋은 hypothesis와 cross-domain ingredient는 있었지만 genealogy와 component-level falsification 구조가 부족했다.

### 이 Batch 후

**Controlled H5 prototype evaluation을 시작하기에는 조건부로 준비되었다.**

이제 평가 가능한 것:
- component necessity
- interaction mechanism
- semantic boundary
- wayfinding
- challenge quality
- adaptation safety

아직 주장할 수 없는 것:
- final Product IA
- 실제 투자성과 개선 증명
- novice / expert universal fit
- durable Design Knowledge promotion
- Approved Design Lab Evaluation Methodology

---

## 13. Recommendation

Screen detail convergence를 잠시 멈추고, 다음 prototype을 **제품 mockup이 아니라 evaluation instrument**로 만든다.

다음 prototype에 명시적으로 포함할 것:

1. stable semantic spaces
2. visible Scope / Mode / Question / return path
3. adaptive vs fixed canvas variant
4. 필요 시 Explore-present vs Explore-absent variant
5. ambiguous case의 Differential-present vs absent variant
6. interruption / resume state
7. System / User / Decision Context의 명확한 boundary

**Recommendation Strength: Very Strong**

---

## 14. CEO Critical Decision

**이번 Batch에는 없음.**

이미 승인된 boundary 아래에서 Design Lab의 평가 준비도를 높이는 작업이며 Product IA, Purpose, Human–AI authority를 변경하지 않는다.

---

## 15. Reference Roots

내부 authority:
- `research_lab/01_methodology/research_methodology.md`
- `research_lab/02_evaluation/evaluation_methodology.md`
- `design_lab/01_operating_system/knowledge_lifecycle.md`
- `design_lab/04_decision_records/DL-DR-0001_human_ai_judgment_authority.md`
- `design_lab/04_decision_records/DL-DR-0002_cross_lab_judgment_semantic_boundary.md`

외부 conceptual root:
- Mica Endsley, *Toward a Theory of Situation Awareness in Dynamic Systems* (1995): https://doi.org/10.1518/001872095779049543
- Richards J. Heuer Jr., *Psychology of Intelligence Analysis*: https://www.cia.gov/resources/csi/books-monographs/psychology-of-intelligence-analysis-2/
- Clinical reasoning / uncertainty review: https://pmc.ncbi.nlm.nih.gov/articles/PMC8015765/
- Eric Horvitz, *Principles of Mixed-Initiative User Interfaces* (CHI 1999): https://doi.org/10.1145/302979.303030
- W3C WCAG 2.2 Predictable interaction: https://www.w3.org/WAI/WCAG22/Understanding/predictable.html

Product-pattern source는 Batch 02와 Batch 03에서 계속 관리한다.