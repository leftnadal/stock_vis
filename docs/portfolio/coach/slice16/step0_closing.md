# Slice 16 Step 0 종결 — 부채 정리 + KPI 정의

> 슬라이스: Slice 16 (E2~E6 화면 복제 — Slice 15 E1 패턴 위에)
> 단계: Step 0 (부채 정리 + KPI 정의, LLM 0콜)
> 베이스: slice15 HEAD `cf37855` (closing)
> 종결 commit: 본 문서 직전 S16-0-(C+D) 커밋
> 신규 LLM 지출: **$0** (Step 0은 코드/문서 작업만)

---

## 0. 한 줄 결과

Slice 16 본작업(E2~E6 화면 복제) 진입 전 Step 0으로 부채 2건(#68 ledger 정합, #70 AllowAny→IsAuthenticated)을 close + cost_ledger 1행 수동 복원 + 슬라이스 KPI 정의. 회귀 무손실(pytest 742→759, IDENTICAL 31/31, vitest 74). 신규 LLM 지출 $0.

---

## 1. Step 0 KPI 매트릭스 — 5/5 통과

| #     | KPI                | 결과                                                                                       |
| ----- | ------------------ | ------------------------------------------------------------------------------------------ |
| S0-K1 | #68 ledger 정합    | CostGuard 기본 slice_id 채택(env → "runtime"), entry_point 인자 전 흐름. 단언 11건 PASS ✅  |
| S0-K2 | #70 AllowAny 해소  | 6 view IsAuthenticated 전환, auth wall 단언 6건 PASS, frontend 무영향 ✅                   |
| S0-K3 | ledger 1행 보정    | Slice 15 P3-C 행 수동 append (slice="slice15", entry_point="e1", source="manual_backfill") ✅ |
| S0-K4 | 회귀               | pytest 742→759 (+17 신규, 기존 무손실), IDENTICAL 31/31, vitest 15/74 무손실 ✅            |
| S0-K5 | 비용·커밋·문서     | $0 (LLM 0콜), 3 commit (S16-0-A + S16-0-B + S16-0-CD), 본 문서 ✅                          |

---

## 2. S16-0-A — #68 ledger entry_point + slice_id 정합 (close)

### 변경
- `portfolio/llm/cost_guard.py`: `slice_id` 기본값을 `field(default_factory=lambda: os.getenv("COACH_RUNTIME_SLICE_ID", "runtime"))`로 변경.
- `config/settings.py`: `COACH_RUNTIME_SLICE_ID = os.getenv("COACH_RUNTIME_SLICE_ID", "runtime")` 추가 (Django 노출 + 명시성).
- `portfolio/llm/client.py`:
  - `complete(..., entry_point: str | None = None)` 옵션 인자 추가 + docstring 갱신.
  - ledger append: `entry_point=None` → `entry_point=entry_point`.
- `portfolio/services/coach/e[1-6]_service.py` 6곳: `client.complete(..., entry_point="eN")` 명시 전달.

### 신규 테스트 (`portfolio/tests/test_s16_step0_ledger_integration.py`, 11건)
| 그룹 | 케이스 수 | 검증 |
|---|---|---|
| CostGuard 기본 slice_id | 3 | env 기본/override/"default" 절대 차단 |
| client.complete entry_point 전 흐름 | 2 | 전달/미전달 backward-compat |
| 6 service 소스 literal 검증 | 6 | parametrize로 entry_point="eN" 존재 단언 |

### 효과
- 운영 view 경로의 ledger 행이 의미값 기록:
  ```
  기존: {"slice": "default", "entry_point": null, ...}
  변경: {"slice": "runtime"|"slice16"|..., "entry_point": "eN", ...}
  ```
- 기존 호출(entry_point 미전달)은 entry_point=null 유지 → backward-compat.

### 부채 close
- **#68** (Slice 14 closing 등록, PS 1.0) — `debts.md` §1 → §2 이전.

### 커밋
`f23d748` — `fix(s16): close #68 ledger entry_point + slice_id 정합 (Step 0-A)`

---

## 3. S16-0-B — #70 AllowAny → IsAuthenticated (close)

### 변경
- `portfolio/api/views.py`:
  - `from rest_framework.permissions import AllowAny` → `IsAuthenticated`.
  - 6 view 모두 `@permission_classes([IsAuthenticated])` 전환.
- `portfolio/tests/api/conftest.py` 신설:
  - `api_client` fixture를 force_authenticate된 APIClient로 통합.
  - `anonymous_api_client` — auth wall 검증 전용.
  - User는 in-memory instance (`User(pk=1, username="coach-test-user")`) — DB 저장 불요.
- `portfolio/tests/api/test_e[1-6]_endpoint.py` 6곳: 로컬 `api_client` fixture 제거 (conftest 위임).

### 신규 테스트 (`portfolio/tests/api/test_s16_auth_wall.py`, 6건 parametrize)
- 6 endpoint 모두 미인증 POST → 401 단언.
- CORS preflight(OPTIONS)는 본 테스트 범위 밖 — django-cors-headers가 view permission 전 응답하므로 APIClient.options() 401과 실 호환성 무관.

### frontend 영향
- `authAxios`가 JWT 자동 첨부 → 정상 호출은 401 미발생.
- MSW 테스트는 mock이라 권한 검사 무관 — vitest 74/74 무손실.

### 부채 close
- **#70** (Slice 15 closing 등록, PS 2.0) — `debts.md` §1 → §2 이전.

### 커밋
`8c4df40` — `fix(s16): close #70 coach view AllowAny → IsAuthenticated (Step 0-B)`

---

## 4. S16-0-C — cost_ledger 1행 수동 보정

### 사실 정렬
- Slice 15 P3-C 호출 직후 ledger 25행 확인 (`tail -1`로 검증).
- 그러나 외부 자동화(#71)의 `git reset --hard`가 working tree와 ledger를 24행으로 복원 → P3-C 행 영구 유실.
- closing.md(`docs/portfolio/coach/slice15/closing.md`)에 실측값 영구 기록.

### 수동 append (Step 0-C 결정 2.a)
ledger 25행 추가:
```json
{
  "timestamp": "2026-05-25T13:06:12.991134+00:00",
  "slice": "slice15",                          // 부정합 보정 (원본 "default")
  "entry_point": "e1",                          // 부정합 보정 (원본 null)
  "provider": "anthropic",
  "model": "claude-haiku-4-5",
  "input_tokens": 1516,
  "output_tokens": 1028,
  "cost_usd": 0.0053248,
  "fallback_from": null,
  "source": "manual_backfill",                  // 자동 append와 구분
  "backfill_note": "Slice 15 P3-C smoke 행 (외부 git reset로 유실, closing.md 영구 기록값 기반 복원)",
  "backfilled_at": "2026-05-26T01:14:14.821974+00:00"
}
```

### 영향
- 신규 LLM 지출 아님 — 과거 발생 비용의 장부 복원.
- 기존 `test_cost_ledger.py` 10/10 PASS — extra key 안전 확인 (`read_records`는 dict 그대로 반환, `sum_cost_usd`는 cost_usd만 사용).
- 향후 ledger 분석 시 `source="manual_backfill"` 필터로 backfill 행 식별 가능.

---

## 5. S16-0-D — Slice 16 KPI 매트릭스 정의

### 회귀 (no-cost) — 모든 Part 공통
| 트랙 | 통과 기준 |
|------|-----------|
| `pytest portfolio/tests tests/coach tests/scoring tests/integration/asgi` | 759/1 이상 유지 (Step 0 종결 시점 baseline) |
| IDENTICAL (4 파일 31 tests) | 31/31 |
| `npx tsc --noEmit` | exit 0 |
| `vitest` | 74/74 이상 (Step 0 종결 시점 baseline) |

### Cost KPI (Part 단계)
- 누적 cap **$1.00** (Slice 16 전체).
- 예상 **$0.03–0.10** — E2~E6 P3-C 5콜 × $0.005–0.02.
- 신규 #72 KPI: **"각 EP(E2~E6) 실 응답 shape == codegen 타입"** — 각 Part P3-C로 충족.

### Part 단위 KPI (E2~E6 공통)
| # | KPI | 통과 기준 |
|---|-----|-----------|
| PartN-K1 | 라우트 | `app/coach/eN/page.tsx` `'use client'` + AuthGuard 패턴 |
| PartN-K2 | 데이터 레이어 | `useENCoach` mutation 훅 (lib/coach/types.ts alias는 Slice 15에서 완성) |
| PartN-K3 | UI | E1 화면 패턴 복제 — 폼 + CommentaryCard + 3-상태 |
| PartN-K4 | 화면 테스트 | 빈/happy/error + a11y/form 검증 ≈ 7건 |
| PartN-K5 | P3-C 실 round-trip | HTTP 200 + 봉투 일치 + codegen 타입 정합 (#72 EP별 close) |
| PartN-K6 | 회귀 | pytest 759/1·IDENTICAL 31/31·vitest 74→74+M·tsc exit 0 |
| PartN-K7 | 비용 | 단일 EP cap $0.05 내 (예상 $0.005–0.02) |
| PartN-K8 | 커밋·문서 | Part 커밋 2~3건 + `slice16/partN.md` |

### Slice 16 종결 KPI (closing 시점)
| # | KPI |
|---|-----|
| S16-K-Final-1 | E2~E6 5 화면 모두 본 KPI 충족 (5 Part 완료) |
| S16-K-Final-2 | 누적 vitest tests = 74 + (E2..E6 신규 합) |
| S16-K-Final-3 | 누적 비용 cap $1.00 내 |
| S16-K-Final-4 | #72 close (5 EP P3-C 모두 정합 확인) |
| S16-K-Final-5 | closing.md + 부채 변동 정리 |

---

## 6. 회귀 매트릭스 (Step 0 시점)

| 트랙 | Slice 15 종결 (`cf37855`) | Slice 16 Step 0 종결 | 변동 |
| ---- | ------------------------- | -------------------- | ---- |
| pytest | 742/1 | **759/1** | +17 (S16-0-A 11 + S16-0-B 6) |
| IDENTICAL | 31/31 | 31/31 | 0 |
| vitest | 15 files / 74 tests | 15 files / 74 tests | 0 (프론트 미변경) |
| tsc --noEmit | exit 0 | exit 0 | 0 |
| cost_ledger 행 | 24 (P3-C 유실) | **25** (수동 backfill로 복원) | +1 |

---

## 7. 커밋 (Step 0, 3건)

| Commit | 단계 | 의미 |
|---|---|---|
| `f23d748` | S16-0-A | fix: #68 ledger entry_point + slice_id 정합 |
| `8c4df40` | S16-0-B | fix: #70 AllowAny → IsAuthenticated |
| (본 커밋) | S16-0-(C+D) | docs+chore: ledger 수동 backfill + Step 0 종결 + KPI 정의 |

---

## 8. HALT 발동 이력 (Step 0)

| 시점 | 유형 | 결과 |
|------|------|------|
| 분기 시점 | 환경 이슈 (#71 재발) | `git checkout -b slice16`이 외부 자동화로 다른 HEAD에서 분기 → `git reset --hard cf37855`로 즉시 교정 + backup 브랜치 `slice16-backup-cf37855` 생성 |
| (그 외) | 다른 게이트 미발동 | tsc/회귀/IDENTICAL 모두 정상 진행 |

---

## 9. 다음 단계 — Part 1 (E2 화면 복제)

### 본작업
Slice 15 E1 패턴을 E2 화면으로 복제:
1. `frontend/lib/coach/api.ts`에 `postE2Coach` 추가 (Part 1에서 E2~E6 path 상수 모두 정리 가능)
2. `frontend/lib/coach/hooks.ts`에 `useE2Coach` 추가
3. `frontend/app/coach/e2/page.tsx` 신설 — E1 패턴 미러
4. `frontend/__tests__/coach/e2-page.test.tsx` 신설
5. P3-C: E2 실 round-trip 1회 ($0.005–0.02) — #72 EP별 close 진행

### Slice 15 closing의 복제 함정 10건 회피 — 모든 Part 공통
- `fetched_at`은 제출 핸들러 내부에서 `new Date().toISOString()` (#24)
- `holdings` sector/asset_class/name=null 자동 채움
- `garp_metrics`/equivalent metrics는 ticker별 nested dict
- API path는 `/coach/eN/` (#19)
- 응답은 `data.output` 접근 (봉투)
- 봉투 wrapper bridge는 자동 적용 — `_wrap_response_envelope` 패턴
- `CoachENRequestRequest` 접미 — alias 사용
- AllowAny → IsAuthenticated 전환됨 (#70 close, S16-0-B) — JWT 필수
- MSW `onUnhandledRequest: 'error'` — 새 핸들러 추가 필수
- 외부 자동화(#71) — backup 브랜치 + `git log` 주기 점검

---

## 10. 부채 변동 (Step 0 시점)

- close: **#68 ledger 정합** (PS 1.0, S16-0-A) + **#70 AllowAny** (PS 2.0, S16-0-B)
- 신규: 0건
- 잔존 OPEN(§1): #51, #63, #66, #67, #59, #69, **#72 (Slice 15 closing, Part별 P3-C로 close 진행)**, #71 환경 이슈
- net: **−2** (Step 0에서 #68/#70 동시 close)

상세는 [debts.md](../debts.md) 갱신본 참조.
