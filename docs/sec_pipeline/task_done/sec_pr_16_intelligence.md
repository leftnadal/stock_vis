# SEC-PR-16: Pipeline Intelligence Reporter

> **완료일**: 2026-04-04

## 생성/수정된 파일

| 파일 | 역할 |
|------|------|
| `sec_pipeline/intelligence.py` | PipelineDataCollector (5차원) + PipelineIntelligenceReporter (Gemini) |
| `sec_pipeline/admin.py` (수정) | PipelineIntelligenceReportAdmin (severity_badge, fieldsets, regenerate) |

## Intelligence 리포트 구조

```
PipelineDataCollector → 5차원 메트릭 수집
  ↓
PIPELINE_INTELLIGENCE_PROMPT → Gemini 2.5 Flash
  ↓
PipelineIntelligenceReport (DB)
  - 5차원 점수 (collection, extraction, matching, sync, quality)
  - health_score (종합)
  - severity (healthy/warning/critical)
  - summary, cross_insights, recommended_actions
  - trend_vs_previous (이전 리포트 대비)
```

## 첫 리포트 결과

- **severity**: critical (매칭률 2.7% 때문)
- **health_score**: 0.2
- **핵심 진단**: 매칭 서비스 문제 → 비미국 주식 미등록이 근본 원인
- **권장 조치**: 매칭 큐 분석, 추출 결과-매칭 입력 정합성 확인

## 다음 PR

→ SEC-PR-17: Celery chord 통합 + E2E 테스트
