# Workstream 002 — Batch 03: Cross-Domain Architecture Generation & Stress Test

**Status:** Working  
**Date:** 2026-08-28  
**Owner:** Stock_vis Design Lab  
**Authority:** Workstream exploration only; not Approved Product IA or Design Knowledge

## 1. Batch Question

> **If Stock_vis IA is generated from structurally similar judgment systems rather than from current financial-product menus, what substantially different product architectures become possible, and which elements survive across realistic investment scenarios?**

Batch 02 created an Idea Pool from investment research/trading, clinical diagnosis, forecasting, intelligence/object systems, incident response, and related decision-support domains. Batch 03 uses those patterns as generative material rather than benchmark decoration.

The goal is deliberately divergent: create architectures with different semantic centers, then attack them with the same scenarios.

## 2. Current Evidence from Source Domains

Recent benchmark signals reinforce several useful distinctions:

- **AlphaSense** now treats Company Profile as a central single-company research hub and lets Generative Search inherit company, dashboard-widget, or selected-document context. It also separates broader Dashboard / monitoring from company deep work. ([Company Profiles](https://help.alpha-sense.com/hc/en-us/articles/42623871994131-Company-Profiles), [Dashboard Gen Search](https://help.alpha-sense.com/hc/en-us/articles/53094515838867-Ask-Questions-About-Your-Dashboard-with-Generative-Search))
- **Koyfin** strongly supports persistent watchlists / portfolios and cross-list alerts, which is useful for coverage and orientation but can become tool-centric if the user must manage many feature-specific views. ([Alerts](https://www.koyfin.com/features/alerts/), [Watchlists](https://www.koyfin.com/features/watchlists/))
- **TradingView** exposes watchlist-wide conditions and alert logic across many symbols, showing the power of a user-defined trigger layer. ([Watchlist Alerts](https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts-your-trading-edge/))
- **VisualDx** explicitly describes a differential that evolves as findings are added or removed, making the relation between evidence and competing possibilities visible in real time. ([VisualDx 2026 update](https://www.visualdx.com/blog/designed-for-the-way-clinicians-think-new-visualdx-enhancements/))
- **Metaculus** allows forecasts to be revised or reaffirmed and preserves time-dependent forecasts; stale forecasts can be withdrawn until revisited. This makes `reviewed and unchanged` different from `not recently reviewed`. ([FAQ](https://www.metaculus.com/faq/))
- **Palantir Foundry** distinguishes central Object Views, exploratory Object Explorer / Quiver, and workflow-specific applications. One semantic object can anchor multiple analyses without every capability becoming a top-level destination. ([Ontology-aware applications](https://www.palantir.com/docs/foundry/ontology/applications))
- **Datadog / PagerDuty** distinguish many signals from a bounded incident investigation, preserve detailed timelines, and increasingly use AI to draft review artifacts while leaving human refinement / governance intact. ([Datadog Incident Investigation](https://docs.datadoghq.com/incident_response/incident_management/investigate/), [PagerDuty AI PIR](https://support.pagerduty.com/main/changelog/ai-powered-post-incident-reviews-in-pagerduty-ui-now-in-early-access))
- **QuantConnect** separates hypothesis generation, research, statistical validation, backtest, paper / live deployment, and post-hoc performance analysis; it also supports comparing live results to simulated expectations. This is a useful analogy for `idea → evidence → test → reality → learning`, but not a direct retail-investment decision rule. ([Research Pipeline](https://www.quantconnect.com/), [Research Guide](https://www.quantconnect.com/docs/v2/cloud-platform/backtesting/research-guide))

These examples do not prove a Stock_vis IA. They provide transferable primitives and failure warnings.

## 3. Common Stress-Test Scenarios

Every candidate architecture is tested against the same six scenarios.

### S1 — Morning Coverage Review
The user has 15–30 holdings / watched companies and three minutes to understand where attention is warranted.

### S2 — New Company Formation
The user encounters a new company and has no prior explicit Investment View.

### S3 — Ambiguous / Mixed Earnings
One event strengthens demand evidence, weakens execution evidence, and increases margin uncertainty.

### S4 — Thematic Exploration
The user begins with `AI power infrastructure` and traverses power, grid, transformer, cooling, data-center and company relationships without yet choosing one company.

### S5 — Forward Comparison / Rotation
The user asks whether IREN should remain in the portfolio or whether NBIS now offers a materially stronger forward opportunity under plausible future scenarios.

### S6 — Human–AI Disagreement / Learning
System Synthesis and the user's Investment View disagree materially. Later reality provides evidence that allows retrospective evaluation of the prior reasoning.

## 4. Architecture Family A — Portfolio Control Tower

### Source inspiration
Trader workflows, watchlists / alerts, incident triage, portfolio monitoring.

### Semantic center
**Coverage set + attention priority.**

```text
Portfolio / Watch Universe
        ↓
Attention Board
  ├─ Review now
  ├─ Monitor
  └─ Quiet
        ↓
Selected company / event
        ↓
Focused Review
        ↓
Decision Context when needed
```

### What it optimizes
- rapid cross-company orientation;
- event / condition triage;
- limited-attention allocation;
- mobile scanability.

### Strengths
- **S1 Morning Review — Very strong.** This is the architecture's natural problem.
- Mixed earnings can become a bounded Focused Review rather than a flood of cards.
- User-defined monitoring rules fit naturally.
- Portfolio users can see attention priority without opening every company.

### Weaknesses
- **S2 New Company — weak to mixed.** A new company has no obvious place unless a separate workspace exists.
- **S4 Theme exploration — weak.** It begins from monitored objects, not open-ended questions or relationship traversal.
- Can over-optimize salience / urgency and turn Stock_vis into an alert inbox.
- Can make `priority` look like `importance is proven` rather than `system currently recommends review`.

### Transfer warning
Use incident-response **triage logic**, not incident-response emotional urgency.

### Current judgment
**Strong component architecture; weak as the whole IA.**

---

## 5. Architecture Family B — Investment Object Workspace

### Source inspiration
Palantir Object Views, AlphaSense Company Profiles, analyst company-workspace patterns.

### Semantic center
**The investment / company object.**

```text
Company / Investment Object
  ├─ System Synthesis
  ├─ My Investment View
  ├─ Changes
  ├─ Evidence / Research
  ├─ Relationships
  ├─ Financials
  ├─ Future Scenarios
  └─ History / Lineage
```

Cross-object Orientation and Decision Context exist around this hub.

### What it optimizes
- continuity of the company-level view;
- deep research without context switching;
- provenance and history;
- contextual AI;
- linking relationships, documents, numbers and scenarios to one persistent object.

### Strengths
- **S2 New Company — Very strong.** The workspace can begin with System Synthesis even before a user view exists.
- **S3 Mixed Earnings — strong.** One event can be mapped back to affected components of the maintained Investment View.
- Strong support for Workstream 001's persistent / revisable company-level state.
- AI can inherit object scope rather than requiring a generic AI destination.

### Weaknesses
- **S1 Morning Review — mixed.** Company-by-company continuity does not solve cross-company prioritization.
- **S4 Theme exploration — mixed to weak** if every exploration must start from a company.
- **S5 Rotation — mixed.** Comparison / capital allocation should not be forced inside one company's workspace.
- Risk of making the company object too dominant and hiding market / thematic structure.

### Current judgment
**Very strong persistent anchor; insufficient alone.**

---

## 6. Architecture Family C — Differential Reasoning Workspace

### Source inspiration
Clinical differential diagnosis, VisualDx / Isabel-style cognitive safety nets, adversarial Research thinking.

### Semantic center
**The unresolved investment problem and competing explanations / futures.**

```text
Problem Representation
        ↓
Competing Views / Scenarios
  A    B    C    D
        ↓
Discriminating Evidence
        ↓
Support / Challenge / Unresolved
        ↓
Updated Investment View
        ↓
Decision Context if action is needed
```

### What it optimizes
- avoiding premature closure;
- showing alternatives explicitly;
- identifying evidence that actually changes the relative plausibility of competing explanations;
- preserving low-probability / high-consequence invalidation paths.

### Strengths
- **S3 Mixed Earnings — Very strong.** Conflicting evidence is not forced into one bullish / bearish conclusion.
- **S6 Human–AI disagreement — Very strong.** System view, user view and alternatives can coexist without manufacturing consensus.
- **S2 New Company — strong.** A first investment case can start as a differential rather than a fixed thesis.
- Strong alignment with Research Lab's preservation of alternatives, uncertainty and non-silent promotion.

### Weaknesses
- **S1 Morning Review — weak.** Differential reasoning is too expensive for every company every morning.
- Can become cognitively heavy for routine monitoring.
- A diagnosis analogy can falsely imply that one explanation must eventually win.
- Any probability-like ranking is unsafe unless Research methodology warrants it.

### Current judgment
**Very strong reasoning lens; unlikely to be a top-level IA by itself.**

---

## 7. Architecture Family D — Forecast & Scenario Board

### Source inspiration
Metaculus, probabilistic forecasting, scenario planning, quant research / expectation-vs-reality workflows.

### Semantic center
**Future questions, scenarios and their revision history.**

```text
Current State
   ↓
Future Questions / Scenarios
   ├─ Base
   ├─ Upside
   ├─ Downside
   └─ Alternative path
        ↓
Enablers / Accelerators / Bottlenecks / Invalidation
        ↓
Expected Growth / Value Outcomes
        ↓
Forecast Revision Timeline
        ↓
Reality / Resolution / Learning
```

### What it optimizes
- forward-looking comparison;
- explicit uncertainty;
- revision of expectations;
- retrospective calibration / learning;
- detecting stale views.

### Strengths
- **S5 Rotation — Very strong.** Relative opportunity is inherently forward-looking.
- **S6 Learning — Very strong.** Prior expectations and later reality can be compared.
- Growth-path conditions fit naturally.
- Reaffirmation provides a useful distinction between active review and stale state.

### Weaknesses
- **S1 Morning Review — weak to mixed** unless only material scenario changes are surfaced.
- **S2 New Company — mixed.** Users may need present understanding before future scenarios.
- High risk of false precision, forecast fetishism or model authority.
- Investment questions often have no clean resolution date or single outcome variable.
- Forecast probability, Research credibility and investment attractiveness must remain separate.

### Current judgment
**Critical future-facing lens; unsafe as the sole product center.**

---

## 8. Architecture Family E — Investigation / Question Workspace

### Source inspiration
Intelligence analysis, Research Lab lifecycle, investigative notebooks / cases, thematic analyst workflows.

### Semantic center
**The question or investigation case.**

Examples:
- `Will power availability remain the binding constraint for AI data-center growth?`
- `Why is IREN underperforming despite strong demand?`
- `Which listed companies benefit most if transformer shortages persist?`

```text
Question / Problem
      ↓
Evidence / Sources
      ↓
Claims / Alternatives
      ↓
Objects / Relationships
      ↓
Research Synthesis
      ↓
Implications for Investment Views
      ↓
Decision Context only if needed
```

### What it optimizes
- **S4 Thematic exploration — Very strong.** The inquiry need not begin from one company.
- cross-company / cross-industry relationship reasoning;
- preserving why evidence was collected;
- reusing Research outputs across multiple Investment Views.

### Strengths
- Excellent fit for ChainSight-like exploration without forcing ChainSight to be a permanent top-level tool.
- Strong support for question-driven AI and deep research.
- Can bridge Research Understanding to multiple investment objects.
- Works well when the user's true starting point is `I need to understand this phenomenon`, not `I need to open company X`.

### Weaknesses
- **S1 Morning Review — weak.** Investigation is too deliberate for routine orientation.
- **S2 New Company — mixed.** Some users want a company overview before they can formulate a useful question.
- Can create project / notebook sprawl.
- Risks duplicating Research Lab semantics if Product starts treating product investigations as Research Knowledge.

### Current judgment
**Strong candidate for an Explore / Investigation space or contextual workspace.**

---

## 9. Architecture Family F — Opportunity Allocation Workspace

### Source inspiration
Portfolio management, buy-side comparison, FactSet-style portfolio analytics, quant research-to-deployment discipline.

### Semantic center
**Relative opportunity under Decision Context.**

```text
Current Portfolio / Opportunity Set
      +
Investment Views / Understanding
      +
Forward Scenarios
      +
Valuation / Constraints / Horizon
          ↓
Relative Opportunity Comparison
          ↓
Judgment
          ↓
HOLD / ADD / REDUCE / ROTATE / WAIT ...
          ↓
Decision / Outcome Review
```

### What it optimizes
- explicit opportunity cost;
- cross-company comparison;
- portfolio concentration / constraints;
- linking analysis to actual capital allocation.

### Strengths
- **S5 Rotation — Very strong.** It directly represents the real investor question `is the difference large enough to reallocate?`
- Portfolio analytics, attribution and risk can become inputs rather than separate disconnected tools.
- Makes `better company` different from `better investment at current price and context`.
- Can support post-decision evaluation of whether the reason for rotation was correct.

### Weaknesses
- **S2 New Company — weak to mixed.** It can push the user toward action before understanding is mature.
- Can turn Stock_vis into recommendation / execution software too early.
- Ranking pressure may collapse uncertainty and asymmetric narratives into one score.
- Decision-support methodology remains partly a Research Trigger, not a Design-owned truth system.

### Current judgment
**Very strong downstream Decision Context architecture; dangerous as the first / universal IA.**

---

## 10. Scenario Stress-Test Summary

`Strong` means the architecture naturally supports the scenario. `Mixed` means it works with extra supporting structure. `Weak` means the architecture fights the user's task.

| Architecture | S1 Morning | S2 New Co. | S3 Mixed Earnings | S4 Theme Explore | S5 Rotation | S6 Disagreement / Learning |
|---|---|---|---|---|---|---|
| A Portfolio Control Tower | Strong | Weak | Strong | Weak | Mixed | Mixed |
| B Investment Object Workspace | Mixed | Strong | Strong | Mixed | Mixed | Strong |
| C Differential Reasoning | Weak | Strong | Strong | Mixed | Strong | Strong |
| D Forecast / Scenario Board | Mixed | Mixed | Strong | Strong | Strong | Strong |
| E Investigation / Question Workspace | Weak | Mixed | Strong | Strong | Strong | Strong |
| F Opportunity Allocation Workspace | Strong | Mixed | Mixed | Mixed | Strong | Strong |

No candidate dominates all scenarios. This is an important result rather than a failure of convergence.

## 11. Strongest Cross-Domain Finding — IA Has Multiple Orthogonal Axes

The failed `one architecture wins everything` competition suggests that Stock_vis IA may be easier to design as a **small semantic grammar** instead of a growing list of features.

Three axes repeatedly appear across domains.

### Axis 1 — Scope / object of attention

```text
Coverage / Portfolio / Universe
↔ Theme / Question / Investigation
↔ Single Investment Object
↔ Comparison / Decision Set
```

These are genuinely different scopes. One screen should not be forced to simulate all four equally well.

### Axis 2 — Reasoning mode

```text
Orient
Explore
Understand / Form View
Monitor / Maintain
Compare
Decide
Review / Learn
```

A user may remain on the same investment object while changing reasoning mode.

### Axis 3 — Time orientation

```text
Past / Lineage
Current State / View
Change
Future Scenarios
Outcome / Learning
```

Time should not be hidden inside separate feature silos such as `News`, `Thesis`, `Forecast`, `History` if those are really views over the same investment reasoning object.

### Implication

Top-level IA should probably encode **stable semantic scope**, while many familiar financial features become **contextual reasoning lenses / capabilities**.

This is stronger than saying `News should not be top level`; it explains *why*.

## 12. Generated Combination Candidates

Rather than choose one borrowed architecture, Batch 03 generates four combination families for later prototyping.

### Combination H1 — Orientation + Investment Object + Decision Context

```text
Orientation
   ↓
Investment Workspace
   ↓ when decision needed
Decision Context
```

Differential, Scenario, Evidence, Relationship, Timeline and AI are contextual lenses inside the workspace.

**Strength:** simplicity and continuity.  
**Risk:** thematic / question-first exploration may still be awkward.

### Combination H2 — Orientation + Investment Object + Explore / Investigation + Decision Context

```text
          Orientation
        /      |      \
Investment   Explore   Decision Context
 Workspace  / Inquiry
```

The same Research / evidence objects may be referenced from Investment and Explore without duplicating authority.

**Strength:** best support for theme-first and company-first journeys.  
**Risk:** Explore may become a second research universe and create navigation complexity.

### Combination H3 — Persistent Workspace + Universal Reasoning Lens Switcher

One persistent context (company, theme, portfolio or comparison set) remains selected while the user switches lenses:

```text
Context: IREN
[View] [Changes] [Differential] [Scenario] [Evidence] [Relations] [History]
```

**Strength:** capability reuse and low nav sprawl.  
**Risk:** a universal switcher may expose too much structure and become another feature toolbar.

### Combination H4 — Question-First Adaptive Workspace

The system starts from `What are you trying to understand / decide?` and composes the relevant scope and lenses dynamically.

Examples:
- `Why did IREN fall?` → Company + Change + Differential + Evidence
- `What benefits from transformer shortages?` → Investigation + Relations + Comparison
- `Should I rotate IREN to NBIS?` → Comparison + Future Scenarios + Decision Context

**Strength:** very close to the user's actual problem.  
**Risk:** AI becomes an invisible router / architect; predictability and learnability may suffer.

## 13. Current Leading Direction

### Recommendation

Do **not** choose D1 vs D2 or a final top navigation yet.

Prototype the semantic grammar itself with at least three substantially different compositions:

1. **H1 — minimal 3-space architecture**
2. **H2 — explicit Explore / Investigation space**
3. **H4 — question-first adaptive composition**

Use H3 as a capability pattern inside prototypes rather than a separate full IA initially.

### Recommendation Strength

**Strong**

### Why

- No source-domain architecture survived every scenario.
- The same durable needs repeatedly recur: orientation, persistent object continuity, alternative reasoning, future scenarios, investigation, and downstream Decision Context.
- The strongest cross-domain insight is not a menu name but the distinction among **scope, reasoning mode and time**.
- Prototyping three different compositions will test whether explicit spaces or adaptive composition better match user mental models.

### Strongest counterargument

A semantic grammar may be intellectually elegant but unnecessarily abstract. A normal financial IA with Dashboard / Company / Portfolio / Discover may be more learnable and easier to ship.

This is a serious alternative. The next prototype should therefore compare not only conceptual coherence but **orientation speed, predictability, number of navigation decisions, mobile burden, and ability to recover from getting lost**.

## 14. What Is NOT Decided

This Batch does not decide:

- final top navigation;
- whether Explore is a permanent top-level space;
- whether a Question Workspace exists as a persistent object;
- whether Differential / Scenario are tabs, overlays, cards or AI-generated views;
- whether Portfolio is a top-level destination or one form of Decision Context;
- whether AI is visible as a destination, panel, omnipresent assistant or background capability;
- final product terminology;
- product schema / ontology;
- prediction probability or rotation methodology.

## 15. Next Batch

Build a **comparative low-fidelity IA prototype** that uses the same scenarios but implements three genuinely different structures:

- **Prototype A — H1 Minimal Three-Space**
- **Prototype B — H2 Explicit Explore Space**
- **Prototype C — H4 Question-First Adaptive Workspace**

Test at minimum:

1. three-minute morning review;
2. first-time company exploration;
3. thematic relationship exploration;
4. mixed earnings review;
5. IREN → NBIS forward comparison / rotation;
6. mobile return / re-orientation after leaving and coming back.

The prototype should surface where the user believes they are, what object / question they are working on, and how easily they can move from understanding to Decision Context without confusing the two.

## 16. CEO Critical Decision

**None in this Batch.**

The Design Lab is deliberately expanding and recombining the idea space. Locking a major IA now would defeat the purpose of the cross-domain exploration.
