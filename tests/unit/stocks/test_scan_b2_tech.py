"""
SCAN-B2-TECH-BE 단위 테스트 (D-SCANNER-SELECT-UX ②-1).

캘큘레이터 기산출 기술 지표를 tagger 통과 + baker 서피스 (재계산 0·additive).
검증: ① 키 통과 정확성 ② 결측 시 키 생략(정칙 ⑴) ③ 기존 키 무변 회귀
④ 상태 enum 서술형 정합(정칙 ⑵).
"""

import numpy as np
import pandas as pd
import pytest

from packages.shared.stocks.services.eod_signal_tagger import EODSignalTagger
from packages.shared.stocks.services.eod_json_baker import EODJSONBaker


# ── base row(신호 컬럼 최소 + 기술 원천 컬럼) ──────────────────────────
def _row(**over) -> pd.Series:
    base = {
        "symbol": "AAA",
        "close": 98.0,
        "change_pct": 1.2,
        "volume": 1_000_000,
        "dollar_volume": 98_000_000.0,
        "sector": "Technology",
        "industry": "Semiconductors",
        "market_cap": 3_000_000_000,
        # 기술 원천 (calculator 기산출)
        "rsi_14": 72.0,
        "high_52w": 100.0,
        "sma_50": 95.0,
        "sma_200": 90.0,
        "prev_sma_50": 94.0,
        "prev_sma_200": 91.0,
        # 활성 신호 1개(T1) — tag_signals 경로 확보
        "sig_T1": True,
        "sig_T1_value": 72.0,
        "sig_T1_direction": "bearish",
    }
    base.update(over)
    return pd.Series(base)


# ═══════════════ ①④ _build_technical 순수 로직 ═══════════════
class TestBuildTechnical:
    def test_full_values_pass_through(self):
        tech = EODSignalTagger._build_technical(_row())
        assert tech == {
            "rsi": 72.0,
            "rsi_state": "overbought",  # 72 > 70
            "dist_52w_high_pct": 98.0,  # 98/100*100
            "ma_state": "above",        # sma50>sma200, 교차 아님
        }

    @pytest.mark.parametrize("rsi,state", [(25, "oversold"), (50, "neutral"), (85, "overbought"), (30, "neutral"), (70, "neutral")])
    def test_rsi_zones(self, rsi, state):
        tech = EODSignalTagger._build_technical(_row(rsi_14=rsi))
        assert tech["rsi"] == float(rsi)
        assert tech["rsi_state"] == state

    def test_ma_golden_cross(self):
        tech = EODSignalTagger._build_technical(_row(sma_50=95, sma_200=90, prev_sma_50=89, prev_sma_200=90))
        assert tech["ma_state"] == "golden_cross"

    def test_ma_dead_cross(self):
        tech = EODSignalTagger._build_technical(_row(sma_50=88, sma_200=90, prev_sma_50=91, prev_sma_200=90))
        assert tech["ma_state"] == "dead_cross"

    def test_ma_above_below(self):
        assert EODSignalTagger._build_technical(_row(sma_50=95, sma_200=90, prev_sma_50=94, prev_sma_200=90))["ma_state"] == "above"
        assert EODSignalTagger._build_technical(_row(sma_50=85, sma_200=90, prev_sma_50=86, prev_sma_200=90))["ma_state"] == "below"

    def test_dist_52w(self):
        assert EODSignalTagger._build_technical(_row(close=95, high_52w=100))["dist_52w_high_pct"] == 95.0

    # ② 결측 시 키 생략 (정칙 ⑴)
    def test_all_missing_returns_none(self):
        tech = EODSignalTagger._build_technical(_row(
            rsi_14=np.nan, high_52w=np.nan, sma_50=np.nan, sma_200=np.nan,
            prev_sma_50=np.nan, prev_sma_200=np.nan,
        ))
        assert tech is None

    def test_partial_missing_omits_keys(self):
        # RSI만 존재, 52주/MA 결측 → rsi 키만
        tech = EODSignalTagger._build_technical(_row(
            high_52w=np.nan, sma_50=np.nan, sma_200=np.nan, prev_sma_50=np.nan, prev_sma_200=np.nan,
        ))
        assert set(tech.keys()) == {"rsi", "rsi_state"}
        assert "dist_52w_high_pct" not in tech
        assert "ma_state" not in tech

    def test_high_52w_zero_omitted(self):
        tech = EODSignalTagger._build_technical(_row(high_52w=0))
        assert "dist_52w_high_pct" not in tech

    def test_ma_partial_prev_missing_omits(self):
        tech = EODSignalTagger._build_technical(_row(prev_sma_200=np.nan))
        assert "ma_state" not in tech


# ═══════════════ ①③ tag_signals 통합 ═══════════════
class TestTagSignalsIntegration:
    def test_technical_surfaced(self, tagger):
        out = tagger.tag_signals(pd.DataFrame([_row()]))
        assert len(out) == 1
        assert out[0]["technical"]["rsi"] == 72.0
        assert out[0]["technical"]["ma_state"] == "above"

    def test_technical_omitted_when_missing(self, tagger):
        out = tagger.tag_signals(pd.DataFrame([_row(
            rsi_14=np.nan, high_52w=np.nan, sma_50=np.nan, sma_200=np.nan,
            prev_sma_50=np.nan, prev_sma_200=np.nan,
        )]))
        assert "technical" not in out[0]  # 정칙 ⑴ — 키 자체 부재

    def test_existing_keys_unchanged(self, tagger):
        """기존 item 키 전건 보존(additive) — technical 외 회귀 0."""
        out = tagger.tag_signals(pd.DataFrame([_row()]))[0]
        for k in ("stock_id", "signals", "tag_details", "signal_count", "bullish_count",
                  "bearish_count", "composite_score", "close", "change_pct", "volume",
                  "dollar_volume", "sector", "industry", "market_cap"):
            assert k in out
        assert out["stock_id"] == "AAA"
        assert out["market_cap"] == 3_000_000_000
        # 신설은 technical 단 하나
        assert set(out.keys()) - {
            "stock_id", "signals", "tag_details", "signal_count", "bullish_count",
            "bearish_count", "composite_score", "close", "change_pct", "volume",
            "dollar_volume", "sector", "industry", "market_cap",
        } == {"technical"}


# ═══════════════ ③ baker _build_preview_stock 서피스 ═══════════════
class TestBakerSurface:
    def _baker(self):
        baker = EODJSONBaker()
        baker._company_name_cache = {"AAA": "Alpha Inc"}  # DB 우회
        return baker

    def _item(self, **over):
        item = {
            "stock_id": "AAA",
            "signals": [{"id": "T1", "value": 72.0, "direction": "bearish", "label": "RSI 72 (과매수)"}],
            "sector": "Technology",
            "industry": "Semiconductors",
            "close": 98.0,
            "change_pct": 1.2,
            "volume": 1_000_000,
            "dollar_volume": 98_000_000.0,
            "market_cap": 3_000_000_000,
            "composite_score": 0.4,
            "news_context": {},
        }
        item.update(over)
        return item

    def test_surfaces_technical_when_present(self):
        item = self._item(technical={"rsi": 72.0, "rsi_state": "overbought", "ma_state": "above"})
        prev = self._baker()._build_preview_stock(item, "T1")
        assert prev["technical"] == {"rsi": 72.0, "rsi_state": "overbought", "ma_state": "above"}

    def test_omits_technical_when_absent(self):
        prev = self._baker()._build_preview_stock(self._item(), "T1")
        assert "technical" not in prev  # 기존 키 무변 회귀

    def test_existing_preview_keys_unchanged(self):
        """technical 부재 시 기존 preview 키셋 완전 동일(회귀 0)."""
        prev = self._baker()._build_preview_stock(self._item(), "T1")
        assert set(prev.keys()) == {
            "symbol", "company_name", "sector", "industry", "close_price",
            "change_percent", "volume", "dollar_volume", "market_cap",
            "composite_score", "signal_value", "signal_direction", "signal_label",
            "news_context", "mini_chart_20d", "chain_sight_cta",
        }
