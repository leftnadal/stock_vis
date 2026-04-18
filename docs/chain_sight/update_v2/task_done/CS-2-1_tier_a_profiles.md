# CS-2-1: Tier A 프로파일 계산

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

## 결과

| 테이블 | 건수 | 상태 |
|--------|------|------|
| GrowthStage | 480 | ✅ |
| CapitalDNA | 473 | ✅ |
| SensitivityProfile | 503 | ✅ (FMP Revenue Segmentation 200 확인) |
| InsiderSignal | 503 | ✅ (Finnhub Insider 200 확인) |

- Celery task: `calculate_all_profiles` (주간 토요일 02:00)
- API 테스트 결과(decisions/003): FMP Revenue(200), Finnhub Insider(200) → 모두 구현

→ 다음: cs_22
