"""apps/platform 은 모델을 정의하지 않는다 (D-P2-S2-PLATFORM).

impression telemetry 데이터 모델 = packages/shared/stocks.ImpressionLog (S1).
platform 은 그것을 소비(write)만 한다 — 의존 방향 platform → shared.
(빈 models.py = makemigrations 산출 0 보장 · 의도 명시로 오해 방지.)
"""
