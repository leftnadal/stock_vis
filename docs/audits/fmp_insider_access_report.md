# FMP Starter 내부자 엔드포인트 접근 검증 보고서

- **실행일시**: 2026-07-04
- **실행 주체**: 지시서 `verify_fmp_insider_access` (읽기 전용 audit)
- **총 API 호출 수**: **10회** (스모크 1 + 프로브 8 + 페이지네이션 1) — 예산 20회 이하 준수 ✅
- **플랜**: FMP Starter (300 req/min, 10,000 req/day)
- **베이스**: `https://financialmodelingprep.com` (stable 경로 전건 성공 → v4 폴백 불필요)

---

## 판정: **PASS**

E1(종목별 검색) + E3(집계 통계) 모두 stable에서 OPEN, 필수 필드(`transactionType`, `filingDate`, `typeOfOwner`) 전건 존재, FMP 반영 지연 ≤ 3일(최신 스트림 E2 기준 2일). **Ultimate 업그레이드 불필요**, SEC β Form 4 파싱 트랙 제거 가능.

> ⚠️ 신선도 단서: 지시서 문구를 **종목별 최신 filingDate ↔ 오늘 간극**으로 엄격 해석하면 NVDA는 5일(3~7일 밴드 = PARTIAL 구간)이다. 그러나 이 5일은 "FMP 반영 지연"이 아니라 **NVDA 임원이 최근 5일간 신규 Form 4를 제출하지 않은 실제 공백**이다. 시스템 전체의 반영 지연은 최신 스트림(E2) 최상단 filingDate = `2026-07-02`(2일)로 측정되며, 이것이 지시서가 정의한 "반영 지연 ≤ 3일 합격" 기준의 정확한 계측기다. 따라서 PASS로 판정하되, 엄격 해석을 선호할 경우 PARTIAL로 하향 가능함을 명시한다.

---

## 엔드포인트별 결과표

| # | 목적 | Stable 엔드포인트 | HTTP | 분류 | 비고 |
|---|------|------------------|------|------|------|
| **E1** | 종목별 내부자 거래 검색 | `/stable/insider-trading/search` | 200 | **OPEN** | NVDA/AAPL/IONQ 3종목 모두 100건/page 반환 |
| **E2** | 최신 내부자 거래 스트림 | `/stable/insider-trading/latest` | 200 | **OPEN** | 최신 filingDate `2026-07-02` (반영 지연 2일) |
| **E3** | 종목별 매수/매도 집계 통계 | `/stable/insider-trading/statistics` | 200 | **OPEN** | 분기별 집계 101 레코드, 자체 집계 코드 불필요 |
| **E4** | (부차) 13F 기관 보유 | `/stable/institutional-ownership/latest` | 402 | **PLAN_LOCKED** | Ultimate 필요. 주 판정 무관(부속 확인) |

- E1·E2·E3 전건 stable OPEN → **v4 레거시 폴백 미실행**.
- E4는 부차 항목으로 판정에 영향 없음(결과만 기록).

---

## 데이터 품질 (Step 2 체크리스트 결과 — NVDA 기준)

### 1. 필드 존재 여부

| 요구 필드 | 존재 | FMP 실제 필드명 |
|-----------|:----:|-----------------|
| `transactionType` (S-Sale/P-Purchase 등) | ✅ | `transactionType` (예: `S-Sale`, `A-Award`, `M-Exempt`, `F-InKind`, `G-Gift`) |
| `securitiesTransacted` | ✅ | `securitiesTransacted` |
| `price` | ✅ | `price` (Award/Exempt 거래는 0) |
| `filingDate` | ✅ | `filingDate` |
| `transactionDate` | ✅ | `transactionDate` |
| `reportingName` | ✅ | `reportingName` |
| `typeOfOwner` | ✅ | `typeOfOwner` (예: `director`, `officer: ...`) |
| `securityName` (파생 식별) | ✅ | `securityName` + `formType` |
| `link` (SEC 원문) | ⚠️ **동등 필드** | `url` = `https://www.sec.gov/Archives/edgar/data/...` — 지시서 "동등 필드" 조항 충족, SEC β 교차검증 훅 확보 |

부가 필드: `reportingCik`, `companyCik`, `acquisitionOrDisposition`(A/D), `directOrIndirect`(D/I), `securitiesOwned`. → 임원 vs 10% 주주 구분 및 직접/간접 보유 노이즈 필터링 가능.

**transactionType 분포(NVDA page0 100건)**: S-Sale 58, A-Award 25, F-InKind 11, G-Gift 5, 공란 1 → 매도/매수 비율 계산의 원천 필드가 실제로 채워져 있음을 확인.

### 2. 신선도

| 종목 | 최신 filingDate | 오늘 대비 간극 | 판정 |
|------|-----------------|:---:|------|
| NVDA | 2026-06-29 | 5일 | 종목 자체 제출 공백 (반영 지연 아님) |
| AAPL | 2026-06-17 | 17일 | 동상 |
| IONQ | 2026-06-22 | 12일 | 동상 |
| **E2 최신 스트림** | **2026-07-02** | **2일** | ✅ **반영 지연 ≤ 3일 합격** |

→ 시스템 반영 지연 = 2일. 종목별 간극은 해당 종목의 실제 filing cadence를 반영하는 것이지 FMP 지연이 아님.

### 3. 커버리지 (최근 90일 건수)

| 종목 | page0 총건 | 최근 90일 | oldest(page0) |
|------|:---:|:---:|---|
| NVDA | 100 | 26 | 2026-02-06 |
| AAPL | 100 | 24 | 2025-10-03 |
| IONQ (중소형주) | 100 | **19** | 2025-06-18 |

→ IONQ가 19건(≠0)으로 **중소형주 커버리지 확인**. SEC EDGAR 교차 확인은 지시서상 "0건인 경우에만" 필요 → **불필요(호출 절감)**.

### 4. E3 집계 품질 (판정 가치 높음)

NVDA statistics 101 레코드, 분기별 구조:
```
{symbol, cik, year, quarter,
 acquiredTransactions, disposedTransactions, acquiredDisposedRatio,
 totalAcquired, totalDisposed, averageAcquired, averageDisposed,
 totalPurchases, totalSales}
```
예: NVDA 2026 Q2 → acquired 2 / disposed 7 / ratio 0.2857, totalDisposed 1,723,625주. IONQ 2026 Q2 → ratio 0.75(중소형주도 집계 제공).

→ **분기별 매수/매도 건수·비율·수량을 FMP가 사전 집계**하여 제공. 온도계에서 자체 집계 코드가 불필요해짐. `totalPurchases`/`totalSales`(공개시장 P/S)와 `acquired`/`disposed`(A/D 전체)가 분리 제공되어 노이즈 필터 설계 유리.

---

## 운영 파라미터 (Step 3)

- **Rate limit 헤더**: 응답에 `X-RateLimit-*` / `Retry-After` **미노출**. `content-type: application/json`, `content-length`만 존재. → 한도는 플랜 문서값(300/min·10k/day)에 의존, 헤더 기반 실시간 잔량 추적 불가.
- **페이로드 크기**: E1 100건 ≈ **59 KB**, E3 statistics ≈ 36 KB, E2 latest 100건 ≈ 61 KB.
  - 온도계 일배치 대역폭 추산: 종목 500개 × 1페이지(59KB) ≈ **29 MB/일**. Starter 20GB/30일 한도 대비 무시 가능(월 ~0.9GB). E3 병행해도 여유.
- **페이지네이션**: `page` 파라미터 정상 동작 확인. page0 = `2026-06-29`~`2026-02-06`, page1 = `2026-02-06`~`2025-12-10`로 시계열 연속·중복 없음(첫 레코드 상이). `limit=100` 적용됨.

---

## PLAN_LOCKED 응답 원문

**E4** `/stable/institutional-ownership/latest` (HTTP 402):
```
Restricted Endpoint: This endpoint is not available under your current subscription
please visit our subscription page to upgrade your plan at https://financialmodelingprep.com/
```
→ 13F 기관 보유(부차 항목)는 Ultimate 필요. 내부자 거래(E1~E3, 주 판정)와 무관.

---

## DECISIONS.md 기록 초안

> **[2026-07-04] FMP Starter 내부자 거래 엔드포인트 = ThemeHeatScore 공급 반응 원천으로 채택 (PASS).**
> E1(search)·E2(latest)·E3(statistics) stable 전건 OPEN, 반영 지연 2일, 필수 필드(transactionType/filingDate/typeOfOwner) + SEC 원문 링크(`url`) 확보, E3가 분기별 매수/매도 집계 사전 제공. **SEC β의 Form 4 직접 파싱 트랙 제거**, 온도계 공급 반응 성분을 FMP 소비로 설계. Ultimate 업그레이드 불요(단 E4 13F는 402 잠김 — 온도계 범위 밖).

---

## 검증 종료 확인

- ✅ 판정 1개 확정: **PASS**
- ✅ 총 API 호출 **10회** (예산 20회 이하 준수)
- ✅ 코드베이스 변경사항 없음 — 기존/추적 파일 수정 0건. 신규 산출물은 이 보고서(`docs/audits/fmp_insider_access_report.md`, untracked) 1개뿐. git 커밋 미생성.
- ✅ API 키 평문 미노출 (환경변수 `$FMP_API_KEY`로만 참조, URL `apikey=` 마스킹, len=32/head=qA1W*** 형식만 기록)
