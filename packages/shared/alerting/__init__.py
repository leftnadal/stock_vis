"""MP2-ALERTS 알림 코어 (D-ALERTS-BOUNDARY-R1) — packages/shared 신설.

3단 파이프라인(D-ALERTS-ARCH): 트리거(앱) → 디스패처·정책(여기) → delivery port(여기).
shared는 앱 무지 유지 — `apps.*`를 import하지 않는다(아키텍처 AST 가드). 앱별 문구는
registry에 등록된 렌더러가 payload만 받아 생성(BOUNDARY-3 registry 선례 동형).
"""
