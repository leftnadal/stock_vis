# 운영 가이드

## 초기 설정

### 1. 권한 설정

```bash
chmod +x scripts/celery-worker.sh scripts/celery-beat.sh scripts/celery-watchdog.sh
```

### 2. 기존 LaunchAgent 교체

```bash
# 기존 서비스 중지
launchctl unload ~/Library/LaunchAgents/com.stockvis.celery-worker.plist 2>/dev/null
launchctl unload ~/Library/LaunchAgents/com.stockvis.celery-beat.plist 2>/dev/null

# 새 서비스 시작 (watchdog 포함)
./scripts/manage-services.sh start
```

### 3. 환경변수 로드 확인

```bash
tail -20 logs/celery-worker.log
```

다음과 같은 로그가 출력되어야 합니다:

```
[Mon Mar  3 10:00:00 KST 2026] .env loaded successfully
[Mon Mar  3 10:00:00 KST 2026] === Environment Check ===
  DJANGO_SETTINGS_MODULE=config.settings
  DB_HOST=(default)
  DB_NAME=(default)
  ALPHA_VANTAGE_API_KEY=SET
  FMP_API_KEY=SET
  GEMINI_API_KEY=SET
  CELERY_BROKER_URL=redis://localhost:6379/0
===========================
```

`SET`이 표시되지 않는 키가 있으면 `.env` 파일을 확인하세요.

---

## 일상 운영

### 서비스 관리

```bash
# 상태 확인
./scripts/manage-services.sh status

# 전체 시작
./scripts/manage-services.sh start

# 전체 중지
./scripts/manage-services.sh stop

# 전체 재시작
./scripts/manage-services.sh restart
```

### 로그 확인

```bash
# Worker 로그
./scripts/manage-services.sh logs worker

# Beat 로그
./scripts/manage-services.sh logs beat

# Watchdog 로그
./scripts/manage-services.sh logs watchdog

# 에러 로그 (모든 서비스)
./scripts/manage-services.sh logs errors
```

---

## 장애 시뮬레이션

### Worker 장애 테스트

```bash
# 1. Worker 프로세스 강제 종료
kill $(pgrep -f "celery.*worker")

# 2. 확인 사항:
#    a) launchd가 즉시 재시작 (KeepAlive: true)
pgrep -f "celery.*worker"  # 새 PID 확인

#    b) 5분 이내 macOS 알림 (소리: Crystal)
#       "Stock-Vis 장애 — Celery Worker 중단됨!"

#    c) 플래그 파일 생성
ls -la /tmp/stockvis-worker-down

#    d) 다음 watchdog 주기에 복구 알림
#       "Stock-Vis 복구 — Celery Worker 복구됨"

#    e) 플래그 파일 삭제
ls -la /tmp/stockvis-worker-down  # 없어야 정상
```

### Beat 장애 테스트

```bash
kill $(pgrep -f "celery.*beat")
# 동일한 복구 흐름 확인
```

### Watchdog 수동 실행

```bash
# 즉시 체크 (5분 대기 없이)
./scripts/celery-watchdog.sh
```

---

## 트러블슈팅

### exit code 78이 여전히 발생하는 경우

```bash
# 1. wrapper script가 실행 가능한지 확인
ls -la scripts/celery-worker.sh
# -rwxr-xr-x 확인

# 2. plist가 wrapper를 가리키는지 확인
cat ~/Library/LaunchAgents/com.stockvis.celery-worker.plist | grep -A2 ProgramArguments
# /bin/bash + wrapper script 경로 확인

# 3. .env 파일 존재 확인
ls -la .env

# 4. 에러 로그 확인
cat logs/celery-worker-error.log
```

### macOS 알림이 오지 않는 경우

```bash
# 1. 알림 권한 확인
# 시스템 설정 → 알림 → Script Editor 또는 osascript 허용 확인

# 2. watchdog이 실행 중인지 확인
launchctl list | grep watchdog

# 3. 수동 알림 테스트
osascript -e 'display notification "테스트 알림" with title "Stock-Vis" sound name "Crystal"'
```

### 연속 알림이 오는 경우

```bash
# 플래그 파일 확인
ls -la /tmp/stockvis-*-down

# 수동으로 플래그 생성 (알림 중지)
touch /tmp/stockvis-worker-down

# 수동으로 플래그 삭제 (알림 재활성화)
rm /tmp/stockvis-worker-down
```

---

## 머신 재구축 / LaunchAgent plist 재생성 체크리스트

> ⚠️ plist 파일(`~/Library/LaunchAgents/com.stockvis.celery-{worker,beat}.plist`)은 **repo 밖 = 머신 로컬**이다. 머신 재구축·OS 재설치·plist 손상 시 **아래를 재적용**해야 한다. (2026-07-10 tz 사고 근원 = beat plist만 메인 repo 경로를 가리키는 **비대칭** 상태였음 → Bug #28 재변질.)

1. **경로 대칭 확인 (가장 중요)** — worker·beat **양쪽** plist의 `ProgramArguments`와 `WorkingDirectory`가 **둘 다** 런타임 트리(`~/worktrees/sv-worker-runtime/scripts/*.sh`)를 가리키는지 확인:

   ```bash
   for svc in worker beat; do
     echo "=== $svc ==="
     plutil -extract ProgramArguments xml1 -o - ~/Library/LaunchAgents/com.stockvis.celery-$svc.plist | grep sv-worker-runtime
     plutil -extract WorkingDirectory  raw  -o - ~/Library/LaunchAgents/com.stockvis.celery-$svc.plist
   done
   ```

   - **메인 편집 repo 경로(`~/Desktop/stock_vis`)를 가리키면 안 된다.** 브랜치 표류한 메인 repo는 stale `config/celery.py`를 로드 → `DatabaseScheduler`의 주기 sync가 DB 스케줄을 옛 dict로 변질시킨다 ([common-bugs #28](../../../sub_claude_md/common-bugs.md) 참조).
   - worker만 런타임 트리·beat는 메인 repo인 **비대칭**이 2026-07-10 사고 원인. 반드시 **둘 다** 런타임 트리.

2. **경로 변경 시 재적재** — `launchctl kickstart`(단순 재기동)로는 plist 변경이 반영되지 않는다. **bootout → bootstrap** 필수:

   ```bash
   launchctl bootout   gui/$(id -u) ~/Library/LaunchAgents/com.stockvis.celery-beat.plist
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.stockvis.celery-beat.plist
   # worker도 동일
   ```

3. **beat DB 스케줄 재점** — 재적재 후 UTC 고정 태스크를 재등록·검증:

   ```bash
   cd ~/worktrees/sv-worker-runtime
   python manage.py register_news_av_beat --apply
   # 검증: collect-av-broad-news 의 CrontabSchedule tz=UTC (crontab id=101)
   python manage.py shell -c "from django_celery_beat.models import PeriodicTask; \
     pt=PeriodicTask.objects.get(name='collect-av-broad-news'); \
     print('tz=', pt.crontab.timezone, 'crontab.id=', pt.crontab_id, 'enabled=', pt.enabled)"
   ```

4. **좀비 beat 0 확인** — `ps aux | grep 'celery.*beat'` → **정확히 1개** (launchd 관리 프로세스만).

> UTC 고정이 필요한 beat 태스크는 `config/celery.py`의 `beat_schedule` dict에 두지 않고 `register_news_av_beat` 전용 관리명령으로만 등록한다(dict crontab은 `CELERY_TIMEZONE`=ET로 해석되어 변질). 근거·상세: [common-bugs #28](../../../sub_claude_md/common-bugs.md).

---

## 로그 파일 목록

| 파일 | 내용 |
|------|------|
| `logs/celery-worker.log` | Worker stdout (환경변수 체크 + celery 출력) |
| `logs/celery-worker-error.log` | Worker stderr |
| `logs/celery-beat.log` | Beat stdout |
| `logs/celery-beat-error.log` | Beat stderr |
| `logs/celery-watchdog.log` | Watchdog 체크 결과 |
| `logs/celery-watchdog-error.log` | Watchdog 에러 |
