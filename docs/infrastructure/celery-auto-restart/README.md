# Celery 자동 재시작 + macOS 알림 시스템

Celery Worker/Beat가 중단되면 자동으로 재시작하고, macOS 알림 센터로 장애/복구를 알려주는 시스템입니다.

---

## 구성 요소

| 구성 요소 | 파일 | 역할 |
|----------|------|------|
| Worker Wrapper | `scripts/celery-worker.sh` | `.env` 로드 + celery worker 실행 |
| Beat Wrapper | `scripts/celery-beat.sh` | `.env` 로드 + celery beat 실행 |
| Watchdog | `scripts/celery-watchdog.sh` | 프로세스 감시 + macOS 알림 |
| Worker LaunchAgent | `~/Library/LaunchAgents/com.stockvis.celery-worker.plist` | 자동 시작 + 재시작 |
| Beat LaunchAgent | `~/Library/LaunchAgents/com.stockvis.celery-beat.plist` | 자동 시작 + 재시작 |
| Watchdog LaunchAgent | `~/Library/LaunchAgents/com.stockvis.celery-watchdog.plist` | 5분 간격 감시 |
| 서비스 관리 | `scripts/manage-services.sh` | 통합 start/stop/status/logs |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                  macOS launchd                       │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────┐          │
│  │ celery-worker    │  │ celery-beat      │          │
│  │ plist            │  │ plist            │          │
│  │ KeepAlive: true  │  │ KeepAlive: true  │          │
│  └────────┬─────────┘  └────────┬─────────┘          │
│           │                     │                    │
│           ▼                     ▼                    │
│  ┌──────────────────┐  ┌──────────────────┐          │
│  │ celery-worker.sh │  │ celery-beat.sh   │          │
│  │ 1. .env 로드     │  │ 1. .env 로드     │          │
│  │ 2. env 확인 로그 │  │ 2. env 확인 로그 │          │
│  │ 3. exec celery   │  │ 3. exec celery   │          │
│  └──────────────────┘  └──────────────────┘          │
│                                                      │
│  ┌──────────────────────────────────────────┐        │
│  │ celery-watchdog plist (StartInterval:300)│        │
│  └────────────────────┬─────────────────────┘        │
│                       │ 5분마다                       │
│                       ▼                              │
│  ┌──────────────────────────────────────────┐        │
│  │ celery-watchdog.sh                       │        │
│  │ 1. pgrep -f "celery.*worker"             │        │
│  │ 2. pgrep -f "celery.*beat"               │        │
│  │ 3. 다운 → macOS 알림 (소리: Crystal)      │        │
│  │ 4. 복구 → macOS 복구 알림                  │        │
│  └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────┘
```

---

## 상세 문서

- [문제 배경 및 해결 방법](./problem-and-solution.md)
- [파일별 상세 설명](./files-detail.md)
- [운영 가이드 (시작/중지/장애 시뮬레이션)](./operations-guide.md)
