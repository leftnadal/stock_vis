# 지시서: SFI-I-2 — 애널리스트 시그널 풀 패널 (C안: 컨텍스트 + 의견 추세)

> repo 배치본. 실행 = 브랜치 `monorepo/sess-sfi-i2`, worktree `~/worktrees/sv-sfi-i2`.
> 선행 = SFI-I1(배포·자동발화 GREEN) + I-1b(유니버스 스코프 9종).

## 세션 계약 헤더
- 종류: 실행(기능 슬라이스) — worktree, 브랜치 monorepo/sess-sfi-i2
- 범위: 스냅샷 조회 API(read-only) + 종목 화면 패널(목표가·업사이드·범위·의견 분포·
  월별 추세 차트). **advisory 화면·엔진·기대수익 무접촉 / 뉴스 배지·chain_sight
  슬롯 무접촉(이월)**
- migrate 없음(read API + FE만). 게이트 실패=정지. 랜딩 D-LAND-ATOMIC, push=병진

## Part A — 거버넌스
1. DECISIONS D-I2-0(C안 확정 08-04) + D-I2-1(API는 I-3 공용 설계) + D-I2-2(추세
   소스 = grades_historical, 자체 축적 시계열은 I-3)
2. TASKQUEUE: I2-NEWS-BADGE-DEFER(뉴스 MarketDataBadge·chain_sight narrative 배선 이월)
   + I3-OWN-TIMESERIES(자체 스냅샷 축적 차트, 데이터 성숙 후)

## STEP 0 — ground truth (실측 완료 요약)
- 어젯밤 발화(08-04 18:30 ET) = universe 9·skip 0·captured 9 (I-1b 스코프 라이브)
- 종목 페이지 목표주가 슬롯 = `overview.analyst_target_price`(page.tsx:578) / 현재가 = `stockQuote.real_time_price`
- grades_historical = 12개월 list({date, analystRatingsStrongBuy/Buy/Hold/Sell/StrongSell}, 최신순)
- API 위치 = `packages/shared/stocks/urls.py`(prefix `/api/v1/stocks/`, APIView+IsAuthenticated)
- 차트 = recharts ^3.3.0 기존 사용(재사용, 신규 의존 없음)

## Part 1 — BE: 스냅샷 조회 API (read-only)
- GET (symbol): 최신 AnalystSignalSnapshot 1건(4신호 + grades_historical + captured_at). 인증 기존 패턴. 미수집 = null 계약(available:false)
- D0 가산: 기존 시리얼라이저·엔드포인트 무변경. openapi 갱신
- pytest: 정상·미수집·최신 행 선택(append 테이블 latest)

## Part 2 — FE: AnalystConsensusPanel
- 2a: 패널(목표주가 + 업사이드% + high/low 범위 바 + 의견 분포 바 + 출처·captured_at)
- 2b: 월별 추세 미니차트(grades_historical → 매수계열 비중, recharts 재사용)
- 미수집/null = 기존 "미설정" 폴백(유령 노출 금지)
- MSW + vitest: 렌더·업사이드·null 폴백·추세 변환. 기존 회귀 green

## Closing 게이트
pytest·vitest 회귀 0 / tsc 0 / --check 0 / 경계·health / openapi 갱신 / cost_ledger /
의미 단위 분리 커밋 / 닫기 보고
