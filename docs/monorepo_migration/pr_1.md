# PR1 — services/\_dormant/graph_analysis/ 이동 지시서

monorepo 8 PR 중 **첫 PR (학습 곡선 슬롯)**. graph_analysis 모듈을 `services/_dormant/`로 이동하면서 §7의 4가지 점검(import 도구·git tag·DECISIONS·health_check)을 동시 정착시켜 PR2~PR8 7개 PR의 패턴 템플릿 확보.

| 메타         | 값                                               |
| ------------ | ------------------------------------------------ |
| PR 번호      | PR1                                              |
| 트랙         | services/\_dormant (휴면, 의존성 그래프 없음)    |
| origin 기점  | `88e042d` (execution_plan_v1 정본화 commit)      |
| branch       | `monorepo/pr1-dormant`                           |
| 사전 git tag | `monorepo-pre-pr1`                               |
| 도구         | ast-grep (D1, 가중합 4.10) + ruff 보조           |
| 검증 단위    | smoke (`pytest -k dormant` + import lint)        |
| 위험도       | 최저 (휴면, 사용자 영향 0)                       |
| 학습 산출물  | ast-grep 패턴 (DECISIONS 박음) + 4가지 점검 정착 |

---

## 0. 입력

- [execution_plan_v1.md](./execution_plan_v1.md) §1 PR1 행, §2 PR1 검증 단위, §3 롤백, §6 통과 기준 8개, §7 학습 곡선 4가지 점검
- [blueprint_v1.md](./blueprint_v1.md) §7 결정 ①②③ (dotted-path · 세션 충돌 방지 분류 · 빌드 도구 보류)
- DECISIONS.md (commit SHA 기록 형식)

---

## 1. 사전 점검 (5단계)

### 1.1 origin baseline 확인

```bash
git fetch origin
git log origin/main --oneline -2
# 기대: 88e042d (execution_plan_v1 정본화) → 9b48d37 (③ 빌드 도구 보류)
git status
# 기대: working tree clean, on main
```

### 1.2 graph_analysis 현재 위치 식별

```bash
find . -type d -name graph_analysis -not -path "./.git/*"
```

**보고 필수**: 출력 결과를 사용자에게 보고. 추정 금지 — 식별된 경로를 §2에서 입력으로 사용.

### 1.3 ast-grep 설치 확인 + 검증

```bash
which sg || which ast-grep
sg --version
# 또는 ast-grep --version
```

**미설치 시 설치 안내**:

```bash
# 옵션 1: Cargo (Rust 사용자)
cargo install ast-grep --locked

# 옵션 2: Homebrew (macOS)
brew install ast-grep

# 옵션 3: 공식 GitHub release 바이너리 + 체크섬 검증 (가장 안전)
#   https://github.com/ast-grep/ast-grep/releases
#   다운로드 후 sha256sum 비교 권장
```

**보안 보완**: 설치 출처는 사용자가 평소 사용하는 패키지 매니저 우선. 신규 도입 환경이라면 공식 release 체크섬 검증 권장.

### 1.4 git tag 박음 (롤백 지점)

```bash
git tag monorepo-pre-pr1 origin/main
git tag -l monorepo-pre-pr1
# 기대: tag 존재 확인
```

### 1.5 health_check baseline 확인

```bash
python scripts/health_check.py
# 기대: 6✅ / 0⚠ / 1❌ (자기참조 메타만 잔존)
```

❌ 신규 발생 시 → PR1 진입 보류, 원인 파악 후 재개.

### 1.6 branch 생성

```bash
git checkout -b monorepo/pr1-dormant
git status
# 기대: on branch monorepo/pr1-dormant, clean
```

---

## 2. 폴더 이동 (3단계)

### 2.1 목표 위치 디렉토리 준비

```bash
mkdir -p services/_dormant
touch services/__init__.py
touch services/_dormant/__init__.py
```

**근거**: dotted-path 결정 ① (`services._dormant.graph_analysis`) → Python 패키지 인식 위해 `__init__.py` 필요. namespace package (PEP 420) 가능하지만 명시적 패키지가 import 추적·IDE 인덱싱에 안정적.

### 2.2 git mv 이동

```bash
# §1.2에서 식별된 경로를 GRAPH_ANALYSIS_PATH로 가정
git mv {GRAPH_ANALYSIS_PATH} services/_dormant/graph_analysis
git status
# 기대: renamed 표시, R100 (100% similarity)
```

**검증**: `git status`에서 `renamed:` 표시 확인. `deleted:` + `new file:` 분리 표시면 `git mv` 실패 → 중단.

### 2.3 commit 1 (의미 분리)

```bash
git add services/__init__.py services/_dormant/__init__.py
git commit -m "monorepo PR1: services/ + services/_dormant/ 패키지 초기화

- __init__.py 추가 (dotted-path 결정 ① 정합)
- _dormant는 휴면 트랙 격리 디렉토리"

git commit -m "monorepo PR1: graph_analysis → services/_dormant/graph_analysis 이동

- git mv로 history 보존
- 호출처 없음 (휴면 모듈)
- import 경로 변경은 별도 commit"
```

**원칙 (D-1 패턴, 슬라이스 16회 검증)**: `__init__.py` 추가와 `git mv`는 의미 단위 분리 commit. 향후 bisect 추적 단순화.

---

## 3. import 변경 (4단계, dry-run 강제)

graph_analysis가 휴면이라 호출처 없을 가능성 높지만 **0건 확신 금지** — 다음 4단계로 안전 확인.

### 3.1 호출처 사전 스캔 (dry-run)

```bash
# 패턴 A: from graph_analysis ...
sg --pattern 'from graph_analysis.$X import $$$' --lang python .

# 패턴 B: import graph_analysis 단독
sg --pattern 'import graph_analysis' --lang python .

# 패턴 C: from graph_analysis import ... (서브모듈 없이)
sg --pattern 'from graph_analysis import $$$' --lang python .
```

**보고 필수**: 3개 패턴 모두 매칭 결과 보고. 매칭 0건이면 §3.2~§3.3 건너뛰고 §3.4로 직행 가능 (자명한 휴면 확인).

### 3.2 rewrite dry-run (매칭 있을 때만)

```bash
# 패턴 A rewrite preview (실제 적용 X, 출력만)
sg --pattern 'from graph_analysis.$X import $$$Y' \
   --rewrite 'from services._dormant.graph_analysis.$X import $$$Y' \
   --lang python .

# 패턴 B rewrite preview
sg --pattern 'import graph_analysis' \
   --rewrite 'import services._dormant.graph_analysis as graph_analysis' \
   --lang python .

# 패턴 C rewrite preview
sg --pattern 'from graph_analysis import $$$X' \
   --rewrite 'from services._dormant.graph_analysis import $$$X' \
   --lang python .
```

**보고 필수**: rewrite preview 출력을 사용자에게 보고 후 §3.3 진입 승인 요청.

### 3.3 rewrite 적용 (-U)

사용자 승인 후:

```bash
# 위 3개 패턴에 -U 추가 적용
sg --pattern '...' --rewrite '...' --lang python -U .
```

### 3.4 ruff import 정렬

```bash
ruff check --select I --fix .
ruff format .  # 형식 정렬 (의미 변경 0)
git diff
# 변경 검토
```

### 3.5 commit 2

```bash
git add -A
git commit -m "monorepo PR1: graph_analysis import 경로 갱신

- ast-grep 3 패턴 적용 (from / import / from-direct)
- ruff import 정렬 보조
- 매칭 N건 (실측치 채움)"
```

---

## 4. 검증 (3단계)

### 4.1 import smoke

```bash
python -c "import services._dormant.graph_analysis; print('OK')"
# 기대: OK 출력
```

실패 시 → §9 롤백.

### 4.2 pytest smoke

```bash
pytest -k dormant --no-cov -q
# 또는 graph_analysis 관련 테스트가 있다면:
pytest -k graph_analysis --no-cov -q
```

테스트 0건 매칭이어도 OK (휴면 모듈 테스트 부재 정상). pytest 자체 collection error 발생 시만 실패로 판정.

### 4.3 ruff lint 전체

```bash
ruff check .
# 기대: All checks passed.
```

**4.4 (선택) IDENTICAL 영향 점검** — 휴면이라 IDENTICAL 영향 0 예상이지만, PR4 이후 활성 트랙 진입 전 인프라 검증 1회는 가치 있음:

```bash
# 코치 응답 1개만 샘플로 IDENTICAL 확인 (전체 31 불필요)
# 실행 명령은 기존 IDENTICAL 검증 스크립트 참조
```

PR1에서는 옵션. PR2부터 필수.

---

## 5. commit 정리

이 시점까지 누적 commit (예상):

- commit 1: `__init__.py` 추가
- commit 2: `git mv` 폴더 이동
- commit 3: import 경로 갱신 + ruff

3개 commit. 의미 단위 분리로 git log 가독성 확보.

```bash
git log monorepo/pr1-dormant --oneline -5
# 3 commits 확인
```

---

## 6. DECISIONS + PROGRESS 갱신

### 6.1 DECISIONS.md 추가 (PR1 entry)

```markdown
### monorepo PR1 — services/\_dormant/graph_analysis 이동 (2026-MM-DD)

**결과**: graph_analysis → services/\_dormant/graph_analysis 이동 완료
**commit SHA**: {3개 SHA 채움}
**branch SHA**: {merge 후 main SHA 채움}

**학습 곡선 4가지 정착**:

1. ast-grep 패턴 3종 정착 → 부록 A 박음 (PR2~PR8 답습용)
2. git tag 롤백 절차 정착 (monorepo-pre-pr1 박음, 미사용)
3. DECISIONS 형식 정착 (본 entry가 PR2~PR8 템플릿)
4. health_check 트랙별 영향 0 확인 (휴면 트랙 특성)

**검증 결과**:

- import smoke: OK
- pytest -k dormant: {N} passed
- ruff check: clean

**다음 PR**: PR2 (packages/) — packages/shared + packages/web 이동
```

### 6.2 부록 A — ast-grep 패턴 (DECISIONS에 박음, PR2~PR8 답습)

```yaml
# 트랙 이동 시 import 경로 변경 패턴 (3종)

pattern_from_submodule:
  pattern: "from {OLD}.${X} import $$${Y}"
  rewrite: "from {NEW}.${X} import $$${Y}"
  lang: python

pattern_import_module:
  pattern: "import {OLD}"
  rewrite: "import {NEW} as {OLD}" # alias로 호환성 유지
  lang: python

pattern_from_direct:
  pattern: "from {OLD} import $$${X}"
  rewrite: "from {NEW} import $$${X}"
  lang: python

# 적용 순서: dry-run → 보고 → 사용자 승인 → -U 적용 → ruff check --select I --fix
```

### 6.3 PROGRESS.md 갱신

```markdown
- monorepo PR1 종결 (services/\_dormant/graph_analysis 이동, 학습 곡선 4가지 정착)
- commit 누적: 9 commits ahead of 9b48d37 (88e042d + PR1 3 commits + DECISIONS 갱신)
```

### 6.4 commit 3

```bash
git add docs/monorepo_migration/DECISIONS.md PROGRESS.md
git commit -m "monorepo PR1: DECISIONS + PROGRESS 갱신

- PR1 학습 곡선 4가지 정착 기록
- ast-grep 패턴 3종 박음 (PR2~PR8 답습용)
- 부록 A 신설"
```

---

## 7. push + 머지 + health_check

### 7.1 branch push

```bash
git push origin monorepo/pr1-dormant
```

### 7.2 PR 생성 (자기 review)

1인 개발이므로 PR은 self-review. GitHub UI 또는 `gh pr create`:

```bash
gh pr create \
  --title "monorepo PR1: services/_dormant/graph_analysis 이동" \
  --body "execution_plan_v1.md PR1 행 실행. 학습 곡선 4가지 정착 (DECISIONS 참조)."
```

### 7.3 main 머지

self-review 통과 후:

```bash
gh pr merge --merge --delete-branch
# 또는 fast-forward 가능:
# git checkout main && git merge --ff-only monorepo/pr1-dormant && git push origin main
```

### 7.4 origin/main 확인

```bash
git checkout main
git pull origin main
git log origin/main --oneline -5
# 기대: PR1 commits → 88e042d → 9b48d37
```

### 7.5 health_check 종결

```bash
python scripts/health_check.py
# 기대: 6✅ / 0⚠ / 1❌ (자기참조만, 신규 결함 0)
```

---

## 8. 통과 기준 (execution_plan §6 답습, 8 항목)

| #   | 항목                                   | PR1 측정                               |
| --- | -------------------------------------- | -------------------------------------- |
| 1   | 검증 항목 PASS                         | §4 3단계 모두 통과                     |
| 2   | IDENTICAL 31/31                        | **N/A** (PR4 이상 적용, PR1 휴면)      |
| 3   | health_check ❌ 신규 0                 | §7.5 확인                              |
| 4   | 누적 비용 임계 미초과                  | **N/A** (코치 응답 영향 없음)          |
| 5   | DECISIONS commit SHA 기록              | §6.1 완료                              |
| 6   | PROGRESS 갱신                          | §6.3 완료                              |
| 7   | 다음 git tag 박음 (`monorepo-pre-pr2`) | `git tag monorepo-pre-pr2 origin/main` |
| 8   | 회귀 카운트 기록                       | DECISIONS에 pytest 카운트 기록         |

8 항목 전건 충족 → PR1 종결.

---

## 9. 실패 시 롤백 절차

### 9.1 머지 전 실패 (branch 단계)

```bash
git checkout main
git branch -D monorepo/pr1-dormant
git tag -d monorepo-pre-pr1  # 사용 안 했으면 정리
```

영향 0, 재진입 가능.

### 9.2 머지 후 실패 발견

**옵션 1: revert PR (권장)**

```bash
git revert -m 1 {PR1-MERGE-SHA}
git push origin main
```

**옵션 2: hard reset (최후 수단)**

```bash
git reset --hard monorepo-pre-pr1
git push --force-with-lease origin main
```

force push는 정합성 사고 가능 → DECISIONS에 사유·SHA 필수 기록.

### 9.3 재진입

실패 원인 분석 → 동일 branch 이름 재사용 (`monorepo/pr1-dormant`) → 위 1~7 재실행. PR 번호 PR1 유지.

---

## 부록 B — PR1 산출물 체크리스트

PR1 종결 시 다음 산출물이 origin/main에 정착해야 함:

- [ ] `services/__init__.py` 신규
- [ ] `services/_dormant/__init__.py` 신규
- [ ] `services/_dormant/graph_analysis/` 이동 완료 (history 보존)
- [ ] import 경로 변경 (호출처 매칭 N건 처리, 또는 0건 확인)
- [ ] ruff check clean
- [ ] DECISIONS PR1 entry + 부록 A (ast-grep 패턴 3종)
- [ ] PROGRESS 갱신
- [ ] git tag `monorepo-pre-pr1` 잔존 (롤백 지점, 미사용)
- [ ] git tag `monorepo-pre-pr2` 신규 (다음 PR 롤백 지점 선제 확보)
- [ ] health_check 6✅/0⚠/1❌

---

## 부록 C — PR2 진입 시 답습할 4가지

PR1 종결 직후 PR2 (packages/) 진입 시 다음 4가지를 DECISIONS 부록 A에서 답습:

1. **ast-grep 패턴 3종** — `{OLD}` `{NEW}` 치환만 하면 PR2 적용 가능
2. **dry-run → 보고 → 승인 → -U** 순서 (보안 보완 단계 강제)
3. **commit 의미 분리** (`__init__.py` / `git mv` / import 변경 / DECISIONS 분리)
4. **통과 기준 8 항목** (PR2부터 IDENTICAL·비용 임계 활성화)

PR1이 패턴 정착 슬롯이고 PR2부터 본격 적용 — PR1 학습 비용이 PR2~PR8에서 7회 회수됨.

---

## 다음 단계

본 지시서 종결 후:

1. PR1 실제 진입 (Claude Code 실행)
2. PR1 종결 보고 → 메모리 갱신 (정본 위치 / A1 / 8 PR 매핑 / PR1 학습 4가지 정착)
3. PR2 지시서 작성 진입 (본 지시서를 템플릿으로 답습)

# §1.0 pre-commit hook 화이트리스트 확장 (1회, PR2~PR8 답습)

# 1) 백업

cp .git/hooks/pre-commit .git/hooks/pre-commit.bak

# 2) 현재 화이트리스트 위치 식별

grep -n "BRANCH_OK\|ALLOWED_BRANCHES" .git/hooks/pre-commit

# 3) monorepo/\* 패턴 블록 추가 (식별된 위치 부근에)

# 예: 기존 [[$CURRENT_BRANCH == slice*]] && BRANCH_OK=true 다음 줄에

# [[$CURRENT_BRANCH == monorepo/*]] && BRANCH_OK=true 추가

# 4) dry-run 검증

git checkout -b test/hook-verify-monorepo
echo "test" > /tmp/hook_test.txt
git add /tmp/hook_test.txt # 실제로는 임시 파일 trace

# hook 실행 여부 확인 (실제 commit 안 함)

# 5) test branch 정리

git checkout main
git branch -D test/hook-verify-monorepo

# 6) DECISIONS 박음 (#73 close 사이드 산출물)

# "부채 #73 close: pre-commit hook monorepo/\* 패턴 추가

# 라인 {N}: [[$CURRENT_BRANCH == monorepo/*]] && BRANCH_OK=true

# 사유: monorepo 8 PR 답습 효율 + 가드 견고성 보존"
