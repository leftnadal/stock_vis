═══════════════════════════════════════════════════════════════
[security/slices/c3_django52.md] C-3 — Django 5.2 LTS 마이그레이션
보안 'C 계획' 마지막 슬라이스 (Django 5.1 EOL → 5.2.14 LTS)
═══════════════════════════════════════════════════════════════

> **마스터 인덱스**: [`../SECURITY_LEDGER.md`](../SECURITY_LEDGER.md) (C-3 행)
> **사전 영향 조사**: [`../audits/2026-05_c3_django_52_impact.md`](../audits/2026-05_c3_django_52_impact.md)
> **지시서**: [`../c3_directive_django52.md`](../c3_directive_django52.md)

---

## 분기

- **base HEAD**: `00dc18d` (slice14, "docs: 코드베이스 감사 보고서 생성")
- **브랜치명**: `security/c3-django-52-lts`
- **pre-commit hook**: `ALLOWED_BRANCHES`에 `security/c3-django-52-lts` 추가
- C-1·C-2·C-3 모두 같은 base에서 **독립 형제 분기**.

---

## 결정 4건 (지시서 §0 명시)

| # | 결정 | 본 슬라이스 반영 |
|---|------|----------------|
| ① | 목표 버전 = **Django 5.2.14** (5.2 LTS 최신 패치, 지원 종료 2028-04) | pyproject `django = "~5.2.14"` (>=5.2.14, <5.3.0). 런타임 `5.2.14` ✓ |
| ② | channels/daphne **현행 유지** + ASGI **영구 게이트** 추가 | channels 4.3.1→4.3.2 caret patch만(메이저 변경 없음), daphne 4.2.1 그대로. ASGI 통합 테스트 2건 신규 (`tests/integration/asgi/test_websocket_handshake.py`) — 회귀 자산으로 영구 편입. |
| ③ | **2-스텝 커밋 구조** (버전 승격 분리) | 커밋 #2(Step 0) = 핀+lock만 / 커밋 #3(Step 1) = 회귀·IDENTICAL·ASGI·종결문서. |
| ④ | **미처리 2건 분리 처리** (housekeeping 즉시 박제) | 커밋 #1 = C-2 closing의 cryptography 표기 1줄 정정 (메이저 경계 → 패치 업그레이드 + 명시 승격) — 독립 housekeeping. |

---

## 변경 파일

| 파일 | 의도 |
|------|------|
| `pyproject.toml` | `django = "^5.1.7"` → `django = "~5.2.14"` |
| `poetry.lock` | Django 5.1.7 → 5.2.14 + transitive 갱신 |
| `tests/integration/asgi/__init__.py` | 신규 — ASGI 통합 테스트 패키지 |
| `tests/integration/asgi/test_websocket_handshake.py` | 신규 — channels consumer 핸드셰이크 2 테스트 (결정 ②) |
| `docs/portfolio/coach/security/slices/c2_backend_deps.md` | C-2 표기 정정 (housekeeping 커밋 #1) — 머지 시 c2 브랜치와 3-way 통합 대상 |
| `docs/portfolio/coach/security/slices/c3_django52.md` | 본 문서 (신규) |
| `docs/portfolio/coach/security/SECURITY_LEDGER.md` | 신규 (c3 브랜치) — C-3 ✅종결 + SEC-#1~5 변동 — 머지 시 c1/c2 LEDGER와 3-way 통합 |
| `docs/portfolio/coach/security/c3_directive_django52.md` | 지시서 자체 — 종결 커밋에 포함 (slice14의 step_*.md 패턴 답습) |

---

## 패키지 변경 before / after

### 직접 명시 (pyproject)

| 패키지 | before | after |
|--------|--------|-------|
| django | `^5.1.7` | **`~5.2.14`** (>=5.2.14, <5.3.0 — 5.2 LTS 라인 패치 흡수 + 5.3 차단) |

### 자동 transitive 갱신 (poetry lock 재해석)

| 패키지 | before | after | 비고 |
|--------|--------|-------|------|
| Django | 5.1.7 | **5.2.14** | LTS 승격 (지지서 ① 목표) |
| channels | 4.3.1 | **4.3.2** | caret patch (`^4.3.1` 자유 영역 — 메이저 변경 없음, 결정 ② 정신 충족) |
| daphne | 4.2.1 | **4.2.1** (그대로) | 결정 ② 그대로 유지 ✓ |
| neo4j | 5.28.2 | 5.28.4 | lock 재해석 caret 자유 |
| psycopg2-binary | 2.9.11 | 2.9.12 | 동상 |
| pytest-django | 4.11.1 | 4.12.0 | 동상 |
| yfinance | 1.3.0 | 1.4.0 | 동상 |
| sentence-transformers | 5.2.0 | 5.5.1 | 동상 |

---

## 검증 게이트 (KPI 매트릭스, 지시서 §C-3 KPI)

| # | KPI | 통과 기준 | 결과 |
|---|-----|----------|------|
| K1 | Django 버전 | pyproject `~5.2.14`, 런타임 `5.2.14` | **PASS** (`django.get_version()` → `5.2.14`) |
| K2 | Python 지원 범위 | 3.10~3.14 | **PASS** (Python 3.12.2) |
| K3 | 마이그레이션 드리프트 | `makemigrations --check --dry-run` = `No changes detected` | **PASS** |
| K4 | 미적용 마이그레이션 | 0건 | **PASS** (`showmigrations | grep -c "^ \[ \]"` = 0) |
| K5 | 회귀 (기존) | 740 전건 통과, Django 승격發 신규 실패 0 | **PASS** (`portfolio/tests tests/coach tests/scoring`: 740 passed / 1 skipped — 베이스라인 동일) |
| K6 | IDENTICAL | 31/31 유지 | **PASS** (`test_e4_conversation_schema + test_llm_client_system_arg + test_input_v2_smoke + test_e3_scoring_integration`: 31 passed) |
| K7 | ASGI 게이트 | 신규 통합 테스트 +N건 추가 및 통과 | **PASS** (+2: stock 핸드셰이크/ping-pong + portfolio 익명 거부) |
| K8 | daphne 기동 | consumer 정상 기동 확인 | **PASS** (`daphne -p 18765` → `Listening on TCP address 127.0.0.1:18765`) |
| K9 | 비용 | $0 (LLM 호출 0) | **PASS** ($0) |
| K10 | 커밋 구조 | 3커밋 (housekeeping + Step0 + Step1) | **PASS** (`45f1893` + `d3fa136` + 종결 커밋) |
| K11 | 문서 | `c3_django52.md` 신설 + `SECURITY_LEDGER.md` 갱신 | **PASS** |

### 전체 회귀 (ASGI 포함)
`portfolio/tests tests/coach tests/scoring tests/integration/asgi`: **742 passed / 1 skipped** (= 740 + 2 ASGI).

---

## HALT 게이트 점검 (지시서 §0.4)

| 게이트 | 발동 여부 |
|--------|----------|
| `makemigrations --check` 비-clean | **미발동** (`No changes detected`) |
| 회귀 신규 실패 ≥1건 | **미발동** (740 동일) |
| IDENTICAL 깨짐 | **미발동** (31/31) |

---

## 비용

- **$0** (LLM 호출 0건, 의존성/문서/테스트 변경만).

---

## 커밋 (3건, 의미 단위 분리)

| # | 해시 | 메시지 |
|---|------|--------|
| 1 | `45f1893` | docs(c3): correct cryptography entry in c2 closing — patch bump, not major-boundary |
| 2 | `d3fa136` | chore(c3): bump Django 5.1.7 → 5.2.14 LTS; migrations clean |
| 3 | (본 커밋) | feat(c3): close Django 5.2 LTS migration — regression 740+2, IDENTICAL 31/31, ASGI gate added |

---

## 잔존 보안 부채 (SECURITY_LEDGER §2 영향)

| ID | 부채 | C-3 영향 |
|----|------|---------|
| SEC-#1 (C-1) | postcss transitive XSS | 변화 없음 (frontend, C-3 무관) |
| SEC-#2 (C-1) | eslint 181 errors | 변화 없음 (frontend, C-3 무관) |
| SEC-#3 (C-2) | pyOpenSSL 25.3.0 → 26.0.0 메이저 | 변화 없음 (Django 5.2와 무관 — cryptography 46.0.x 호환 유지) |
| SEC-#4 (C-2) | lxml 6.0.2 → 6.1.0 충돌 | 변화 없음 |
| SEC-#5 (C-2) | pyjwt CVE-2025-45768 disputed | 변화 없음 |

C-3 자체로 **Django 5.1 EOL 해소** — Django 5.1 시리즈 11 advisory (PYSEC-2025-14/37/47/104/105/106/107/108/109 + CVE-2025-59682, BIT-django-2025-* 등) **5.2.14에 모두 fix됨** — 닫힘.

---

## 다음 (메모)

- C-3 종결 후 **C 묶음 (C-1 + C-2 + C-3) → `slice14` 머지** (지시서 §종결 체크리스트):
  - SECURITY_LEDGER 3-way merge (3 브랜치 모두 LEDGER 수정)
  - slices/c2_backend_deps.md 2-way (c2 원본 ↔ c3 정정본)
  - 머지 후 slice14에서 회귀 742 + IDENTICAL 31/31 재확인
- **ML-1** (torch/transformers): C 묶음 외 후순위 별도 트랙.
- **Slice 15** (프론트 코치 화면): C 묶음 머지 후 진입.
