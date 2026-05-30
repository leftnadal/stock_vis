from unittest.mock import MagicMock, patch

import pytest

from chainsight.services.path_service import (
    _compute_bridge_scores,
    _compute_sector_uniqueness,
    _normalize_rank,
    compute_landmark_scores,
    generate_summary_path,
)


def test_short_path_unchanged():
    assert generate_summary_path(['A', 'B']) == ['A', 'B']
    assert generate_summary_path(['A', 'B', 'C']) == ['A', 'B', 'C']
    assert generate_summary_path(['A', 'B', 'C', 'D']) == ['A', 'B', 'C', 'D']


@patch('chainsight.services.path_service._fetch_centrality')
@patch('chainsight.services.path_service.Stock.objects.filter')
def test_long_path_compressed(mock_filter, mock_centrality):
    mock_centrality.return_value = {
        'B': {'pagerank': None, 'betweenness': None, 'degree': 10},
        'C': {'pagerank': None, 'betweenness': None, 'degree': 15},
        'D': {'pagerank': None, 'betweenness': None, 'degree': 8},
        'E': {'pagerank': None, 'betweenness': None, 'degree': 6},
        'F': {'pagerank': None, 'betweenness': None, 'degree': 7},
    }
    mock_qs = MagicMock()
    mock_qs.values_list.return_value = [
        ('A', 'Tech'), ('B', 'Tech'), ('C', 'Tech'),
        ('D', 'Finance'), ('E', 'Tech'), ('F', 'Tech'), ('G', 'Tech'),
    ]
    mock_filter.return_value = mock_qs

    summary = generate_summary_path(['A', 'B', 'C', 'D', 'E', 'F', 'G'])
    assert summary[0] == 'A'
    assert summary[-1] == 'G'
    assert len(summary) == 4  # 7 nodes -> start + 2 landmarks + end


def test_normalize_rank():
    result = _normalize_rank({'A': 10, 'B': 20, 'C': 30})
    assert result['A'] == 0.0
    assert result['B'] == 0.5
    assert result['C'] == 1.0


def test_normalize_rank_single():
    result = _normalize_rank({'A': 5})
    assert result['A'] == 1.0


def test_bridge_score_center_highest():
    centrality = {
        'B': {'degree': 10}, 'C': {'degree': 10}, 'D': {'degree': 10},
    }
    scores = _compute_bridge_scores(
        middle=['B', 'C', 'D'],
        full_path=['A', 'B', 'C', 'D', 'E'],
        centrality=centrality,
    )
    assert scores[1] > scores[0]
    assert scores[1] > scores[2]


@patch('chainsight.services.path_service.Stock.objects.filter')
def test_sector_uniqueness(mock_filter):
    mock_qs = MagicMock()
    mock_qs.values_list.return_value = [
        ('A', 'Tech'), ('B', 'Tech'), ('C', 'Healthcare'),
        ('D', 'Tech'), ('E', 'Tech')
    ]
    mock_filter.return_value = mock_qs

    scores = _compute_sector_uniqueness(
        middle=['B', 'C', 'D'],
        full_path=['A', 'B', 'C', 'D', 'E'],
    )
    assert scores[1] == 1.0
    assert scores[0] == pytest.approx(0.25)
    assert scores[2] == pytest.approx(0.25)


@patch('chainsight.services.path_service._fetch_centrality')
@patch('chainsight.services.path_service.Stock.objects.filter')
def test_null_centrality_fallback(mock_filter, mock_centrality):
    mock_centrality.return_value = {
        'B': {'pagerank': None, 'betweenness': None, 'degree': 5},
        'C': {'pagerank': None, 'betweenness': None, 'degree': 8},
        'D': {'pagerank': None, 'betweenness': None, 'degree': 4},
    }
    mock_qs = MagicMock()
    mock_qs.values_list.return_value = [
        ('A', 'Tech'), ('B', 'Tech'), ('C', 'Tech'), ('D', 'Tech'), ('E', 'Tech')
    ]
    mock_filter.return_value = mock_qs

    summary = generate_summary_path(['A', 'B', 'C', 'D', 'E'])
    assert summary[0] == 'A'
    assert summary[-1] == 'E'
    assert len(summary) == 3  # 5 nodes -> start + 1 landmark + end
