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

## 로그 파일 목록

| 파일 | 내용 |
|------|------|
| `logs/celery-worker.log` | Worker stdout (환경변수 체크 + celery 출력) |
| `logs/celery-worker-error.log` | Worker stderr |
| `logs/celery-beat.log` | Beat stdout |
| `logs/celery-beat-error.log` | Beat stderr |
| `logs/celery-watchdog.log` | Watchdog 체크 결과 |
| `logs/celery-watchdog-error.log` | Watchdog 에러 |
