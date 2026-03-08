# 파일별 상세 설명

## 1. scripts/celery-worker.sh

Worker 실행 wrapper script.

```bash
#!/bin/bash
set -e

# 1. .env 안전 로드 (while read 패턴)
#    - 빈 줄, #으로 시작하는 주석, 공백만 있는 줄 무시
#    - export로 현재 shell 환경에 주입
while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# || "$line" =~ ^[[:space:]]*$ ]] && continue
    export "$line"
done < .env

# 2. 환경변수 확인 로그
#    - DB_HOST, API 키 존재 여부(SET/빈값) 등 출력
#    - logs/celery-worker.log에서 확인 가능

# 3. exec celery — PID가 shell에서 celery로 교체
exec "$VENV_DIR/bin/celery" -A config worker -l info --concurrency=4
```

**핵심 포인트**: `exec` 사용으로 wrapper shell이 종료되지 않고 celery 프로세스로 교체됩니다. launchd가 추적하는 PID가 그대로 celery 프로세스가 됩니다.

---

## 2. scripts/celery-beat.sh

Beat 실행 wrapper script. Worker와 동일 패턴이지만 실행 명령이 다릅니다:

```bash
exec "$VENV_DIR/bin/celery" -A config beat -l info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## 3. scripts/celery-watchdog.sh

프로세스 감시 + macOS 알림 스크립트.

### 알림 함수

```bash
notify() {
    local title="$1"
    local message="$2"
    osascript -e "display notification \"$message\" with title \"$title\" sound name \"Crystal\""
}
```

- `osascript`: macOS AppleScript 실행기
- `sound name "Crystal"`: 시스템 내장 알림 소리

### 프로세스 체크 로직

```
pgrep -f "celery.*worker" 실행
├── 프로세스 있음
│   └── 플래그 파일 있음? → 삭제 + "복구" 알림
└── 프로세스 없음
    └── 플래그 파일 없음? → 생성 + "중단" 알림
```

### 플래그 파일

| 파일 | 용도 |
|------|------|
| `/tmp/stockvis-worker-down` | Worker 다운 상태 플래그 |
| `/tmp/stockvis-beat-down` | Beat 다운 상태 플래그 |

플래그가 이미 있으면 알림을 보내지 않아 5분마다 반복 알림을 방지합니다.

---

## 4. LaunchAgent plist 파일

### com.stockvis.celery-worker.plist / celery-beat.plist

| 속성 | 값 | 설명 |
|------|---|------|
| `ProgramArguments` | `/bin/bash`, wrapper script 경로 | 바이너리 직접 실행 → wrapper로 변경 |
| `WorkingDirectory` | 프로젝트 루트 | `.env` 상대 경로 해석용 |
| `RunAtLoad` | `true` | 로그인 시 자동 시작 |
| `KeepAlive` | `true` | 종료 시 즉시 재시작 |
| `ThrottleInterval` | `10` | 재시작 최소 간격(초) |
| `StandardOutPath` | `logs/celery-*.log` | stdout 로그 |
| `StandardErrorPath` | `logs/celery-*-error.log` | stderr 로그 |

### com.stockvis.celery-watchdog.plist

| 속성 | 값 | 설명 |
|------|---|------|
| `StartInterval` | `300` | 5분(300초) 간격 실행 |
| `RunAtLoad` | `true` | 로드 즉시 첫 체크 |

---

## 5. config/settings.py 변경

```python
# 추가된 설정
CELERY_RESULT_EXTENDED = True
```

이 설정으로 `django_celery_results`의 `TaskResult` 모델에 다음 필드가 추가 저장됩니다:
- `task_name`: 실행된 태스크 이름 (예: `stocks.tasks.sync_daily_prices`)
- `task_args`: 태스크 인자
- `task_kwargs`: 태스크 키워드 인자

---

## 6. scripts/manage-services.sh 변경

기존 worker/beat만 관리하던 것에 watchdog을 추가:

```bash
# 추가된 plist 변수
WATCHDOG_PLIST="$HOME/Library/LaunchAgents/com.stockvis.celery-watchdog.plist"

# start/stop에 watchdog 포함
# status에 watchdog 상태 표시
# logs에 watchdog 옵션 추가
```

`stop` 시 watchdog을 먼저 중지하여 불필요한 다운 알림을 방지합니다.
