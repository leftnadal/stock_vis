═══════════════════════════════════════════════════════════════
[advisories/2026-05_dependency-audit.md] 의존성 보안 스캔
═══════════════════════════════════════════════════════════════

## 메타

| 항목 | 값 |
|------|----|
| 스캔 일자 | 2026-05-22 ~ 2026-05-24 |
| 도구 (프론트) | `npm audit` (npm 동봉) |
| 도구 (백엔드) | `pip-audit 2.10.0` (격리 venv `/tmp/sv_audit_tool/`에 설치, 프로젝트 환경 불변) |
| 스캔 대상 | `frontend/package-lock.json`, `poetry run pip freeze` (161 패키지) |
| 비용 | $0 (LLM 호출 0) |

---

## §1. 프론트엔드 npm audit (next 16.0.0 시점 = C-1 분기 base)

### §1.1 패키지·심각도 요약

| 패키지 | severity | 직접/전이 | advisory 수 | C-1 처리 |
|--------|---------|----------|-------------|----------|
| **next** | **critical** | direct | **22~23건** | C-1에서 16.2.6 상향 → critical 1건 포함 모두 해소 |
| axios | high | direct | 17건 | C-1에서 ^1.16.1 → 모두 해소 |
| js-cookie | high | direct | 1건 | C-1에서 ^3.0.7 → 해소 |
| ajv | moderate | transitive | 1건 | C-1 npm audit fix(--force 없이) → 해소 |
| brace-expansion | moderate | transitive | 2건 | 동상 → 해소 |
| flatted | high | transitive | 2건 | 동상 → 해소 |
| follow-redirects | moderate | transitive | 1건 | 동상 → 해소 |
| js-yaml | moderate | transitive | 1건 | 동상 → 해소 |
| minimatch | high | transitive | 6건 | 동상 → 해소 |
| picomatch | high | transitive | 4건 | 동상 → 해소 |
| postcss | moderate | transitive | 1건 | **잔여 (SEC-#1)** — `npm audit fix --force`만 가능 → next@9.3.3 메이저 다운그레이드 = 미적용 |

- **before (16.0.0)**: 1 critical / 5 high / 5 moderate (11 패키지, 총 ~55 advisory 행)
- **after (C-1 적용, 16.2.6)**: 0 critical / 0 high / 2 moderate (next + postcss — 둘 다 동일 advisory)

### §1.2 핵심 발견 — Next.js critical RCE

| advisory | severity | CVSS | 제목 |
|----------|----------|------|------|
| **GHSA-9qr9-h5gf-34mp** | **critical** | **10.0** | Next.js is vulnerable to RCE in React flight protocol (≥16.0.0-canary.0 <16.0.7) |

- "React2Shell"로 알려진 RCE. 16.0.0이 정확히 취약 범위.
- 본 advisory만이 C-1을 "긴급 hotfix"로 분류한 결정적 근거.

### §1.3 그 외 Next.js 22건 분류

| 분류 | 건수 | 대표 advisory |
|------|------|--------------|
| Middleware/Proxy bypass | 4건 (high·high·high·high) | GHSA-26hh-7cqf-hhc6 (<16.2.6, segment-prefetch), GHSA-267c-6grr-h53f, GHSA-492v-c6pp-mqqv, GHSA-36qx-fr4f-26g5 |
| Server Components / RSC DoS | 4건 (high) | GHSA-mwv6-3258-q52c, GHSA-q4gf-8mx6-v5v3, GHSA-8h8q-6873-q5fj, GHSA-h25m-26qc-wcjf |
| Cache poisoning / SSRF / WebSocket | 4건 (low·moderate·high) | GHSA-vfv6-92ff-j949, GHSA-wfc6-r584-vfw7, GHSA-c4j6-fc7j-m34r, GHSA-3g8h-86w9-wvmq |
| XSS (CSP nonce / beforeInteractive) | 2건 (moderate) | GHSA-ffhc-5mcf-pf4q, GHSA-gx5p-jg67-6x7h |
| Image Optimization DoS | 3건 (moderate) | GHSA-9g9p-9gw9-jx7f, GHSA-3x4c-7xq6-9pq8, GHSA-h64f-5h5j-jqjh |
| HTTP smuggling / Server Actions / PPR | 3건 (moderate) | GHSA-ggv3-7p47-pfv8, GHSA-w37m-7fhw-fmv9, GHSA-5f7q-jpqc-wp7h |
| Cache Components DoS | 1건 (high) | GHSA-mg66-mrh9-m8jx |

### §1.4 axios 17건 (CVSS 7.5 / 7.4 / 7.2 다수)

대표 항목:
- **GHSA-43fc-jf86-j433** (high, CVSS 7.5) — DoS via `__proto__` in mergeConfig (1.13.4 이하 영향, C-1 분기 base 1.13.1 영향)
- **GHSA-pf86-5x62-jrwf** (high, CVSS 7.4) — Prototype Pollution gadgets (Response/Data/Request hijack)
- **GHSA-pmwg-cvhr-8vh7** (high, CVSS 7.2) — NO_PROXY bypass (127.0.0.0/8) — Incomplete fix CVE-2025-62718
- **GHSA-q8qp-cvcw-x6jj** (high, CVSS 7.4) — Prototype pollution gadgets in HTTP adapter (cred injection)

C-1에서 axios 1.13.1 → ^1.16.1 상향으로 17건 모두 해소.

### §1.5 js-cookie 1건

- **GHSA-qjx8-664m-686j** (high, CVSS 7.5) — Per-instance prototype hijack in `assign()` (cookie-attr injection)
- C-1에서 3.0.5 → ^3.0.7 상향으로 해소.

---

## §2. 백엔드 pip-audit (poetry env 시점 2026-05-24)

### §2.1 패키지·advisory 요약 — 19 패키지 × 총 46건

| 패키지 | 설치 버전 | advisory 수 | 비고 |
|--------|----------|-------------|------|
| **django** | **5.1.7** | **11건** (고유 9, 중복 2 포함) | C-3 LTS 마이그레이션 1순위 대상 |
| **cryptography** | **46.0.3** | **3건** | C-2 후보 (PYSEC-2026-36/35, CVE-2026-26007) |
| filelock | 3.20.0 | 2건 | TOCTOU/symlink |
| requests | 2.32.5 | 1건 | CVE-2026-25645 (extract_zipped_paths) |
| idna | 3.11 | 1건 | CVE-2026-45409 |
| urllib3 | 2.5.0 | 4건 | PYSEC-2026-141, CVE-2025-66418/66471, CVE-2026-21441 |
| jupyter-core | 5.7.2 | 1건 | CVE-2025-30167 (dev/notebook only) |
| lxml | 6.0.2 | 1건 | PYSEC-2026-87 |
| pyasn1 | 0.6.1 | 2건 | DoS |
| pygments | 2.19.1 | 1건 | CVE-2026-4539 |
| pyjwt | 2.10.1 | 2건 | PYSEC-2026-120 (crit Header 검증), PYSEC-2025-183 (disputed) |
| pyopenssl | 25.3.0 | 2건 | CVE-2026-27448/27459 |
| pytest | 9.0.2 | 1건 | CVE-2025-71176 (dev only) |
| python-dotenv | 1.1.0 | 1건 | CVE-2026-28684 (symlink TOCTOU) |
| **transformers** | **5.0.0rc1** | **1건** | CVE-2026-1839 — Trainer RCE |
| sqlparse | 0.5.3 | 1건 | GHSA-27jp-wm6q-gp25 |
| **torch** | **2.7.1** | **5건** | ML-1 트랙. PYSEC-2025-203~206 + CVE-2025-3730 |
| tornado | 6.4.2 | 4건 | PYSEC-2026-140, CVE-2025-47287, CVE-2026-35536, GHSA-78cv-mqj4-43f7 |
| twisted | 25.5.0 | 1건 | PYSEC-2026-160 |

### §2.2 핵심 발견 — Django 5.1 EOL

- **Django 5.1.7 → 5.1 시리즈는 PYSEC 6건 이상 분포** (PYSEC-2025-14/37/47/104/105/106/107/108/109 + CVE-2025-59682)
- 패치 분포: `4.2.21~4.2.27 (LTS)`, `5.1.8~5.1.15 (5.1 시리즈 마지막)`, `5.2.1~5.2.9 (5.2 LTS)`
- **5.1 시리즈는 5.1.15에서 종료된 비-LTS** — 누적 패치가 5.2 LTS로 이전됨.
- **C-3 (Django 5.2 LTS 마이그레이션)**의 직접 근거. 5.1 → 5.2는 마이너 + Django 정책 상 LTS 흐름.

### §2.3 핵심 발견 — 그 외

| 패키지 | 핵심 |
|--------|------|
| cryptography 46.0.3 | DNS name 검증 / 버퍼 오버플로 / public_key API — 46.0.7로 fix (C-2 후보) |
| pyjwt 2.10.1 | `crit` Header Parameter 미검증 — 2.12.0로 fix (인증 토큰 영향, C-2 우선순위) |
| urllib3 2.5.0 | streaming API / proxy redirect — 2.7.0로 fix (C-2) |
| transformers 5.0.0rc1 | Trainer arbitrary code execution — 5.0.0rc3로 fix (ML-1) |
| torch 2.7.1 | 5건 모두 PYSEC, 다수 fix=2.9.0 (ML-1) |

### §2.4 부수 — freeze에 없는 항목

`pip-audit`/freeze 모두에 부재 (실제 미설치):
- `pillow` — 설치 안 됨
- `gunicorn` — 설치 안 됨 (daphne 4.2.1 사용 중)
- `uvicorn` — 설치 안 됨

`requirements.txt`는 별도 KB 의존성 2건만 명시 (`pinecone>=3.0.0`,
`sentence-transformers>=2.2.0`) — poetry와 별도 환경에서 관리됨.

---

## §3. 시점 간 비교

| 시점 | 프론트 (next 16.0.0) | 프론트 (next 16.2.6, C-1 후) | 백엔드 (Slice 14) |
|------|---------------------|------------------------------|------------------|
| critical | 1 | 0 | (pip-audit는 심각도 미표기) |
| high | 5 | 0 | - |
| moderate | 5 | 2 (postcss transitive) | - |
| total adv | ~55 | ~2 | 46 |

다음 스캔 시 본 파일과 비교용. `advisories/`에 보존 — 수정 없이 누적.

---

## §4. 사용한 명령 (재현용)

```bash
# 프론트
cd frontend
npm audit --json   # JSON 출력, advisory 상세

# 백엔드 (격리 venv)
poetry run pip freeze > /tmp/sv_backend_freeze.txt
python3 -m venv /tmp/sv_audit_tool
/tmp/sv_audit_tool/bin/pip install --upgrade pip pip-audit
/tmp/sv_audit_tool/bin/pip-audit -r /tmp/sv_backend_freeze.txt --no-deps --desc
```

`/tmp/` 산출물은 프로젝트 환경 외부 — 보존 여부 자유.
