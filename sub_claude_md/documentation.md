# 문서화 워크플로우

## 플랜 모드 문서화 규칙

**모든 구현 계획은 docs 폴더에 문서화**:

1. **플랜 모드 진입 시**: 해당 기능의 설계 문서를 적절한 폴더에 생성
2. **구현 완료 후**: 문서 업데이트 및 CLAUDE.md 반영

## docs 폴더 구조

```
docs/
├── architecture/          # 시스템 아키텍처, 설계 문서
├── features/              # 기능별 설계 및 구현 가이드
│   ├── chain-sight/
│   ├── screener/
│   ├── market-movers/
│   ├── keywords/
│   ├── news/
│   ├── stock-sync/
│   ├── empty-basket/
│   └── watchlist/
├── infrastructure/        # 인프라, AWS, 배포 문서
│   ├── aws/
│   └── serverless/
├── testing/               # 테스트 전략, QA 리포트
│   └── qa-reports/
├── bug-reports/           # 버그 리포트
├── user-guide/            # 사용자 가이드
├── ai-analysis/           # AI 분석 설계
├── migration/             # API 마이그레이션
└── misc/                  # 기타 문서
```

## 문서 업데이트 트리거

| 상황 | 업데이트 대상 |
|------|-------------|
| 새 기능 구현 | `docs/features/{기능}/` + CLAUDE.md "구현 완료 기능" |
| 아키텍처 변경 | `docs/architecture/` + CLAUDE.md 해당 섹션 |
| API 추가/변경 | CLAUDE.md "주요 API 엔드포인트" |
| 버그 수정 | `docs/bug-reports/` + CLAUDE.md "자주 발생하는 버그" |
| 사용자 기능 | `docs/user-guide/` 해당 섹션 |

## 문서 네이밍 규칙

- **설계 문서**: `UPPER_SNAKE_CASE.md` (예: `SCREENER_UPGRADE_PLAN.md`)
- **가이드 문서**: `lower-kebab-case.md` (예: `testing-guide.md`)
- **폴더**: `lower-kebab-case`

## 전체 문서 목록: [docs/README.md](docs/README.md)
