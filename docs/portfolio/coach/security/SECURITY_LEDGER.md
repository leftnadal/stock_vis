═══════════════════════════════════════════════════════════════
[security/SECURITY_LEDGER.md] 보안 작업 마스터 대장
═══════════════════════════════════════════════════════════════

> 모든 보안 작업의 단일 인덱스. 새 보안 슬라이스가 진입할 때마다
> 1행씩 추가. 자세한 내역은 `slices/{작업명}.md` 또는 `advisories/`를
> 링크로 추적.
>
> 상태 범례: ▶진행/예정 · ✅종결 · ⏸대기/보류 · ❌취소 (`README.md` 참조)
>
> ⚠ 본 LEDGER는 C-1(security/c1-frontend-deps) / C-2(security/c2-backend-deps) /
> C-3(security/c3-django-52-lts) 세 형제 브랜치에서 각각 갱신됨. C 묶음
> slice14 머지 시 3-way merge로 §1·§2 통합. (본 통합본은 c-bundle 시점에 작성.)

---

## §1. 보안 작업 인덱스

| ID | 작업 | 상태 | 분기 base | 브랜치 | 비용 | 기록 링크 |
|----|------|------|----------|--------|------|----------|
| **C-1** | 프론트 긴급 hotfix (next 16.2.6 + 의존성) | ✅ 종결 | `00dc18d` | `security/c1-frontend-deps` | $0 | [slices/c1_frontend_hotfix.md](slices/c1_frontend_hotfix.md) |
| **C-2** | 백엔드 의존성 패치 (cryptography/urllib3/twisted/tornado 등 14 패키지) | ✅ 종결 | `00dc18d` | `security/c2-backend-deps` | $0 | [slices/c2_backend_deps.md](slices/c2_backend_deps.md) |
| **C-3** | Django 5.2 LTS 마이그레이션 | ⏸ 대기 | - | - | - | - |
| **ML-1** | ML mini-slice (torch/transformers CVE) | ⏸ 후순위 | - | - | - | - |

### 시리즈 ID 컨벤션
- **C-N**: Cleanup/CVE 시리즈 — Slice 14 후속 보안 트랙
- **ML-N**: ML/AI 의존성 전용 (torch/transformers/sentence-transformers 등)
- 향후 도메인 추가 시 README의 명명 규칙 §에 등록 후 사용

---

## §2. 미해결 보안 부채

본 표의 부채는 **C-시리즈 슬라이스가 명시적으로 닫거나, 자연 해소를
모니터링하기 전까지 유지**된다. `debts.md`(전체 부채 대장)와 양쪽에 같이
등록되지 않을 수 있으므로, **보안 도메인은 본 표가 1차 소스**.

| ID | 부채 | 발생 시점 | 미적용 사유 | 해소 조건 / 모니터링 |
|----|------|----------|-------------|---------------------|
| **SEC-#1** | `postcss` transitive XSS (GHSA-qx2v-qp2m-jg93) — `node_modules/next/node_modules/postcss <8.5.10` | C-1 closing (2026-05-24) | `npm audit fix --force`만 가능 → `next@9.3.3` 다운그레이드 = 메이저 파괴적. C-1 §--force 금지 정신. | 다음 next 패치 릴리스가 nested postcss를 ≥8.5.10으로 갱신하면 자연 해소. `npm audit` 정기 점검. |
| **SEC-#2** | `eslint` 전체 lint 181 errors (any 사용 / unused vars 등) | C-1 이전부터 존재 (**pre-existing**) | C-1은 의존성 hotfix만 — 코드 품질 부채는 범위 밖. C-1 변경 파일 단독 lint = 0 error 확인. | 코드 품질 정리 슬라이스 별도. **Slice 15(프론트 코치 화면) 진입 전 정리 여부 결정 대상**. |
| **SEC-#3** | `pyOpenSSL` 25.3.0 → 26.0.0 (CVE-2026-27448, CVE-2026-27459 — 각 1건, 총 2건) | C-2 closing (2026-05-24) | 메이저 경계(25→26), 비파괴 범위 밖. C-2 §범위 밖 명시. cryptography 46.x ↔ pyopenssl 25.x는 호환 유지. | 별도 메이저 슬라이스. cryptography 다음 메이저 업그레이드 시점에 함께 검토. |
| **SEC-#4** | `lxml` 6.0.2 → 6.1.0 (PYSEC-2026-87 / GHSA-vfmq-68hx-4jfw / CVE-2026-41066) | C-2 closing (2026-05-24) | `poetry update lxml` 명시했으나 의존성 충돌 — 다른 패키지가 lxml 6.0.x 고정 요구. 지시서 §"강제 해결 금지". | 충돌 패키지 분석 후 처리. 또는 lxml 6.0.x 패치 릴리스 대기. |
| **SEC-#5** | `pyjwt` CVE-2025-45768 (PYSEC-2025-183) | C-2 closing (2026-05-24) | **disputed** (공급자: key 길이는 애플리케이션 책임). fix 버전 없음. | 분쟁 결론 모니터링. application 측 key 강도 가드. |

### 부채 ID 컨벤션
- `SEC-#N`: 보안 도메인 부채 번호. 일반 `#N` 부채(`debts.md`)와 충돌 회피.
- 닫힐 때는 `slices/{닫은 작업}.md` 링크 + closing 일자 명시 후 §3로 이동.

---

## §3. 종결된 보안 부채

(현재 없음. 닫힌 부채는 닫은 슬라이스 기록에 통합되고 본 §3에 1줄 요약으로 남는다.)

---

## 변경 이력

| 일자 | 변경 | 작성 |
|------|------|------|
| 2026-05-24 | 본 LEDGER 신설 + C-1 종결 / C-2·C-3·ML-1 예정 등록 / SEC-#1·SEC-#2 미해결 부채 등록 | C-1 후속 docs 슬라이스 (`security/c1-frontend-deps`) |
| 2026-05-24 | C-2 종결 등록 + SEC-#3·SEC-#4·SEC-#5 미해결 부채 추가 | C-2 closing (`security/c2-backend-deps`) |
| 2026-05-25 | C-1+C-2 통합 (c-bundle 머지 1차) — LEDGER UNION 해결 | c-bundle Step 1.3 |
