# DSS-BEAT-1 — DSS 주간 적재 자동화 (beat 태스크 + 폴백 명령)

## 계약 헤더 (요지)
- 트랙: DSS 주간 운영 자동화 / ID: DSS-BEAT-1 / 근거: D-DSS-BEAT-1(병진 승인 08-31)
- worktree ~/worktrees/sv-dss-beat1 · 브랜치 monorepo/sess-dss-beat1
- beat DB 변경 승인(본 지시서) — PeriodicTask 1행 INSERT(enabled=False) → §D 검증 통과 후 enable(2단 스위치)
- W1 docs / W2 code(chain_sight celery 태스크+command+tests·서비스 로직 무수정 래핑만) / W3 DB(PeriodicTask 1행+§D후 enable)
- 커밋: 1=0게이트 → 2=코드+테스트 → 3=(필요시)장부. HALT-0.

## 정본 절차 = 지시서 원문 (§A 태스크+폴백 / §B beat enabled=False / §C push / §D 재시작 상신·2단 스위치)

---

## 집행 결과 (DSS-BEAT-1, 2026-08-31 machine clock)

### STEP 0 (worktree @ origin/main `88326c61`, clock 2026-08-31 14:16 KST)
| # | 결과 |
|---|---|
| 0-1 | health 15 OK / 1 WARN((i) runtime_check 고아 스윕 24h 로그) / 0 ERROR. 신규 (ii)형 0 → HALT 아님 |
| 0-2 | 수집 태스크 = `chainsight-snapshot-analyst-estimates`(PeriodicTask enabled=True·queue=None default·crontab m=30 h=16 dow=5 tz=America/New_York = **Fri 16:30 ET**). EstimateSnapshot created_at 최근 3회(08-28·08-21·08-14 전부 금) = **20:30–20:40 UTC(16:30–16:40 ET, 10분창)**. → **DSS 스케줄 = Fri 19:00 ET**(수집 시작 +2.5h·완료 +2.3h·금요일 한정·18:45 monitor/18:50 advisor 회피). 기존 DSS PeriodicTask 부재 → 신규 |
| 0-3 | 라우팅: `config/celery.py` task_routes = `services.rag_analysis.*`·`services.news.sync_news_to_neo4j`만 neo4j 큐. **chainsight-* = default 큐**(neo4j 격리 아님) → 라우팅 전제 성립(HALT 회피). 워커 = `com.stockvis.celery-worker` @ `sv-worker-runtime`(현 `8cfbcabb` = origin/main 대비 **4 behind stale**·#47 → §D 재시작 상신에 worker_sync 반영). DatabaseScheduler(config/settings.py:507·#28 = PeriodicTask DB 행 정본) |
| 0-4 | dogfood(`auto_agent_system/dogfood/`)에 ThemeDemandScore/사분면 API 신선도 **미포함**(grep 0) → TASKQUEUE AGENT 이관 등재만(구현 금지) |
| 0-5 | 태스크 관례 = `apps/chain_sight/tasks/*.py` + `tasks/__init__.py`에 서브모듈 import 필수. command = `apps/chain_sight/management/commands/`. 테스트 = `tests/chainsight/` |

### 0-6 확정 파일 목록
- NEW `apps/chain_sight/tasks/dss_tasks.py` (celery `load_dss_weekly`)
- MODIFY `apps/chain_sight/tasks/__init__.py` (`from .dss_tasks import *`)
- NEW `apps/chain_sight/management/commands/load_dss_week.py` (폴백 command)
- NEW `tests/chainsight/test_dss_beat.py` (pytest)
- W3 DB: PeriodicTask `chainsight-load-dss-weekly` 1행 INSERT(enabled=False)
