# C-N-REPAIR 무인 자동화 — 활성화 런북 (디렉터 게이트)

> 산출: 2026-07-29 세션(`monorepo/sess-CN-repair`). 빌드·안전검증 완료. **활성화는 prod 쓰기+AV 소비 = 디렉터 명시 승인 후** ([[feedback_deploy_approval_explicit_quote]]).

## 산출물
| 파일 | 역할 |
|------|------|
| `scripts/cn_repair_nightly.sh` | 래퍼 — 순번 판정·1배치 실행·이상치 판정·알림·완료 자동 unload |
| `scripts/cn_repair_status.py` | 상태 머신(체크포인트 카운터·이상치 밴드, stdlib) |
| `docs/operations/com.stockvis.cn_repair.nightly.plist` | launchd plist (22:10 KST, RunAtLoad=false) |
| `tests/unit/ops/test_cn_repair_status.py` | 상태 머신 단위 테스트 9건 |

## 동작 요약
- **순번**: `status.json.next_batch`(기본 1). **성공 시에만 전진** → batch1 누락 방지(캘린더 산술 기각, D-CN-REPAIR-AUTO-CHECKPOINT).
- **하루 1배치**(AV 레이트리밋 보존). 22:10 KST(리마인더 22:00 뒤). 슬립 중 놓친 잡은 기상 시 실행(launchd StartCalendarInterval).
- **실행 트리**: `~/worktrees/sv-worker-runtime`(origin/main 추적, --dates·계획서 착지).
- **이상 시에만 알림**: `~/Library/Logs/stockvis/cn_repair/ALERT_YYYY-MM-DD.txt` + macOS 알림. 정상=무알림.
- **10/10 완료**: DONE 마커 + launchd 자동 unload + 다음 단계 안내.

## 검증 완료(안전분, 자율 수행)
- 신규 pytest 9 + 기존 backfill 11(멱등 3건 포함) = 20 passed
- 래퍼 dry-run: batch1→20창 매핑 정확·카운터 불변·무쓰기
- 완료 경로: next_batch=11 → DONE 안내(dry-run은 unload 안 함)
- 배치 매핑 1~10 = 192일(20×9+12), batch11=완료 경로
- 경계 GREEN(stdlib만)

## ⏸ 활성화 절차 (디렉터 승인 후에만 — 병진 수동 또는 명시 승인 인용)

### 사전(랜딩): 래퍼를 실행 트리에 착지
```bash
# 1) 이 세션 브랜치를 origin/main에 랜딩(no-ff, 별도 승인) 후:
cd /Users/byeongjinjeong/Desktop/stock_vis && bash scripts/worker_sync.sh   # sv-worker-runtime 동기화
# 2) 착지 확인
ls ~/worktrees/sv-worker-runtime/scripts/cn_repair_nightly.sh
```

### G1: 래퍼 라이브 dry-run(실행 트리에서, 무쓰기)
```bash
~/worktrees/sv-worker-runtime/scripts/cn_repair_nightly.sh --dry-run
# 기대: "다음 배치: 1 / 10" · "백필 대상: 20창" · status.json 미생성
```

### G2: 첫 배치 실수동 1회(--commit, prod 쓰기·AV ~20 req) — 멱등 IDENTICAL 실증
```bash
~/worktrees/sv-worker-runtime/scripts/cn_repair_nightly.sh          # 실행(batch1)
# → status.json: next_batch=2, history[0] 기록. saved>0 기대.
# 멱등 실증(2회째 = 카운터 무관, 커맨드 직접):
VENV=~/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin/python
cd ~/worktrees/sv-worker-runtime && $VENV manage.py backfill_broad_news --commit --max-requests 20 \
  --dates "$(sed -n 's/.*--dates "\([^"]*\)".*/\1/p' docs/features/cn_repair/repair_batch_plan.md | sed -n 1p)"
# 기대: "커버됨 skip: 20창 · 백필 대상: 0창" · saved 0(전량 이미 커버=IDENTICAL 증명)
```

### G3: launchd 등록 + kickstart 실측
```bash
cp docs/operations/com.stockvis.cn_repair.nightly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.stockvis.cn_repair.nightly.plist
launchctl list | grep cn_repair                      # 등록 확인
# 강제 1회(다음 배치 = batch2, prod 쓰기 주의):
launchctl kickstart -k gui/$(id -u)/com.stockvis.cn_repair.nightly
tail ~/Library/Logs/stockvis/cn_repair/nightly_$(date +%F).log   # 정상=무ALERT
```
> ⚠️ kickstart는 실배치를 돌린다(prod 쓰기). G2를 이미 했다면 batch2가 실행됨 → 순번이 하루 당겨짐(무해, 다음 밤부터 정상 리듬). kickstart 없이 다음 22:10 자연 실행만 기다려도 됨.

### 비활성/롤백
```bash
launchctl bootout gui/$(id -u)/com.stockvis.cn_repair.nightly
rm ~/Library/LaunchAgents/com.stockvis.cn_repair.nightly.plist
# 재수집 데이터는 멱등 upsert(추가/갱신)만 — 롤백해도 파괴 없음.
```

## 남은 결정(디렉터)
- **압축 실행**: rate-limit 이유라 기본 1배치/밤. 한 밤 다배치(sleep 간격)로 10일→단축 원하면 승인 필요.
- **Cowork 22:00 리마인더**: 완료 시 삭제 or "전날 밤 결과 요약 리포트"로 용도변경 — 별도 결정(수동 유보).
- **활성화 시점**: 지금 랜딩+활성화 vs 첫 배치만 수동 후 관찰.
