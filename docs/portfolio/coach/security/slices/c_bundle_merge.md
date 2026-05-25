═══════════════════════════════════════════════════════════════
[security/slices/c_bundle_merge.md] C 묶음 머지 — 세 보안 슬라이스 통합
C-1 (프론트) + C-2 (백엔드 deps) + C-3 (Django 5.2 LTS) → c-bundle
═══════════════════════════════════════════════════════════════

> **마스터 인덱스**: [`../SECURITY_LEDGER.md`](../SECURITY_LEDGER.md)
> **지시서**: [`../c_bundle_merge_directive.md`](../c_bundle_merge_directive.md)

---

## 통합 대상

| 슬라이스 | 브랜치 | 종결 HEAD |
|----------|--------|----------|
| C-1 | `security/c1-frontend-deps` | next 16.0.0→16.2.6 등 (vitest 65/65) |
| C-2 | `security/c2-backend-deps` | cryptography/urllib3/twisted 14 패키지 (pytest 740/1, IDENTICAL 31/31) |
| C-3 | `security/c3-django-52-lts` | Django 5.2.14 LTS + ASGI 게이트 (pytest 742/1, IDENTICAL 31/31) |

- **공통 base**: `00dc18d` (slice14)
- **통합 브랜치**: `security/c-bundle` (00dc18d에서 분기)

---

## Step 1 — 순차 머지 + 충돌 해결

### S1-2. C-1 머지 (클린)
- `git merge --no-ff security/c1-frontend-deps` → 충돌 0 (예상대로).

### S1-3. C-2 머지 (LEDGER 1차 충돌)
- 충돌: `SECURITY_LEDGER.md` (add/add, 4 hunks) — **예상**
- 해결: **UNION** — C-1 항목 + C-2 항목 + SEC-#1~#5 통합.

### S1-4. C-3 머지 (4 충돌 — 2 예상 + 2 예상 외 의존성)

| 파일 | 종류 | 예상 | 해결 |
|------|------|------|------|
| `SECURITY_LEDGER.md` | add/add, 4 hunks | ✅ §0.3 | UNION (C-3 행/SEC 추가) |
| `slices/c2_backend_deps.md` | add/add | ✅ §0.3 | **C-3 정정본 채택** (`--theirs`). C-3본은 C-2 원본 + cryptography 2줄(L24, L47) 정정 — 누락 0 확인. |
| `pyproject.toml` | content, 1 hunk | ❌ **예상 외** | UNION — 사용자 결정으로 진행 |
| `poetry.lock` | content | ❌ **예상 외** | 텍스트 머지 금지 — `poetry lock` **재생성** |

#### 예상 외 충돌 처리 (사용자 결정 후 진행)
지시서 §0.5 HALT 트리거 발동 후 사용자에게 보고 → "B (본질 정합)" 결정.

- **pyproject.toml UNION**: C-2 4건 (`cryptography ^46.0.7` / `python-dotenv ^1.2.2` / `requests ^2.33.0` / `pytest ^9.0.3`) + C-3 1건 (`django = "~5.2.14"`). **5건 모두 포함 확인**.
- **poetry.lock 재생성**: `git checkout --theirs poetry.lock` (C-3 lock 채택) → `poetry lock` → `poetry install`. 충돌 lock 덮어씀.

#### 재생성 lock 검증 게이트 (사용자 지시 §4)
| 항목 | 기대 | 결과 |
|------|------|------|
| Django | 5.2.x | **5.2.14** ✓ |
| cryptography | ≥46.0.7 | **46.0.7** ✓ |
| channels | 메이저·마이너 변동 없음 | 4.3.1 → **4.3.2** (caret patch만) ✓ |
| daphne | 변동 없음 | **4.2.1** (그대로) ✓ |

### S1-5. 머지 후 sanity
- `git status` unmerged: **0**
- `git log --graph` 머지 커밋 3건 정상 (`05c9ee8` C-2 통합 / `6d4cf6d` C-3 통합 + C-1 머지 별도)

### 머지 직후 K3 재확인 (사용자 지시 §6)
- `python manage.py makemigrations --check --dry-run` → **`No changes detected`** ✓

---

## Step 2 — 1차 검증 (c-bundle 게이트)

| 게이트 | 기준 | 결과 |
|--------|------|------|
| 백엔드 회귀 | 742 passed / 1 skipped | **PASS** (742/1, `portfolio/tests tests/coach tests/scoring tests/integration/asgi`) |
| IDENTICAL | 31/31 | **PASS** (31 passed) |
| 프론트 vitest | 65/65 | **PASS** (12 files / 65 tests) |

---

## Transitive 패키지 lock diff (V2 해소)

C-3 종결 보고에서 "poetry lock 재해석 결과"로만 적혔던 transitive 항목의 실제 `poetry.lock` 기준 before(base `00dc18d`) → after(c-bundle 통합본) 버전:

| 패키지 | base `00dc18d` | c-bundle 통합본 | 변화 종류 |
|--------|---------------|----------------|----------|
| **Django** | 5.1.7 | **5.2.14** | LTS 승격 (C-3) |
| **cryptography** | 46.0.3 | **46.0.7** | 패치 (C-2 명시 승격) |
| **channels** | 4.3.1 | **4.3.2** | caret patch (LTS 호환 유지) |
| **daphne** | 4.2.1 | **4.2.1** | **변동 없음** ✓ |
| neo4j | 5.28.2 | 5.28.4 | caret patch |
| psycopg2-binary | 2.9.11 | 2.9.12 | caret patch |
| pytest-django | 4.11.1 | 4.12.0 | caret minor |
| yfinance | 1.3.0 | 1.4.0 | caret minor |
| sentence-transformers | 5.2.0 | 5.5.1 | caret minor |

(C-2 명시 패키지 — urllib3 2.5.0→2.7.0 / pyjwt 2.10.1→2.13.0 / twisted 25.5.0→26.4.0 / tornado 6.4.2→6.5.5 / sqlparse 0.5.3→0.5.5 / filelock 3.20.0→3.29.0 / pyasn1 0.6.1→0.6.3 / pygments 2.19.1→2.20.0 / jupyter_core 5.7.2→5.9.1 / pytest 9.0.2→9.0.3 / python-dotenv 1.1.0→1.2.2 / requests 2.32.5→2.34.2 / idna 3.11→3.16 / lxml 6.0.2 그대로 — SEC-#4 — 는 별도 c2 closing 참조.)

---

## 비용

**$0** (LLM 호출 0).

---

## 커밋 구조

c-bundle 위 커밋 4건 (3 머지 + 1 문서):
1. `(c-bundle 위) Merge security/c1-frontend-deps` (S1-2, 충돌 0)
2. `05c9ee8` `Merge security/c2-backend-deps into security/c-bundle (Step 1.3)` (LEDGER UNION)
3. `6d4cf6d` `Merge security/c3-django-52-lts into security/c-bundle (Step 1.4)` (LEDGER UNION + c2 closing 정정 + pyproject UNION + poetry.lock 재생성)
4. (본 커밋) `docs(c-bundle): record C-1/C-2/C-3 integration — conflict resolution, lock diff, 1st-pass gates`

---

## 다음 (Step 3)

`security/c-bundle` → `slice14` **`--no-ff`** 머지 → 2차 재확인:
- pytest 742/1
- IDENTICAL 31/31
- vitest 65/65

종결 후 보안 C 계획 완료, Slice 15(프론트 코치 화면) 진입 가능.
