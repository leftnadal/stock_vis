═══════════════════════════════════════════════════════════════
[security/slices/c2_backend_deps.md] C-2 — 백엔드 보안 의존성 비파괴 업그레이드
pip-audit 46 → 21 (25 advisory 해소, §범위 밖 21건 보존)
═══════════════════════════════════════════════════════════════

> **마스터 인덱스**: [`../SECURITY_LEDGER.md`](../SECURITY_LEDGER.md) (C-2 행)
> **원본 스캔**: [`../advisories/2026-05_dependency-audit.md`](../advisories/2026-05_dependency-audit.md) (§2)

---

## 분기

- **base HEAD**: `00dc18d` (slice14, "docs: 코드베이스 감사 보고서 생성")
- **브랜치명**: `security/c2-backend-deps`
- **pre-commit hook**: `ALLOWED_BRANCHES`에 `security/c2-backend-deps` 추가
- C-1 형제 브랜치(독립). C-1 위에 쌓지 않음.

---

## 변경 파일 (백엔드 한정, 2건)

| 파일 | 의도 |
|------|------|
| `pyproject.toml` | 직접 의존성 4건 갱신 (python-dotenv, requests, pytest) + cryptography 신규 명시(메이저 경계 강제용) |
| `poetry.lock` | poetry update <명시 14개>로 갱신 |

`git diff --stat 00dc18d HEAD`:
```
poetry.lock    | 289 +++++++++++++++++++++++++--------------------------------
pyproject.toml |   7 +-
2 files changed, 131 insertions(+), 165 deletions(-)
```

frontend/ 변경 **0** ✓, 앱 로직·코치 엔진·API 코드 변경 **0** ✓.

---

## 변경 패키지 before / after

### §1.1 pyproject.toml 직접 의존성

| 패키지 | before | after | 표기 |
|--------|--------|-------|------|
| python-dotenv | `^1.1.0` | **`^1.2.2`** | caret 유지 |
| requests | `^2.32.5` | **`^2.33.0`** | caret 유지 |
| pytest (dev) | `^9.0.2` | **`^9.0.3`** | caret 유지 |
| **cryptography** | (미명시) | **`^46.0.7`** (신규) | caret. **메이저 경계 46.x 강제용** — transitive caret 자유 영역에서 48.0.0 자동 점프 방지 |

### §1.2 poetry.lock 전이 의존성 (실제 설치 버전)

| 패키지 | before | after | advisory 해소 |
|--------|--------|-------|--------------|
| cryptography | 46.0.3 | **46.0.7** | 3건 |
| pyjwt | 2.10.1 | **2.13.0** | 2건 (PYSEC-2026-120 + disputed 2025-183) |
| urllib3 | 2.5.0 | **2.7.0** | 4건 |
| idna | 3.11 | **3.16** | 1건 |
| twisted | 25.5.0 | **26.4.0** | 1건 (§1 메이저 경계 26.x 명시 허용) |
| tornado | 6.4.2 | **6.5.5** | 4건 |
| sqlparse | 0.5.3 | **0.5.5** | 1건 |
| filelock | 3.20.0 | **3.29.0** | 2건 |
| pyasn1 | 0.6.1 | **0.6.3** | 2건 |
| pygments | 2.19.1 | **2.20.0** | 1건 |
| jupyter_core | 5.7.2 | **5.9.1** | 1건 |
| pytest | 9.0.2 | **9.0.3** | 1건 |
| python-dotenv | 1.1.0 | **1.2.2** | 1건 |
| requests | 2.32.5 | **2.34.2** | 1건 |
| **lxml** | 6.0.2 | **6.0.2 (그대로)** | **0건 — 충돌로 미상향 (부채)** |

**총 25 advisory 해소** (대상 14 패키지).

### §1.3 §범위 밖 보존 확인 (자동 점프 방지)

| 패키지 | before | after | 처리 |
|--------|--------|-------|------|
| Django | 5.1.7 | **5.1.7** (그대로) | C-3 LTS 마이그레이션 소관 — 보존 |
| pyOpenSSL | 25.3.0 | **25.3.0** (그대로) | 메이저 점프 필요(26.x), 비파괴 범위 밖 — SEC-#3 부채 |
| torch | 2.7.1 | **2.7.1** (그대로) | ML-1 트랙 — 보존 |
| transformers | 5.0.0rc1 | **5.0.0rc1** (그대로) | ML-1 트랙 — 보존 |

`poetry lock` 전체 재해석 회피 + 정밀 `poetry update <명시 14개>` 호출로 §범위 밖 패키지 미변경 보장.

---

## 적용 못 한 패키지 + 사유

| 패키지 | 사유 | 처리 |
|--------|------|------|
| lxml 6.0.2 → 6.1.0 | poetry update에 명시했으나 lock 변경 0 — 다른 패키지가 lxml 6.0.x 고정 요구 (의존성 충돌). 지시서 §2 "강제 해결 금지" → 보류. | SEC-#4 부채로 기록 |
| pyOpenSSL 25.3.0 → 26.0.0 | 메이저 경계(25→26)이며 C-2 §범위 밖에 명시됨. | SEC-#3 부채로 기록 (별도 메이저 슬라이스 필요) |
| pyjwt CVE-2025-45768 (PYSEC-2025-183) | **disputed** (공급자가 분쟁 — key 길이는 애플리케이션 책임). fix 버전 없음. | SEC-#5 모니터링 부채 |
| Django 5.1.7 (11 advisory) | C-3 LTS 마이그레이션 소관. C-2 §범위 밖. | C-3 진입 시 일괄 해소 |
| torch 5건 + transformers 1건 | ML-1 트랙 소관. C-2 §범위 밖. | ML-1 진입 시 처리 |

---

## pip-audit before / after

| 시점 | adv | 패키지 수 |
|------|-----|----------|
| **before** (slice14 HEAD `00dc18d`) | **46** | **19** |
| **after** (C-2 적용) | **21** | **5** (django/torch/pyopenssl/lxml/transformers — 모두 §범위 밖) |

**해소 25건** = §1 대상 14 패키지에서 일괄 닫힘. **§1 대상 패키지의 잔여 advisory = 0** ✓ (게이트 4 PASS).

---

## pytest before / after

| 시점 | passed | skipped | 범위 |
|------|--------|---------|------|
| before | **740** | 1 | `portfolio/tests tests/coach tests/scoring` |
| after | **740** | 1 | 동일 범위 |

**회귀 0** ✓.

### IDENTICAL 31/31

- before: 31/31 PASS
- after: **31/31 PASS** ✓ (의존성만 변경, service/LLM 호출 경로·시그니처 무수정 → 해시 불변)

---

## 검증 게이트 6종

| # | 게이트 | 결과 | 비고 |
|---|--------|------|------|
| 1 | poetry lock + install 성공, lock 정상 갱신 | **PASS** | `poetry update` 14개 명시, lock 289줄 변경 |
| 2 | 백엔드 정상 기동/import | **PASS** | `python manage.py check` = 0 issues |
| 3 | pytest passed 수 ≥ 베이스라인 | **PASS** | 740/1 동일 (회귀 0) |
| 4 | pip-audit §1 대상 advisory 0건 | **PASS** | 잔여 21건 모두 §범위 밖 (django/torch/pyopenssl/lxml/transformers) |
| 5 | git diff frontend/ 변경 0 | **PASS** | `pyproject.toml` + `poetry.lock` 2 파일만 |
| 6 | IDENTICAL 31/31 PASS | **PASS** | service/LLM 경로 무수정 |

---

## 호환성 강제 코드 수정

**0건** (커밋 2 = 불필요).

- pytest 740 동일 + IDENTICAL 31/31 PASS — 모든 의존성 업그레이드가 코드 변경 없이 호환.
- C-1의 `7482fdc` 선례(Next 16 빌드 강제)와 달리, C-2의 업그레이드는 백엔드 테스트 스위트에서 강제 수정 0 트리거.

---

## 비용

**$0** (LLM 호출 0).

---

## 커밋 (2건)

| # | 해시 | 메시지 |
|---|------|--------|
| 1 | `6d846c1` | C-2 — 백엔드 보안 의존성 비파괴 업그레이드 |
| 2 | (본 커밋) | docs(security) — C-2 closing + LEDGER 갱신 |

지시서 §커밋 §2(호환성 강제 수정) 커밋: **불필요**.

---

## 신규 보안 부채 (SECURITY_LEDGER §2 추가)

| ID | 부채 | 발생 | 미적용 사유 | 해소 조건 |
|----|------|------|-------------|----------|
| **SEC-#3** | pyOpenSSL 25.3.0 → 26.0.0 (CVE-2026-27448 / CVE-2026-27459, 각 1건씩 2건) | C-2 (2026-05-24) | 메이저 경계(25→26), 비파괴 범위 밖. C-2 §범위 밖 명시. | 별도 메이저 슬라이스. cryptography 46.x ↔ pyopenssl 25.x는 호환 유지. |
| **SEC-#4** | lxml 6.0.2 → 6.1.0 (PYSEC-2026-87 / GHSA-vfmq-68hx-4jfw) | C-2 (2026-05-24) | poetry update에 명시했으나 의존성 충돌 — 다른 패키지가 lxml 6.0.x 고정 요구. 지시서 §2 "강제 해결 금지". | 충돌 패키지 분석 후 처리. 또는 lxml의 6.0.x 패치 릴리스 대기. |
| **SEC-#5** | pyjwt CVE-2025-45768 (PYSEC-2025-183) | C-2 (2026-05-24) | **disputed** (공급자: key 길이는 애플리케이션 책임). fix 버전 없음. | 분쟁 결론 모니터링. application 측 key 강도 가드. |

---

## 다음 (메모, 본 closing 범위 밖)

- **C-3**: Django 5.2 LTS 마이그레이션 (django 11 advisory 일괄 해소) — 다음 시리즈.
- **ML-1**: torch/transformers CVE — ML 트랙.
- **SEC-#3 pyopenssl**: cryptography 다음 업그레이드 시점에 pyopenssl 호환성 함께 검토.
- **SEC-#1 (C-1 후속)**: postcss transitive — 모니터링 계속.
- **SEC-#2 (C-1 후속)**: eslint 181 errors — Slice 15 진입 전 정리 결정 대상.
