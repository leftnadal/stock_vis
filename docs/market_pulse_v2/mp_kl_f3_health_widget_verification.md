# MP-KL-F3 — health 위젯 명세 검증

> 작성: 2026-06-11 · 트랙: MP-KL (market_pulse Phase 1 K/L 후속) · 상태: **확정(RESOLVED)**
> 선결 관계: `MP-LIVE-VERIFY` 게이트의 선결 조건 (이 검증 통과로 게이트의 "health" 항목 해소)

## 1. 질문

`MP1-L` 산출물 표기 — "health 위젯은 `StatusBanner` 매핑 **추정**(`MP-KL-F3` 확인)".
즉 **사용자 대면 health 위젯이 `StatusBanner`로 충족되는가, 별도 위젯이 필요한가**를 확정한다.

## 2. 실측 — 백엔드에 status 표면이 2개 존재

| 표면 | 위치 | 권한 | 내용 | 프론트 소비 |
|------|------|------|------|------------|
| **overview `_meta.status`** | `apps/market_pulse/api/views/overview.py:273-286` (`api/status.derive_status`) | 공개(인증 사용자) | 5값 enum: `OK`/`INSUFFICIENT_DATA`/`STALE`/`FAILED`/`MARKET_CLOSED` + `status_reason` | ✅ `StatusBanner` |
| **`/health` (HealthView)** | `apps/market_pulse/api/views/health.py` | **`IsAdminUser` 전용** | DB ping + cache ping + 6개 스냅샷 `last_runs` 타임스탬프 | ❌ 미호출 (운영 점검용) |

- 프론트 `frontend/app/market-pulse-v2/` + `hooks/useMarketPulseV2.ts` + `lib/api/marketPulseV2.ts` 전수 grep → **`/health` 호출 0건**. `fetchOverview`/`fetchCardDetail`/`fetchI18n`/`refreshNews` 4개 fetch만 존재.
- `page.tsx:59` → `<StatusBanner status={meta.status} reason={meta.status_reason} />` 가 유일한 사용자 대면 상태 위젯.

## 3. 정합 검증 — status 5값 3중 일치

| 소스 | 값 |
|------|-----|
| 백엔드 `apps/market_pulse/api/status.py:APIStatus` | OK / INSUFFICIENT_DATA / STALE / FAILED / MARKET_CLOSED |
| 프론트 타입 `lib/api/marketPulseV2.ts:23 APIStatus` | OK / INSUFFICIENT_DATA / STALE / FAILED / MARKET_CLOSED |
| 위젯 `components/StatusBanner.tsx:5 COPY` | 5값 전수 매핑 (OK는 `return null`로 숨김, 나머지 4값 톤+라벨) |

→ **누락/초과 값 없음.** `StatusBanner`의 `COPY[status] ?? COPY.OK` 폴백도 안전.

## 4. 결론 (확정)

1. **사용자 대면 "health 위젯" = `StatusBanner`로 충족.** overview `_meta.status` 5값을 전수 매핑하므로 **별도 위젯 불필요**. `MP1-L`의 "추정"을 **확정**으로 승격.
2. **백엔드 `/health`(HealthView)는 `IsAdminUser` 전용 ops probe** — 일반 사용자 화면 위젯 대상이 **아님**. 현재 프론트 미통합 상태가 **정상(의도된 설계)**.
3. 운영 점검용 health probe를 화면에 노출할 필요가 생기면 **admin 전용 대시보드 별도 트랙**으로 분리한다(능동 모니터링 `MP1-N`과 결이 맞음 — 사용자 Phase 1 출시 범위 밖).

## 5. 후속

- `MP-LIVE-VERIFY` 게이트의 health 선결 항목 **해소**. 게이트 잔여 = 서버 기동 + overview 200 + 5 card_id detail 응답 + 실 렌더 대조(라이브 환경 필요).
- F3는 코드 변경 없음(검증·확정 only). `StatusBanner` 현행 유지.
