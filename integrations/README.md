# integrations/

외부 시스템과의 격리된 연계 트랙. monorepo blueprint §② 분류 결정에 따라 메인 앱·도메인 서비스와 별도 위치.

## 분류 기준

- **read-only contract 기반 외부 자동화** — 외부 봇/시스템에 데이터를 노출하거나 받는 격리 인터페이스
- 메인 세션과 도메인 성격이 다른 격리 트랙 (apps/services와 세션 충돌 회피)
- 가중합 평가: `iron_trading`은 C(integrations) 5.0 > A(apps) 3.20 > B(services) 2.35 (blueprint_v1.md §②)

## 디렉토리 규약

```
integrations/
├── __init__.py
├── README.md
├── _shared/              # 2+ integration 공유 유틸 자리 (현재 비어 있음)
│   └── __init__.py
└── {integration_name}/   # 각 외부 시스템 1:1 매핑
    ├── apps.py           # Django AppConfig (name=dotted-path, label=단축명)
    ├── migrations/
    ├── services/
    ├── urls.py
    └── views.py
```

## 멤버

| integration | 역할 | contract |
|---|---|---|
| `iron_trading` | 외부 봇 read-only API (시세 + Market Pulse + Signals) | `/api/v1/iron-trading/` 엔드포인트 |

## 네임스페이스 규약 (잠정 v0.1)

- 새 integration 추가 시 `integrations/{name}/` 단일 패키지
- 2+ integration이 공유하는 유틸 발견 시 `_shared/`로 승격
- 외부 호출 0건 + 세션 휴면 시 `_dormant/`로 격리 (현재 부재)
- 본 규약은 **2번째 integration 진입 시 재검토** (현재는 iron_trading 단일 → 검증 사례 부족)

## 답습 자산 (monorepo PR3 학습)

PR3 정착 패턴 — 후속 integration 추가 시 답습:
- Django 패치 7종 (INSTALLED_APPS / AppConfig.name+label / urls.py include / celery beat / asgi routing 등)
- regex 기반 import 재작성 (ast-grep `$X` single-segment 한계 회피)
- 동적 import (mock.patch) 별도 sweep
- ruff format pre-step 분리 (scope 외 격리)

상세: `DECISIONS.md` 부록 A
