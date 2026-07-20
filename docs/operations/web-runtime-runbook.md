# WEB-RUNTIME-RUNBOOK — :3000 프론트 서빙 운영 런북

> 성문화: MGMT-BATCH-12 (2026-07-20). 실측 근거 = FE-8000-PROD-APPLY 집행(2026-07-18).
> 단일 출처 = 이 문서. 관련 결정 = DECISIONS `FE-8000-PROD-APPLY 집행 기록`·`D-DEPLOY-CHECKLIST`(common-bugs 배포 체크리스트).

## 1. 서빙 실체 (실측 정정 포함)

- **`:3000` = `next start` (prod 모드)** — 2026-07-18 FE-8000-PROD-APPLY로 dev→prod 전환.
  - cwd = `/Users/byeongjinjeong/worktrees/sv-web-runtime/frontend`, HEAD = origin/main(detached).
  - 프로세스: `npm run start` → `next-server (vN)`. orphan-subshell(nohup)로 기동.
- **launchd 감독 없음** — ⚠ 종전 장부의 "launchd 입양 고아 `npm run dev`" 서술은 **오인**이었다.
  - `com.stockvis.web` launchd 라벨 = **daphne 백엔드(:18765)** (`sv-api-runtime/scripts/daphne-web.sh`) — **:3000과 무관**.
  - `:3000`엔 전용 plist·KeepAlive **없음**. 2026-07-18 리스너 kill 후 **45초+ 무respawn 실측** = 감독자 부재 확정.
- 백엔드 API = daphne `:18765` (별도, `com.stockvis.web`가 감독). 프론트는 이 절대 base로 호출(#55).

## 2. 기동 / 재빌드 정식 절차 (FE-8000-PROD-APPLY 채록 전사)

마이그레이션·env 인라인 포함 반영은 [배포 체크리스트](../../sub_claude_md/common-bugs.md)(#53~#55)와 짝.

1. **기존 리스너 완전 정리**: `lsof -nP -iTCP:3000 -sTCP:LISTEN` → PID 확인 후 `kill`. 리스너 0 확인.
   - ⚠ **`com.stockvis.web`(daphne)는 건드리지 않는다** (:18765, 별개).
2. **45초+ 무respawn 확인**: kill 후 :3000이 되살아나지 않는지 관측(감독자 없으므로 정상). *(#61 — 잔존 리스너와 경합 시 신규 prod가 34초 만에 사망한 07-18 사례 재발 방지.)*
3. **재빌드**: `cd sv-web-runtime/frontend && npm run build`.
   - `.env.local`(→ Desktop 심링크)에서 `NEXT_PUBLIC_API_URL` 자동 로드. **빌드 성공 = fail-fast 게이트 통과(env 존재 검증)**.
   - `#48` 심링크 node_modules면 Turbopack 빌드 거부 → 격리 `npm ci` 후 재시도.
4. **기동(orphan-subshell)**: `( nohup npm run start > /tmp/next_prod_3000.log 2>&1 < /dev/null & )`.
5. **생존 확인**: ~48초(8틱) `curl :3000` 200 + 리스너 PID 불변 확인.
6. **검증 3종**(§3).

## 3. 검증 체크리스트

- [ ] `curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/` = **200**.
- [ ] **실렌더**: 홈 대시보드 + 리더보드(또는 대상 화면) 스크린샷.
- [ ] **절대 base**: 네트워크 요청이 `http://localhost:18765/api/v1/...`로 나가는지(비-:8000·비-상대) 1건 육안. `jwt/verify 200` = 인증 세션.
- [ ] **impression 수집 재개**: 대시보드 노출(카드 뷰포트 50%×1초 + 5초 flush) 후
      `ImpressionLog`에 당일 신규 행 증가 SELECT (read-only). *(07-18 실측: 신규 8행 = dashboard_eod 4 + news_chip 4.)*
- [ ] **fail-fast 게이트**: 별도 절차 불요 — **빌드 성공으로 갈음**(env 미설정이면 build/기동이 즉시 중단).

## 4. 알려진 리스크

1. **orphan-subshell = 재부팅 비지속**. 재부팅·세션 종료 후 :3000이 자동 부활하지 않는다.
   - 해소 = **launchd 정식 등록**(plist 초안 = `com.stockvis.web-frontend.plist`, §5). **load는 사용자 수동**(TASKQUEUE `LAUNCHD-WEB-PLIST-LOAD`).
2. **출처 불명 dev 프로세스 출현 1회**(2026-07-18 20:12 `npm run dev`가 :3000 재점유 → 1차 prod 사망). supervisor 아님 확인(45초 무respawn). 재발 시 `ps -o pid,ppid,lstart,command` 계보 추적.
3. **로그 경로 = `/tmp/next_prod_3000.log`** — 재부팅 소실. plist 정식화 시 `~/Library/Logs/stockvis/web-frontend.log`(영속)로 이전 예정.

## 5. launchd 정식화 (초안 — load 금지)

- plist 초안: [`com.stockvis.web-frontend.plist`](./com.stockvis.web-frontend.plist) (Label `com.stockvis.web-frontend`, KeepAlive, 영속 로그).
- **⚠ 이 저장소 파일은 초안이다.** `~/Library/LaunchAgents`로의 복사·`bootstrap`·`load`는 **사용자 수동**(시스템 설정 변경 = 자동 금지).
- 수동 적용(안내):
  ```
  cp docs/operations/com.stockvis.web-frontend.plist ~/Library/LaunchAgents/
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.stockvis.web-frontend.plist
  ```
  적용 후 재부팅 지속 검증 = `LAUNCHD-WEB-PLIST-LOAD`.
- `.next.old-*` 격리 백업(구 빌드)은 무해하나 정리 후보 → 사용자 수동 `rm -rf`.
