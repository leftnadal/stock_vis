# 테마 온도계 시각 검증 (트랙1 / 경량 로컬 렌더 B) — B3 보고

> 작성: 2026-07-13 검증 세션. 베이스라인 `aaaf495` (worktree `~/worktrees/sv-theme-heat`).
> 성격: 로컬 표시 검증(배포·인증·워커 불요, 원장 무변경). **mock 데이터** 사용(실값 아님).

## 하네스 (B0)

- 방식: **경로 (i) next dev 부분 라우트** — 신설 `frontend/app/render-harness/theme-heat/page.tsx`.
  실 `ThemeHeatBar`/`ThemeHeatCard`를 실 Tailwind v4 + `app/globals.css` 맥락에서 렌더.
- 데이터 주입: 컴포넌트가 자체 fetch(TanStack Query)하므로 **QueryClient 캐시에 mock fixture를 seed**(`staleTime:Infinity`) → 캐시 히트, **네트워크·백엔드·인증 0**. 모듈 모킹/MSW 불요.
- 시나리오: `?s=bar | card12 | card13`.
- 실행 메모(재사용 시): worktree frontend에 node_modules 심링크(→Desktop 메인 트리) + **`next dev --webpack -p 3006`**.
  ⚠ **Turbopack 불가** — Turbopack이 파일시스템 루트 밖 심링크를 거부(`Symlink … points out of the filesystem root`). webpack 플래그로 우회. (격리 `npm ci` 하면 Turbopack도 가능하나 느림.)

## 스크린샷 (B2) — 전부 실 브라우저 + 실 CSS

라이트 4컷 + 다크 2컷 촬영. 모두 컴포넌트 무변경(펼침은 실제 "성분 근거 펼치기" 클릭).

| 컷 | 시나리오 | 확인된 렌더 | B1/B2 스펙 대조 |
|----|---------|-----------|----------------|
| (a) | 버튼바 | computed 5(Energy58+1·ConsCyc57−2·Ind56·Tech56+3·FinSvc55−12, 전부 amber=가열) + 누적 Healthcare **25/26 · D-1** 진행바 | ✅ 일치. delta_1d=0(Industrials)은 델타 숨김 정상 |
| (b) | FinSvc 07-12(개정일) | 온도 **55** 가열 · **−12 (1일)** · **[개정일 재산출]** 중립 마커 · 견인 **· 산출 보류 ⓘ** · 신뢰 6/8 | ✅ 일치 |
| (c) | (b) 펼침 의미 레이어 | C1 몸값부담·밸류에이션 **z 0.14 · 3년 자기 이력 대비 (시계열 기준)** / C3 이야기밀도 z 0.90 / C7 수급쏠림 z 0.41 / C8 실적안따라옴 **수집 대기** | ✅ 일치 |
| (d) | FinSvc 07-13(정상일) | 온도 55 · **−3 (1일)**(개정일 마커 **부재**) · 견인 정상 재개 **▼ 냉각 이야기 밀도 86%** · 신뢰 6/8 | ✅ 일치 |
| (a-dark) | 버튼바(다크) | bg-gray-900 배경 · amber(dark:text-amber-400) 스코어 · 다크 보더 정상 | ✅ prefers-color-scheme 기반 다크 정상 |
| (c-dark) | 펼침 카드(다크) | 헤더/z값/구분선 다크 대비 정상 | ✅ 정상 |

> 다크 전환 = macOS 외관 다크(→Chrome `prefers-color-scheme: dark` 활성). Tailwind v4 기본 `dark:` = 미디어쿼리 기반이라 클래스 토글 불가 → OS/에뮬레이션 필요.

## 목업 대조 (B3)

- 지시서가 지목한 목업 `v3_integration.html`·`delta_transition.html`은 **worktree/브랜치에 부재**(전수 검색 0건).
  → 목업 파일 직접 대조 불가. 대신 **B1 스펙 문자열**(카피 함수 `themeHeatCopy.ts` 결과 포함)과 대조 → **전 항목 일치**.

## 실 CSS 이슈 (jsdom이 못 보는 것 — 후속 소패치 후보)

1. **[minor·a11y] 중립 마커 대비 부족.** `개정일 재산출`·`견인 · 산출 보류`·delta·성분 basis 문구가 `text-gray-400`(라이트 흰 배경 대비 ≈2.5:1, WCAG AA 4.5:1 미달). 의도적 de-emphasis(경보 아님)지만 가독 경계선. 결정 시 `gray-500` 상향 검토.
2. **[minor·반응형] 의미 레이어 한 줄 collision 가능.** 성분 행은 좌(label)·우(z·basis) `justify-between` 1행. FinSvc 실측은 `max-w-md`에서 안 겹침. 다만 **긴 label + 긴 basis("3년 자기 이력 대비 (시계열 기준)")** 조합에서 폭이 더 좁아지면 접촉/줄바꿈 가드 없음 → 우측 문구 `whitespace-nowrap`+`shrink-0` 또는 모바일 2행 스택 검토.
3. **오버플로/클리핑 없음.** 카드·버튼·진행바 모두 컨테이너 내 정상. 라이트/다크 색·간격·정렬 일관.

## 결론

- 트랙1 목표(배포 없이 실 브라우저+실 CSS 렌더 확인) 달성. **B1/B2 스펙 대비 렌더 정합 — 블로킹 결함 0.**
- 소패치 후보 2건(대비·반응형 collision 가드)은 mock 렌더 관찰이라 실데이터 무관, 별도 판단.
- 하네스는 잔존 시 카드 변경마다 재사용하는 **시각 회귀 도구**. (⚠ node_modules 심링크 + `--webpack` 실행 규약 위 참조.)
- **주의**: mock 데이터라 실값 정합은 이 트랙 범위 밖(추후 실데이터 라이브 = 선택지 A, 자연 배포 시).
