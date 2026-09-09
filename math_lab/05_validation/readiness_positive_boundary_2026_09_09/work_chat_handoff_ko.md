# StockVis Work → Chat Handoff — DailyPrice Positive-Side Boundary Refinement

## Executive Summary

승인된 positive-side refinement를 별도 branch에서 구현했다. 이제 nonfatal 관측과 가격 행 존재를 연구 입력 허용으로 연결하지 않는다. Inventory Permission / Declared-Use Eligibility / Observed Content Status / Research Input Sufficiency를 구별하고, 이번 probe가 내리는 모든 sufficiency는 unassessed로 남긴다. 정상·1행·혼합 사례에서도 research_input_permitted=false와 permitted_symbols=[]를 유지한다. 기존 negative cases 및 F2를 포함한 52개 테스트가 통과했다. F2 코드, recovery addendum, 공통 eligibility gate, 원 candidate와 원 run artifacts는 변경하지 않았다.

## Current Task / Authority

- Work: DailyPrice Positive-Side Boundary Refinement
- Direct authority: 이 세션에서 제공된 사용자의 Next Work 지시
- Parent candidate: ebcc59afc4b5d6919893b083ca2fde066c05d28a
- New branch: math-lab/readiness-positive-boundary-v0.1
- Candidate SHA: 이 문서를 포함하는 candidate commit; 전달본에서 정확한 SHA를 추가한다.
- Original Job / Run: SV-MATH-DP-READINESS-001 / 17239e86-7a44-4077-99e2-0bbbe0852f08
- Original candidate: 1f5fa8420a02fbd683a31d75a5bd8724d78f188c
- State: Candidate / Not Promoted
- New automation run: 없음. 단위·fixture 검증만 수행했으며 실제 관측 run을 생성하지 않음.

## Original Objective / What Was Done

ebcc59af의 positive-side 과잉 표현을 제거한다. 해당 commit으로 새 worktree를 만들어 DailyPrice 결과 schema와 renderer, 관련 테스트만 수정했다. 기존 negative gate는 유지한다. 결과 schema는 daily-price-readiness-result/0.3이다.

## Semantic Contract — Before / After

| 의미 | ebcc59af / v0.2 | 새 candidate / v0.3 |
|---|---|---|
| Inventory / Diagnostic Permission | read-only 세션 확인에 따른 진단 권한 | 동일, 연구 입력 권한과 분리 |
| Declared-Use Eligibility | exploratory_only가 research_input_permitted=true로 연결됨 | 선언 용도의 제한을 나타내는 eligibility. 충분성·사용 권한을 뜻하지 않음을 eligibility_scope로 명시 |
| Observed Content Status | observed_nonfatal_symbols가 허용 종목 목록에 연결됨 | 종목별 observed_content_status와 scope별 요약; 관측 사실로만 기록 |
| Research Input Sufficiency | 별도 평가 상태 없음 | 종목별·선언 용도별 unassessed. 충분하다고 판정하는 경로 없음 |
| 실제 입력 허용 표현 | nonfatal 종목에 true / permitted_symbols 채움 | 모든 결과에서 false / 빈 목록 유지 |

`exploratory_only`는 기존 공통 enum을 유지한 declared-use 제한이다. 이 probe에서 그 값은 충분한 입력 또는 사용 허가가 아니다. `eligibility_scope=declared_use_contract_only_not_sufficiency_or_authorization`와 별도 sufficiency/permission을 함께 출력한다. 공통 `data_eligibility.py`는 수정하지 않았다. 과거의 `usable_for_exploration_but_not_confirmation` reason은 새 결과에서 제거했다.

### Observed content 상태

- not_observed: 관측하지 못함.
- no_price_rows_observed: 조회했으나 해당 가격 행이 없음.
- fatal_observed: 기존 진단이 fatal OHLCV 이상을 기록함.
- nonfatal_observed: 가격 행을 관측했고 기존 fatal 진단이 기록되지 않음. 정상성·정확성·완전성·충분성의 증명이 아님.
- mixed_observed: scope 안에 fatal과 nonfatal 대상이 모두 있음. 개별 종목 상태를 반드시 함께 보존한다.

Scope 요약의 nonfatal_observed는 모든 대표 종목이 관측됐다는 뜻이 아니다. 개별 존재/부재·행 수·관측 상태는 representative_basket에 유지한다. observed_nonfatal_symbols는 관측 목록이며 permitted_symbols는 항상 비어 있다.

### 1-row nonfatal 필수 사례

```json
{
  "observed_content_status": "nonfatal_observed",
  "research_input_sufficiency": "unassessed",
  "research_input_permitted": false,
  "permitted_symbols": []
}
```

이 구조는 1행뿐 아니라 3행·30행 synthetic에서도 동일하다. 이력 길이·최소 행 수·결측률·종목 통과 비율 threshold를 추가하지 않았다. 빈 데이터/fatal 사례도 sufficiency라는 별도 평가 축은 unassessed로 두며, 기존 negative evidence가 선언 용도 eligibility를 차단한다. `unassessed`를 충분 또는 불충분으로 임의 변환하지 않는다.

부분 조회 실패에서는 완료된 representative 관측과 nonfatal 상태를 유지하고 전체 eligibility는 금지한다. 미관측 상태를 가격이 나쁘다는 관측 결과로 취급하지 않는다.

## Tests / Verified Facts

- 52 passed in 0.22s.
- 기존 46개 테스트를 현 의미에 맞게 유지·갱신하고 6개 positive/partial-state 사례를 추가했다.
- Positive: 0/1/3/30행, JSON·Markdown 직렬화, 부분 조회 실패, 미관측의 의미.
- Negative: 빈 가격 데이터, 대표 6종목 모두 fatal, 원 dirty fixture의 금지 유지.
- Normal/mixed: nonfatal 관측 보존, permission=false, sufficiency=unassessed.
- F2: 기존 연결/query/cleanup 및 최종 serialization 정제 회귀 통과. F2 구현과 테스트 내용은 재설계하지 않았다.
- Recovery: 이전 addendum을 재작성하지 않았다. 해당 폴더가 parent 대비 byte-for-byte 변경 없음임을 git diff로 확인했다.
- Shared gate / Research Lab / Lab Automation / 원 .lab_automation 산출물 변경 없음.
- git diff --check 통과.

테스트 환경: Linux Python 3.12.14 / pytest 9.1.1. Django plugin 및 repo pytest.ini를 제외한 독립 단위·SQLite·fake PostgreSQL 실행이다. 실제 Mac/PostgreSQL/production 데이터 검증이 아니다.

```bash
PYTHONPATH=/workspace/scratch/e542666b2021/review-deps \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python -m pytest -c /dev/null --rootdir=. --confcutdir=math_lab/runtime \
  math_lab/runtime/test_data_eligibility.py \
  math_lab/runtime/test_daily_price_readiness.py \
  math_lab/runtime/test_daily_price_boundaries.py \
  math_lab/runtime/test_daily_price_positive_boundary.py -q -p no:cacheprovider
```

## Changes / References

- math_lab/runtime/daily_price_readiness.py — 관측/충분성 분리, positive permission 제거, 부분 관측 유지 및 출력 변경.
- math_lab/runtime/daily_price_probe.py — fallback source version 문자열만 0.3으로 갱신. F2 경로 변경 없음.
- math_lab/runtime/test_daily_price_boundaries.py — normal/mixed 및 negative expectation 갱신. F2 test 부분 유지.
- math_lab/runtime/test_daily_price_positive_boundary.py — 신규 positive-side 회귀 테스트.
- math_lab/05_validation/readiness_positive_boundary_2026_09_09/ — 이번 handoff 및 validation evidence.
- 기존 recovery evidence: math_lab/05_validation/readiness_followup_2026_09_09/recovery_evidence_addendum.json 및 recovery_evidence/ (변경 없음).

## Unresolved / Data Gaps / Impact

1. 실제 DailyPrice 데이터 상태는 여전히 미관측이다. 새 실제 데이터 결함을 발견했다고 주장하지 않는다.
2. Sufficiency 평가 기준과 이를 판정하는 protocol은 미정이다. 새 숫자 기준·PIT·조정주가·배당 의미론·최종 바스켓을 만들지 않았다.
3. 외부 소비자가 있다면 schema v0.3에서 eligibility를 permission으로 변환하지 않아야 한다. 저장소 내 관련 renderer/CLI/test를 갱신했으며 공통 Lab contract를 바꾸지 않았다.
4. 관측 status의 nonfatal은 기존 검사가 fatal을 표시하지 않았다는 제한적 기술이다. 가격 정확성·이상 부재 전부를 보증하지 않는다.
5. 최신 공식 문서 전체 및 Mac의 최신 runner는 이번 작업에서 실시간 확인하지 않았다. 직접 승인된 Next Work 지시 아래 변경을 제한했다.

Founding/Methodology에 새 공식 규칙을 추가하지 않았다. 단일 boolean으로 관측·충분성·권한이 합쳐지는 것을 줄이는 구현이다. 다른 Lab와 공통 Automation에 직접 변경은 없다. F2와 recovery 기록은 기존 검증 상태로 보존한다.

## Why This Returns to Chat / Next Work

요청된 수정·검증·후보 생성이 완료되어 결과를 인계한다. 이번 작업에서 새 의미 결정이 필요한 stop condition은 발견되지 않았다.

다음 단계는 사용자가 지정한 **SV-MATH-DP-OBSERVATION-002의 실제 read-only observation**이다. 실행 기준은 ebcc59af가 아니라 이번 새 candidate여야 한다. 새 Job/Run/Artifact lineage를 사용하고 원 Job 재실행, output 덮어쓰기는 하지 않는다. 실제 관측을 진행해도 sufficiency는 미평가로 남기고 숫자 기준이나 예측·모델·백테스트로 확대하지 않는다.

Mac의 기존 source worktree와 최신 local runner 및 허용된 DB 접근 경로에서 실행해야 한다. 이 Work 환경에는 Mac 경로가 없어 이번에는 live observation을 실행하지 않았다. 제공한 bundle로 새 candidate를 가져온 뒤 현재 local runner contract를 확인하는 것이 실행 준비의 다음 단계다. 권한 확대·production schema·공통 Automation contract 변경 등이 필요하면 원 stop condition대로 Chat에 인계한다.

## Work Recommendation / Options

추천: 수정 결과를 기준으로 OBSERVATION-002의 실행 준비와 제한된 실제 관측으로 진행한다.

Recommendation Strength: Strong.

근거: negative gate를 유지하면서 positive observations를 충분성/권한으로 오독하는 경로를 차단했고 52개 회귀 검증이 통과했다. 실제 데이터 인벤토리가 다음 단계의 주요 미확인이다.

대안: 추가 독립 검토를 먼저 진행할 수 있다. 외부 consumer 또는 기존 공식 계약과의 충돌 우려가 있으면 이 안이 적절하지만 실제 관측 확보가 늦어진다.

추천이 틀릴 수 있는 조건: 미확인 소비자가 exploratory_only를 여전히 실행 권한으로 간주하거나 v0.3을 읽지 못한다면 실제 실행 전에 그 소비 경로를 먼저 검토해야 한다.

## Chat / CEO에 남는 판단

이번 작업에서 새 threshold 또는 sufficiency 정책의 승인을 요청하지 않는다. 새 candidate의 검토 결과를 다음 Work에 전달하며, OBSERVATION-002 실행 과정에 새 권한/의미론 문제가 생기면 그때 구체적인 증거와 함께 판단을 요청한다. Promotion은 이번 실행 지시와 별개로 계속 보류한다.

## Current Safety State

- original candidate ebcc59af modified: false
- original candidate 1f5fa842 modified: false
- original Job / recovery reexecuted: false
- original run artifacts overwritten: false
- F2 implementation redesigned: false
- recovery addendum modified: false
- live observation performed: false
- push / merge / deploy / main modified: false / false / false / false
- external ledger modified: false
- destructive cleanup: false
- new candidate: 별도 branch에서 생성; Mac 반영은 아직 안 됨
- current promotion state: Not Promoted / separate approval required
