# CS-EXP STEP 0 — Ground Truth 조사 결과 (진입 체크포인트)

> 세션: monorepo/sess-cs-exp (worktree stock_vis_cs_exp), 진입일 기준 main = ffbe599
> 상태: STEP 0 완료, **Part A 진입 전 HALT** — FMP holdings 전제 붕괴(디렉터 결정 필요)

## 전제 충족 확인
- RD1 종결(TASKQUEUE CS-RD1 done) + cs-rd1(`0724b76`)·cs-univ(`9d80cdc`) main 머지됨 ✅

## 1. "추가 32" 메커니즘
- 단일 경로 아님 = **(A) SP500 과거 탈락 잔류 18개** + **(B) 온디맨드 자동 생성 14개**의 합.
- (B) 경로 = `StockSyncService.sync_overview(symbol)` — `packages/shared/stocks/services/stock_sync_service.py:172` `Stock.objects.update_or_create(...)`.
- **재사용 가능**: 신규 종목 편입은 `StockSyncService().sync_overview(symbol)` 그대로 사용. 새 메커니즘 발명 불필요.
- HALT 조건("재사용 불가 구조") 미해당.

## 2. FMP ETF holdings 엔드포인트 — ⚠️ 전제 붕괴
- shared FMP 래퍼(serverless_client.py / client.py)에 holdings 메서드 **없음**.
- `/stable/etf-holdings`·`/stable/etf-holder`·`/stable/etf-stock-exposure` → 404, `/api/v3/etf-holder` → 403(Legacy, Starter Plan 미지원).
- **결론: FMP로 holdings 수집 불가.** 사용 콜 5회(SMH 테스트).
- 실제 경로 = 운용사 공식 CSV/XLSX 직링크: `services/serverless/services/etf_csv_downloader.py` `ETFCSVDownloader.download_holdings()` + `ETF_CSV_SOURCES`(55행~). 파서: spdr(XLSX)/ishares/ark/invesco/generic(CSV).
- → 지시서 Part A 채택 기준 ③ "FMP holdings 응답 정상"은 무효. 대체 기준 = "운용사 CSV URL 확보 + 파서 매칭" 필요.

## 3. 기존 ETFProfile 21개 분류
| 분류 | 심볼 | 개수 | holdings 행 |
|---|---|---|---|
| (a) 섹터형 | XLB XLC XLE XLF XLI XLK XLP XLRE XLU XLV XLY | 11 | 8,233 |
| (b) 테마형+holdings 보유 | BOTZ ICLN LIT SOXX | 4 | 2,562 |
| (c) 테마형+holdings **미수집(0행)** | ARKG ARKK BETZ HACK KWEB TAN | 6 | 0 |
| (d) 광역 | (없음) | 0 | - |
| 합계 | | 21 | 10,795 |
- (c) 6개는 parser_type은 있으나 CSV URL 만료/변경 추정 → Part A 착수 전 URL 상태 재확인 1순위.

## 4. 커버리지 분모 통일
- 현재 유니버스 N = **535** (`Stock.objects.count()`). Stock에 `is_active` 류 플래그 없음 → 전체 = active.
- 3.9%(분모 503=`SP500Constituent.is_active=True`) vs 4.5%(분모 535=Stock 전체) 차이 32 = (A)18+(B)14.
- **고정: 분모 = `Stock.objects.count()` = 535** (편입 후 증가).

## HALT 판단 / 디렉터 결정 필요 사항
- "추가 32" 메커니즘은 재사용 가능(HALT 아님).
- 그러나 **FMP holdings 불가 → Part A의 수집 수단이 CSV 직링크로 전환**됨. 이는 지시서 전제와 다름:
  1. 후보 ETF(SMH·IGV·SKYY·CIBR 등 ~25종)마다 운용사 CSV URL을 소싱/검증해야 함(파서 매칭 포함).
  2. 기존 (c) 6개 테마 ETF부터 CSV URL이 깨져 holdings 0건 — 신규 수집보다 선행 복구 대상.
- **권고: Part A 진입 전 디렉터가 ① CSV 직링크 경로 승인 + URL 소싱 책임 주체, ② (c) 6개 선복구 우선순위를 결정.**
