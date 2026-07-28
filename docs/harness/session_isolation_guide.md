# 세션 격리 규약 — OPS-WORKTREE-ISOLATION (Phase 1)

- 목표: 새 실행 세션이 이 문서를 안 읽어도 **마커·헬퍼·(Phase 2)hook·(Phase 3)verify가 사고를 막는다.** 단, 읽을 문서도 둔다.
- 계보: 동시성 사고 3건(트리 탈취/워커 리셋/미커밋 WIP). 설계 = `design_ops_worktree_isolation_v1.md`(Opt-2). 구현 지시서 = `docs/instructions/ops_worktree_isolation_impl_directive.md`.

## 원칙 (요약)

1. **세션 코드 작업 = 일회용 격리 worktree.** 상주 worktree 금지. 생성·작업·제거.
2. **런타임 트리(sv-worker/web/api-runtime)는 자동화 단독 소유(R1).** 세션이 직접 조작·마커 생성 금지 — 헬퍼가 거부한다.
3. **공유 트리(~/Desktop/stock_vis) 이탈 시 dirty를 전용 브랜치로 wip 커밋**(3차 사고 대책).
4. **통합은 원격 전용 refspec / 격리 worktree merge**(공유 트리에서 main 직접 push 금지 — Phase 2 hook).

## 세션 마커 `.session-marker`

트리 루트의 JSON(`session_id`·`track`·`created_at`[epoch]·`purpose`). 자동화(리셋·rehome)가 존중:
- **신선(<24h)** → 트리 보존(skip + 로그 `marker respected`).
- **stale(≥24h, TTL)** → 경고 + 리셋 진행 + 마커 제거(고아 마커 자기치유).
- **부재** → 현행 동작.

`MARKER_TTL_HOURS`로 임계 조정. 런타임 트리는 예외(마커 있으면 anomaly 경고, 리셋 진행).

## 헬퍼 (Opt-1 흡수)

```bash
bash scripts/wt-open.sh <track> [purpose]   # ~/worktrees/sv-<track> 생성 + 브랜치 monorepo/sess-<track> + 마커
#   ... 작업 ...
bash scripts/wt-close.sh ~/worktrees/sv-<track>   # dirty→wip 프롬프트 → 마커 제거 → worktree 제거
```

- `wt-open`: 런타임 트리 경로 충돌·기존 존재 거부. origin/main 기준 브랜치.
- `wt-close`: dirty면 wip 커밋(전용 브랜치) 프롬프트 후에만 제거 — 미커밋 유실 방지. `--force-wip`로 무프롬프트.

## 라이브러리 API (`scripts/lib/session_marker.sh`, source 전용)

- `marker_respect <tree> <caller>` → `skip|heal|proceed`(stderr 로그). 자동화 리셋 직전 호출.
- `marker_write <tree> <track> [purpose]` / `marker_remove <tree>` / `marker_state <tree>`(0신선/1stale/2부재) / `is_runtime_tree <tree>` / `marker_track <tree>`.

## 자동화 통합 현황

- `worker_sync.sh`: 런타임 3트리에 `marker_respect`(예외 — anomaly 경고만, R1).
- (Phase 2) 공유 트리 git hook: post-checkout 경고 / pre-push·pre-commit 보호브랜치 차단.
- (Phase 3) `verify_pair_aggregation.py` 02:30: 워커트리 drift·stale 마커 인벤토리·코드버전 정합 ALERT.
- ⚠ **nightly(`~/stock-vis-nightly/run_tier*.sh`)는 자기 클론 대상**이라 세션 트리 무접촉 → 마커 존중은 방어적(현 topology상 inert). 향후 rehome이 세션 트리를 건드리면 `marker_respect` 삽입.

## 테스트

`bash tests/ops/test_session_marker.sh` — 신선 skip / stale heal / 부재 proceed / 런타임 거부 / 불량마커 heal.
