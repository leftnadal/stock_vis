# macOS Tahoe — cron 전체 디스크 접근 권한 설정

> macOS Tahoe (한글 OS) 기준 | 2026-04-16 작성
> 이 설정이 없으면 crontab에 등록된 작업이 **조용히 실패**합니다 (에러 로그도 남지 않음)

---

## 왜 필요한가?

macOS는 보안 정책상 `cron` 데몬이 사용자 홈 디렉토리(`~/`)의 파일에 접근하는 것을 기본 차단합니다.
전체 디스크 접근 권한(Full Disk Access)을 부여해야 crontab 작업이 정상 실행됩니다.

**증상**: crontab은 등록되어 있으나 실행 흔적이 전혀 없음 (로그 파일 미생성, 커밋 없음)

---

## 설정 방법

### 1단계: 시스템 설정 열기

터미널에서 아래 명령어를 실행하면 해당 설정 화면이 바로 열립니다:

```bash
open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
```

또는 수동으로:

```
 메뉴 → 시스템 설정 → 개인정보 보호 및 보안 → 전체 디스크 접근 권한
```

---

### 2단계: cron 추가

1. 화면 하단의 **`+`** 버튼 클릭
2. **Touch ID** 또는 **비밀번호** 입력하여 잠금 해제
3. Finder 파일 선택 창이 열림

---

### 3단계: 숨김 폴더로 이동 (핵심)

`/usr/sbin`은 Finder에서 기본적으로 보이지 않는 숨김 경로입니다.

1. 파일 선택 창에서 **`⌘ + ⇧ + G`** (Command + Shift + G) 누름
2. **"폴더로 이동"** 입력란이 나타남
3. 아래 경로를 정확히 입력:

```
/usr/sbin
```

4. **Enter** 또는 **"이동"** 클릭

> 만약 파일이 안 보이면: **`⌘ + ⇧ + .`** (Command + Shift + 마침표)를 눌러 숨김 파일 표시를 켜세요

---

### 4단계: cron 선택

1. 파일 목록에서 **`cron`** 을 찾아 클릭
2. **"열기"** 버튼 클릭

---

### 5단계: 토글 확인

목록에 `cron`이 추가된 후 **토글이 켜짐(ON) 상태**인지 확인합니다.

```
cron          ✅ 켜짐
```

---

### 6단계 (권장): Terminal도 추가

같은 화면에서 `+` 버튼을 다시 눌러:

1. **`⌘ + ⇧ + G`** → `/System/Applications/Utilities` 입력 → Enter
2. **터미널.app** 선택 → **"열기"**

최종 상태:

```
cron          ✅ 켜짐
터미널        ✅ 켜짐
```

---

## 설정 후 확인

재부팅은 필요 없습니다. 바로 테스트:

```bash
# 현재 시각 + 2분 후로 임시 crontab 등록
echo "$(( $(date +%M) + 2 )) $(date +%H) * * * echo 'cron works' > /tmp/cron_test.txt" | crontab -

# 2분 후 확인
cat /tmp/cron_test.txt
# "cron works" 가 출력되면 성공

# 테스트 후 원래 crontab 복원
crontab -e
```

또는 기존 nightly 스크립트를 현재 시각 +2분으로 임시 변경하여 테스트:

```bash
# 현재 crontab 백업
crontab -l > /tmp/crontab_backup.txt

# 확인 후 복원
crontab /tmp/crontab_backup.txt
```

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `+` 버튼이 비활성 | 잠금 해제 안 됨 | Touch ID / 비밀번호로 잠금 해제 |
| `/usr/sbin`에서 cron이 안 보임 | 숨김 파일 미표시 | `⌘ + ⇧ + .` 으로 숨김 파일 켜기 |
| "폴더로 이동" 대화상자가 안 뜸 | 단축키 오류 | 파일 선택 창이 활성 상태에서 `⌘ + ⇧ + G` 재시도 |
| 추가했는데도 cron 작업 안 됨 | PATH 문제 | crontab에 `PATH=...` 명시 (현재 설정 확인) |
| 추가했는데도 cron 작업 안 됨 | claude CLI 인증 | `claude --version` 이 cron 환경에서 되는지 확인 |
