# Slice 8 Part 2 — 사전 점검 지시서

> **목적:** Part 2 본 작업 진입 전 (1) 환경 이슈 처리 (E2+F4) + (2) 사실관계 점검 동시 완료

---

## 메타

| 항목      | 값                                      |
| --------- | --------------------------------------- |
| 작성일    | 2026-05-16                              |
| 브랜치    | `slice8`                                |
| 시작 상태 | 회귀 414 / 비용 $1.595 / 부채 4건 close |
| 비용      | $0 (LLM 호출 없음)                      |
| 회귀 예상 | +0~3 (hook 단위 테스트 정도)            |
| 예상 시간 | 60~90분                                 |

---

## Step Q-1: E2 iCloud 이중 경로 표지

### 목적

실수로 iCloud 측 작업 진입 시 즉시 인지 가능하도록 표지 2건 설치.

### 작업

**1. iCloud 측 경고 표지**

```bash
# iCloud 복사본 루트 위치 확인 (사용자 답변 필요 시 묻기)
# 일반적 경로: ~/Library/Mobile Documents/com~apple~CloudDocs/.../stock_vis/

cat > <iCloud_path>/stock_vis/DO_NOT_EDIT_USE_DESKTOP.md << 'EOF'
# ⚠️ 이 디렉토리는 백업용입니다

**작업 금지.** 모든 작업은 다음 경로에서 진행하세요:

```

/Users/byeongjinjeong/Desktop/stock_vis

```

이 iCloud 복사본은 동기화 백업이며, 직접 편집 시 양 경로 간 충돌 위험이 있습니다.

- 작성일: 2026-05-16
- 정책 근거: Slice 8 Part 1 사고 후속 (#38)
- 결정 출처: docs/portfolio/coach/slice8/part1_closing.md
EOF
```

**2. Desktop 측 표지**

```bash
cat > /Users/byeongjinjeong/Desktop/stock_vis/WORKSPACE_ROOT.md << 'EOF'
# ✅ Source of Truth — Stock-Vis Portfolio Coach

**이 경로가 실제 작업 디렉토리입니다.**

```

/Users/byeongjinjeong/Desktop/stock_vis

```

iCloud 측 복사본(`~/Library/Mobile Documents/.../stock_vis`)은 백업용이며 직접 편집 금지.

- 작성일: 2026-05-16
- 정책 근거: Slice 8 Part 1 사고 후속 (#38)
- 검증 방법: 새 작업 시작 시 `pwd` 명령으로 이 경로 확인
EOF
```

**3. .gitignore 추가 (선택)**

- Desktop 측 `WORKSPACE_ROOT.md`는 git tracked로 유지 (영구 자산)
- iCloud 측 표지는 iCloud 자체 동기화로 양쪽에 전파될 가능성 → 한 번만 만들고 확인

### KPI

- [ ] iCloud 측 `DO_NOT_EDIT_USE_DESKTOP.md` 존재 확인
- [ ] Desktop 측 `WORKSPACE_ROOT.md` 존재 확인
- [ ] Desktop 측 표지 git commit (메시지: `[slice8] add WORKSPACE_ROOT.md (#38)`)
- [ ] 회귀 0건 추가 (docs only)

### 실패 시

- iCloud 경로 미상: 사용자에게 구체 경로 문의 후 진행
- iCloud 측 권한 오류: read-only 마운트 가능성 → 사용자 확인

---

## Step Q-2: F4 pre-commit hook 브랜치/경로 검증

### 목적

브랜치 자동 전환 사고(`fix/*-20260516`) 재발 차단 + Desktop 외 경로 작업 차단.

### 대상 파일

- `.git/hooks/pre-commit` (신규)
- `docs/portfolio/coach/slice8/pre_commit_policy.md` (신규, 정책 문서)

### 작업

**1. pre-commit hook 작성**

```bash
cat > .git/hooks/pre-commit << 'HOOKEOF'
#!/bin/bash
# Slice 8 Part 2 — pre-commit 브랜치/경로 검증
# 부채 #39 (Slice 8 Part 2 사이드 산출물)

set -e

# === 1. 브랜치 화이트리스트 검증 ===
CURRENT_BRANCH=$(git branch --show-current)
ALLOWED_BRANCHES=("main" "portfolio" "slice8" "slice9")  # 슬라이스 진행 시 갱신

BRANCH_OK=false
for allowed in "${ALLOWED_BRANCHES[@]}"; do
    if [ "$CURRENT_BRANCH" = "$allowed" ]; then
        BRANCH_OK=true
        break
    fi
done

if [ "$BRANCH_OK" = false ]; then
    echo "❌ pre-commit 차단: 비화이트리스트 브랜치 '$CURRENT_BRANCH'"
    echo ""
    echo "  허용 브랜치: ${ALLOWED_BRANCHES[*]}"
    echo "  의심: 자동 브랜치 전환 도구 (#40 추적 중)"
    echo ""
    echo "  해결:"
    echo "    git branch --show-current  # 현재 브랜치 확인"
    echo "    git checkout slice8         # 원하는 브랜치로 이동"
    echo "    git cherry-pick <commit>    # 필요 시 작업 이전"
    exit 1
fi

# === 2. 작업 경로 검증 ===
EXPECTED_PATH="/Users/byeongjinjeong/Desktop/stock_vis"
CURRENT_PATH=$(pwd)

# realpath로 심볼릭 링크 해소 (macOS 호환)
if command -v realpath > /dev/null; then
    CURRENT_REAL=$(realpath "$CURRENT_PATH")
    EXPECTED_REAL=$(realpath "$EXPECTED_PATH")
else
    CURRENT_REAL="$CURRENT_PATH"
    EXPECTED_REAL="$EXPECTED_PATH"
fi

if [ "$CURRENT_REAL" != "$EXPECTED_REAL" ]; then
    echo "⚠️  pre-commit 경고: 비표준 작업 경로"
    echo ""
    echo "  현재: $CURRENT_REAL"
    echo "  표준: $EXPECTED_REAL"
    echo ""
    echo "  iCloud 측 작업 의심. 확인 후 진행하세요."
    echo "  (강제 차단 아님 — 의도적 작업이면 계속 진행)"
fi

echo "✅ pre-commit 검증 통과 (branch=$CURRENT_BRANCH)"
exit 0
HOOKEOF

chmod +x .git/hooks/pre-commit
```

**2. 정책 문서 작성**

````bash
cat > docs/portfolio/coach/slice8/pre_commit_policy.md << 'POLICYEOF'
# pre-commit hook 정책

## 정책
- 브랜치 화이트리스트: main / portfolio / slice<N>
- 작업 경로: /Users/byeongjinjeong/Desktop/stock_vis (경고만)
- 부채 ID: #39

## 화이트리스트 갱신 시점
새 슬라이스 진입 시 `ALLOWED_BRANCHES` 배열에 추가:
```bash
ALLOWED_BRANCHES=("main" "portfolio" "slice8" "slice9" "slice10" ...)
````

## hook 비활성화 (긴급 시만)

```bash
git commit --no-verify -m "..."
```

- 사용 시 commit message에 사유 명시
- Slice 종결 보고서에 비활성화 회수 기록

## 사고 학습 케이스

- 2026-05-16: Slice 8 Part 1에서 `fix/*-20260516` 자동 전환 발생 (도구 미상, #40 추적 중)
  POLICYEOF

````

**3. 단위 테스트 (수동)**
- 정상 케이스: `slice8` 브랜치에서 commit → 통과 확인
- 차단 케이스: 임시 브랜치 생성 후 commit 시도 → 차단 확인 후 다시 `slice8`로 복귀

### KPI
- [ ] `.git/hooks/pre-commit` 존재 + 실행 권한 부여
- [ ] 정상 케이스 통과 확인 (Step Q-1 commit에서 자동 검증)
- [ ] 차단 케이스 확인 (수동 테스트 1회)
- [ ] 정책 문서 작성 완료

### 주의
- `.git/hooks/`는 git tracked가 아니므로, 다른 환경(iCloud 등)에서는 hook 부재 가능 → Desktop 단독 작업 정책으로 보완
- 향후 `husky` 같은 도구로 tracked hook 도입 검토 가능 (Slice 9 후보)

---

## Step Q-3: F4 자동 브랜치 전환 도구 원인 규명 (#40)

### 목적
`fix/*-20260516` 형태 브랜치를 자동 생성/전환한 도구 식별 → 비활성화 또는 격리.

### 추적 후보 (가능성 순)

1. **VS Code Git Lens / Git Graph 자동 동작**
   - 설정: VS Code → Settings → "git.branchAutoCreate" 검색
2. **GitHub Desktop / GitKraken 등 외부 GUI**
   - 프로세스 확인: `ps aux | grep -E "GitHub|GitKraken|Sourcetree"`
3. **다른 AI/자동화 도구** (Cursor 등)
   - `ps aux | grep -iE "cursor|copilot|continue"`
4. **GitHub Actions / Pre-push hook 잔재**
   - `ls -la .github/workflows/`
   - `ls -la .git/hooks/`
5. **macOS launchctl 자동 작업**
   - `launchctl list | grep -i git`

### 작업

```bash
# 후보 1: VS Code 설정 확인
code --list-extensions 2>/dev/null | grep -iE "git|lens|graph" > /tmp/vscode_git_ext.log

# 후보 2: 외부 GUI 프로세스 확인
ps aux | grep -E "GitHub Desktop|GitKraken|Sourcetree|Tower|Fork" | grep -v grep > /tmp/git_gui_processes.log

# 후보 3: AI 도구 프로세스 확인
ps aux | grep -iE "cursor|copilot|continue|tabnine" | grep -v grep > /tmp/ai_tool_processes.log

# 후보 4: GitHub Actions 잔재
find .github -type f 2>/dev/null > /tmp/github_workflows.log
ls -la .git/hooks/ > /tmp/git_hooks.log

# 후보 5: macOS daemon
launchctl list 2>/dev/null | grep -iE "git|github" > /tmp/launchctl_git.log

# 후보 6: git reflog로 자동 전환 패턴 추적
git reflog | grep -iE "fix/.*-2026" | head -20 > /tmp/branch_switch_reflog.log
````

### 보고

점검 보고서에 다음 포함:

- 각 후보별 검출 결과 (검출 / 미검출)
- 가장 의심 가는 후보 1~2개
- 즉시 비활성화 가능 여부

### KPI

- [ ] 6개 후보 모두 점검 완료
- [ ] 결과 보고서에 기록
- [ ] 원인 식별 시: 즉시 비활성화 또는 사용자에게 결정 위임
- [ ] 원인 미식별 시: pre-commit hook으로 차단 유지, #40 keep_open

---

## Step Q-4: 사실관계 점검 (Part 2 지시서 작성 입력)

### 목적

Part 2 임무(#28 output schema action_items 강제 슬롯) 작성에 필요한 코드베이스 사실 수집.

### 점검 항목

#### R1. `portfolio/llm/` 현재 구조 (Part 1 commits 이후)

```bash
ls -la portfolio/llm/
wc -l portfolio/llm/*.py
```

**보고:** 파일 목록 + 각 라인 수 + Part 1 변경 반영 상태

#### R2. `portfolio/schemas/` 현재 구조 (Part 1 #27 schema close 이후)

```bash
ls -la portfolio/schemas/
wc -l portfolio/schemas/*.py
grep -l "TimeSeriesContext" portfolio/schemas/*.py
grep -l "commentary" portfolio/schemas/*.py
```

**보고:**

- 모든 `.py` 파일 목록
- `TimeSeriesContext` 정의 위치
- commentary input schema 파일명 및 위치
- **output schema 파일 존재 여부** (가장 중요)

#### R3. 기존 output schema 존재 여부

```bash
grep -rn "class.*Output" portfolio/schemas/ portfolio/llm/ 2>/dev/null
grep -rn "class.*Commentary" portfolio/schemas/ portfolio/llm/ 2>/dev/null
grep -rn "action_items" portfolio/ 2>/dev/null
grep -rn "ActionItem" portfolio/ 2>/dev/null
```

**보고:**

- 기존 output 모델 정의 (있다면 시그니처 전부)
- `action_items` 또는 `ActionItem` 기존 정의 (있다면 위치 + 시그니처)
- 기존 commentary 출력 schema가 어디서 어떻게 정의되는지

#### R4. 진입점별 output 처리 흐름

```bash
# 진입점별 commentary 생성 service 위치 확인
find portfolio -name "*service*" -name "*.py" | head -20
grep -l "def.*commentary" portfolio/**/*.py 2>/dev/null | head -10

# DIMENSION_LOOKUP (Slice 4 도입) 현재 상태
grep -rn "DIMENSION_LOOKUP" portfolio/ 2>/dev/null
```

**보고:**

- 진입점별 service 파일 위치
- DIMENSION_LOOKUP 정의 위치 + 현재 entry 수 (E1~E6 + e3_portfolio + ?)
- output schema가 service에서 어떻게 사용되는지

#### R5. 기존 fixture에서 output 형태

```bash
# Part 1 smoke fixture (있다면)
ls -la portfolio/tests/fixtures/ 2>/dev/null
ls -la tests/portfolio/coach/slice*/fixtures/ 2>/dev/null

# 기존 output snapshot
find portfolio/tests -name "*snapshot*" -o -name "*output*" | head -10
```

**보고:**

- output snapshot 파일 위치 (있다면)
- 기존 LLM 응답 fixture 위치
- Part 1 추가 fixture와의 관계

#### R6. Part 1에서 추가된 산출물 검증

```bash
# Part 1 commits에서 추가된 파일 목록
git diff --name-only <slice7_final>..HEAD | head -30

# 부채 처리 상태 점검
cat docs/portfolio/coach/slice8/part1_closing.md 2>/dev/null | head -50
```

**보고:**

- Part 1 추가 파일 12건 실제 위치
- 종결 보고서 KPI 재확인

### KPI

- [ ] R1~R6 모두 보고서 작성 완료
- [ ] 보고서 위치: `docs/portfolio/coach/slice8/phase1_findings_part2.md`

---

## Step Q-5: 사전 점검 보고서 작성

### 대상 파일

`docs/portfolio/coach/slice8/phase1_findings_part2.md`

### 보고서 템플릿

```markdown
# Slice 8 Part 2 — 사전 점검 보고서

## Q-1 E2 iCloud 표지 결과

- [ ] iCloud 측 DO_NOT_EDIT_USE_DESKTOP.md 작성: PASS/FAIL
- [ ] Desktop 측 WORKSPACE_ROOT.md 작성: PASS/FAIL
- [ ] Desktop 표지 commit: \_\_\_
- 부채 #38: close

## Q-2 F4 pre-commit hook 결과

- [ ] hook 설치: PASS/FAIL
- [ ] 실행 권한: PASS/FAIL
- [ ] 정상 케이스 통과: PASS/FAIL
- [ ] 차단 케이스 확인: PASS/FAIL
- [ ] 정책 문서 작성: PASS/FAIL
- 부채 #39: close

## Q-3 자동 브랜치 전환 도구 추적 결과

- 후보 1 (VS Code Git extensions): 검출/미검출, 의심 도구: \_\_\_
- 후보 2 (외부 Git GUI): 검출/미검출
- 후보 3 (AI 도구): 검출/미검출
- 후보 4 (GitHub Actions / hooks): 검출/미검출
- 후보 5 (macOS launchctl): 검출/미검출
- 후보 6 (reflog 패턴): \_\_\_
- **가장 의심 후보:** \_\_\_
- 즉시 비활성화 가능: 예/아니오
- 부채 #40: close / keep_open

## Q-4 사실관계 점검 결과

### R1. portfolio/llm/ 현재 구조

- 파일 목록:
  - cost_guard.py (\_\_\_줄)
  - token_budgets.py (\_\_\_줄)
  - budget_estimator.py (\_\_\_줄)
  - exceptions.py (\_\_\_줄)
  - 기타: \_\_\_

### R2. portfolio/schemas/ 현재 구조

- 파일 목록: \_\_\_
- TimeSeriesContext 위치: \_\_\_
- commentary input schema 파일: \_\_\_
- **output schema 파일 존재 여부:** 예/아니오, 위치 \_\_\_

### R3. 기존 output schema

- 기존 output 모델: \_\_\_
- action_items 기존 정의: 예/아니오, 위치 \_\_\_
- ActionItem 기존 정의: 예/아니오, 위치 \_\_\_
- 기존 commentary 출력 schema: \_\_\_

### R4. 진입점별 output 처리 흐름

- service 파일 위치: \_\_\_
- DIMENSION_LOOKUP 위치: \_\_\_
- 현재 entry 수: \_\_\_
- output schema 사용 방식: \_\_\_

### R5. 기존 fixture에서 output 형태

- fixture 위치: \_\_\_
- snapshot 위치: \_\_\_
- 기존 LLM 응답 fixture: \_\_\_

### R6. Part 1 산출물 검증

- 추가 파일 12건 실제 위치 (한 줄씩):
  - ***
- 종결 보고서 KPI 재확인: PASS/FAIL

## Phase 2 진입 준비 완료 여부

- [ ] 환경 이슈 처리 (E2 + F4) 완료
- [ ] 사실관계 점검 6종 완료
- [ ] 사용자 회수 대기

## 신규 발견 (있을 시)

- Part 2 작업에 영향을 줄 만한 예상외 코드베이스 상태: \_\_\_
- 추가 부채 후보: \_\_\_
```

### KPI

- [ ] 보고서 파일 작성 완료
- [ ] Q-1 ~ Q-4 모든 빈칸 \_\_\_ 채워짐

---

## 산출물 체크리스트

| #   | 산출물           | 위치                                                      | 부채 |
| --- | ---------------- | --------------------------------------------------------- | ---- |
| 1   | iCloud 표지      | iCloud 측 stock_vis/DO_NOT_EDIT_USE_DESKTOP.md            | #38  |
| 2   | Desktop 표지     | /Users/byeongjinjeong/Desktop/stock_vis/WORKSPACE_ROOT.md | #38  |
| 3   | pre-commit hook  | .git/hooks/pre-commit                                     | #39  |
| 4   | hook 정책 문서   | docs/portfolio/coach/slice8/pre_commit_policy.md          | #39  |
| 5   | 도구 추적 로그   | /tmp/\*.log (참조용)                                      | #40  |
| 6   | 사전 점검 보고서 | docs/portfolio/coach/slice8/phase1_findings_part2.md      | —    |

---

## 실행 순서

```
1. Q-1 E2 표지        (iCloud + Desktop, commit)
2. Q-2 F4 hook        (작성 + 권한 + 테스트)
3. Q-3 도구 추적      (6 후보 점검)
4. Q-4 사실관계       (R1~R6 점검, 코드 변경 없음)
5. Q-5 보고서 작성    (phase1_findings_part2.md)
6. 사용자 회수        → Part 2 지시서 v2 작성 단계
```

---

## 위험 신호 및 대응

| 조건                                        | 처리                                              |
| ------------------------------------------- | ------------------------------------------------- |
| Q-2 hook 자기 자신을 차단 (Q-1 commit 실패) | hook 화이트리스트에 현재 브랜치 추가 후 재시도    |
| Q-3 원인 미식별                             | #40 keep_open, hook으로 차단 유지, Slice 9 후보   |
| Q-4 예상외 코드 구조 발견                   | 보고서에 그대로 기록, 판단은 Part 2 지시서 v2에서 |
| Q-1/Q-2 작업 중 회귀 발생                   | 즉시 중단, 사용자 보고                            |
| 비용 발생 (예상 외)                         | 즉시 중단, 사용자 보고                            |

---

## 비용 예산

- **목표: $0 증가** (LLM 호출 0건)
- Part 1 종결 시점 누적: $1.595
- 사전 경고 임계: $1.60 (마진 0.3%)
- 임계 통과 시: 즉시 중단 + 사용자 결정

---

## 회귀 예산

- **목표: +0~3건** (hook 단위 테스트 정도, 또는 0건)
- Part 1 종결 시점 누적: 414
- Slice 8 Fallback 누적 임계: 사전 점검 + Part 2 합산 검토

---

**사전 점검 종료 후 사용자에게 보고. 사용자가 Part 2 지시서 v2 작성 의뢰할 때까지 대기.**

문서 끝.
