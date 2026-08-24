"""Macro Playbook (1.6-S1 / D-P16-ENGINE) — anomaly와 완전 분리된 별도 모듈.

의미 구분(불변): anomaly = 단일 지표 이상치 발화(boolean). playbook chain = 다신호 합류의
**부분 점등**(lit_count/total) + 서사. 두 체계를 섞지 않는다. anomaly/engine·rules.yaml 무접촉.

저장 = compute-on-read(stress 관례 준용, 스냅샷 모델·마이그레이션 0). 판단·상태·서사는
전부 BE(payload builder)에서 완성 — FE 재판정 0. 문턱값 = v0.1 잠정(S4-REBASE 재산정).
"""
