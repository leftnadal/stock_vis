# NEO4J-RESTORE-P2 설치 runbook (병진 수동 — launchctl 실행은 사람이)

> 목적: 타르볼 Neo4j를 launchd(KeepAlive+RunAtLoad)로 항구화 → 재부팅·비정상 종료 시 자동 재기동.
> CC는 plist·본 runbook 제작까지만. **launchctl bootstrap/bootout·파일 제거는 병진 수동.**
> plist: `scripts/ops/launchd/com.stockvis.neo4j.plist` (plutil -lint OK, JAVA_HOME=openjdk@21 명기).

## 선결: 현행 수동 기동과의 교대 (중복 기동 방지)
launchd가 붙기 전에 현재 수동/세션 기동된 neo4j가 살아있으면 포트 7687 충돌. **반드시 정지 후 bootstrap**:

```
# 1) 기존 pid 확인 (java neo4j)
pgrep -fl "neo4j" | grep -i java
# 2) 있으면 정지 (JAVA_HOME 필요)
JAVA_HOME=/opt/homebrew/opt/openjdk@21 ~/neo4j/bin/neo4j stop
# 3) plist 배치 + 로드 (bootstrap)
cp ~/worktrees/sv-neo4j-recon/scripts/ops/launchd/com.stockvis.neo4j.plist ~/Library/LaunchAgents/ && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.stockvis.neo4j.plist
```
(위 3줄이 핵심 설치 절차. cp 경로는 실제 체크아웃 위치로 조정.)

## 검증 (bootstrap 후)
```
launchctl list | grep com.stockvis.neo4j        # 등재·pid 확인
lsof -nP -iTCP:7687 | grep LISTEN                # bolt 리스닝
```
- 인증까지 확인하려면 `.env` 자격증명으로 RETURN 1 (CC read-only 스크립트 재사용 가능).

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
