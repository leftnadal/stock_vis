# MGMT-BATCH-B — 브랜치·worktree 분류 보고 (read-only)

> 세션 종류: **관리(mgmt) · 읽기 전용** · 코드 변경 0 · 삭제 0 (D-BRANCH-DELETE-MANUAL 준수 — 후보만 보고)
> 측정 시각: 2026-09-03 (세션 진행 중) · 산출물 = 이 보고서 + 하네스 부기

---

## §0 세션 헤더 · baseline · 충돌/미발견 사항

**계약 헤더**
- 세션 종류 = mgmt / read-only
- 범위 = 로컬 브랜치·worktree 전수 분류 보고 (삭제·정리 미집행)
- baseline origin/main = **`1d528a6e`** (fetch 후 측정. 로컬 `main`도 동일)
- ⚠ 재개 문서의 baseline `eb3cdd85`는 **stale** — origin/main이 그 뒤 **14 커밋 전진**(다른 세션 착지분). `eb3cdd85`는 origin/main의 조상 확인 = **되감김 아님**(§6 HALT 조건 해당 없음).

**지시서-하네스 충돌 / 특이사항 (등재 여부 = 디렉터 결정)**
1. **★ 세션 worktree 이상 — 착지 경로 미상 (디렉터 처분 요청)**: 이 세션은 전용 mgmt worktree가 아니라 **메인 worktree `/Users/byeongjinjeong/Desktop/stock_vis`가 `monorepo/sess-signal-fwd-recon`(cca67275, **08-10**) 로 체크아웃된 상태**에서 구동됨. 이 브랜치는 origin/main보다 **821 커밋 뒤처짐**·NOT-MERGED·dirty=20(관심 docs untracked). 지시서 §5는 "정상 착지 절차대로 커밋+착지"를 요구하나, ⓐ 이 stale 피처 브랜치에 mgmt 보고서를 얹는 것은 무관 작업 혼입, ⓑ 여기서 main 착지는 stale 브랜치발(發) **공유 main 접촉**(Gate4급·명시 승인 필요·[[feedback_deploy_approval_explicit_quote]]). → **보고서는 scratchpad에 영속화**하고 착지 경로·위치는 **디렉터 처분 대기**. (하네스 우선 원칙 §0.6 적용.)
2. **health_check 시작 ❌ 2건 = stale worktree 아티팩트 (실패 아님)**: `origin/main 해시`·`PROGRESS 갱신 stale` 두 ERROR는 모두 이 worktree HEAD(cca6727)가 origin/main(1d528a6)보다 뒤처진 데서 발생 — health_check 자체가 `실행 트리 정합 WARN: HEAD≠origin/main`으로 원인을 명시. 프로덕션/런타임 실패 아님 → **원인 파악 완료, §6 HALT 해당 없음**.
3. **BATCH-A 전용 보고서 미발견**: `MGMT-BATCH-A_classification.md` 파일 없음. "MGMT-BATCH-A" 문자열은 하네스 파일(DECISIONS/PROGRESS/TASKQUEUE/common-bugs)에만 존재. → **"이전 판정" 열은 문서 흔적 기반으로만 기재**, 전용 4건 분류표는 미발견.
4. **반복성 함정 후보 (common-bugs 1줄 후보)**: `git worktree list --porcelain`의 HEAD는 **명령 시점 캐시** — 세션 초와 중반 사이 런타임 트리 HEAD가 `8489b2d0`→`1d528a6e`로 바뀜(세션 구동 sync가 중간에 돎). 측정은 **동일 시점 스냅샷**으로 묶어야 정합. (bash `IFS=$'\t' read`가 탭을 whitespace로 취급해 빈 필드 붕괴 → awk `-F'\t'` 필수. 이건 measure 스크립트 함정.)

**디렉터 처분 반영 (옵션 2 조건 (a)~(f) 집행 결과)**

5. **착지 경로 확정 (옵션 2)**: `git worktree add ~/worktrees/sv-mgmt-b -b monorepo/sess-mgmt-b origin/main`로 **origin/main 기준 전용 mgmt 트리 생성**. 현재 트리(sess-signal-fwd-recon, dirty)는 **미접촉**(checkout/stash/reset 0). 이 트리 `docs/mgmt/`에 보고서 착지.
6. **★ baseline 라이브 드리프트**: 측정 스냅샷은 `1d528a6e`, 착지 시점 origin/main = **`04ec8bf7`**(+추가 전진, EVT-CHAIN-1 랜딩 등). 다른 활성 세션이 실시간으로 브랜치·worktree를 바꾸는 중 → **분류표는 `1d528a6e` 스냅샷 기준**이며, 그 이후 신규분은 §2-D에 별도 격리. **삭제 실행 전제 = 모든 CC 세션 종료 + 활성 목록 재측정**(조건 d).
7. **조건 (c) 사유 재대조 결과 (origin/main 04ec8bf7 기준·08-10 트리 미사용)**: 보류 8건 사유 **전부 현행 확인** — research-os/research-lab(TASKQUEUE)·review-tool(TASKQUEUE §215 수요게이트)·news-vocab(DECISIONS/TASKQUEUE)·sec-pipeline-tests×2(**PROGRESS 550-551** "main 흡수 검증 보류"). 판정 갱신 1건: **`sess-rehome-graph` = 아크 RESOLVED**(TASKQUEUE "NT-REHOME-GRAPH resolved 2026-07-03"·DECISIONS D-REHOME-GRAPH·명시적 전달 브랜치 `3ddcb7b`) → 검토필요 유지하되 Q8 정밀화(잔여 drop-migration 파일이 main에 있는가). 모든 판정은 `git show origin/main:…`로 대조 — **이 트리의 08-10 판 하네스로 판정한 항목 없음**.

---

## §1 첫 sync 검증 (1-A)

| 항목 | 관측 | 판정 |
|---|---|---|
| 런타임 트리 HEAD (worker·web·api) vs origin/main | 세션 초 `8489b2d0`(behind) → 세션 중반 **`1d528a6e` = origin/main 동일** | ✅ 세션 구동 sync가 돌아 **behind 해소** (초기엔 잔존이었으나 자기수복) |
| `~/Library/Logs/stockvis/deploy_history.log` | **존재·3줄**, 마지막 `2026-09-03T11:10` (worker `9caf9e37→8489b2d0`, web/api `35a1550b→8489b2d0`) | ✅ **부트스트랩 공백 이미 통과** — 신버전 worker_sync.sh가 일지 기록 중 |
| worker_sync.sh 신버전 여부 | deploy_history 기록·health_check 자동 실행 정황 = **신버전 활성** | ✅ 신버전 |
| sync 후 health_check 자동 실행 | 신버전 활성 정황 확인 | ✅ |

→ 재개 문서 3번(방어 장치 최종 검증) **전반부 완료**: 런타임 behind 해소 + deploy_history.log 생성·기록 확인. D-DEPLOY-PATH-1 방어 4종 라이브.

---

## §2 브랜치 분류표

**전수 225 브랜치** (main 제외). 요약: **즉시삭제 159 · 즉시삭제(wt선행) 42 · 보류 8 · 검토필요 15 · 유지 1**.

판정 명령(브랜치별): `git merge-base --is-ancestor <b> origin/main` (MERGED) · `git cherry origin/main <b> | grep -c '^+'` (main에 내용 없는 커밋 = cherry+) · `git rev-list --left-right --count origin/main...<b>` (behind/ahead) · worktree 부착 여부.

### §2-A NOT-MERGED 22건 (실제 미머지 내용 보유 — 개별 조사 대상)

| 브랜치 | 마지막 커밋 | cherry+ | beh/ah | WT | 소속 아크·상태 (출처) | 이전판정 | 이번 분류 | 근거 |
|---|---|---|---|---|---|---|---|---|
| **monorepo/sess-signal-fwd-recon** | cca67275 08-10 | 7 | 821/8 | WT(메인) | SIGNAL-FORWARD (이 세션 체크아웃 트리) | — | **유지** | 이 세션 worktree·dirty=20 |
| monorepo/sess-hub-recon | f039decb **09-03 11:56** | 1 | 9/1 | WT | HUB-V02-RECON 허브 v0.2 재료조사 (커밋 메시지) | — | **검토필요** | **오늘 커밋 = 활성 세션 가능성** (Q1) |
| design/stock-data-inspector-v0.1 | 1826fb88 **09-03 11:36** | 1 | 14/1 | WT | read-only stock data inspector (design/ 네이밍=monorepo 규칙 이탈) | — | **검토필요** | **오늘 커밋 = 활성 가능성**·네이밍 이탈 (Q2) |
| monorepo/sess-r2pre | 9bc85fff 08-31 | 1 | 101/1 | WT | R2 사전작업. R2-S2 랜딩됨(`d54b15a2`) | — | **검토필요** | R2-S2에 흡수됐나·잔여 거버넌스 1커밋 (Q3) |
| monorepo/sess-eodsig-freshgate | d1a2b43e 08-31 | 2 | 109/2 | WT(sess-main-integrate) | EODSIG-FRESH-GATE. 배포·확증 완료(`d0114efc`). MEMORY="오염 브랜치 방치" | — | **검토필요** | A2 importlib 잔여 2커밋·**통합트리 점유** (Q4) |
| monorepo/sess-cn-repair-land | f72c0c3a 07-30 | **0** | 675/1 | WT | C-N-REPAIR 야간배치. C-N 백필 122/122 완결 | — | **검토필요** | **squash-merge**(cherry0=내용 main에)·`-d` 거부됨→`-D` 필요 (Q5) |
| monorepo/sess-hold-p1 | b8d767aa 07-24 | 5 | 821/6 | — | Monitor HOLD-P1(mig0008) 랜딩. sess-signal-fwd-recon의 계보 공유 | — | **검토필요** | 5커밋 main 흡수 확인 필요 (Q6) |
| monorepo/research-os-governance | 74a2e775 07-23 | 2 | 821/2 | WT | Research OS Phase 1·RSH-001 진행·ADR-001 approved·미push (MEMORY) | — | **보류** | 살아있는 재사용 사유(RSH-001 완주 대기) |
| monorepo/sess-phase3-drift | 96542c9b 07-22 | 1 | 806/1 | WT | Phase 3 drift 수리 STEP 0→**HALT**(커밋 메시지) | — | **검토필요** | HALT된 recon·재개/폐기 미결 (Q7) |
| monorepo/research-lab-foundation | 6973bda3 07-21 | 1 | 821/1 | — | research lab foundation (research-os와 한 쌍) | — | **보류** | research-os 재사용 사유에 종속 |
| monorepo/sess-rehome-graph | 3ddcb7bb 07-03 | 1 | 1281/1 | — | **NT-REHOME-GRAPH RESOLVED**(D-REHOME-GRAPH)·명시적 전달 브랜치(TASKQUEUE/DECISIONS) | — | **검토필요** | 아크 종결이나 잔여 drop-migration 1커밋 main 존재 확인 필요 (Q8) |
| monorepo/sess-mgmt | 5a4ce8e9 07-02 | 4 | 1625/8 | — | NT-P1-DELEGATE 위임기록 (구 범용 mgmt) | — | **검토필요** | 오래된 범용 mgmt·4커밋 미상 (Q9) |
| monorepo/nightly-20260619 | bf613df7 06-20 | 1 | 1444/1 | — | nightly 코드베이스 감사 보고서(자동) | — | **검토필요** | nightly 감사 1커밋·폐기 가부 (Q10) |
| monorepo/nightly-20260618 | b77635b8 06-19 | 1 | 1446/1 | — | nightly 코드베이스 감사 보고서(자동) | — | **검토필요** | 동상 (Q10) |
| monorepo/sess-news-vocab | cc918c40 08-06 | 1 | 494/1 | WT(dirty=1) | NEWS-VOCAB v1 완결 트랙·`cc918c40` 미push (MEMORY) | — | **보류** | 미push 완결 + worktree dirty |
| monorepo/sess-news-auth | ebc51b33 06-15 | 2 | 1545/2 | WT | NEWS-AUTH → rebase로 main 흡수(`a4c1cc4`, PROGRESS) | — | **검토필요** | 잔여 2커밋=append-only 메타인가 (Q11) |
| monorepo/sess-cleanup-l2-worktree | 573af006 08-06 | 1 | 500/1 | — | CLEANUP-L2-WORKTREE (chainsight L2 evidence) | — | **검토필요** | 흡수 여부 미상 (Q12) |
| monorepo/sess-mgmt-nt11-stray-guard | 02942460 06-07 | 4 | 1584/4 | WT | NT-11 완료대기검증·NT-11b 분리등록 | — | **검토필요** | 4커밋 미상·완료 여부 (Q13) |
| iron-trading-api | 9ca8b478 05-26 | 1 | 1750/1 | — | iron-trading Codex 핸드오프. `docs/trading_bot_api/` 최근 추가(untracked) | — | **검토필요** | **별 프로젝트·활성 트랙 가능성** (Q14) |
| monorepo/sess-review-tool | 90de95be 08-01 | 3 | 645/3 | WT | REVIEW-TOOL-V6-IMPROVE 등재(**수요 게이트**, TASKQUEUE) | — | **보류** | 문서화된 대기 사유(수요 게이트) |
| test/sec-pipeline-tests | e12c71ae 05-18 | 1 | 1823/1 | — | sec_pipeline 미흡수 단위테스트·**흡수검증 보류**(TASKQUEUE) | (5/12 stale base 삭제 시 보존) | **보류** | 문서화된 흡수검증 보류 |
| test/sec-pipeline-tests-20260519 | ac588d3c 05-19 | 1 | 1818/1 | — | sec_pipeline 미흡수 단위테스트(별파일)·흡수검증 보류(TASKQUEUE) | 동상 | **보류** | 문서화된 흡수검증 보류 |

### §2-B MERGED + worktree 부착 44건 (내용 main 흡수·worktree 정리 선행)

- **즉시삭제(wt선행) 42건** (clean·worktree 제거 후 `git branch -d` 안전): `sess-rc-inc, sess-evt-7, sess-agent-s2, sess-mgmt-b46, sess-newsfix-be, nightly-20260902, sess-d1-close, sess-r2s2, sess-mgmt-b45, sess-newsfix-sync, sess-ops-hc-wire, sess-eodsig-obs, sess-ops-pgbackup, sess-mgmt-b43, sess-mgmt-b42, sess-ops-guard-s1, sess-mig-bundle-1, sess-mgmt-b41, sess-ops-watchdog-web, sess-mgmt-b40, sess-eodsig-deploy, sess-close-0831, sess-quad-impl1, sess-guide-s1, sess-mgmt-btriage1, sess-scan-b2fe, sess-rc-a0-recon, sess-swap-close, sess-scan-b2tech, sess-scan-b1, sess-coach-scb, sess-evt-0, sess-mgmt-coach-ckpt, sess-coach-fe-recon, sess-mgmt-split-close, sess-s2b1-shared, sess-split-deploy, sess-s2b1-fe, sess-s2b1-be, sess-split-guard, sess-s2b1, sess-mgmt-cleanup-script`
  - 지시서 §2 지목분 확인: **split 아크 3건**(sess-mgmt-split-close·sess-split-deploy·sess-split-guard) = 전부 MERGED clean → 삭제 가능. **sv-coach-fe-recon**(sess-coach-fe-recon) = MERGED clean → stale 판명 재확증, 삭제 가능. **sv-coach-scb**(sess-coach-scb) = MERGED(82843eea main 흡수)·**D1-SCOREBOARD 아크 09-02 종결로 재사용 사유 소멸** → 삭제 가능. **sv-d1-close**(sess-d1-close) = MERGED(eb3cdd85)·D1 종결 → 삭제 가능.
- **보류 2건** (MERGED이나 worktree dirty → worktree 선정리 필요): `sess-mgmt-b44`(dirty=4), `sess-ops-plist-tree`(dirty=1)

### §2-C MERGED + worktree 미부착 159건 (즉시삭제 — `git branch -d` 안전)

내용 전부 main 흡수(ancestor)·worktree 미부착 → `-d`로 안전 삭제. 전량 목록은 명령 초안(Block B1) 참조.
- **nightly-* 75건**: `nightly-20260620` ~ `nightly-reports`·`nightly-audit-20260602` (자동 스냅샷)
- **sess-* 84건**: sess-evt-corr3b, sess-evt-6/4/1, sess-evt-corr3, sess-agent-s1/-land, sess-rca1-lesson, sess-decreg-0827, sess-mps1/2-stress-*, sess-boundary-llm(-core/-closeout), sess-regen-v2, sess-20*(2/2d/2e/2f/leaderboard/17-ego), sess-mon-timing-p1/p2/p25, sess-mgmt-batch5/9/10/11/12, sess-health-blocked-build, sess-impr-*, sess-C-core-l2, sess-dash-s3, sess-16-graph-grounding, sess-platform-*, sess-CN-news-backfill, sess-fmp-testdebt, sess-forward-survey, sess-mgmt-(harden/d2destale/p2d1/p2s2reg/xapp-rule/flush/flush3/ledger/ledger-s3/v1-decision/v2/kl-close/phase1-*/nt7-close), sess-eventgroup-window, sess-shared-p2impr-s1, sess-A-spy-restore, sess-B-analog-card, sess-pf-test, sess-s4, sess-b1-*, sess-cd-read, sess-cd-stab-aprime, sess-news-av-broad, sess-rehome-graph-code, sess-mp-vixstale(-step0), sess-iron-latest-date, sess-sector-hist-be, sess-fred-backfill, sess-ux-s1~s5(census/timeline/flowbands), sess-market_pulse (외)

### §2-D baseline(`1d528a6e`) 이후 신규 — 오늘 활성 세션 (04ec8bf7 시점·전량 검토필요)

> 다른 활성 세션이 스냅샷 이후 생성/전환. 전부 이미 MERGED(cherry 0)이나 **오늘 활성 트리** → 삭제 후보 아님. **삭제 실행 전제 = 모든 CC 세션 종료 후 재측정**.

| 브랜치 | 마지막 커밋 | merged | WT | 분류 | 근거 |
|---|---|---|---|---|---|
| monorepo/sess-mgmt-b | 04ec8bf7 09-04 | Y | sv-mgmt-b | **유지** | **이 세션 것**(착지 트리) |
| monorepo/sess-evt-8 | 45eba56e 09-03 19:04 | Y(behind1) | sv-evt-1 | **검토필요(오늘활성)** | EVT-CHAIN-1 → origin/main 랜딩(04ec8bf7). worktree sv-evt-1이 sess-evt-7→8 **브랜치 전환**(활성 증거) (Q15) |
| monorepo/sess-agent-s21 | 04ec8bf7 09-03 | Y | sv-agent-s21 | 검토필요(오늘활성) | 신규 worktree·clean·활성 |
| monorepo/sess-s3s1 | 04ec8bf7 09-03 | Y | sv-s3s1(dirty2) | 검토필요(오늘활성) | 신규·dirty·활성 |
| monorepo/sess-s3pre | 1d528a6e 09-03 | Y | sv-s3pre(dirty3) | 검토필요(오늘활성) | 신규·dirty·활성 |
| monorepo/sess-v02s1-trustfix | a4dc21b5 09-03 17:34 | Y | sv-v02s1 | 검토필요(오늘활성) | HUB-V02-S1 신뢰수리·신규·활성 |
| monorepo/nightly-20260903 | 04ec8bf7 09-03 | Y | stock-vis-nightly/repo | 유지(자동화) | 당일 nightly·자동화 인프라 트리 점유 |

부수 영향: 스냅샷의 `sess-evt-7`은 worktree(sv-evt-1)가 sess-evt-8로 전환돼 **worktree 미부착**으로 바뀜 → MERGED noWT = 즉시삭제로 재분류(단, 삭제 전 재측정 전제).

---

## §3 worktree 분류표

**스냅샷(1d528a6e) 61 worktree**: 즉시정리 43 · 보류 12 · 유지 6. **드리프트(04ec8bf7) 후 66 worktree**: 신규 5(sv-mgmt-b 유지 + 활성 4 보류). **현행 요약: 즉시정리 43 · 보류 16 · 유지 7**.

### 유지 7 (스냅샷 6 + 이 세션 신규 1)
| 경로 | 브랜치 | 사유 |
|---|---|---|
| /Users/byeongjinjeong/worktrees/sv-mgmt-b | **sess-mgmt-b** | **이 세션 착지 트리(신규·origin/main 04ec8bf7 기준)** |
| /Users/byeongjinjeong/Desktop/stock_vis | sess-signal-fwd-recon | 이 세션 구동 트리(⚠ stale·§0-1·Q16) |
| /Users/byeongjinjeong/Desktop/sess-main-integrate | sess-eodsig-freshgate | 공유 통합 트리([[lesson_shared_main_worktree_holds_other_session_merge]]) — ⚠단, 부착 브랜치=검토필요 (Q4) |
| /Users/byeongjinjeong/stock-vis-nightly/repo | nightly-20260902 | nightly 자동화 인프라 |
| /Users/byeongjinjeong/worktrees/sv-worker-runtime | (detached 1d528a6e) | 런타임 배포 트리 |
| /Users/byeongjinjeong/worktrees/sv-web-runtime | (detached 1d528a6e) | 런타임 배포 트리 (dirty=2=빌드산출물) |
| /Users/byeongjinjeong/worktrees/sv-api-runtime | (detached 1d528a6e) | 런타임 배포 트리 (dirty=1=빌드산출물) |

### 보류 12 (dirty 또는 부착 브랜치 NOT-MERGED)
| 경로 | 브랜치 | dirty | 사유 |
|---|---|---|---|
| /Users/byeongjinjeong/worktrees/sv-mgmt-b44 | sess-mgmt-b44 | 4 | dirty (미커밋 변경) |
| /Users/byeongjinjeong/worktrees/sv-ops-plist-tree | sess-ops-plist-tree | 1 | dirty |
| /Users/byeongjinjeong/worktrees/sv-news-vocab | sess-news-vocab | 1 | dirty + 브랜치 보류 |
| /Users/byeongjinjeong/Desktop/stock_vis_design_inspector | design/stock-data-inspector-v0.1 | 0 | 브랜치 검토필요(오늘 커밋) |
| /Users/byeongjinjeong/Desktop/stock_vis_news_auth | sess-news-auth | 0 | 브랜치 검토필요 |
| /Users/byeongjinjeong/Desktop/stock_vis_nt11 | sess-mgmt-nt11-stray-guard | 0 | 브랜치 검토필요 |
| /Users/byeongjinjeong/worktrees/sv-cn-repair-land | sess-cn-repair-land | 0 | 브랜치 검토필요(squash) |
| /Users/byeongjinjeong/worktrees/sv-hub-recon | sess-hub-recon | 0 | 브랜치 검토필요(오늘 커밋) |
| /Users/byeongjinjeong/worktrees/sv-phase3-drift | sess-phase3-drift | 0 | 브랜치 검토필요(HALT) |
| /Users/byeongjinjeong/worktrees/sv-r2pre | sess-r2pre | 0 | 브랜치 검토필요 |
| /Users/byeongjinjeong/worktrees/sv-research-os | research-os-governance | 0 | 브랜치 보류(RSH-001) |
| /Users/byeongjinjeong/worktrees/sv-review-tool | sess-review-tool | 0 | 브랜치 보류(수요게이트) |

### 보류 — 신규 활성 4 (드리프트분, 스냅샷 12에 추가 → 현행 16)
| 경로 | 브랜치 | dirty | 사유 |
|---|---|---|---|
| /Users/byeongjinjeong/worktrees/sv-evt-1 | sess-evt-8 | 0 | **오늘 활성**(sess-evt-7→8 전환) |
| /Users/byeongjinjeong/worktrees/sv-agent-s21 | sess-agent-s21 | 0 | 오늘 활성(신규) |
| /Users/byeongjinjeong/worktrees/sv-s3s1 | sess-s3s1 | 2 | 오늘 활성·dirty |
| /Users/byeongjinjeong/worktrees/sv-s3pre | sess-s3pre | 3 | 오늘 활성·dirty |
| /Users/byeongjinjeong/worktrees/sv-v02s1 | sess-v02s1-trustfix | 0 | 오늘 활성(신규) |

(※ sv-evt-1은 스냅샷에선 sess-evt-7 부착 즉시정리였으나 브랜치 전환으로 보류 재분류. 신규 worktree 4 + 재분류 1 = 보류 +5, 단 sv-evt-1은 스냅샷 즉시정리에서 이동이므로 순증 표기상 활성 5건.)

### 즉시정리 43 (clean·부착 브랜치 MERGED 또는 detached·ref손실0)
Block A 명령 초안 참조. 포함: 42개 MERGED+clean worktree(§2-B) + detached 무브랜치 **sv-monitor-rebuild**(df9591f9)·**sv-dash-s0**(5afab5fe). detached 2건은 브랜치 ref 없어 제거 시 손실 0. **단 sv-evt-1은 드리프트로 보류 이동** → 삭제 실행 시 재측정 필수.

---

## §4 병진 수동 실행용 명령 초안 (실행 금지 — D-BRANCH-DELETE-MANUAL)

> 순서: **Block A(worktree 제거) → Block B2(그 브랜치 -d) → Block B1(미부착 브랜치 -d) → Block C(원격)**. 모두 `-d`(소문자) — 거부 시 HALT·`-D` 자가전환 금지. squash-merge인 `sess-cn-repair-land`은 §6 Q5 확인 후에만.
> 전량 = scratchpad `cmd_A_worktree.txt`(43) / `cmd_B1_branch_noWT.txt`(159) / `cmd_B2_branch_wt.txt`(42) / `cmd_C_remote.txt`(5).

**Block C — 원격 브랜치 삭제 (MERGED 확인 5건·공유상태 변경·최종 승인 요)**
```
git push origin --delete monorepo/sess-mgmt-b46
git push origin --delete monorepo/sess-newsfix-be
git push origin --delete monorepo/sess-r2s2
git push origin --delete monorepo/sess-mgmt-b45
git push origin --delete monorepo/sess-newsfix-sync
```
(로컬 즉시삭제류 중 자기 원격ref 보유·원격도 MERGED 확인분만. 그 외 로컬 브랜치의 원격은 이미 `[gone]`이거나 origin/main 추적이라 대상 아님.)

---

## §5 요약 카운트

**브랜치 (스냅샷 1d528a6e·전수 225)**: 즉시삭제 159 + 즉시삭제(wt선행) 42 + 보류 8 + 검토필요 15 + 유지 1 = **225 ✓**
**브랜치 드리프트(04ec8bf7)**: +신규 6(유지 1=sess-mgmt-b·유지-자동화 1=nightly-903·검토필요-오늘활성 4=evt-8/agent-s21/s3s1/s3pre/v02s1 중 5건 §2-D) → **브랜치 유지 총 2**(signal-fwd-recon + mgmt-b)
**worktree (스냅샷 61)**: 즉시정리 43 + 보류 12 + 유지 6 = 61 → **드리프트 후 66**: 즉시정리 43 + 보류 16 + **유지 7**
**원격 삭제 후보**: 5 (전부 MERGED 확인)

---

## §6 검토필요 — 병진 답변 필요 질문

- **Q1** `sess-hub-recon` (오늘 09-03 11:56 커밋) — **진행 중 활성 세션인가?** 아니면 HUB-V02-RECON 종료본인가?
- **Q2** `design/stock-data-inspector-v0.1` (오늘 09-03 11:36) — 활성 작업인가? design/ 네이밍(monorepo 규칙 이탈) 의도적?
- **Q3** `sess-r2pre` 잔여 1커밋(FE-DEPLOY 거버넌스)이 R2-S2에 흡수됐나, 별도 보존 가치 있나?
- **Q4** `sess-eodsig-freshgate` A2 importlib 잔여 2커밋이 main 흡수분과 별개인가? 이 브랜치가 **공유 통합 트리 sess-main-integrate를 점유** 중 — 통합 트리를 main/다른 브랜치로 재지정할까?
- **Q5** `sess-cn-repair-land` = squash-merge(내용 main에·`-d` 거부). **`-D` 강제 삭제 승인하는가?**
- **Q6** `sess-hold-p1` 잔여 5커밋 — main 흡수 확인되나? (sess-signal-fwd-recon과 계보 공유)
- **Q7** `sess-phase3-drift` = HALT된 recon. 재개 예정인가, 폐기인가?
- **Q8** `sess-rehome-graph` 잔여 1커밋(drop-migration) 아크 상태·처분?
- **Q9** `sess-mgmt` 잔여 4커밋(구 범용 mgmt) 폐기 가부?
- **Q10** `nightly-20260618`·`nightly-20260619` 감사 보고서 1커밋 — 폐기 가부? (나머지 nightly는 이미 main 흡수라 즉시삭제)
- **Q11** `sess-news-auth` 잔여 2커밋 = append-only 메타(NEWS-AUTH는 `a4c1cc4`로 rebase 흡수됨)인가?
- **Q12** `sess-cleanup-l2-worktree` 잔여 1커밋(chainsight L2 evidence) 흡수 여부?
- **Q13** `sess-mgmt-nt11-stray-guard` 잔여 4커밋·NT-11 완료 여부? (자기 원격ref 보유)
- **Q14** `iron-trading-api` = 별 프로젝트(iron-trading, `docs/trading_bot_api/` 최근 추가). **활성 트랙인가?** (`sess-iron-latest-date`도 관련 — 단 그건 MERGED)
- **Q15** (드리프트) `sess-evt-8`·`sess-agent-s21`·`sess-s3s1`·`sess-s3pre`·`sess-v02s1-trustfix` = 오늘 활성 세션. **진행 중 세션 종료됐는가?** (전부 MERGED이나 삭제는 세션 종료 + 재측정 후)
- **Q16** (조건 e) 메인 트리 `/Users/byeongjinjeong/Desktop/stock_vis`가 **stale 피처 브랜치(sess-signal-fwd-recon)** 체크아웃 + 하네스 08-10 판. **이 트리를 main으로 되돌릴 것인가?** 고유 7커밋(SIGNAL-FORWARD)의 처분 = chain_sight 프로젝트 판단.

---

## §7 최종 보고 (디렉터)

```
[MGMT-BATCH-B 착지 보고]
착지 트리/브랜치: ~/worktrees/sv-mgmt-b · monorepo/sess-mgmt-b (origin/main 04ec8bf7 기준 신규·옵션2)
   (세션 구동 트리 = Desktop/stock_vis·sess-signal-fwd-recon = 미접촉·§0-1·Q16)
baseline: 측정 스냅샷 1d528a6e / 착지 시점 origin/main 04ec8bf7 (라이브 드리프트·되감김 아님)
첫 sync 검증: 런타임 HEAD 일치 = Y(세션 중 자기수복) · deploy_history.log = 생성됨(정상, 부트스트랩 통과) · worker_sync.sh 신버전 = Y
분류 카운트(스냅샷): 브랜치 N=225 / 즉시삭제 159 / 즉시삭제(wt선행) 42 / 보류 8 / 검토필요 15 / 유지 1  ·  worktree N=61
드리프트(04ec8bf7): 브랜치 +6(오늘 활성)·worktree 61→66 / 브랜치 유지 2 · worktree 유지 7 · 보류 16 · 원격후보 5
검토필요 질문: §6 Q1~Q16 (16건, Q15=드리프트 활성·Q16=메인 트리 처분)
BATCH-A 이전판정과 상충: 0 (전용 BATCH-A 보고서 미발견)
조건 (c) 재대조: 보류 8건 사유 origin/main 전부 확인·rehome-graph 판정 정밀화(아크 resolved)·08-10 트리 미사용
하네스 충돌·미발견: §0 7건 (착지경로=옵션2 해소 / health ❌2=stale 아티팩트 / BATCH-A 미발견 / IFS·캐시 함정 / baseline 드리프트 / 조건c / 조건e)
착지: sv-mgmt-b docs/mgmt/ + TASKQUEUE 부기
서빙 반영: **코드 변경 없음 — 문서만, 다음 sync에 자동 반영**
HALT 여부: 아님 (완주). 삭제 실행 전제 = 모든 CC 세션 종료 + 활성 목록 재측정
```
