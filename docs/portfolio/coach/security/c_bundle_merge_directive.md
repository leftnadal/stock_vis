# C 묶음 머지 지시서 — security/c-bundle → slice14

> 대상: Claude Code 실행 환경
> 작업: 보안 'C 계획' 세 브랜치(C-1·C-2·C-3)를 통합 브랜치에서 합쳐 검증 후 `slice14`에 머지
> 작성 근거: 머지 전략 결정 = B(통합 브랜치 경유), 가중합 4.80 vs C 3.75 (1점 초과 차이 → 자동 확정)

---

## 0. 컨텍스트 & 작업 원칙

### 0.1 현재 위치

- 보안 'C 계획' 세 슬라이스 모두 종결:
  - C-1 프론트 hotfix — `security/c1-frontend-deps` (vitest 65/65)
  - C-2 백엔드 의존성 — `security/c2-backend-deps` (pytest 740/1, IDENTICAL 31/31)
  - C-3 Django 5.2 LTS — `security/c3-django-52-lts` (pytest 742/1, IDENTICAL 31/31, 커밋 `45f1893`·`d3fa136`·`a76e678`)
- 셋 모두 `slice14`(`00dc18d`)에서 분기한 **독립 형제 브랜치**. 본 작업은 이 셋을 본류로 통합.

### 0.2 전략 — 왜 통합 브랜치인가

세 브랜치를 `slice14`에 직접 순차 머지하면 본류가 중간에 불완전 상태로 존재하고 충돌이 2회로 쪼개진다. 대신 **격리된 `security/c-bundle` 브랜치에서 셋을 합치고 충돌·검증을 한 작업 공간에서 끝낸 뒤**, 검증 완료된 통합본만 `slice14`에 단 한 번 머지한다. 본류는 항상 클린하게 유지된다.

### 0.3 예상 충돌 (이 2개 파일만 — 그 외는 HALT 신호)

| 파일                                                      | 충돌 종류 | 원인                                                                        |
| --------------------------------------------------------- | --------- | --------------------------------------------------------------------------- |
| `SECURITY_LEDGER.md`                                      | 3-way     | C-1·C-2·C-3 세 브랜치가 모두 base 버전에서 갈라져 각자 수정                 |
| `docs/portfolio/coach/security/slices/c2_backend_deps.md` | 2-way     | C-2가 생성/작성 ↔ C-3 housekeeping 커밋(`45f1893`)이 cryptography 항목 정정 |

### 0.4 충돌 해결 원칙

- **`SECURITY_LEDGER.md`**: **UNION**. C-1·C-2·C-3 각 브랜치가 추가한 항목을 모두 보존, 어느 것도 삭제하지 않는다. §2 잔존 보안 부채(SEC-#1~#5) 목록은 세 브랜치 간 중복 없이 일관되게 통합. 한 브랜치에만 있는 항목이 누락되지 않도록 세 최종본을 모두 대조.
- **`c2_backend_deps.md`**: **C-3 정정본 채택.** C-3의 `45f1893`은 cryptography 항목을 의도적으로 바로잡은 housekeeping 커밋이다(46.0.3→46.0.7 패치 + pyproject 명시 승격). C-2 원본의 "메이저 경계 강제" 표현은 폐기, C-3 정정 내용을 최종본으로.

### 0.5 HALT 규칙

- **예상 외 충돌**: `SECURITY_LEDGER.md`·`c2_backend_deps.md` 외의 파일에서 충돌이 발생하면 → **즉시 중단.** 어떤 파일·어떤 hunk인지 그대로 병진에게 보고. 세 브랜치는 격리돼 있었으므로 다른 충돌은 예상 밖.
- **검증 게이트**: `c-bundle` 1차 검증 또는 `slice14` 2차 재확인에서 회귀 ≠ `742 passed / 1 skipped`, 또는 IDENTICAL ≠ 31/31, 또는 frontend vitest ≠ 65/65 → **즉시 중단, 보고.** 종결 진입 금지.
- LLM 호출 0 — 예상 비용 $0.

### 0.6 커밋 구조

- `c-bundle` 위: 머지 커밋 3건(C-1·C-2·C-3 머지) + 문서 커밋 1건(`c_bundle_merge.md`).
- `slice14` 위: 머지 커밋 1건(`--no-ff`).

---

## Step 1 — 통합 브랜치 생성 + 세 브랜치 순차 머지 + 충돌 해결

### S1-1. 통합 브랜치 생성

```
git checkout 00dc18d
git checkout -b security/c-bundle
```

### S1-2. C-1 머지 (충돌 없음 예상)

```
git merge --no-ff security/c1-frontend-deps
```

- C-1은 프론트 변경 중심. `SECURITY_LEDGER.md`는 base에서 처음 갈라진 수정이므로 이 시점엔 충돌 없음(클린 머지 예상).
- 충돌이 나면 HALT 규칙 적용(예상 외).

### S1-3. C-2 머지 (LEDGER 3-way 중 첫 충돌)

```
git merge --no-ff security/c2-backend-deps
```

- 예상 충돌: `SECURITY_LEDGER.md` — C-1 변경분 ↔ C-2 변경분. **0.4 원칙대로 UNION 해결**(C-1·C-2 항목 모두 보존).
- `c2_backend_deps.md`는 이 단계에선 C-2가 신규 추가/작성 → 충돌 없음.
- 그 외 파일 충돌 시 HALT.

### S1-4. C-3 머지 (LEDGER 3-way 완성 + c2 문서 2-way)

```
git merge --no-ff security/c3-django-52-lts
```

- 예상 충돌 2건:
  - `SECURITY_LEDGER.md` — c-bundle의 (C-1+C-2) 통합본 ↔ C-3 변경분. UNION 해결로 3-way 완성. C-3가 추가한 Django 5.1 EOL 해소 항목(PYSEC 9건 + CVE-2025-59682) 포함 확인.
  - `c2_backend_deps.md` — C-2 원본 ↔ C-3 정정본. **C-3 정정본 채택**(0.4 원칙).
- 그 외 파일 충돌 시 HALT.

### S1-5. 머지 후 즉시 sanity 확인

- `git status` — working tree clean, 미해결 충돌 0.
- `git log --oneline --graph` — c-bundle에 머지 커밋 3개가 의도대로 들어갔는지.
- 이 단계까지 통과해야 Step 2 진입.

---

## Step 2 — c-bundle 1차 검증 + 통합 문서 작성

### S2-1. 1차 검증 (HALT 게이트)

`c-bundle` 브랜치에서:

1. 백엔드 회귀: `pytest` → **742 passed / 1 skipped** (C-3가 만든 742 베이스라인 유지, ASGI 게이트 2건 포함).
2. IDENTICAL 결정성: 기존 검증 메커니즘 실행 → **31/31** 유지.
3. 프론트 회귀: frontend에서 `vitest` → **65/65** (C-1 베이스라인 유지).
4. 하나라도 어긋나면 → 중단, 어느 게이트·무엇이 깨졌는지 보고.

### S2-2. 통합 문서 작성 + transitive lock diff 기록 (V2 해소)

**신규 파일**: `docs/portfolio/coach/security/slices/c_bundle_merge.md`

- 포함 내용:
  - 통합 대상 세 브랜치 및 base(`00dc18d`)
  - 수행한 충돌 해결 2건(LEDGER 3-way UNION / `c2_backend_deps.md` 2-way C-3본 채택)
  - **transitive 패키지 lock diff** — C-3 종결 보고에서 "poetry lock 재해석 결과"로만 적힌 항목의 실제 before→after 버전을 `poetry.lock` diff로 추출해 기록(neo4j / psycopg2 / pytest-django / yfinance / sentence-transformers 등). 보안 슬라이스의 audit 기록 보강.
  - channels `4.3.1 → 4.3.2`(caret patch) 명기.
  - 1차 검증 결과(742/1 + IDENTICAL 31/31 + vitest 65/65)
- 분량은 간결하게 — 통합 사실·결과 보존 수준.

### S2-3. 문서 커밋

```
git add docs/portfolio/coach/security/slices/c_bundle_merge.md
git commit -m "docs(c-bundle): record C-1/C-2/C-3 integration — conflict resolution, lock diff, 1st-pass gates"
```

---

## Step 3 — slice14 머지 + 2차 재확인

### S3-1. slice14에 통합본 머지

```
git checkout slice14
git merge --no-ff security/c-bundle
```

- `--no-ff` 필수 — 머지 커밋 1개가 "여기서부터 C 계획 전체가 본류에 들어왔다"는 명확한 경계 표식이 된다.
- 이 시점 충돌은 예상되지 않음(`c-bundle`이 이미 `00dc18d` 기반 통합본). 충돌 발생 시 HALT.
- **커밋 메시지 예**: `merge(slice14): integrate security C-bundle (C-1 frontend + C-2 deps + C-3 Django 5.2 LTS)`

### S3-2. 2차 재확인 (HALT 게이트)

`slice14`에서:

1. `pytest` → **742 passed / 1 skipped**
2. IDENTICAL → **31/31**
3. frontend `vitest` → **65/65**
4. 어긋나면 → 중단, 보고.

### S3-3. 통합 마무리

- 2차 재확인 전건 통과 시 C 묶음 머지 완료.
- `security/c-bundle` 및 C-1·C-2·C-3 브랜치는 머지 완료 후 정리 가능(삭제 여부는 병진 판단 — 기본은 삭제 권장, 히스토리는 머지 커밋에 보존됨).

---

## C 묶음 머지 KPI 매트릭스 (종결 보고에 포함)

| #   | KPI                  | 통과 기준                                                    |
| --- | -------------------- | ------------------------------------------------------------ |
| M1  | 통합 브랜치          | `security/c-bundle`을 `00dc18d`에서 분기                     |
| M2  | 세 브랜치 머지       | C-1·C-2·C-3 모두 `c-bundle`에 머지(머지 커밋 3건)            |
| M3  | LEDGER 3-way         | `SECURITY_LEDGER.md` UNION 해결, 세 브랜치 항목 무손실       |
| M4  | c2 문서 2-way        | `c2_backend_deps.md` = C-3 정정본                            |
| M5  | 예상 외 충돌         | 0건 (위 2파일 외 충돌 없음)                                  |
| M6  | 1차 검증 (c-bundle)  | pytest 742/1 + IDENTICAL 31/31 + vitest 65/65                |
| M7  | 통합 문서            | `c_bundle_merge.md` 신설, transitive lock diff 기록(V2 해소) |
| M8  | slice14 머지         | `--no-ff` 머지 커밋 1건                                      |
| M9  | 2차 재확인 (slice14) | pytest 742/1 + IDENTICAL 31/31 + vitest 65/65                |
| M10 | 비용                 | $0 (LLM 호출 0)                                              |

---

## 산출물 목록

1. `security/c-bundle` 브랜치 — 머지 커밋 3 + 문서 커밋 1
2. `SECURITY_LEDGER.md` — 3-way UNION 통합본
3. `docs/portfolio/coach/security/slices/c2_backend_deps.md` — C-3 정정본으로 정착
4. `docs/portfolio/coach/security/slices/c_bundle_merge.md` — 통합 종결 문서(lock diff 포함)
5. `slice14` — C 묶음 머지 커밋(`--no-ff`)

---

## 종결 체크리스트 — C 계획 완료 후

- [ ] C 묶음 머지 완료 → 보안 'C 계획' 전체 종료.
- [ ] `slice14`에서 회귀 742/1 + IDENTICAL 31/31 + vitest 65/65 최종 확인 완료.
- ⏸ ML mini-slice(torch/transformers)는 후순위 별도 트랙 — C 묶음에 포함하지 않음.
- ▶ **다음 = Slice 15 진입** — 기존 Next.js 앱에 코치 E1~E6 화면 추가. C 묶음 머지가 하드 선행조건이었으므로 이제 해제됨.

---

## 한눈 요약

```
Step 1 : 00dc18d → security/c-bundle 분기 → C-1·C-2·C-3 순차 머지
         충돌 2건만 예상: LEDGER 3-way(UNION) / c2 문서 2-way(C-3본 채택)
         그 외 충돌 → HALT
Step 2 : c-bundle 1차 검증(742/1 + IDENTICAL 31/31 + vitest 65/65)
         + c_bundle_merge.md 작성(transitive lock diff = V2 해소)
Step 3 : c-bundle → slice14 머지(--no-ff) → 2차 재확인
종결   : 보안 C 계획 완료 → Slice 15(프론트 코치 화면) 진입
```
