═══════════════════════════════════════════════════════════════
[security/audits/] read-only 영향 조사·인벤토리
═══════════════════════════════════════════════════════════════

## 목적

보안 슬라이스(`slices/`)에 들어가기 **전에** 수행한 read-only 영향 조사·
인벤토리 보고를 보존한다. 코드 변경 없이 디스크/패키지 메타데이터/
스캐너 출력만 모은 시점 스냅샷. 슬라이스 지시서가 정확해지도록 받쳐주는
역할 + 시점 비교 자료.

`advisories/` (취약점 스캔 원본)과 분리한 이유:
- `advisories/` = 도구가 뱉은 취약점 목록 (예: pip-audit 출력)
- `audits/` = **사람이 정리한 영향 조사** (코드 grep 결과 + 인벤토리 +
  매트릭스 + 호환성 메타데이터 등)

같은 시점이라도 둘은 다른 입력원에서 만들어진다.

---

## 폴더 구조

```
security/audits/
├── README.md                                    ← 본 인덱스
├── YYYY-MM_{주제}.md
```

## 인덱스 (2026-05 분량)

| 파일 | 주제 | 입력원 | 후속 슬라이스 |
|------|------|--------|--------------|
| [`2026-05_frontend_inventory.md`](2026-05_frontend_inventory.md) | 프론트엔드 현황(디렉터리/프레임워크/완성도/백엔드 연동/배포 흔적) | ls / package.json / lockfile / grep | C-1, Slice 15 진입 결정 |
| [`2026-05_nextjs_security_exposure.md`](2026-05_nextjs_security_exposure.md) | Next.js 5월 13개 권고 코드 실사용 + 배포 노출 + 업그레이드 범위 | npm audit / grep / next.config 검토 | C-1 |
| [`2026-05_external_resources_inventory.md`](2026-05_external_resources_inventory.md) | 전체 외부 자원 인벤토리 (npm/Python/런타임/Docker 이미지) | npm ls / poetry.lock / Dockerfile / docker-compose | C 시리즈 전반 |
| [`2026-05_c3_django_52_impact.md`](2026-05_c3_django_52_impact.md) | Django 5.1.7 → 5.2 LTS 마이그레이션 영향 조사 (5.2 변경점 vs 코드 실사용) | manage.py check / grep / 패키지 메타데이터 | C-3 지시서 정밀화 |

연관 자료:
- [`../advisories/2026-05_dependency-audit.md`](../advisories/2026-05_dependency-audit.md) — npm audit + pip-audit 출력 (audits의 인벤토리/영향 조사와 입력원이 다른 형제)

---

## 보고 원칙 (audits 작성 시 적용)

- **사실만** 기록. 추천·판단·다음 단계 제안 0.
- 코드 경로·버전 번호·경고 메시지는 **그대로** 인용 (요약 금지).
- 모르는 항목은 `확인 불가` 명시.
- 출처 명시 (`manage.py check` / `npm audit` / `grep` 등).
- 변경 없음 (read-only) — 본 폴더의 작성·갱신만 docs 변경.
