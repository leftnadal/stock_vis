# Slice 15 Part 2 종결 문서 — E1 화면 UI

> 슬라이스: Slice 15 (프론트 코치 화면 — E1 GARP 진단, 파일럿 단일)
> 단계: Part 2 (UI 계층, 데이터 레이어는 Part 1)
> 베이스: Part 1 종결 `9de1cdb`
> 종결 시점 commit: `79c9724`
> 누적 LLM 비용: **$0**

---

## 0. 한 줄 결과

Part 1의 `useE1Coach` 위에 라우트(`app/coach/e1/page.tsx`) + 포트폴리오 입력 폼 + `CommentaryCard` (E2~E6 재사용 본보기) + 3-상태(빈/로딩/에러/성공) UI를 올림. MSW 위 화면 렌더 테스트 3건 신규 (vitest 67→70). TS strict 통과, 회귀 무손실, $0.

---

## 1. KPI 매트릭스 — 10/10 통과

| #      | KPI                | 기준                                                            | 결과                                                                                              | 상태 |
| ------ | ------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---- |
| P2-K1  | 라우트             | `app/coach/e1/` 페이지 신설, 클라이언트 컴포넌트                | `app/coach/e1/page.tsx`, `'use client'`, AuthGuard 패턴 (portfolio/dashboard 관례 일치)           | ✅   |
| P2-K2  | 입력 폼            | `E1Request` 조립, `useE1Coach.mutate` 호출                      | portfolio_id + preset + 보유 종목 동적 행(ticker/weight/EPS growth/PE/PEG). 제출 핸들러에서 typed E1Request 조립 | ✅   |
| P2-K3  | CommentaryCard     | `E1Output` 표시, 순수 표시 컴포넌트 (데이터 페칭 없음)          | `components/coach/CommentaryCard.tsx`, output prop만 받음, useQuery/useMutation 사용 안 함        | ✅   |
| P2-K4  | 3-상태 처리        | 로딩·에러·빈 상태 각각 명시 UI                                  | `isIdle` → empty-state, `isPending` → loading-state, `isError` → error-state (role="alert"), `isSuccess` → CommentaryCard | ✅   |
| P2-K5  | 데이터 레이어 불변 | `lib/coach/*`·MSW 인프라 무수정                                 | git diff 확인 — lib/coach/{types,api,hooks}.ts + __tests__/mocks/* 변경 0                          | ✅   |
| P2-K6  | 화면 테스트        | 빈·happy·에러 3 케이스 통과                                     | `__tests__/coach/e1-page.test.tsx` 3건 PASS                                                       | ✅   |
| P2-K7  | 타입·회귀          | tsc exit 0, vitest 67→67+M (기존 67 무손실)                     | tsc exit 0, vitest 13→14 files, 67→70 tests (+3)                                                  | ✅   |
| P2-K8  | 백엔드 무변경      | pytest 742/1·IDENTICAL 31/31 불변                               | git diff 확인 — backend 변경 0 (Part 1 P1-0 이후 백엔드 무손)                                      | ✅   |
| P2-K9  | 비용               | $0 (LLM 실호출 0)                                               | 모든 검증 MSW 가짜 응답                                                                            | ✅   |
| P2-K10 | 커밋·문서          | Part 2 커밋(권장 2~3) + part2.md                                | 3 커밋 (CommentaryCard + page/form + screen tests) + 본 문서                                       | ✅   |

---

## 2. 화면 구조

```
app/coach/e1/page.tsx
├── E1CoachPage (default export)
│   └── AuthGuard                       — portfolio/dashboard 패턴 일치
│       └── E1CoachContent (named export, 테스트 진입점)
│           ├── header: 제목 + 설명
│           ├── form (P2-B)
│           │   ├── portfolio_id (text)
│           │   ├── preset (select: garp/focused/income/growth/factor)
│           │   ├── holdings rows (동적): ticker / weight / EPS growth / PE / PEG
│           │   └── 제출 버튼
│           └── result section (aria-live=polite)
│               ├── empty-state    (mutation.isIdle)
│               ├── loading-state  (mutation.isPending)
│               ├── error-state    (mutation.isError, role=alert)
│               └── CommentaryCard (mutation.isSuccess)
│
components/coach/CommentaryCard.tsx
└── 순수 표시 컴포넌트, output prop만 받음
    ├── header: summary + confidence 배지
    ├── 핵심 관찰 (key_observations)
    ├── 추천 액션 (action_items, priority 배지)
    └── 리스크 (risk_flags)
```

---

## 3. 3-상태 처리 (코치 UX 핵심)

| 상태       | 트리거                   | UI 요소                                                                | 접근성             |
| ---------- | ------------------------ | ---------------------------------------------------------------------- | ------------------ |
| **빈**     | `mutation.isIdle`        | data-testid="empty-state" + 점선 박스 + 안내 문구                       | aria-live=polite   |
| **로딩**   | `mutation.isPending`     | data-testid="loading-state" + Loader2 스피너 + "진단 작성 중" 메시지   | aria-busy=true     |
| **에러**   | `mutation.isError`       | data-testid="error-state" + AlertCircle + 친화적 문구 (원시 에러 미노출) | role=alert         |
| **성공**   | `mutation.isSuccess`     | CommentaryCard(output)                                                  | (정적 렌더)        |

**원시 에러 미노출 보장**:
- "잠시 후 다시 시도해 주세요. 문제가 계속되면 관리자에게 문의해 주세요." 문구만.
- 테스트가 `screen.queryByText(/500/)`, `/AxiosError/` 모두 미존재 검증.

---

## 4. CommentaryCard — 6 진입점 재사용 본보기

### 설계 원칙
- **순수 표시**: `output: E1Response['output']`만 prop으로 받음. react-query 훅 사용 안 함, 부모가 데이터 페칭·상태 관리 책임.
- **graceful empty section**: `key_observations`/`action_items`/`risk_flags` 비어있으면 섹션 자체 미렌더 → E2~E6의 다양한 output shape에서 자연스럽게 동작.
- **deprecated 필드 무시**: `metrics_table`(#21) 명시적으로 미렌더.
- **테스트 진입**: `data-testid="commentary-card"`로 화면 테스트가 존재 검증.

### Slice 16+ 복제 패턴
다른 진입점 화면을 만들 때:
```tsx
import { useE2Coach } from '@/lib/coach/hooks'  // ← Part 1 alias 확장
import CommentaryCard from '@/components/coach/CommentaryCard'

const mutation = useE2Coach()
// ... 폼 조립 (E2Request 형태)
{mutation.isSuccess && mutation.data && <CommentaryCard output={mutation.data.output} />}
```
- CommentaryCard 자체는 prop 타입이 `E1Response['output']`이지만 E2~E6 output도 형태 호환 (summary/confidence/action_items 등 공통 필드 — 백엔드 `commentary_output.py` 공통 base).
- 더 엄밀히 하려면 Slice 16+에서 `type CoachOutput = E1Response['output'] | E2Response['output'] | ...` union 또는 base type alias 도입 검토 후보.

---

## 5. AuthGuard 우회 패턴 (테스트 진입점)

`AuthGuard`는 `useAuth` (AuthContext)에 의존하므로 테스트가 무거워짐. 해결:
- `app/coach/e1/page.tsx`에서 `E1CoachContent`를 **named export**로 노출.
- 테스트는 `import { E1CoachContent }`로 직접 렌더 — AuthGuard / AuthContext 미통과.
- 페이지(`E1CoachPage`)는 default export로 AuthGuard 래퍼 유지 → 실제 라우트는 정상 보호.

이 패턴을 Slice 16+ E2~E6 페이지도 그대로 복제 권장.

---

## 6. E1Request 조립 디테일

```ts
const request: E1Request = {
  portfolio_id: portfolioId.trim(),
  fetched_at: new Date().toISOString(),     // ← 제출 핸들러 안에서 호출 (#24 회피)
  preset,                                    // garp/focused/income/growth/factor
  entry_point: 'e1',
  holdings: validRows.map((r) => ({
    ticker: r.ticker.trim().toUpperCase(),
    weight: Number(r.weight),
    sector: null,                            // 화면 미노출, null 자동 채움
    asset_class: null,
    name: null,
  })),
  garp_metrics: Object.fromEntries(
    validRows.map((r) => [
      r.ticker.trim().toUpperCase(),         // ← key는 종목 ticker
      {
        eps_growth_rate: r.epsGrowth ? Number(r.epsGrowth) : null,
        pe_ratio: r.pe ? Number(r.pe) : null,
        peg_ratio: r.peg ? Number(r.peg) : null,
      },
    ]),
  ),
}
```

### 회피한 함정
- **모듈 레벨 `Date.now()`/`new Date()`** (#24): 제출 핸들러 안에서만 호출 → hydration mismatch 차단.
- **클라이언트 측 과도한 검증**: portfolio_id·ticker·weight 빈값만 거부. 본격 검증은 Pydantic serializer.
- **#19 (`/api/v1` 중복)**: api.ts의 `COACH_E1_PATH = '/coach/e1/'` — baseURL이 `/api/v1` 포함이라 path는 짧게.

---

## 7. 회귀 매트릭스

| 트랙                | 베이스 (Part 1 종결) | Part 2 종결      | 변동 |
| ------------------- | -------------------- | ---------------- | ---- |
| `npx tsc --noEmit`  | exit 0               | exit 0           | 0    |
| vitest              | 13 files / 67 tests  | 14 files / 70 tests | +3 (모두 신규 화면 테스트, 기존 67 무손실) |
| pytest (백엔드)     | 742/1*               | 742/1*           | 0 (백엔드 무손, 미실행) |
| IDENTICAL 31/31     | 31*                  | 31*              | 0 (백엔드 무손, 미실행) |

*Part 1 P1-0 (`1718d47`)에서 마지막 검증. Part 2는 프론트 전용이라 미실행.

---

## 8. 커밋 (3건)

| Commit | 의미 단위 | 변경 |
|---|---|---|
| `ec61c1c` | feat(s15): CommentaryCard — coach diagnosis display component | 1 file, +121 |
| `a488d67` | feat(s15): E1 coach screen — route + portfolio input form | 1 file, +275 |
| `79c9724` | test(s15): E1 screen render tests | 1 file, +97 |

---

## 9. HALT 발동 이력

- **외부 자동 브랜치 전환 1회**: Part 2 작업 도중 외부 자동화가 working tree를 `iron-trading-api` 브랜치로 전환 → vitest.setup.ts·apps.py가 "원래" 상태로 보이는 현상. slice15 HEAD 무사 확인 후 즉시 `git checkout slice15` 복귀, 신규 P2 파일은 untracked로 유지되어 무손실. 작업 계속. 메모리 `[[project_nightly_automation]]` 패턴 확인됨.
- **다른 HALT 게이트**: tsc·vitest·데이터 레이어 불변·백엔드 무변경 모두 미발동.

---

## 10. 산출물 매핑 (지시서 §산출물)

| # | 지시서 항목 | 실제 파일 |
|---|------|------|
| 1 | `app/coach/e1/page.tsx` | ✅ 275줄 (페이지 + 폼) |
| 2 | 포트폴리오 입력 폼 | ✅ page.tsx 내부 (폼 분리 안 함 — 파일럿 단순성) |
| 3 | `components/coach/CommentaryCard.tsx` | ✅ 121줄 |
| 4 | `__tests__/coach/e1-page.test.tsx` | ✅ 97줄, 3 케이스 |
| 5 | Part 2 종결 문서 | ✅ 본 문서 |

---

## 11. Part 3 진입 메모

- Part 3 책임: MSW 통합 테스트 강화 + Slice 15 종결.
- 화면 테스트는 본 Part 2에서 happy/error/빈 3건 PASS — Part 3에서는 통합 시나리오 (폼 입력 → 제출 → 결과 표시) 강화 또는 인증 흐름·에러 변형(400 vs 500) 보강이 후보.
- 또는 Part 3을 슬라이스 종결(문서 정리, 부채 정리, 다음 슬라이스 진입 준비) 단계로 가볍게 마무리.

---

## 12. 부채 / 후속

- 부채 신규 0건.
- 후속 검토 (Slice 16+):
  - CommentaryCard prop 타입을 `E1Response['output']`에서 union/base alias로 일반화.
  - 폼을 별도 컴포넌트로 분리 (`components/coach/CoachInputForm.tsx`) — E2~E6 폼이 서로 다른 input shape이라 진입점별 분리가 자연스러움.
  - 폼 라이브러리 (react-hook-form 등) 도입 검토 — 현재 useState 기반은 종목 행 10개 이상 시 부담.
- 외부 자동화 (`com.stockvis.nightly`) 인지 갱신 — Part 2 도중 또 발생. 메모리에 사례 추가.
