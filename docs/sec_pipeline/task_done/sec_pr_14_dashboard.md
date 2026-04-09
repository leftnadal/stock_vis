# SEC-PR-14: Admin 대시보드 + quality_checks

> **완료일**: 2026-04-04

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `sec_pipeline/quality_checks.py` | 7개 체크 + get_dashboard_stats |
| `sec_pipeline/views.py` | sec_pipeline_dashboard (staff_member_required) |
| `sec_pipeline/urls.py` | /admin/dashboard/ URL |
| `templates/admin/sec_pipeline/dashboard.html` | 4-grid 대시보드 |
| `config/urls.py` (수정) | sec_pipeline URL include |

## 7개 품질 체크

| # | 체크 | 임계값 |
|---|------|--------|
| 1 | 수집 실패율 | > 20% |
| 2 | Track B unknown 비율 | > 30% |
| 3 | Ticker 매칭률 | < 30% |
| 4 | 평균 confidence | < 0.5 |
| 5 | 미매칭 큐 적체 | > 100건 |
| 6 | Neo4j dirty 적체 | > 50건 |
| 7 | 섹션 검증 실패 | > 0건 |

## 다음 PR

→ SEC-PR-15: On-demand 수집 + FMP RSS
