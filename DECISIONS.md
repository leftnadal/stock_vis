# StockVis Decisions

## D-RESEARCH-WORK-BOUNDARY — Research Chat/Lab와 Research Work 역할 분리

**Date:** 2026-09-20  
**Status:** Active  
**Owner approval:** Approved by Project Owner

**Decision**

Research Chat/Lab은 연구의 의미·구조·실험 설계·해석과 material한 의사결정을 책임진다. Research Work는 승인된 설계를 구현하고 실험을 실행하며, 실행 중 발생한 기술 결함을 승인 범위 안에서 자율적으로 보완하고 결과를 집계·검증·패키징한다.

Work는 모든 기술 수정마다 Chat 승인을 요청하지 않는다. 새 권한·비용·데이터 전달이 필요하거나 연구 질문·실험 contrast·평가 의미·해석 경계를 바꿔야 하는 경우, 또는 연구 방향을 흔드는 material result/blocker가 있는 경우에만 Chat으로 escalation한다.

**Why**

반복적인 Chat↔Work 인계가 Project Owner를 수동 중계자로 만들고 Research Lab의 연구 설계 집중도를 낮췄다. 공식 Research Methodology도 Research Design과 Investigation을 구분한다. 따라서 연구 의미와 설계를 Chat/Lab에, 승인된 설계의 실행과 기술적 완성을 Work에 두어 책임을 명확히 하고 불필요한 승인 ping-pong을 줄인다.

**Boundary**

이 결정은 기존의 승인되지 않은 모델/API 호출, 유료 비용, private payload 전송, push/merge/deploy 같은 권한을 새로 부여하지 않는다. Research Knowledge admission, 공식 Methodology 변경, 연구 결론의 일반화는 Work가 독자 확정하지 않는다.

## [2026-09-20] D-GUIDE-ANCHOR-DEFER-1031 — 가이드 앵커 유예 2건 기한 연장 [guide][harness][cross-track]

> 출처: MGMT 배치(2026-09-20). 대상 = `guideAnchors.test.ts` `PENDING_ANCHORS`의 `chainsight.backbone`·`dashboard.tabs`.
> 이 항목은 `guideAnchors.test.ts` 주석이 요구하는 **연장 근거 기록**이다. 이 기록 없이 `until`만 바꾸는 것은 금지돼 있다.

**결정**: 두 앵커의 유예 기한을 **2026-09-30 → 2026-10-31**로 연장한다. 연장은 **1회**이며, 재연장은 **소유 트랙의 명시적 요청과 근거**가 있을 때만 한다.

**Why**: ⑴ **둘 다 market_pulse 소관이 아니다** — `chainsight.backbone`은 chain_sight 트랙(`GUIDE-CS-REFRESH` 2단계), `dashboard.tabs`는 dashboard 앱 트랙(`GUIDE-ORPHAN-DASHTABS`, 큐에 "소유: dashboard 앱 트랙" 명시). 해결 ⑴(문구 등재)·⑵(앵커 제거) 모두 남의 트랙 화면을 건드린다. ⑵ 기한을 그대로 두면 **09-30에 그 두 트랙과 무관한 세션까지 guide 스위트 RED로 막힌다** — 트립와이어가 잡으려던 것은 방치이지 무관한 세션이 아니다. ⑶ 연장은 되돌릴 수 있고, 등재·제거는 되돌리기 어렵다.

**측정(2026-09-20)**: `GUIDE-CS-REFRESH` 2단계의 착수 트리거였던 `monorepo/sess-s3s1`(및 `-b`·`-c`)은 **전건 origin/main에 착지 완료** — chain_sight 트랙은 **지금 착수 가능**하다. `GUIDE-ORPHAN-DASHTABS`는 2026-09-10 등재 이후 상태 변화 없음(🔴).

**감수하는 단점**: 6주 연장은 짧지 않다. 그러나 dashboard 트랙이 3주간 무반응이었으므로 **짧은 연장은 같은 결과를 반복할 뿐**이라 보았다. 실효는 기간이 아니라 **통지**에 있다고 판단해, 두 큐 항목에 기한·소유·트리거 상태를 박고 우선순위를 올린다.

**How to apply**: `frontend/__tests__/guide/guideAnchors.test.ts`의 `PENDING_ANCHORS` 두 항목 `until`을 `2026-10-31`로 갱신하고, 각 `why`에 **이 결정 ID와 소유 트랙**을 덧붙인다. TASKQUEUE `GUIDE-CS-REFRESH` 2단계·`GUIDE-ORPHAN-DASHTABS`에 새 기한과 소유를 명시한다.
