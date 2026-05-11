# Market Pulse v2 — API Contract

**스펙 진실의 소스**: drf-spectacular 자동 생성 — `GET /api/v2/schema/?format=json`
**UI 진단**: `/api/v2/swagger/`, `/api/v2/redoc/`

## Endpoints

| Method + Path | 인증 | 캐시 | Throttle |
|---------------|------|------|----------|
| `GET /overview` | IsAuthenticated | 5분 글로벌 | user 60/min + 1000/h |
| `GET /cards/{id}/detail` | IsAuthenticated | brief 30분 / 그 외 5분 | user 60/min + brief LLM 5/min |
| `POST /news/refresh` | IsAuthenticated | NewsViewLog 24h unique | user 60/min |
| `GET /i18n` | IsAuthenticated | 24h 글로벌 | user 60/min |
| `GET /health` | IsAdminUser | 10초 | (admin only) |

`{id}`: regime, breadth, sector, flow, brief.

## 인증
JWT Bearer. v1 default `IsAuthenticatedOrReadOnly` 의존하지 않고, 모든 marketpulse view는 명시적 `IsAuthenticated` 또는 `IsAdminUser`.

## 응답 envelope

`/overview`:
```json
{
  "_meta": {
    "status": "OK | INSUFFICIENT_DATA | STALE | FAILED | MARKET_CLOSED",
    "status_reason": "string",
    "generated_at": "ISO8601",
    "latency_ms": 0,
    "data_finalized": false,
    "cache": "HIT | MISS"
  },
  "ticker_bar": [...],
  "news": [...],
  "anomaly": {...},
  "cards": { regime, breadth, sector, flow, brief }
}
```

## i18n 정책 (D4)
응답 본체는 영문 키만. 한글 라벨은 `/i18n?locale=ko` 별도 조회. UI는 키-라벨 매핑을 클라이언트에서 합성.

## Immutable post-FE start
Frontend 작업 시작 후 응답 스키마 변경 금지. 추가 필드는 가능, 제거/이름 변경 불가.
