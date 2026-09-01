"""야간 하네스 건강 점검 에이전트 (OPS-HEALTHCHECK-NIGHTLY-WIRE).

`scripts/health_check.py`를 매일 돌려 결과를 트리 밖에 적재하고, 전일 대비 변화만
메일로 보고한다. dogfood(제품 관점 도그푸딩)와 **완전히 분리된 잡**이다 — 한쪽이
죽어도 다른 쪽 보고가 멈추지 않게 하기 위함(D-HC-NIGHTLY-WIRE, 옵션 A).
"""
