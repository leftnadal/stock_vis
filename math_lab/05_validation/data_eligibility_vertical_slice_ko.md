# Data Eligibility Gate — Vertical Slice v0.1

**Status:** Experimental / Implementation Candidate  
**Date:** 2026-09-05  
**Branch:** `math-lab/data-eligibility-v0.1`

## 0. 한눈에 보는 요약

Math Lab Constitution의 첫 software enforcement로 Data Eligibility Gate의 최소 구현을 추가했다.

이 Gate는 `데이터가 좋은가?` 또는 `모델이 맞는가?`를 판단하지 않는다. 선언한 연구용도에서 **해당 Data View를 사용할 자격이 있는가**만 판정한다.

현재 구현은 production Django model과 분리되어 있으며, Claude Code의 main 작업을 건드리지 않는다.

## 1. Current Contract

Input은 `DataViewContract`다.

핵심 필드:

- data_view_id
- source_system
- intended_use: exploratory / confirmatory / replication
- availability_confidence: exact / reconstructed / proxy / unknown
- point_in_time_reconstructable
- content_fingerprint
- extraction_version
- universe_version
- entity_resolution_version
- revision_lineage_available
- future_information_known
- known_contamination

Output은 다음 세 상태 중 하나다.

```text
confirmatory_safe
exploratory_only
prohibited_for_declared_use
```

## 2. Current Rules

### Hard prohibition

다음은 declared use와 무관하게 금지한다.

- known future information
- known contamination

### Confirmation / replication minimum

현재 최소 조건은:

- point-in-time reconstructable
- availability confidence가 exact 또는 reconstructed
- stable content fingerprint
- versioned extraction path

### Exploration

위 조건이 부족해도 future information 또는 known contamination이 없다면 `exploratory_only`로 사용할 수 있다.

이 distinction은 발견 능력을 불필요하게 죽이지 않으면서 confirmation의 증거 기준을 보호하기 위한 것이다.

## 3. Deliberate Non-Decisions

v0.1은 아직 다음을 강제하지 않는다.

- revision lineage를 모든 데이터에서 mandatory로 할지
- universe/entity version이 언제 mandatory인지
- fundamental publication delay의 exact rule
- market close / timezone availability rule
- ChainSight edge별 availability contract
- provider별 correction policy
- cost / license eligibility

이들은 adapter와 real-data pilot에서 필요성이 확인될 때 추가한다.

## 4. Unit-Test Scenarios

현재 test file은 최소한 다음을 공격한다.

1. clean confirmatory view
2. unknown availability로 confirmation 시도
3. weak provenance를 exploration에 사용
4. known future information
5. known contamination
6. reconstructed availability
7. missing content fingerprint
8. missing extraction version

## 5. 다음 검증

첫 real-data adapter 후보는 StockVis `DailyPrice`다.

현재 목표는 production schema를 변경하는 것이 아니라:

```text
DailyPrice
→ read-only adapter
→ DataViewContract
→ EligibilityDecision
```

을 만들어 현재 데이터가 어느 수준까지 confirmatory-safe인지 실제로 확인하는 것이다.

이 과정에서 adjusted price, split/dividend, provider vintage, correction lineage가 부족하면 Data Gap / Opportunity로 기록한다.
