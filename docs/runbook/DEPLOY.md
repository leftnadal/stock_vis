# DEPLOY.md — 런타임 배포·동기 런북 (RB-1)

> **단일 출처**: 런타임 인벤토리(트리·포트·라벨)의 정본은 `scripts/runtime_check.py`의
> `RUNTIME_INVENTORY` 상수다. 이 문서는 그것을 **참조**할 뿐 복제하지 않는다(drift 방지).
>
> **설계 사상 — 감지는 자동, 집행은 사람.** 자동 감지(runtime_check + launchd)는 이상을
> 기록·표면화·알림만 하고, 집행(kill·kickstart·checkout·동기)은 사람이 절차대로 한다.
> 근거 = 스테일 런타임 3건(worker 24커밋 / web :3000 고아 Aug10 / api :18765 고아 daphne
> Aug13)의 공통 근인 = **관리이탈 고아의 포트 점유 + 동기 시점 무정의**, 셋 다 "수일 무감지".
> 결정: D-RB-1(감지 자동화)·D-RB-2(랜딩 DoD 동기). 인시던트 #45·#116.

---

## 1장 — 고아 스윕 (관리이탈 프로세스 포트 점유 감지·처리)

### 1.1 자동 감지 (read-only)
```bash
sv health              # health_check가 runtime_check.log 최근 24h 이상을 표면화
python scripts/runtime_check.py    # 3종 즉시 감지(고아·드리프트·launchd), 종료코드 0/1/2
```
runtime_check는 인벤토리 각 포트의 **리스너 pid가 launchd 관리 pid 자신/자손인지** 대조한다.
자손도 아니면 = **ORPHAN**(관리이탈 프로세스가 포트 점유). launchd 주기 job이 1시간마다
자동 실행(§부록), ERROR 시 메일·데스크탑 알림.

### 1.2 수동 대조 (판정 재현)
```bash
PORT=18765; LABEL=com.stockvis.web        # api 예시 (인벤토리 참조)
lsof -ti:$PORT -sTCP:LISTEN                 # 실제 리스너 pid
ps -o pid,ppid,lstart -p <리스너pid>        # 기동시각·부모(오늘 아님 + ppid→1 = 고아 의심)
launchctl print gui/$(id -u)/$LABEL | grep 'pid ='   # launchd 관리 pid
# 리스너 pid가 launchd pid 자신도, 그 자손도 아니면 → 고아 확정
```

### 1.3 고아 발견 시 처리 절차 (집행 = 사람, APISYNC/WEBSYNC 전례 성문화)
> ⚠ runtime_check는 **절대 이 절차를 자동 실행하지 않는다.** 감지·알림까지만. 아래는 사람이.
1. **정당 리스너 확인**: `launchctl print`로 관리 pid 확인, 실제 포트 리스너와 불일치 확정.
2. **고아 종료**: `kill -TERM <고아pid>`(자식까지: npm 부모→next 자식 쌍이면 부모 TERM).
3. **재기동**: `launchctl kickstart -k gui/$(id -u)/<label>` → launchd 관리본이 포트 탈환.
4. **검증**: 리스너 pid 기동시각=지금 + `lsof -ti:$PORT` 단일 + 서빙 cwd=동기 트리.
   - #116 함정: kickstart는 launchd 추적 인스턴스만 재기동 → 고아 잔존 시 EADDRINUSE.
     반드시 고아 kill이 선행. (:3000 web / :18765 api 공통.)

---

## 2장 — 동기 절차 (랜딩 DoD, D-RB-2)

> **랜딩 세션의 완결 동작 = 런타임 동기.** main이 전진하는 순간이 유일한 동기 필요 시점이다
> (야간 자동 동기 도입 안 함 — D-RB-2). 세션 규약(SESSION_CONTRACT §H)은 이 절을 포인터한다.

### 2.1 표준 절차 (worker·api = `sv sync` 자동)
```bash
sv sync    # worker_sync.sh — 3트리 re-detach(origin/main) + worker/beat/daphne 재기동
```
가드레일 표준(APISYNC/SYNC 전례 흡수):
1. **롤백 포인트 기록**: 각 런타임 트리 현재 HEAD(`git -C <tree> rev-parse HEAD`).
2. **마이그 프리뷰**: `migrate --plan`으로 신규 마이그 확인(prod DB write는 병진 게이트).
3. **재기동**: `sv sync`가 worker/beat(kickstart celery-worker/beat) + api(kickstart
   com.stockvis.web) 자동 처리. 실행 시 `sync-audit.log`에 집행 감사 1줄 자동 기록(3장).
4. **스모크**: api authed 200(`/api/v2/market-pulse/regime/stress`), worker `celery inspect ping`.
5. **고아 단독 리스너 확인**: `lsof -ti:18765` 단일 + 기동시각=지금(1장 검증).

### 2.2 web 프로덕션 리빌드 (⚠ `sv sync` 미커버 — 수동, SYNC-COVERAGE)
> `worker_sync.sh`의 web 파트는 **re-detach만** 하고 재기동하지 않는다(주석 "next dev
> 핫리로드" = **프로덕션 빌드(npm run start)엔 거짓** — 핫리로드 없음). 따라서 FE 변경
> 반영은 아래 수동 절차(WEBSYNC 전례). 후속 자동화 = TASKQUEUE `SYNC-COVERAGE`.
```bash
WEB=/Users/byeongjinjeong/worktrees/sv-web-runtime
cd $WEB && git fetch origin main && git checkout --detach origin/main   # 트리 동기
cd $WEB/frontend
cp -r .next .next.bak                                    # ① 무중단 폴백 백업
npm run build                                            # ② 빌드 먼저 — 실패 시 .next.bak 복원·중단
# 성공 시에만:
launchctl kickstart -k gui/$(id -u)/com.stockvis.web-frontend    # ③ 서빙 교체
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/     # ④ 스모크 200
# ⑤ BUILD_ID 갱신 + 리스너 단독·신선 확인(1장) → .next.bak 제거
```
package.json/lock 변경 시 `npm install` 선행(worker_sync가 경고).

---

## 3장 — 감사 (집행 귀속)

| 로그 | 위치 | 내용 | 판독 |
|------|------|------|------|
| `sync-audit.log` | `~/Library/Logs/stockvis/` | `sv sync` 집행마다 시각·pid·ppid(부모명)·tty·전 트리 HEAD | 미귀속 동기 사건 발생 시 시각으로 대조 → 누가 실행했나 즉시 특정 |
| `runtime_check.log` | `~/Library/Logs/stockvis/` | 감지 실행마다 JSON 1줄(시각·종합·항목별 판정·behind) | 드리프트 지속시간·고아 발생 이력 추적 |

**귀속 확인 절차** (08-18 14:57 사건류 재발 시): ⑴ `sync-audit.log`에서 해당 시각 엔트리 →
pid·ppid·tty로 실행 주체 특정(과거엔 이 로그가 없어 reflog+web.log+프로세스 포렌식 3중 대조
비용 발생). ⑵ 병렬 세션/수동 여부 확정. ⑶ 미귀속이면 원장에 INC 등재.

---

## 부록

### A. 런타임 인벤토리 (정본 = `scripts/runtime_check.py::RUNTIME_INVENTORY`)
| name | tree | port | launchd label |
|------|------|------|---------------|
| worker | sv-worker-runtime | — | com.stockvis.celery-worker |
| beat | sv-worker-runtime | — | com.stockvis.celery-beat |
| web | sv-web-runtime | 3000 | com.stockvis.web-frontend |
| api | sv-api-runtime | 18765 | com.stockvis.web (daphne) |
> 이 표는 편의 사본이며 **정본이 아니다.** 불일치 시 `RUNTIME_INVENTORY`가 이긴다.

### B. 알려진 예외 — neo4j (OPS-NEO4J-TREE, 별건)
neo4j 워커(`com.stockvis.celery-worker-neo4j`)는 현재 미커밋 recon 트리(`Desktop/stock_vis`)
에서 구동 중(#45 표류 리스크). **인벤토리에서 의도적 제외** — 정리는 OPS-NEO4J-TREE 별건.
전용 런타임 트리로 이관 후 인벤토리 편입 대상.

### C. 감지 주기 조정
`docs/operations/com.stockvis.runtime-check.plist`의 `StartInterval`(초, 기본 3600).
변경 후 `launchctl bootout` → `bootstrap` 재등록. 드리프트 WARN 임계 = `runtime_check.py`의
`DRIFT_WARN_HOURS`(기본 24h).

### D. 관련 문서
- 배포 체크리스트(마이그·env·번들): `sub_claude_md/common-bugs.md` "배포 체크리스트"(단일 출처).
- web 서빙 실체: `docs/operations/web-runtime-runbook.md`.
- 결정: DECISIONS `D-RB-1`·`D-RB-2`·`D-MPS-OPS-SYNC/WEBSYNC/APISYNC`.
