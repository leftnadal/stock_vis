# Approval-Gated Promotion Policy v0.1

## 0. 한눈에 보는 요약

StockVis Lab Automation Platform은 agent가 작업을 수행하는 것과 그 결과를 canonical/production 영역으로 승격하는 것을 분리한다.

기본 흐름:

```text
local work
  -> candidate revision
  -> review
  -> PUSH approval
  -> remote branch
  -> PR / evaluation
  -> MERGE approval
  -> main
  -> deployment assessment
  -> DEPLOY approval
  -> production
```

각 승인은 서로 독립적이며 특정 commit SHA에만 유효하다.

## 1. Approval Invariants

1. Push approval은 merge를 허가하지 않는다.
2. Merge approval은 deploy를 허가하지 않는다.
3. 승인 이후 revision SHA가 바뀌면 기존 승인은 무효다.
4. 일반 approval은 force-push main, destructive DB action, secret mutation, production data deletion을 허가하지 않는다.
5. catastrophic health-check failure의 rollback은 사전에 정의된 rollback policy가 있을 때만 자동 허용할 수 있다.
6. rollback은 이전에 승인된 known-good revision으로의 복구만 자동화 대상이 될 수 있다.

## 2. Candidate Revision Package

승인 요청 전 최소한 다음이 있어야 한다.

- exact revision SHA
- changed paths
- test summary
- failed/skipped tests
- data/schema impact
- migration 여부
- security/secret impact
- deployment impact
- risk summary
- result manifest
- recommended next stage

## 3. CEO Attention

CEO는 routine local experiment와 draft 생성을 승인하지 않는다.

기본적으로 CEO approval을 요구하는 것은:

- remote push
- canonical authority promotion
- main merge
- production deploy
- material resource commitment
- cross-Lab constitutional change

운영 경험상 remote push approval이 과도한 병목이 되면 low-risk pre-approved policy를 별도 실험할 수 있으나, v0.1에서는 명시적 승인을 유지한다.

## 4. Deployment Adapter

공통 core는 실제 deployment command를 알지 않는다.

```text
Approval Controller
  -> Deployment Adapter
       -> GitHub Actions / SSH / Docker / cloud CLI / local deploy script
```

StockVis의 실제 deployment mechanism을 local runner가 조사한 뒤 adapter를 연결한다. 배포 방식이 확인되기 전에는 deploy action을 성공한 것으로 기록하지 않는다.
