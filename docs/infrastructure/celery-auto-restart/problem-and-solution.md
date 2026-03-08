# 문제 배경 및 해결 방법

## 기존 문제

### 1. LaunchAgent exit code 78

기존 plist가 celery 바이너리를 직접 실행:

```xml
<!-- 기존 (문제) -->
<key>ProgramArguments</key>
<array>
    <string>/path/to/venv/bin/celery</string>
    <string>-A</string>
    <string>config</string>
    <string>worker</string>
    ...
</array>
```

launchd 환경에서는 사용자 shell 프로필(`.zshrc`, `.bash_profile`)이 로드되지 않으므로 `.env` 파일의 환경변수(DB 연결 정보, API 키 등)가 없는 상태로 실행 → Django settings 로드 실패 → **exit code 78** (configuration error).

### 2. 터미널 의존 실행

수동으로 터미널에서 `celery -A config worker -l info`를 실행하다가 터미널을 닫으면 프로세스도 함께 종료 → 데이터 수집 중단.

### 3. 장애 인지 불가

Worker/Beat가 조용히 죽어도 알림이 없어 한참 뒤에야 발견.

---

## 해결 방법

### Wrapper Script 도입 (exit 78 해결)

plist → wrapper shell script → celery 실행 구조로 변경:

```xml
<!-- 변경 후 -->
<key>ProgramArguments</key>
<array>
    <string>/bin/bash</string>
    <string>/path/to/scripts/celery-worker.sh</string>
</array>
```

Wrapper script가 하는 일:
1. `.env` 파일을 읽어서 환경변수로 `export` (주석, 빈 줄 안전 처리)
2. 주요 환경변수 로드 상태를 로그에 출력 (디버깅 용이)
3. `exec`으로 celery 실행 → 프로세스가 shell을 대체하여 PID 유지

### KeepAlive로 자동 재시작

plist의 `KeepAlive: true` 설정으로 프로세스가 어떤 이유로든 종료되면 launchd가 즉시 재시작합니다. `ThrottleInterval: 10`으로 최소 10초 간격을 두어 빠른 반복 실패 시 CPU 과부하를 방지합니다.

### Watchdog로 macOS 알림

별도 LaunchAgent가 5분마다 `celery-watchdog.sh`를 실행:
- `pgrep`으로 프로세스 존재 여부 확인
- 다운 감지 시 `osascript`로 macOS 알림 센터에 소리(Crystal) 포함 알림
- 플래그 파일(`/tmp/stockvis-*-down`)로 연속 알림 방지
- 복구 시 플래그 삭제 + 복구 알림

### CELERY_RESULT_EXTENDED

`config/settings.py`에 `CELERY_RESULT_EXTENDED = True` 추가:
- `django-db` result backend 사용 시 `task_name`, `task_args`, `task_kwargs`가 `TaskResult` 모델에 저장
- Admin Dashboard에서 태스크별 현황 조회 가능
