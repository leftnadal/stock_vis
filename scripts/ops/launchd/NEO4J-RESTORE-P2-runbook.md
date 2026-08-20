# NEO4J-RESTORE-P2 설치 runbook (병진 수동 — launchctl 실행은 사람이)

> 목적: 타르볼 Neo4j를 launchd(KeepAlive+RunAtLoad)로 항구화 → 재부팅·비정상 종료 시 자동 재기동.
> CC는 plist·본 runbook 제작까지만. **launchctl bootstrap/bootout·파일 제거는 병진 수동.**
> plist: `scripts/ops/launchd/com.stockvis.neo4j.plist` (plutil -lint OK, JAVA_HOME=openjdk@21 명기).

## 소스 정본 (worktree 소멸과 무관)
- 본 plist·runbook은 **origin/main에 영구 존재**(`scripts/ops/launchd/`). 세션 worktree가 정리돼도 사라지지 않는다.
- 재설치 시 **main을 체크아웃한 어느 트리에서든** cp 가능(예: origin/main pull된 `~/Desktop/stock_vis` 또는 임의 클론). 아래 예시의 `<MAIN_TREE>`를 그 경로로 치환.

## 선결: 로그 디렉토리 + 현행 수동 기동과의 교대 (중복 기동 방지)
launchd가 붙기 전에 현재 수동/세션 기동된 neo4j가 살아있으면 포트 7687 충돌. **반드시 정지 후 bootstrap**:

```
# 0) 로그 디렉토리 선행 생성 — launchd는 StandardOut/ErrorPath 디렉토리를 만들지 않는다.
#    부재 시 서비스가 로그를 못 열어 무기록 침묵 사망(2026-05 원사건 재현). 반드시 먼저.
mkdir -p ~/Library/Logs/stockvis
# 1) 기존 pid 확인 (java neo4j)
pgrep -fl "neo4j" | grep -i java
# 2) 있으면 정지 (JAVA_HOME 필요)
JAVA_HOME=/opt/homebrew/opt/openjdk@21 ~/neo4j/bin/neo4j stop
# 3) plist 배치 + 로드 (bootstrap)
cp <MAIN_TREE>/scripts/ops/launchd/com.stockvis.neo4j.plist ~/Library/LaunchAgents/ && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.stockvis.neo4j.plist
```
(위 4줄이 핵심 설치 절차. `<MAIN_TREE>`=main 체크아웃 경로.)

## 검증 (bootstrap 후)
```
launchctl list | grep com.stockvis.neo4j        # 등재·pid 확인
lsof -nP -iTCP:7687 | grep LISTEN                # bolt 리스닝
```
- 인증까지 확인하려면 `.env` 자격증명으로 RETURN 1 (CC read-only 스크립트 재사용 가능).

## 운영 규칙 (설치 후 — KeepAlive 의미)
- **의도적 정지는 `neo4j stop`이 아니라 launchctl bootout으로.** KeepAlive=true라서 `~/neo4j/bin/neo4j stop`으로 죽여도 launchd가 **30초 내 재기동**(ThrottleInterval=30) → stop이 사실상 무효.
- 임시 정지 → 재개 예시:
```
# 정지 (KeepAlive 감시 해제)
launchctl bootout gui/$(id -u)/com.stockvis.neo4j
# 재개
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.stockvis.neo4j.plist
```
- 반대로, **평소엔 정지 자체가 불필요**(크래시·재부팅 시 자동 복구가 목적). 유지보수(백업·설정변경) 때만 위 정지→재개.

## 죽은 homebrew 엔트리 처리 (후보 보고 — 병진 판단)
- `~/Library/LaunchAgents/homebrew.mxcl.neo4j.plist`는 **제거된 바이너리**(`/opt/homebrew/opt/neo4j/bin/neo4j` 부재)를 가리키는 무효 엔트리. 로드 시 기동 실패·혼선.
- 후보 조치(병진 수동): `launchctl bootout gui/$(id -u)/homebrew.mxcl.neo4j 2>/dev/null; rm ~/Library/LaunchAgents/homebrew.mxcl.neo4j.plist`
- ⚠️ 파일 제거·bootout은 **D-BRANCH-DELETE-MANUAL 정신에 준해 병진 수동**. CC 미집행.

## 롤백
```
launchctl bootout gui/$(id -u)/com.stockvis.neo4j
rm ~/Library/LaunchAgents/com.stockvis.neo4j.plist
```
- 롤백 후에도 수동 기동(JAVA_HOME + `~/neo4j/bin/neo4j start`)은 그대로 가능.
