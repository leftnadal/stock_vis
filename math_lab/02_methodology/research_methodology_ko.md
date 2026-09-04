# Stock_vis Math Lab Research Methodology

**Status:** Working / Active Working Baseline Candidate  
**Version:** 0.1  
**Date:** 2026-09-04  
**Owner:** Stock_vis Math Lab

## 0. 한눈에 보는 요약

Math Lab 연구는 모델 실행이 아니라 **문제 → 시도 집합 → claim → 실험 → 반복검증**의 구조로 관리한다. 연구의 핵심 위험은 미래정보, hidden multiple testing, universe drift, source ancestry, overfitting이므로 이를 기록과 Data Gate로 다룬다.

## 1. Research Program과 Case

### Research Program

장기적인 연구 문제군을 묶는다. 예: `Predictive Information in Equity Relationship Networks`.

### Research Case

하나의 unresolved problem을 operationally 이어가는 container다.

최소 의미:

- Trigger
- Problem
- Research Question
- unit of analysis
- scope
- posture
- related Search Families / Experiments
- current findings
- unresolved gaps
- next action
- revision history

## 2. Fresh Question + Prior Attempt Review

새로운 관점을 보호하기 위해 material Question framing은 먼저 fresh reasoning을 허용한다.

그러나 evidential claim을 만들기 전에는 반드시 prior Attempt Registry를 확인한다.

> **Fresh-first for ideas; registry-required for evidential claims.**

## 3. Search / Experiment Family

하나의 실험만 기록해서는 hidden multiple testing을 알 수 없다. 같은 또는 밀접한 research problem 아래 target, horizon, feature, model, hyperparameter, seed, subgroup, regime를 반복 탐색한 시도는 Search Family로 연결한다.

Family는 다음을 보존한다.

- target variants
- horizon variants
- feature families
- model families
- hyperparameter/search budget
- random seeds
- retries
- failed / aborted / invalid attempts
- holdout exposures
- selection rule

agent별 파일 분산은 family-level evidential history를 소거하지 않는다.

## 4. Candidate Quantitative Claim

Run metric과 claim을 분리한다.

```text
Run Metric ≠ Candidate Quantitative Claim
```

Claim은 최소한 다음 scope를 가져야 한다.

- market / universe
- unit of analysis
- time/frequency
- horizon
- feature / target meaning
- relevant regime or condition
- direction / effect
- uncertainty

한 Run이 Claim 전체를 자동으로 정당화하지 않는다.

## 5. Experiment Protocol

Experiment는 scientific design이다. Run은 protocol을 실행한 instance다.

material protocol은 다음을 명시한다.

- research posture: exploratory / confirmatory / replication
- candidate claim
- prediction target / horizon
- unit of analysis
- universe
- data views
- feature definitions
- model use
- benchmark
- temporal split
- purge / embargo
- primary / secondary metrics
- search budget
- stopping rule
- robustness tests
- failure conditions
- protocol version / freeze state

## 6. Run Record

Run은 최소한 다음을 보존한다.

- protocol version
- code commit
- environment digest
- Data View fingerprint
- configuration / seed
- agent/model/tool version
- terminal status
- metrics
- artifacts
- deviation
- failure
- holdout exposure

`completed`, `failed`, `aborted`, `invalidated`를 모두 기록한다.

## 7. Data Eligibility Gate

material input은 declared use에 대해 먼저 판정한다.

```text
confirmatory_safe
exploratory_only
prohibited_for_declared_use
```

availability confidence는 별도 축이다.

```text
exact
reconstructed
proxy
unknown
```

### Point-in-Time Contract

가능한 경우 다음 시간을 구분한다.

- **effective_time** — 현실의 어느 시점/기간을 설명하는가
- **available_at** — 당시 처음 사용할 수 있었던 시점
- **recorded_at** — Stock_vis에 실제 저장된 시점
- **revision / supersession lineage** — 이후 수정되었는가

현재 값이 과거에도 알려졌다고 가정하지 않는다.

## 8. Specialized Data Views

필요에 따라 일반 Data View를 확장한다.

### Universe View

그 시점의 constituent, IPO/delisting, eligibility를 재구성한다.

### Entity Resolution View

ticker reuse, share class, ADR, merger, spin-off, successor entity를 시간축에서 관리한다.

### Graph Data View

ChainSight 등 network input은 다음을 보존한다.

- graph as-of
- node universe
- entity-resolution version
- edge type / direction
- edge origin class
- edge available_at
- score / aggregation version
- component source refs
- content hash
- leave-one-out rule
- feature lag rule

## 9. Baselines and Controls

복잡한 모델은 단순 baseline을 안정적으로 초과해야 한다.

연구 유형에 따라 다음 control을 고려한다.

- naive / historical mean
- simple momentum / reversal
- linear model
- random / degree-matched graph
- edge permutation
- placebo timing / target
- feature ablation
- source-origin ablation

baseline도 versioned definition을 가진다.

## 10. Confirmation

confirmation은 exploration에서 사용한 tuning logic과 동일 data exposure를 무제한 반복하는 행위가 아니다.

material confirmation은 frozen protocol 또는 predeclared tuning procedure와 protected data를 사용한다.

holdout 확인 후 material redesign이 발생하면 새 confirmation warrant가 필요하다.

## 11. Reproduction과 Replication

### Reproduction

같은 data / code / environment / declared stochastic tolerance에서 결과가 다시 생성되는가.

### Replication

원 실험을 넘어 다른 조건에서도 핵심 claim이 유지되는가.

Replication profile은 다음 독립성을 구분한다.

- Data Independence
- Time Independence
- Universe Independence
- Implementation Independence
- Agent/Researcher Independence
- Model-family Independence
- Source-ancestry Independence

정확한 required count는 현재 Non-Decision이다.

## 12. Result Direction과 Maturity 분리

결과 방향:

```text
positive / null / negative / contradicted / inconclusive / invalid
```

연구 성숙도:

```text
exploration / candidate_pattern / experimental / replicated / validated
```

둘을 하나의 status로 합치지 않는다.

## 13. Data Gap / Opportunity

연구 중 필요한 데이터 부족이나 valuable transformation을 발견하면 정식 proposal을 만든다.

최소 내용:

- research need
- requested data / transformation
- current limitation
- 신규수집 / backfill / 가공 / provenance 개선 여부
- frequency / history / universe
- reusability
- expected API / storage / compute / engineering cost
- alternatives
- priority: Required / High Value / Exploratory
- Lead recommendation

가역적인 작은 가공은 delegated working decision으로 진행할 수 있다. 유료 provider, 대규모 backfill, production schema 대수술, 큰 storage/compute 또는 licensing risk는 CEO Decision Package로 올린다.

## 14. Research Data Layer

장기 방향은 production DB를 직접 연구 근거로 사용하는 대신 얇은 read-only Research Data Layer를 두는 것이다.

```text
Stock_vis / ChainSight Production Data
        ↓
Research Adapter
        ↓
Point-in-Time Data / Graph View
        ↓
Sealed or Reconstructable Export
        ↓
Experiment
```

source schema를 먼저 크게 바꾸지 않는다. 반복 pilot에서 필요한 metadata가 확인된 뒤 upstream 변경을 제안한다.

## 15. Current Non-Decisions

현재 고정하지 않는다.

- exact holdout size / period
- exact p-value threshold
- exact replication count
- exact model family
- exact storage backend
- exact registry DB
- exact YAML/JSON implementation schema
- exact agent count / voting rule
- exact CI platform
- exact production deployment rule
