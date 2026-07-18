# TRACKS.md — Theme Heat 수동 운용표 (결정38, 2026-07-18~)

> TH beat 3종 `enabled=False`(순수 수동 체제, 임시 — TH-DEPLOY 완료 시 재활성화).
> 실행 위치 = `~/worktrees/sv-theme-heat` + venv `…/stock_javis_system-_jE0wOmK-py3.12` +
> `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES PGGSSENCMODE=disable DJANGO_SETTINGS_MODULE=config.settings`.
> 원장 = 로컬 단일 `stock_vis`(dev 단독). 원장 쓰기는 건별 승인.

## 비활성 beat (결정38)

| beat | 원래 스케줄 | 상태 | 수동 대체 |
|------|-----------|------|----------|
| chainsight-snapshot-analyst-estimates | 금 16:30 ET | **disabled** | 상비 절차 ① |
| chainsight-collect-theme-filings | (주간) | **disabled** | 필요 시 수동 |
| chainsight-theme-heat-daily | 매일 18:00 ET | **disabled** | 상비 절차 ② |

## 상비 절차

**① 주간 EstimateSnapshot (C8)** — 매주 금 16:30 ET 이후(주말 보정 가능):
```
snapshot_estimates_for_symbols(client, get_or_create_universe_snapshot(batch_date=D)[0], D)
```
FMP API 소비. 멱등. **결손=소급불가 → 즉시 상신.** 최근: 2026-07-17 = 997행/499종목/99.6%/eps결측0%.

**② 일간 heat** — `compute_theme_heat(date(Y,M,D))`. DB-only(외부 API 0). 멱등. 롤백=`ThemeHeatScore.objects.filter(date=D).delete()`. 사전 무변경 구간=마커 불요. 최근 원장: 2026-07-13.

**③ 뉴스 집계(C3 입력)** — `aggregate_theme_news_volume()`. ⚠ **override 트랙 코퍼스 동결 중 실행 금지**(G2 완료까지). 동결 해제 후 재개.

## 진행 트랙

- **TH-C3-LLM-DICT-1 (override 적재)** — per-term override 레이어(결정35, 모델+마이그 0024+aggregation 코드 완료·미적용). 30건 판정 확정(A14 none/B5 GICS/C11 FMP+회부). 확정 2×2 82/17/44/72·3분할 89/10/116·G2 92/19/0/0. **쓰기 3단(0024 적용→적재 ovr_v1→재산출 forward-only+마커) 건별 승인 대기.** 코퍼스 동결 유지.
- **TH-DEPLOY** — override 적재 완결 직후 차기 정식 트랙(결정38). 착수 조건 = 쓰기 3단 + G2 검증 완료. worktree→main 병합(39 ahead/277 behind, 0016 마이그 renumber 0016~0024) + 워커 재시동.
