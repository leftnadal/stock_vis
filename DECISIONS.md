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

