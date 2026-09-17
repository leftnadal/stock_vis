# SCB-RECOVER-PROBE 보고서 — 재부팅 복구 실측 + 논거 원천 플랜 게이트 프로브

- 실행: 2026-09-15 08:35~09:30 KST · 구동 트리 `~/worktrees/sv-recover-1` · 브랜치 `monorepo/sess-recover-1`
- baseline `origin/main` = `50d37950` (세션 중 `2eca515d`로 전진 — §2)
- 성격: ops/recon. 코드 변경 0 · DB 쓰기 0 · 마이그 0 · 서비스 조작 0
- 외부 API 콜: **2/3** (예비 1콜 미사용)
- 선행: `docs/mgmt/SCB-CONTEXT-RECON_report.md` (09-10)

---

## §1-A git 상태

| 항목 | 디렉터 09-14 17:18 관측 | 본 세션 재측정 (09-15 09:10) | 일치 |
|---|---|---|---|
| 본진 HEAD | `2eca515d` (main) | `2eca515d` (main) | ✅ |
| `origin/main` | `50d37950` | `50d37950` → 세션 중 `2eca515d` | 변동 |
| ahead / behind | 4 / 0 | **4 / 0** (fast-forward, 발산 아님) | ✅ |
| 미push 4커밋 | `2eca515d`·`d2caada3`·`8cbb7f65`·`3631bb81` | 동일 | ✅ |
| 4커밋 파일 전수 | 전부 문서 | `PROGRESS.md`·`TASKQUEUE.md`·`docs/instructions/RC-D-0.md`·`docs/reports/rc_d0_store_dedup_recon.md` — **코드 0** (+200/−2) | ✅ |
| worktree / 로컬 / 원격 | 56 / 66 / 28 | **58 / 69 / 28** (본 세션 +1, 외 +1) | 근사 |
| 본진 clean | tracked 0 · untracked 20 | tracked 0 · untracked **21** | ✅ |
| `maintenance.lock` | mtime 08-31 15:01 | 동일 (0 byte) | ✅ |

`git merge-base --is-ancestor origin/main HEAD` = **OK** (순수 FF).

---

## §1-B health_check 항목별 (2026-09-15 09:13:47, 구동 트리에서 측정)

| 상태 | 항목 | 사유 | 판별 |
|---|---|---|---|
| ❌ | origin/main 해시 | **메시지-라벨 불일치**: 항목명은 "origin/main 해시"인데 출력은 `PROGRESS.md 112.3h 미갱신 (임계 72h)` | **판별 가능** — PROGRESS 마지막 갱신 09-10 → 112h 경과. 미push 4커밋과 **무관** |
| ✅ | brunch / worktree 존재 | 활성 표기 전건 존재 | — |
| ✅ | PROGRESS 갱신 stale | 09-10 이후 22 commits (warn≥50) | — |
| ✅ | TASKQUEUE done 매칭 | done/verified 8건 | — |
| ✅ | TASKQUEUE 주장 vs 증거 | 불일치 0 | — |
| ✅ | DECISIONS 갱신일 | 09-10 (4일 전) | — |
| ✅ | slice* 미머지 brunch | 0건 | — |
| ✅ | **외부 자동화 commit** | `origin/main..HEAD` 범위 commit 없음 | §1-C nightly와 **무관** — nightly는 애초에 커밋하지 않음(설계, §1-C 참조) |
| ✅ | shared 경계 | 우회 0 / 동결 잔여 1 | — |
| ✅ | 외부-LLM 경계 | 신규 직접호출 0 | — |
| ✅ | known-fail 레지스트리 | 환경 known-fail 1건 (Finnhub 키 부재) | — |
| ✅ | 발행 로그 신선도 | Django/DB 미가용 → 검사 생략 (SECRET_KEY 미설정 = 비런타임 환경) | 검사 자체가 skip |
| ⚠ | 실행 트리 정합 | `HEAD=50d3795 ≠ origin/main=2eca515` · 트리=`sv-recover-1` | **판별 가능 — 측정 위치 아티팩트**. 실제 런타임 3트리는 전부 `2eca515d` behind 0 (§1-D) |
| ✅ | monitor refresh 신선도 | 동일 사유로 생략 | — |
| ❌ | stale pending 백-어노테이션 | `2026-09-07 DUAL-OBS-1` age 8일 (임계 3거래일) — 순수 stale, RESOLVED/LANDED/SUPERSEDED 부기 필요 | **판별 가능** — 부기 누락 |
| ⚠ | 런타임 감지 로그(runtime_check) | 최근 24h WARN `@2026-09-14T00:40:22Z` · runs_24h=24 | 미확인 (WARN 사유 원문 미조회) |
| ✅ | launchd 실행 트리 정합 | 잡 13건 전부 런타임/허용 경로 | — |
| ✅ | .env 심링크 실체 | 런타임 트리 2건 심링크·대상 실재 | — |

**합계: ✅14 / ⚠2 / ❌2.** 추이(디렉터 제공 09-10 ⚠2 → recon ⚠1 → 지금): **⚠2 · ❌2**. ❌ 2건은 모두 *문서 부기* 성질(PROGRESS 갱신·stale 백어노테이션)이며 코드·런타임 결함 아님.

---

## §1-C nightly — "리포트가 안 쌓인다"의 근인 3분할

**전제 정정: nightly 자동화는 죽지 않았다.** 09-15 05:20/05:40에도 정상 발화.

| 산출물 | 최신 | 상태 |
|---|---|---|
| `~/stock-vis-nightly/logs/tier3_audits_20260914_230004.log` | 09-14 23:00 발화 → 23:45 완료 | ✅ |
| `~/stock-vis-nightly/health/health_20260915.json` | 09-15 05:40 | ✅ |
| `~/stock-vis-nightly/dogfood/rubric_20260915.json` | 09-15 05:20 | ✅ |
| `~/stock-vis-nightly/daily-snapshots/` | 09-15 07:07 | ✅ |
| `~/stock-vis-nightly/repo/docs/nightly_auto_system/reports/9월/14일/` | `performance_audit.md`(441줄)·`security_audit.md`(578줄)·`api_dependency_audit.md`(451줄) **created** | ✅ |

### 근인 ① 브랜치 ahead=0 = **설계이지 고장 아님 (판별 가능)** — *2026-09-17 기전 정밀화*

`~/stock-vis-nightly/publish_reports.sh:12-13` 원문:
```
#    D2 git 커밋 아님: 발행본은 미추적 파일로 배치
#       (read 경로 .gitignore가 무시 → git status 무오염, origin 무오염).
```
**⚠️ 초판 서술 정정(09-17)**: "tier3가 커밋하지 않는다"는 부정확했다. tier3는 매일 **커밋을 시도한다** — 09-14 로그에 `📝 감사 보고서 커밋 중 (격리 브랜치 monorepo/nightly-20260914)` → `ℹ️ 커밋할 변경사항 없음`. 실제 기전은 **`.gitignore:229` 가 격리 nightly repo에도 적용**되어 생성물이 전부 ignore 대상이라 스테이징할 것이 0이라는 것이다(`git -C ~/stock-vis-nightly/repo check-ignore -v` 로 실증). 결과는 같고 D2 설계 의도와도 일치한다. 따라서 `monorepo/nightly-20260903/10/11/12/13/14` 전부 ahead=0은 **정상 산출**. 6월(`nightly-20260618/19` ahead=1)은 D2 결정 **이전**의 구 설계.

### 근인 ② 본진 `docs/nightly_auto_system/reports/` 7~9월 부재 = **publish_reports.sh 미호출 (판별 가능)**

- 원본(SRC_ROOT) `~/stock-vis-nightly/repo/docs/nightly_auto_system/reports/` = **4·5·6·7·8·9월 전부 존재** (9월 mtime 09-14 23:00)
- 목적지(DEST_ROOT) `~/Desktop/stock_vis/docs/nightly_auto_system/reports/` = **4·5·6월만**, 마지막 mtime **6월 30일 23:26**
- `grep -rn "publish_reports" ~/stock-vis-nightly/*.sh ~/stock-vis-nightly/repo/scripts/*.sh` → **호출처 0건** (자기 자신의 주석만)

→ 발행 단계가 파이프라인에서 **끊겨 있다**. 리포트는 생성되지만 본진으로 복사되지 않는다. git 추적본이 4·5·6월인 것도 동일 시점 경계와 일치.

### 근인 ③ 09-14 tier3 작업 실패 9건 — **근인 확정(09-17 조회). 인증/401 아님.**

생성 3 / 실패 9(데이터 무결성 · Beat 스케줄 · API 문서 · 카탈로그 동기화 · API 응답 일관성 · 모바일 UX · 설계서 갭 3종). 9건 **전부 동일한 단일 사유**, 동일 초(23:45:16) 연속 실패:

```
run_tier3_audits.sh: line 80: /Users/byeongjinjeong/.nvm/versions/node/v22.19.0/bin/claude: No such file or directory
```

- `run_tier3_audits.sh:28` `CLAUDE_BIN="$(which claude 2>/dev/null || echo "$HOME/.nvm/.../claude")"` → `:80`에서 실행.
- 해당 경로는 **심링크** → `../lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe`. bash의 `No such file or directory`는 **타깃이 없는 dangling 심링크**에서도 발생한다.
- 현재(09-17 14:33) 심링크·타깃 모두 **존재**, mtime `Sep 17 14:33` = CLI 패키지가 방금 교체된 흔적. 09-14 23:45에도 같은 교체 창에 걸렸을 개연성이 높으나 **당시 mtime 증거는 없어 직접 확증 불가 = 미확인**.
- **일시적 창 확정**: 09-10 0 · 09-11 0 · 09-12 0 · **09-14 9건** · **09-15 0 · 09-16 0**. 09-13 로그의 1건은 **거짓 양성**(감사 보고서 본문이 인용한 문자열이지 실패가 아님).
- 첫 3건(performance·security·api_dependency)은 23:00~23:45 **정상 완료** → 실행 도중 바이너리가 사라졌다는 해석과 정합.

**디렉터 가설(`claude -p` 401 인증)은 반증.** 로그 전수에 `401`/`unauthorized`/`credit`/`quota` 계열 **실패** 기록 0건(매칭 라인은 전부 감사 *보고서 본문* 내용). **이미 자연 해소**(09-15 11건 · 09-16 12건 정상 생성). **조치 없음.**

### 09-14/09-15 발화 여부

- `monorepo/nightly-20260914` 브랜치 **존재**(디렉터 09-14 17:18 "부재" 관측 이후, 당일 23:00 발화 시 생성). `nightly-20260915`는 아직 부재 — tier3 스케줄이 **23:00**이고 현재 09:30이므로 **미도래, 미발화 아님**.

### launchd

`launchctl list | grep stockvis` = **13건 로드**. 마지막 exit code:

| 잡 | pid | last exit | 비고 |
|---|---|---|---|
| celery-worker-neo4j | 3464 | 0 | 09-12 18:37 기동, 생존 |
| web-frontend | 89961 | **143** (SIGTERM) | 09-15 09:15 재기동 |
| web (daphne) | 87609 | 0 | 09-15 09:13 재기동 |
| celery-worker | 87499 | **-9** (SIGKILL) | 09-15 09:13 재기동 |
| celery-beat | 87504 | 0 | 09-15 09:13 재기동 |
| neo4j | 3469 | 0 | 생존 |
| pg-backup / nightly / verify-pair / celery-watchdog | — | 0 | 주기 잡, 정상 |
| dogfood | — | **2** | 09-15 05:20 실행됨(산출물 생성 확인) |
| healthcheck | — | **2** | 09-15 05:40 실행됨(산출물 생성 확인) |
| runtime-check | — | **1** | health ⚠와 연동 |

repo plist vs 설치본: `runtime-check`·`web-frontend` **IDENTICAL**. `cn_repair.nightly`는 repo에만 존재하고 설치본은 `.disabled-20260811`로 비활성 = launchctl 목록 부재와 정합.

---

## §1-C 후속 — 발행 소급 집행 (2026-09-17, 승인 [3])

**디렉터 교정 접수·실증**: "main에 7~9월 부재"는 **이상 신호가 아니다**. `.gitignore:229` `docs/nightly_auto_system/reports/**/*.md`(근거 = DECISIONS `[2026-06-23] B-2`)가 적용되며 `git check-ignore -v`로 실증했다. 추적본이 4·5·6월뿐인 것은 gitignore 도입 **이전**의 역사 파일이다. 진짜 문제는 **본진 트리에 발행본 파일 자체가 없는 것**이었고, 원인은 B-2가 "사용자 수동"으로 남긴 발행 절차가 3개월간 한 번도 이행되지 않은 것이다(자동화 고장 아님).

**집행**: `~/stock-vis-nightly/publish_reports.sh` 를 2026-07-01 ~ 2026-09-30 각 날짜로 수동 실행(멱등·비차단·always exit 0·D1 원본 불변).

| 구분 | 건수 |
|---|---|
| 루프 일수 | 92 |
| ✅ 발행 | **69일** |
| ℹ️ 원본 디렉터리 부재 | 21일 |
| ℹ️ 원본에 .md 없음(빈 디렉터리) | 2일 (7월 21일 · 8월 25일) |
| ⚠️ 경고·오류 | **0** |

**사후 실측** — 본진 `docs/nightly_auto_system/reports/`: 7월 **29일/347md** · 8월 **30일/348md** · 9월 **10일/100md** = **795개**, 원본 전량과 일치(차집합 `diff`로 확인). `git status docs/nightly_auto_system/` = **출력 0**(gitignore 정상·origin 무오염).

**reader 인식 검증**(읽기 전용): `packages/shared/metrics/services/agent_reports.py` · `REPORTS_BASE` = 본진 경로 하드코딩 · `_find_report_path`는 어제→오늘→그제→3일전 순 탐색. 2026-09-17 기준 **12/12 전건 인식**(전부 `9월/16일/`에서 해소), `extract_audit_insights` 샘플 정상(`api_consistency_audit` 405줄·헤딩 6·severity_hits 1). **6/16 이후 "보고서 없음" 해소.**

**미집행(지시 준수)**: 자동 배선(nightly 스크립트 말미 `publish_reports.sh` 호출 추가)은 repo 밖 파일 수정이라 **하지 않았다**. 발행은 이번 1회 수동뿐이므로 **배선하지 않으면 09-17 이후분은 다시 누적된다.**

---

## §1-D 런타임 서비스 생존

**부팅 시각 = 2026-09-12 12:32:23 KST** (재부팅은 3일 전, "직후" 아님). 서비스 최초 기동 09-12 18:37.

| 서비스 | 상태 | 근거 |
|---|---|---|
| PostgreSQL | ✅ | `pg_isready` = accepting · `psql -d stock_vis` 성공 |
| Redis | ✅ | `PONG` |
| Neo4j | ✅ | bolt 7687 OPEN · http 7474 OPEN · java pid 3469 |
| Celery worker (default) | ✅ | pid 87499 · `--concurrency=4` · cwd `sv-worker-runtime` |
| Celery worker (neo4j) | ✅ | pid 3464 · `-Q neo4j --pool=solo` |
| **Celery beat** | ✅ | pid 87504 · DatabaseScheduler |
| daphne (:18765) | ✅ | pid 87609 |
| next-server (:3000) | ✅ | pid 89979 · node v22.19.0 · cwd `sv-web-runtime/frontend` |

### ⚠️ 세션 중 배포 발생 — 서비스 재기동은 본 세션이 유발한 것이 아님

`~/Library/Logs/stockvis/deploy_history.log` 실측:
```
2026-09-15T09:13:20+0900 | worker | 5e4e70ea → 2eca515d
2026-09-15T09:13:33+0900 | web    | 1efd410c → 2eca515d
2026-09-15T09:13:34+0900 | api    | 5e4e70ea → 2eca515d
2026-09-15T09:13:44+0900 | HEALTH FAIL | ❌2건
```
병렬 주체가 09:13에 `sv sync` 배포를 집행했다. 이것이 ① `origin/main` 09:12:02 push ② worker/beat/daphne/web-frontend 09:13~09:15 재기동 ③ HEALTH FAIL ❌2건 기록을 모두 설명한다. **본 세션은 서비스를 기동·재기동하지 않았다(규칙 6 준수).**

### 런타임 3트리 HEAD

| 트리 | HEAD | behind origin/main |
|---|---|---|
| sv-api-runtime | `2eca515d` | **0** |
| sv-web-runtime | `2eca515d` | **0** |
| sv-worker-runtime | `2eca515d` | **0** |

### beat 3종 last_run

| beat | recon 09-10 | **지금 (09-15 09:20)** | 판정 |
|---|---|---|---|
| `portfolio-analyst-signals-daily` | 2026-09-09 23:30 | **2026-09-14 23:30 UTC** (enabled=True, total_run 32) | ✅ 전진 |
| `newsfix-sync-stocknews` | 2026-09-09 21:30 | **2026-09-14 21:30 UTC** (enabled=True, total_run 8) | ✅ 전진 |
| `neo4j-health-check` | 2026-09-10 04:00 | **2026-09-14 22:00 UTC** (enabled=True, total_run 9570) | ✅ 전진 |

beat 전체 스케줄 상위 40건 전부 `enabled=True`, 최신 발화 `2026-09-14 23:35 UTC`(= 09-15 08:35 KST) = 측정 시점 직전. **beat enabled 토글 없음(읽기만).**

### AnalystSignalSnapshot — 성적판 표본

- **recon 274 → 지금 301 (+27 증가) ✅** — 표본은 정지하지 않았다.
- 심볼 11종 · source 전부 `fmp` · 회당 9행 (11심볼 중 9종 적재)
- crontab = `30 19 * * 1-5` **America/New_York**, task `apps.portfolio.tasks.ingest_analyst_signals`
- ET 기준 캡처 시각 최근 14: `09-14 Mon 19:30` · `09-12 Sat 18:04/18:05` · `09-10 Thu` · `09-09 Wed` · `09-08 Tue` · `09-07 Mon` · `09-04 Fri` · `09-03 Thu` · `09-02 Wed` · `09-01 Tue` · `08-31 Mon` · `08-28 Fri` · `08-27 Thu`
- **결측 1건: ET 09-11 (Fri) 19:30** — 그 시각은 KST 09-12 08:30, 머신 부팅(09-12 12:32 KST) **이전 = 전원 오프**. **판별 가능** = 재부팅 전 오프 구간의 직접 결과.
- **이례 1건: ET 09-12 (Sat) 18:04/18:05** — 토요일이며 예약 시각(19:30)도 아님. 캐치업인지 수동 실행인지 **미확인**.

---

## §2 미push 4커밋 처분

| 조건 | 판정 |
|---|---|
| ① behind == 0 | ✅ (ahead 4 / behind 0, is-ancestor OK) |
| ② 4커밋 문서 전용 | ✅ (4파일 전부 문서, 코드 0) |
| ③ 병진 명시 승인 `승인 PUSH` | ✅ |

**집행**: `git -C ~/Desktop/stock_vis push origin main` → 출력 **`Everything up-to-date`**.

사후: `git ls-remote origin refs/heads/main` = `2eca515d…`, ahead 0 / behind 0. **4문서커밋 원격 반영 확인.**

⚠️ **정직 기록**: 원격은 push 시점에 **이미** `2eca515d`였다(내 push는 no-op, 로컬 추적ref만 갱신). `refs/remotes/origin/main` reflog에 `2026-09-15 09:12:02 update by push` 1건이 있으나, 이것이 내 push가 학습한 원격 상태인지 §1-D의 병렬 배포 주체가 09:12에 선행 push한 것인지는 **미확인**. 결과 상태는 목표와 동일. `--force` 미사용, non-ff 미발생.

---

## §3 논거 원천 플랜 게이트 프로브 ★ — **RED → GREEN 반전**

FMP client 무수정 · 임시 스크립트(scratchpad, 미커밋) · `urllib` 직접 호출 · 키 미출력.

### 콜 1/3

```
엔드포인트 : GET /stable/grades?symbol=NVDA
상태코드   : 200
응답 키 전수: action · date · gradingCompany · newGrade · previousGrade · symbol
논거 텍스트 유무 : 없음 (등급 변경 행만 — 서술 텍스트 필드 0)
행 규모    : NVDA 1심볼 = 1,158행 · 2012-02-13 ~ 2026-09-04 (14년 5개월)
샘플      : {"symbol":"NVDA","date":"2026-09-04","gradingCompany":"Needham",
            "previousGrade":"Buy","newGrade":"Buy","action":"maintain"}
판정       : GREEN — 개별 애널리스트 등급 변경 행이 즉시 수집 가능.
            recon이 미지수로 남긴 gradingCompany/previousGrade/newGrade/action 4필드 전부 실재.
```

### 콜 2/3

```
엔드포인트 : GET /stable/grades-news?symbol=NVDA&limit=5
상태코드   : 200
응답 키 전수: action · gradingCompany · newGrade · newsBaseURL · newsPublisher ·
             newsTitle · newsURL · previousGrade · priceWhenPosted · publishedDate · symbol
논거 텍스트 유무 : **있음** — newsTitle · newsURL · newsBaseURL · newsPublisher ·
                  priceWhenPosted · publishedDate (지시서가 지목한 4필드 전부 실재)
행 규모    : limit=5로 호출 → 5행 반환. **1심볼당 총 행수·과거 소급 범위 = 미확인**
            (예산 규칙상 예비 콜은 402 대안 전용이므로 규모 측정에 쓰지 않음)
샘플      : {"symbol":"NVDA","publishedDate":"2026-09-11T18:05:10.000Z",
            "newsURL":"https://thefly.com/ajax/news_get.php?id=4424733",
            "newsTitle":"Buy/Sell: Wall Street's top 10 stock calls this week",
            "newsBaseURL":"thefly.com","newsPublisher":"TheFly",
            "newGrade":"Underweight","previousGrade":"Outperform",
            "gradingCompany":"Morgan Stanley","action":"downgrade",
            "priceWhenPosted":219.415}
판정       : GREEN — 즉시 수집 가능.
```

### 콜 3/3 — **미사용** (1·2 모두 200, 402 미발생 → 대안 경로 불필요)

### 확정

> **논거 텍스트 원천 = GREEN.** 현행 FMP Starter 키로 402 없이 200 수신. recon의 RED("논거 텍스트 엔드포인트 미구현")는 **`grades-historical` 한 경로만 본 결과**였고, `grades` + `grades-news` 두 경로가 실재한다. 디렉터 선택지 **(b) 신규 FMP 수집**의 플랜 게이트가 열렸다.

**GREEN의 정확한 범위(단서, 가감 없이)**:
- 텍스트 입도 = **헤드라인 + 발행처 + URL + 당시 주가**. 애널리스트 논거 **본문 prose는 FMP가 주지 않는다**. 본문이 필요하면 `newsURL`을 외부 페치해야 하며 그 경로는 본 프로브 범위 밖.
- 샘플 5행 중 1·5행이 **같은 `newsTitle`/`newsURL`** 을 공유(Morgan Stanley·Wells Fargo). 즉 `newsTitle`은 애널리스트 1인의 논거가 아니라 **복수 등급 변경을 묶은 집계 기사** 제목일 수 있다.
- `packages/shared/api_request/providers/fmp/client.py`에 두 메서드 **부재**(recon 확인 그대로). 수집하려면 client 확장이 선행 — 본 세션 무수정.

---

## §4-A 운영 DB 확정 — **동일 DB**

- `config/settings.py:269-281` → `NAME` = **`'stock_vis'` 하드코딩**. `DB_NAME` 환경변수 오버라이드 경로 **없음**. USER/PASSWORD/HOST/PORT만 env.
- `.env`의 DB 관련 키는 `DB_HOST=127.0.0.1` 단 1개 → 나머지 전부 settings 기본값.
- 런타임 3트리의 `.env`는 **본진 `.env`의 심링크**(health "심링크 실체" ✅로도 확증).

→ **개발 DB == 런타임 DB == `stock_vis@127.0.0.1`. "prod와 상이 가능"은 해소.** (기존 교훈 `lesson_dev_prod_shared_db`와 정합.)

| 테이블 | recon 09-10 (개발 DB) | 본 세션 09-15 (런타임 DB) | 판정 |
|---|---|---|---|
| `AnalystSignalSnapshot` | 274 | **301** | 동일 DB · +27 |
| `StockNews` | 98,583 (09-09) | **110,887** | 동일 DB · 증가 (09-14 1,112행/09-13 758/09-12 1,316) |
| `NewsEntity` | 614k~624k (recon 표기 614k) | **624,562** | 동일 DB |
| `NewsArticle` | (recon 미표기) | 493,264 | — |

접속 권한 제약 없음.

---

## §4-B cost_ledger — **recon의 "측정 위치 오류" 가설은 반증**

`apps/portfolio/llm/cost_ledger.py:30` `DEFAULT_LEDGER_PATH = REPO_ROOT/"docs"/"portfolio"/"coach"/"cost_ledger.jsonl"`, `REPO_ROOT = Path(__file__).resolve().parents[2]`. 오버라이드 `COST_LEDGER_PATH`는 `.env`에 **없음**.

| 트리 | `docs/portfolio/coach/cost_ledger.jsonl` | mtime |
|---|---|---|
| 본진 stock_vis | **31행** | 2026-05-28 12:58 |
| sv-api-runtime | **31행** | 2026-07-06 16:46 (checkout) |
| sv-web-runtime | **31행** | 2026-07-06 12:38 (checkout) |
| **sv-worker-runtime** | **31행** | 2026-07-05 06:20 (checkout) |

**런타임 트리에도 31행 — 본진과 동일. append 0건.** mtime은 전부 워크트리 체크아웃 시각이지 기록 시각이 아니다.

원장 내용: `timestamp` 범위 **2026-05-22T13:01Z ~ 2026-05-26T06:45Z**. 키 = `timestamp·slice·entry_point·provider·model·input_tokens·output_tokens·cost_usd·fallback_from`. entry_point 분포 = `slice14` 24 / `runtime` 6 / `slice15` 1.

→ **판정: coach LLM 휴면 또는 로깅 미작동. 마지막 기록 2026-05-26.** 진입점별 최근 30일 사용량 = **산출 불가(데이터 0건)**.

- 프로덕션 유일 호출처 = `apps/portfolio/llm/client.py:197` (`from ...cost_ledger import append_call as _ledger_append`, try/except 흡수). 나머지는 테스트.
- `celery-worker.log`에 `cost_ledger` 문자열 **0건** → append 실패 경고(`cost_ledger append 실패`)도 기록 없음. 실패 후 침묵인지 호출 자체가 없는지 **미확인**.
- 별도 주의: 거의 모든 트리 **루트**에 동명 `cost_ledger.jsonl`(4행·최신 2026-08-05)이 있으나, 이는 슬라이스 개발 원장(`commits`/`files_changed`/`tests_added`/`gates`)으로 **LLM 비용 원장과 무관**. 혼동 금지.

---

## §5 정정 기록

| 파일 | 위치 | 정정 |
|---|---|---|
| `TASKQUEUE.md` | NEWSFIX-SYNC-BE 행 | `⚠ prod 무변(StockNews 0행·beat enabled=False)` → **StockNews 110,887행 · beat enabled=True(last_run 2026-09-14 21:30 UTC·total_run 8)**. 근거 = recon 보고서 §C + 본 세션 런타임 DB 실측 |
| `TASKQUEUE.md` | SCB-CONTEXT-LAYER 행 | `⚠ stale 문서: …·cost_ledger 로깅 경로` → **논거 축 RED→GREEN 반전(§3)** + cost_ledger 가설 반증(§4-B) 반영 |

`NEWS-DEPLOY-EXEC` 행은 이미 09-04~08 실측으로 정정되어 있어 무접촉. 같은 문구의 **코드 주석은 0건**(`grep` 전수 — `config/settings.py:35`는 ADVISOR 건으로 무관). `PROGRESS.md`·`DECISIONS.md`의 동일 문자열은 전부 **날짜가 박힌 과거 이력** 또는 **타 beat 건**이라 정정 대상 아님.

---

## 종합

- **즉시 조치 필요: 0건** (서비스 전건 생존, beat 전건 전진, 표본 축적 재개 확인)
- **병진 판단 필요: 4건** — 아래 "디렉터 결정 필요 사항"
- **정상: PG·Redis·Neo4j·worker×2·beat·daphne·next-server·런타임 3트리 동기(behind 0)·nightly 발화·beat 40+종 enabled**

**가장 큰 미지수 1건**: `/stable/grades-news`의 **1심볼당 총 행수와 과거 소급 범위**. `limit=5`로만 호출해 규모를 모른다. 수집 파이프라인 설계(배치 크기·FMP 일일 쿼터 소모·백필 비용)가 이 수에 직접 의존한다.

### 디렉터 결정 필요 사항 (사실만)

1. **논거 축 선택지 재개봉** — recon이 제시한 (a)카운트추이 대체 / (b)신규 FMP수집 / (c)news 우회 중 **(b)가 402 없이 열렸다**. 단 텍스트 입도는 헤드라인 수준이고, `newsTitle`이 복수 등급변경을 묶은 집계 기사일 수 있다.
2. **nightly 발행 단계 단절** — `publish_reports.sh` 호출처 0건. 리포트 7·8·9월분이 `~/stock-vis-nightly/repo/` 에만 있고 본진에 복사되지 않는다. 6월 30일 이후 3개월 누적.
3. **tier3 09-14 작업 9건 실패** — 데이터 무결성·Beat 스케줄·API 문서·카탈로그 동기화·API 응답 일관성·모바일 UX·설계서 갭 3종. 실패 사유 미조회.
4. **세션 중 병렬 배포 발생** — 09-15 09:13 `sv sync`로 3트리가 `2eca515d`로 전진, worker(SIGKILL -9)·beat·daphne·web-frontend 재기동. 본 세션 무관. `deploy_history.log`는 같은 시각 `HEALTH FAIL ❌2건`도 기록.

### 부수 관측 (조치 안 함)

- health ❌ `origin/main 해시` 항목이 **PROGRESS stale 메시지를 출력** — 항목명/메시지 불일치.
- `DUAL-OBS-1`(09-07) 순수 stale 8일 — 백어노테이션 부기 필요.
- `AnalystSignalSnapshot` ET 09-12(Sat) 18:04/18:05 이례 실행 — 캐치업/수동 여부 미확인.
- `celery-beat-error.log` 386MB · `celery-worker-error.log` 384MB · `celery-worker-neo4j-error.log` 534MB — 로테이션 부재로 보이나 본 세션 조치 없음.

## HALT / 예외

- HALT **미발동**.
- 예외 사용 2건: §2 push(승인 토큰 인용, 조건 ①②③ 재확인 후 집행 — 결과 no-op) · §5 문서 갱신(코드·DB 무접촉).
- 규칙 6 준수: 죽은 서비스 없었고, 어떤 서비스도 기동·재기동하지 않았다. beat `enabled` 토글 0. DB 쓰기 0. 마이그 0. 외부 콜 2/3.
