# TH-NEO4J-RECON-1 — Neo4j 다운 read-only 정찰 보고

- 세션: `monorepo/sess-neo4j-recon` (worktree `~/worktrees/sv-neo4j-recon`)
- machine clock 기준: 2026-08-13 06:57 UTC / 15:57 KST (epoch 1786604271)
- origin/main HEAD: `7b4775d2` (2026-08-13 15:44 KST)
- health_check: 14✅ / 1⚠ / 0❌ — WARN = 실행트리 origin/main 뒤처짐(#47, 세션브랜치 자연 상태·양성)
- 지시서 커밋(§0-0): `150f86cf`
- 종류: read-only. HALT-0. DB·서비스 조작 무접촉. push 없음.

---

## 요지 (TL;DR)

- **Neo4j는 2026-05-01 12:05:08 UTC(정상 shutdown) 이후 무재기동. 다운 ≈ 3.5개월.** 지시서의 "≤08-03" 추정은 **반증**됨.
- **데이터 안전 = 정상.** 현행 인스턴스(타르볼 `~/neo4j`) 데이터 36M, 스토어 파일 온전, 종료 시 checkpoint(txId 41224) 정상 기록, `store_lock` 0바이트(정상 정지). 손상/유실 정황 0 → HALT 트리거 미발동.
- **근본원인 = 재기동 수단 부재.** 현행 인스턴스는 **타르볼 `~/neo4j`**인데 여기엔 launchd(auto-restart)가 **없음**. 유일한 Neo4j launchd(`homebrew.mxcl.neo4j.plist`)는 **이미 제거된 homebrew 바이너리**(`/opt/homebrew/opt/neo4j/bin/neo4j` 부재)를 가리키는 **죽은 엔트리**이며, 살아있어도 구(舊) Apr-3 데이터를 서빙. 05-01 종료 후 06-21·07-23 재부팅은 celery 워커(KeepAlive)만 복구했고 Neo4j는 복구하지 못함.
- **heat는 Neo4j 무의존.** compute_theme_heat / TNV 체이닝은 DB·뉴스 기반(`c3_narrative_service`)이라 Neo4j 다운의 영향을 받지 않음. 과거 "heat 6/11"은 **비체인·별개 커버리지 이슈**로, Neo4j 복구 신호로 쓸 수 없음(지시서 §3-2②의 heat 전제는 부정확 — 아래 대체 검증 제시).
- **Q19(co-mention)는 별개 사안 실측 고정.** Neo4j는 2026-04-30까지 데이터 쓰기가 있었고 05-01 종료 → co-mention 단절 시작(04-25)을 **6일 선행**. 04-25에 Neo4j는 살아있었으므로 co-mention 단절은 Neo4j 다운으로 설명 불가.

---

## §1 다운 진단 (실측)

### 1-1 다운 상태·시점 확정

| 항목 | 실측값 | 근거 명령/경로 |
|---|---|---|
| Neo4j 서버 프로세스 | **부재** (celery `-Q neo4j` 워커 15346만 생존) | `ps aux \| grep -i neo4j` |
| bolt 7687 리스너 | **없음** | `lsof -nP -iTCP:7687` → 무출력 |
| 현행 인스턴스 마지막 종료 | **2026-05-01 12:05:08 UTC** "Neo4j Server shutdown initiated by request" → Stopped, 이후 "Started" 없음 | `~/neo4j/logs/neo4j.log:1043`, `~/neo4j/logs/debug.log`(tail: Checkpoint @ txId 41224) |
| 현행 인스턴스 마지막 데이터 쓰기 | **2026-04-30 07:45 UTC** | `ls -lat ~/neo4j/data/databases/neo4j/` (neostore.*.db) |
| homebrew 인스턴스 마지막 종료 | 2026-04-03 05:01:34 UTC "Stopped" | `/opt/homebrew/var/log/neo4j.log`(마지막 줄) |
| 마지막 시스템 재부팅 | 2026-07-23 14:57, 2026-06-21 19:23 | `last reboot` |

- "≤08-03" 추정 **반증**: 실측 다운 개시 = 2026-05-01 12:05 UTC. 08-03·08-10은 heat 관측 시점일 뿐 다운 개시 시점이 아님(§2에서 heat는 Neo4j 무의존임을 별도 실측).
- 워커 로그(`~/worktrees/sv-worker-runtime/stocks.log`, mtime 08-13 11:30)에는 `ServiceUnavailable: Couldn't connect to localhost:7687 ... Connection refused` 시그니처 **12,680건** 누적(전 구간 실패). 단 이 로그는 선행 타임스탬프가 없어 다운 개시 시점 근거로는 서버 로그를 채택.
- neo4j-queue 워커(pid 15346)는 fd 3w를 `~/Desktop/stock_vis/stocks.log`에 물고 있으나 그 파일 mtime = **Jul 30 12:11**(그 이후 무기록) — Neo4j 상대 작업이 장기 무진행임을 방증.

### 1-2 launchd 등재 여부 (launchctl 미실행 — plist 파일 read-only 열람만)

- `~/Library/LaunchAgents/homebrew.mxcl.neo4j.plist`: `ProgramArguments = /opt/homebrew/opt/neo4j/bin/neo4j console`, `WorkingDirectory = /opt/homebrew/var/neo4j`, **KeepAlive 없음**, RunAtLoad=true.
  → 그러나 `/opt/homebrew/opt/neo4j/bin/neo4j` 및 `/opt/homebrew/Cellar/neo4j/*` **부재**(homebrew neo4j 제거됨). 이 plist는 **로드해도 기동 실패**하는 죽은 엔트리이며, 설령 데이터가 있어도 구(舊) Apr-3 스냅샷을 가리킴.
- `~/Library/LaunchAgents/com.stockvis.celery-worker-neo4j.plist`: KeepAlive=true → 워커 15346이 재부팅에도 살아있는 이유. (Neo4j 서버와 무관, 소비자 프로세스일 뿐)
- **타르볼 `~/neo4j`를 가리키는 launchd 없음** (`grep -rl "Users/byeongjinjeong/neo4j" ~/Library/LaunchAgents /Library/LaunchDaemons` → NONE). → 현행 인스턴스는 **자동 재기동 수단이 전무**.

### 1-3 원인 좁히기

- 프로세스 부재(기동 실패 반복 아님): 서버 로그가 05-01 정상 종료에서 깨끗이 끝나고 이후 로그 자체가 없음 = 재기동 시도조차 없었음. 포트/설정 문제 아님(정상 종료).
- 종결 근본원인: **① 현행(타르볼) 인스턴스에 launchd/KeepAlive 부재, ② 유일한 Neo4j launchd는 제거된 homebrew를 가리키는 무효 엔트리** → 05-01 수동/로그아웃성 종료 이후 어떤 재부팅(06-21·07-23)도 Neo4j를 되살리지 못함.

### 1-4 데이터 안전 실측 (HALT 트리거 검사 — 정상)

| 인스턴스 | du | 스토어 최신 mtime | 무결성 정황 |
|---|---|---|---|
| 타르볼 `~/neo4j/data` (현행) | **36M** | neostore.*.db = 2026-04-30 07:45, indexstats = 05-01 21:05(KST)=종료 checkpoint | `checkpoint.0` 존재, `neostore.transaction.db.0`(29MB), `store_lock` 0바이트 → 정상 정지. 손상 정황 0 |
| homebrew `/opt/homebrew/var/neo4j/data` (구) | 11M | 2026-04-03 17:55 | 잔존 아티팩트(레거시) |

→ 유실/손상 없음. 복구는 데이터 복원 없이 **현행 타르볼 인스턴스 기동만**으로 성립.

---

## §2 의존 지도

### 2-1 Neo4j 소비처 + 다운 기간 열화 양태

Neo4j 참조 코드(py, tests/migrations 제외):
`apps/chain_sight/graph/{repository,__init__}.py`, `apps/chain_sight/tasks/relation_tasks.py`, `packages/shared/metrics/services/daily_report.py`, `services/rag_analysis/services/{neo4j_driver,neo4j_service,graphrag_scorer,hybrid_search,pipeline}.py`, `services/rag_analysis/tasks.py`, `services/serverless/services/supply_chain_service.py`, `shared_kb/*`, `config/{settings,celery}.py`.

워커 로그 TASK FAILURE 분해(대표):

| 태스크 | 실패건수 | 열화 양태 |
|---|---|---|
| `metrics.tasks.send_agent_report_task` | 87 | **전체 실패** — `_neo4j_session()` 직접 드라이버 콜, graph 메트릭 try/except 부재(`daily_report.py:66-78,300`) |
| `metrics.tasks.send_daily_report_task` | 40 | **전체 실패**(동상) |
| `config.tasks.send_celery_error_digest` | 39 | 상위 실패 캐스케이드 |
| `apps.chain_sight.tasks.relation_tasks.update_relation_confidence` | 36 | 전체 실패(로그 초기 구간·P1A `08adeabb`에서 Neo4j 콜 제거되어 사후 완화됨) |
| `services.news.tasks.collect_press_releases_fmp` | 25 | Neo4j 무관(FMP 경로) — 병존 노이즈 |
| `apps.chain_sight.tasks.relation_tasks.extract_co_mentions` | 9 | 전체 실패 |
| `...calculate_price_co_movement` | 5 | 전체 실패 |
| `services.serverless.tasks.build_patent_network` | 1 | 전체 실패 |

- **heat = 무영향(중요).** `apps/chain_sight/tasks/heat_tasks.py`(compute_theme_heat_task) 및 `heat_synthesis/heat_components/sector_heatmap_service`에 Neo4j 진입점 0. TNV 체이닝은 `c3_narrative_service.aggregate_theme_news_volume`(DB/뉴스)라 Neo4j 무관. heat는 실패 목록에도 없음. → 과거 "heat 6/11"은 Neo4j 다운과 무관한 별개 데이터 커버리지 이슈("비체인").
- 열화 양태 요약: 대다수 소비처가 **예외 전파형 전체 실패**(예외 삼킴·부분 계산 아님). `daily_report.py`는 graph 메트릭 세션을 try/except 없이 열어 태스크가 통째로 실패·retry 소진. RAG GraphRAG(`graphrag_scorer/hybrid_search/pipeline`)·shared_kb 온톨로지는 온디맨드 경로로 호출 시 동일하게 실패 예상.

### 2-2 Q19(co-mention) 분리 — 실측 고정

- Neo4j 생존 입증: 데이터 쓰기 **2026-04-30 07:45 UTC**, 정상 종료 **2026-05-01 12:05 UTC**.
- co-mention 단절 시작(Q19 트랙 기준선) = **04-25**. → Neo4j 다운(05-01)을 **6일 선행**하며, 04-25 시점 Neo4j는 정상 가동 중.
- ∴ co-mention 04-25 단절은 Neo4j 다운으로 **설명 불가 = 별개 사안**. 동일 원인 정황 없음.
- 한계 고지: 본 세션은 Neo4j-측 타임라인만 실측했고, "04-25 co-mention 단절" 신호 자체는 Q19 트랙 소관 데이터로 독립 재확인하지 않았음(범위 밖). 본 세션 기여 = Neo4j 다운 시점(05-01) 확정으로 **인과 배제**를 실측 근거로 고정.

---

## §3 상신

### 3-2 복구 절차서 초안 (병진 수동 실행용 — 본 세션 미실행)

**전제 확인(수동, read-only 명령):**
```
launchctl list | grep -i neo4j
#   기대: com.stockvis.celery-worker-neo4j (워커) = 존재
#         homebrew.mxcl.neo4j = 존재하더라도 바이너리 부재 → 로드/기동 실패하는 죽은 엔트리(사용 금지)
lsof -nP -iTCP:7687 | grep LISTEN     # 현재: 무출력(다운)
```
판독: `homebrew.mxcl.neo4j`를 `launchctl load` 하지 말 것 — 바이너리 부재로 실패하며, 데이터도 구 Apr-3 스냅샷.

**기동 명령 후보(현행 타르볼, 택1):**
```
# 관측하며 기동(권장, foreground)
~/neo4j/bin/neo4j console
# 또는 백그라운드
~/neo4j/bin/neo4j start && ~/neo4j/bin/neo4j status
```

**기동 후 검증 체크리스트:**
1. **bolt 7687 응답**
   ```
   lsof -nP -iTCP:7687 | grep LISTEN            # LISTEN 확인
   ~/neo4j/bin/cypher-shell -a bolt://localhost:7687 -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1;"
   ```
   - 인증 실패 시: .env `NEO4J_PASSWORD`(len=32)와 타르볼 auth 불일치 → 비밀번호 재설정 필요(디렉터 판단, 본 세션 auth 스토어 미변경).
2. **그래프 존재(1573노드 기준선 대조)**
   ```
   ~/neo4j/bin/cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "MATCH (n) RETURN count(n);"
   ```
   기대: 약 1,573노드대(과거 운영 기준선). 0이면 잘못된 데이터 디렉토리 기동.
3. **소비처 회복(heat 아님 — 지시서 §3-2② 대체)**
   - heat는 Neo4j 무의존이므로 "다음 heat 11/11"은 Neo4j 복구 신호로 **부적합**.
   - 올바른 복구 신호 = Neo4j 소비 태스크 성공: 다음 `metrics.tasks.send_daily_report_task`/`send_agent_report_task` 발화에서 `ServiceUnavailable` 소멸, 또는 즉시 확인용
     ```
     grep -c "Couldn't connect to localhost:7687" ~/worktrees/sv-worker-runtime/stocks.log   # 기동 후 증가 멈춤
     ```
   - Chain Sight 조회 API(`apps/chain_sight/api/views.py` 경유) 200 응답 확인.
4. **실패 시 판단 기준**
   - 기동 로그 `~/neo4j/logs/neo4j.log`에 bind(포트 점유)/auth 오류 → 원인별 대응.
   - "store is not cleanly shut down / recovery" 류 로그 = 손상 정황 → **즉시 HALT + 상신**(본 세션 실측상 checkpoint 정상이라 가능성 낮음).

### 3-3 조치 선택지 골격 (결정 = 디렉터)

- **(a) 단순 재기동으로 충분:** 데이터 온전·정상 종료 → 타르볼 기동만으로 즉시 복원 성립. 최소 개입.
- **(b) 재발 방지 설계 필요 (권장 근거 제시):** 현행 인스턴스에 auto-restart 수단이 전무하고, 유일한 Neo4j launchd는 제거된 homebrew를 가리키는 무효 엔트리라 **재부팅마다 재발**. 항구 조치 후보 —
  - ① 타르볼용 launchd(KeepAlive+RunAtLoad) 신설, 그리고 **죽은 `homebrew.mxcl.neo4j.plist` 제거**(혼선·오기동 위험 제거), 또는
  - ② homebrew neo4j 재설치 후 타르볼 36M 데이터를 이관하여 launchd 일원화.
  - 근거만 제시, 채택·집행은 디렉터 전권. (launchd 신설/plist 삭제는 서비스 조작 → 본 세션 범위 밖)

---

## 커밋 해시
- 지시서(§0-0): `150f86cf`
- 본 보고서: (커밋 후 세션 출력 말미에 명시)

**→ HALT (상신 종료)**
