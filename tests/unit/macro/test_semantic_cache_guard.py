"""
Semantic Cache AnalysisCache 라벨 가드 테스트

검증 항목:
  - AnalysisCache 라벨 미존재 시 'not_initialized' 반환, WARNING 없음
  - AnalysisCache 라벨 존재 시 정상 MATCH 쿼리 실행
"""

import pytest
from unittest.mock import patch, MagicMock


class TestAnalysisCacheLabelGuard:
    """get_cache_stats()의 라벨 가드 검증"""

    @patch('rag_analysis.services.semantic_cache_setup.get_neo4j_driver')
    def test_label_not_exists_returns_not_initialized(self, mock_driver_fn, caplog):
        """라벨 미존재 → status: not_initialized, WARNING 없음"""
        from rag_analysis.services.semantic_cache_setup import get_cache_stats

        # Mock: db.labels() → AnalysisCache 없음 (cnt=0)
        mock_session = MagicMock()
        mock_label_result = MagicMock()
        mock_label_record = MagicMock()
        mock_label_record.__getitem__ = lambda self, key: 0
        mock_label_result.single.return_value = mock_label_record

        mock_session.run.return_value = mock_label_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_driver_fn.return_value = mock_driver

        import logging
        with caplog.at_level(logging.WARNING):
            result = get_cache_stats()

        assert result['status'] == 'not_initialized'
        assert result['total_entries'] == 0
        # MATCH 쿼리 실행 안 됨 (run은 라벨 체크 1회만)
        assert mock_session.run.call_count == 1

        # WARNING 로그 없음
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) == 0

    @patch('rag_analysis.services.semantic_cache_setup.get_neo4j_driver')
    def test_label_exists_runs_match_query(self, mock_driver_fn):
        """라벨 존재 → MATCH 쿼리 정상 실행"""
        from rag_analysis.services.semantic_cache_setup import get_cache_stats

        mock_session = MagicMock()

        # 첫 번째 run: 라벨 체크 → cnt=1
        mock_label_record = MagicMock()
        mock_label_record.__getitem__ = lambda self, key: 1

        mock_label_result = MagicMock()
        mock_label_result.single.return_value = mock_label_record

        # 두 번째 run: MATCH 쿼리 → 통계
        mock_stats_record = MagicMock()
        mock_stats_record.__getitem__ = lambda self, key: {
            'total': 10, 'active': 8, 'expired': 2, 'avg_hits': 3.5
        }[key]

        mock_stats_result = MagicMock()
        mock_stats_result.single.return_value = mock_stats_record

        mock_session.run.side_effect = [mock_label_result, mock_stats_result]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_driver_fn.return_value = mock_driver

        result = get_cache_stats()

        assert result['status'] == 'available'
        assert result['total_entries'] == 10
        assert result['active_entries'] == 8
        assert result['expired_entries'] == 2
        # run이 2회 호출됨 (라벨 체크 + MATCH)
        assert mock_session.run.call_count == 2

    @patch('rag_analysis.services.semantic_cache_setup.get_neo4j_driver')
    def test_driver_none_returns_unavailable(self, mock_driver_fn):
        """드라이버 없음 → status: unavailable"""
        from rag_analysis.services.semantic_cache_setup import get_cache_stats

        mock_driver_fn.return_value = None
        result = get_cache_stats()

        assert result['status'] == 'unavailable'
        assert result['total_entries'] == 0
