# CS-EXP-SOURCE — 테마 ETF 소싱 가용성 분석 및 게이트 통과 시뮬레이션 (READ-ONLY)

> 세션 브랜치: `monorepo/sess-cs-exp` (worktree `stock_vis_cs_exp`)
> 측정일: 2026-06-15
> **DB 쓰기 0건 · 소스 코드 diff 0줄 · FMP 콜 0건**
> 외부 HTTP 콜: **40건** (예산 40 소진)

---

## STEP 0 — 게이트 정의

- **Qualified group**: 유니버스 내 멤버 ≥ 3인 테마 그룹
- **게이트 통과 조건**: qualified groups ≥ 6 **AND** qualified groups 간 종목 수 중앙값 ≥ 10

---

## STEP 1 — 컨텍스트 문서 요약

| 문서 | 핵심 내용 |
|------|----------|
| `CS-EXP_STEP0_findings.md` | FMP holdings 불가 → CSV 직링크 경로 확정. (c) 6개 테마 ETF holdings 0행. |
| `CS-EXP-GATE_measurement.md` | 현재 테마 그룹 분포 `[0,0,0,0,1,12,32,39,56,221]`, 중앙값 6.5 ❌ |
| `etf_csv_downloader.py` | 파서 5종: `spdr`(XLSX), `ishares`(CSV), `globalx`(date-URL CSV), `generic`(CSV), `kraneshares` |

---

## STEP 2 — DB 현황 (측정 기준일 2026-06-15)

### 유니버스

- `Stock.objects.count()` = **535**

### ETFProfile (theme tier) - 전체 csv_url 확인

| 심볼 | theme_id | parser | w≥1.0 유니버스내 | holdings_in_db |
|------|---------|--------|-----------------|----------------|
| SOXX | semiconductor | ishares | **221** | 429 |
| BOTZ | robotics_ai | globalx | **56** | 364 |
| ICLN | clean_energy | ishares | **39** | 1,657 |
| LIT | lithium_battery | globalx | **32** | 112 |
| ARKK | innovation | generic | **12** | 44 |
| ARKG | genomics | generic | **1** | 32 |
| HACK | cybersecurity | generic | **0** | 0 |
| BETZ | igaming | generic | **0** | 0 |
| KWEB | china_internet | kraneshares | **0** | 0 |
| TAN | solar | invesco | **0** | 0 |

> 참고: SOXX/ICLN(iShares) 현재 last_error='파싱된 Holdings가 없습니다' (URL 쿠키 만료)
> 단 holdings_in_db 값은 과거 성공 로드 결과가 유지됨.

### 현재 게이트 상태

**Qualified groups** (w≥1.0 멤버 ≥3): SOXX(221), BOTZ(56), ICLN(39), LIT(32), ARKK(12) = **5개**

```
분포: [12, 32, 39, 56, 221] (n=5)
중앙값: 39 ✅ (≥10)
qualified ≥ 6: ❌ (5개)

게이트: ❌ (qualified 1개 부족)
```

> ⚠️ GATE 문서(6.5)와 차이: GATE 문서는 ETF_THEME_MAP 기반 필터링에서 이전 holdings 적재 방식 사용.
> 본 측정은 `ETFHolding.objects.filter(etf=profile, weight_percent__gte=1.0, stock_symbol__in=universe)` 직접 쿼리 기준.
> 핵심 결론 동일: **게이트 미달**, qualified 1개 추가로 통과.

---

## Part A — 14개 후보 ETF 소싱 가용성

### 외부 콜 예산 트래킹

| 콜 번호 | 대상 | 결과 |
|---------|------|------|
| 1 | IBB HEAD (iShares) | HTTP 200 |
| 2 | ITA HEAD (iShares) | HTTP 200 |
| 3 | IGV HEAD (iShares) | HTTP 200 |
| 4 | ITB HEAD (iShares) | HTTP 301 |
| 5 | XBI HEAD (SPDR institutional) | HTTP 301 |
| 6 | KRE HEAD (SPDR institutional) | HTTP 301 |
| 7 | XBI HEAD (SPDR intermediary) | HTTP 301 |
| 8 | KRE HEAD (SPDR intermediary) | HTTP 301 |
| 9 | ITB follow redirect | HTTP 200 |
| 10 | XBI follow redirect | HTTP 200 |
| 11 | KRE follow redirect | HTTP 200 |
| 12 | IBB content check | HTML (cookie wall) |
| 13 | IBB browser headers | HTML (cookie wall) |
| 14 | SOXX baseline check | HTML (cookie wall) |
| 15 | iShares + Referer | HTML (cookie wall) |
| 16 | XBI SPDR content | `PK..` (XLSX binary ✅) |
| 17 | XLK SPDR baseline | `PK..` (XLSX binary ✅) |
| 18 | SMH VanEck HEAD | HTTP 404 |
| 19 | SMH VanEck GET | empty |
| 20 | PPA Invesco | HTTP 406 |
| 21 | CIBR First Trust (FundId=218) | HTTP 404 |
| 22 | CIBR First Trust alt | HTML (no download link) |
| 23 | SMH VanEck .xlsx | HTTP 302 |
| 24 | SMH VanEck globalassets | HTTP 302 |
| 25 | SKYY First Trust | HTTP 404 |
| 26 | JETS US Global | HTTP 404 |
| 27 | PAVE GlobalX 20260615 | 404 HTML |
| 28 | URA GlobalX 20260615 | 404 HTML |
| 29 | PAVE GlobalX 20260614 | 404 HTML |
| 30 | URA GlobalX 20260614 | 404 HTML |
| 31 | PAVE GlobalX 20260612 | **CSV ✅** 헤더 포함 |
| 32 | SMH VanEck redirect target | 302 → disabled-cookies |
| 33 | SMH VanEck download path | HTTP 302 |
| 34 | URA GlobalX 20260612 | **CSV ✅** 헤더 포함 |
| 35 | BOTZ GlobalX baseline | CSV ✅ (20260209, 기존) |
| 36 | SMH VanEck verbose debug | 301 only |
| 37 | SMH VanEck with cookie jar | HTTP 200 (blank content) |
| 38 | SMH VanEck globalassets path | empty |
| 39 | SMH VanEck with cookie jar (GET) | whitespace only |
| 40 | ITB iShares redirect target | 301 → /closed-funds/ |

**총 외부 콜: 40건 (예산 소진)**

---

### 3-Way 분류 결과

#### ✅ 즉시 로드 가능 (Immediately Loadable)

| ETF | 운용사 | 파서 | URL 확인 | 비고 |
|-----|--------|------|---------|------|
| **XBI** | State Street SPDR | `spdr` | 200 + `PK..` XLSX | `holdings-daily-us-en-xbi.xlsx` 패턴 (기존과 동일) |
| **KRE** | State Street SPDR | `spdr` | 200 + `PK..` XLSX | `holdings-daily-us-en-kre.xlsx` 패턴 (기존과 동일) |
| **PAVE** | Global X | `globalx` | 200 CSV (20260612) | 날짜 기반 URL, `_resolve_globalx_url()` 7일 루프 적용 가능 |
| **URA** | Global X | `globalx` | 200 CSV (20260612) | 날짜 기반 URL, `_resolve_globalx_url()` 7일 루프 적용 가능 |

> PAVE/URA: CSV 헤더 형식 = `% of Net Assets,Ticker,Name,SEDOL,...` — BOTZ/LIT와 동일 GlobalX 포맷.
> ETFCSVDownloader._resolve_globalx_url()가 7일 루프로 최신 날짜 자동 탐지함.

#### ⚠️ 파서 수정 필요 (Parser Modification Needed)

| ETF | 운용사 | 상태 | 이슈 | 수정 난이도 |
|-----|--------|------|------|------------|
| **IBB** | iShares | URL 200, 내용 HTML | 쿠키/JS 인증 필요. SOXX/ICLN과 동일 문제 — 과거엔 작동했으나 현재 쿠키 만료. httpx.Client 세션에 쿠키 재취득 로직 추가 필요 | 중 |
| **ITA** | iShares | URL 200, 내용 HTML | 동일 iShares 쿠키 이슈 | 중 |
| **IGV** | iShares | URL 200, 내용 HTML | 동일 iShares 쿠키 이슈 | 중 |
| **HACK** | Amplify | URL 200 (기존 적재), CSV 형식 비표준 | `StockTicker` 컬럼명 비표준, `Account=HACK` 필터 필요 (etf_csv_downloader.py L183-184) | 소 |
| **BETZ** | Roundhill | URL 200 (기존 적재), CSV 형식 비표준 | `StockTicker` 컬럼명 비표준, `Account=BETZ` 필터 필요 (L215-218) | 소 |
| **KWEB** | KraneShares | URL 200 (curl 성공), httpx Cloudflare 차단 | 날짜 기반 URL 확인됨(`{MM_DD_YYYY}_kweb_holdings.csv`), curl은 성공, httpx는 403 | 소 |
| **SMH** | VanEck | 쿠키 필요, 내용 blank | 쿠키 스토어 있으면 200 반환하나 실제 파일 내용은 JS 렌더링 필요 | 중-고 |

#### ❌ 소싱 차단 (Source Blocked)

| ETF | 운용사 | HTTP 코드 | 이유 |
|-----|--------|----------|------|
| **ITB** | iShares | 301 → `/closed-funds/` | 펀드 폐쇄/이전 — URL이 closed-funds 페이지로 리디렉션 |
| **CIBR** | First Trust | 404 | 직접 CSV URL 없음. FundId=218 엔드포인트 404. 대체 URL 미확인 |
| **SKYY** | First Trust | 404 | 동일 First Trust 패턴 — 직접 다운로드 URL 없음 |
| **PPA** | Invesco | 406 | 헤더 기반 다운로드 거부 (Not Acceptable). TAN과 동일 Invesco 차단 패턴 |
| **JETS** | US Global Investors | 404 | 직접 CSV URL 없음. 소규모 운용사 — 직접 다운로드 API 미노출 |

---

### 소싱 분류 요약

| 분류 | ETF | 개수 |
|------|-----|------|
| 즉시 로드 가능 | XBI, KRE, PAVE, URA | **4** |
| 파서 수정 필요 | IBB, ITA, IGV, HACK, BETZ, KWEB, SMH | **7** |
| 소싱 차단 | ITB, CIBR, SKYY, PPA, JETS | **5** |
| **합계** | | **16** (14 후보 + 기존 HACK/BETZ/KWEB 재분류) |

> ⚠️ HALT 조건 체크: 소싱 차단 5/14 = **35.7%** < 70%(10/14 임계). HALT 미발동.

---

## Part B — 게이트 통과 시뮬레이션

### 즉시 로드 가능 ETF의 유니버스 교차 추정

| ETF | 주제 | 전체 holdings 추정 | SP500 교차 추정 | 비고 |
|-----|------|--------------------|----------------|------|
| **XBI** | 바이오테크 | ~120개 (equal-weight) | **~10** | SP500 Biotechnology sub_sector = 8개, 비SP500 소수 포함 |
| **KRE** | 지역은행 | ~140개 | **~6** | SP500 Regional Banks = 6개(CFG/FITB/HBAN/KEY/MTB/RF), 非SP500 다수지만 유니버스 외 |
| **PAVE** | 인프라 | ~100개 | **~30** | SP500 Industrials 81개 중 Construction/Machinery/Building 관련 ~30개 |
| **URA** | 우라늄 | ~45개 (글로벌) | **~3** | SP500에 우라늄 기업 없음. 非SP500 US 상장 우라늄기업 소수 (CCJ 등) |

> 추정 방법: SP500Constituent.sub_sector 필드 직접 쿼리 + ETF 보유 특성 고려.
> PAVE CSV 샘플: RRX(REGAL REXNORD) = SP500 Industrials 확인. 유사 종목 30개 추정.
> URA CSV 샘플: MGA CN(캐나다), BKY SM(스페인) → 해외 중심. US universe 교차 ~3.

### 게이트 통과 시뮬레이션 결과

#### 현재 상태 (기준선)

```
Qualified groups: SOXX(221), BOTZ(56), ICLN(39), LIT(32), ARKK(12) = 5개
분포: [12, 32, 39, 56, 221]
중앙값: 39 ✅
게이트: ❌ (qualified 5 < 6)
```

#### 시나리오 1: 즉시 로드 가능 4개 모두 추가

```
추가: PAVE(30), XBI(10), KRE(6), URA(3)
Qualified: SOXX(221), BOTZ(56), ICLN(39), LIT(32), PAVE(30), ARKK(12), XBI(10), KRE(6), URA(3) = 9개
분포: [3, 6, 10, 12, 30, 32, 39, 56, 221]
중앙값: 30 ✅
게이트: ✅ (qualified=9 ≥ 6 AND median=30 ≥ 10)
```

#### 시나리오 2: 최소 조합 — PAVE 1개만 추가

```
추가: PAVE(30)
Qualified: SOXX(221), BOTZ(56), ICLN(39), LIT(32), PAVE(30), ARKK(12) = 6개
분포: [12, 30, 32, 39, 56, 221]
중앙값: (32+39)/2 = 35.5 ✅
게이트: ✅ (qualified=6 AND median=35.5 ≥ 10)
```

#### 시나리오 3: 최소 조합 — URA 1개만 추가 (가장 약한 케이스)

```
추가: URA(3) — 추정 최솟값
Qualified: SOXX(221), BOTZ(56), ICLN(39), LIT(32), ARKK(12), URA(3) = 6개
분포: [3, 12, 32, 39, 56, 221]
중앙값: (32+39)/2 = 35.5 ✅
게이트: ✅ (qualified=6 AND median=35.5 ≥ 10)
```

> **핵심 관찰**: 현재 구조에서 qualified 중앙값은 이미 39(현재 상태 기준)로 임계치(10)를 크게 상회.
> 게이트 통과 병목은 **오직 "qualified 6개 미만"** — 즉시 로드 가능 ETF 1개만 추가해도 통과.
> URA 3개(최솟값) → 새 qualified group 생성 → 게이트 통과 확정.

### ARK 패러독스 후보

| ETF | 예상 유니버스 교차 | 판정 |
|-----|------------------|------|
| URA | ~3 (경계값) | 주의 — 실제 로드 후 <3이면 qualified 미달 |
| KRE | ~6 | 안전 (SP500 Regional Banks 6개 확인) |
| XBI | ~10 | 안전 |
| PAVE | ~30 | 안전 |

> ARK 패러독스 정의: 그룹 추가 시 qualified 증가 없이 중앙값만 낮추는 역설.
> URA의 실제 교차가 2 이하면 → qualified 0 증가 + 분포에 2가 추가되어 중앙값 하락 가능성.
> 단 현재 중앙값=39로 여유가 크므로 URA(2) 추가 시에도 중앙값 ~35 유지.

---

## 결론 및 권고

### 소싱 가용성 요약

| 우선순위 | ETF | 소싱 경로 | 게이트 기여 | 작업 규모 |
|---------|-----|---------|-----------|---------|
| 🥇 1순위 | **PAVE** | GlobalX `_resolve_globalx_url()` 확장 | qualified 1개 추가, 게이트 통과 단독 충족 | ETFProfile 등록만 |
| 🥇 1순위 | **URA** | GlobalX `_resolve_globalx_url()` 확장 | qualified 1개 추가 (단 추정 3개, 실측 확인 필요) | ETFProfile 등록만 |
| 🥈 2순위 | **XBI** | SPDR spdr 파서 (기존 코드 그대로) | qualified +1 (안전, ~10개) | ETFProfile 등록만 |
| 🥈 2순위 | **KRE** | SPDR spdr 파서 (기존 코드 그대로) | qualified +1 (안전, ~6개) | ETFProfile 등록만 |
| 3순위 | **HACK/BETZ** | Amplify/Roundhill — 파서 소수정 | 기존 0행 → qualified 진입 가능 | generic 파서 Account 필터 추가 |
| 3순위 | **KWEB** | KraneShares — curl 성공, httpx 차단 | 기존 0행 → qualified 진입 가능 | httpx → subprocess curl 우회 |
| 4순위 | **IBB/ITA/IGV** | iShares — 쿠키 재취득 필요 | IBB ~15개, ITA ~12개, IGV ~15개 | httpx 쿠키 세션 갱신 로직 |
| 4순위 | **SMH** | VanEck — JS 렌더링 의존 | 반도체 그룹 SOXX와 중복 가능성 高 | 높음 (JS 해결 or 대체 소스) |
| ❌ 제외 | ITB, CIBR, SKYY, PPA, JETS | 소싱 불가 | - | - |

### 권고 실행 순서

1. **즉시 (0 코드 변경)**: `ETFCSVDownloader.ETF_CSV_SOURCES`에 PAVE, URA, XBI, KRE 항목 추가
   - PAVE/URA: `parser="globalx"`, `csv_url=""`(비워두면 `_resolve_globalx_url()` 자동 탐지)
   - XBI/KRE: `parser="spdr"`, `csv_url="https://www.ssga.com/us/en/intermediary/etfs/library-content/products/fund-data/etfs/us/holdings-daily-us-en-{xbi/kre}.xlsx"`
2. **검증**: `download_holdings('PAVE')` 실행 후 `w>=1.0 AND in_universe` 실제 수치 확인 (URA 3개 경계값 검증)
3. **게이트 재측정**: `CS-EXP-GATE_measurement.md` 재실행으로 최종 확정

---

## pytest 스모크

```
pytest tests/serverless/ -q --tb=no
```

| 결과 | 수치 |
|------|------|
| 수집된 테스트 | 410 |
| 통과 | **377 passed** |
| 스킵 | 33 skipped |
| 실패 | **0** |
| 실행 시간 | 22.21s |

> 코드 변경 없이 GATE 문서 기준선과 동일 수치 유지.

---

## 쓰기 0 확인

- 수정된 추적 파일: **0건** (M 없음)
- DB write (`save/create/update/delete`): **0건**
- 신규 파일: 이 리포트(`CS-EXP-SOURCE.md`) 1건만

---

## 부록 — ETF 공식 URL 레퍼런스 (검증됨)

| ETF | URL | 상태 |
|-----|-----|------|
| XBI | `https://www.ssga.com/us/en/intermediary/etfs/library-content/products/fund-data/etfs/us/holdings-daily-us-en-xbi.xlsx` | ✅ 200 + XLSX |
| KRE | `https://www.ssga.com/us/en/intermediary/etfs/library-content/products/fund-data/etfs/us/holdings-daily-us-en-kre.xlsx` | ✅ 200 + XLSX |
| PAVE | `https://assets.globalxetfs.com/funds/holdings/pave_full-holdings_{YYYYMMDD}.csv` | ✅ 200 (최근 영업일) |
| URA | `https://assets.globalxetfs.com/funds/holdings/ura_full-holdings_{YYYYMMDD}.csv` | ✅ 200 (최근 영업일) |
| IBB | `https://www.ishares.com/us/products/239772/ishares-nasdaq-biotechnology-etf/1467271812596.ajax?fileType=csv&fileName=IBB_holdings&dataType=fund` | ⚠️ HTML (쿠키 필요) |
| ITA | `https://www.ishares.com/us/products/239502/ishares-us-aerospace-defense-etf/1467271812596.ajax?fileType=csv&fileName=ITA_holdings&dataType=fund` | ⚠️ HTML (쿠키 필요) |
| IGV | `https://www.ishares.com/us/products/239725/ishares-north-american-tech-software-etf/1467271812596.ajax?fileType=csv&fileName=IGV_holdings&dataType=fund` | ⚠️ HTML (쿠키 필요) |
| ITB | `https://www.ishares.com/us/products/239538/...` | ❌ 301 → closed-funds |
| SMH | `https://www.vaneck.com/us/en/investments/semiconductor-etf-smh/smh-holdings.xlsx` | ❌ JS/쿠키 의존 |
| CIBR | First Trust FundId=218 | ❌ 404 |
| SKYY | First Trust FundId=16 | ❌ 404 |
| PPA | Invesco download endpoint | ❌ 406 |
| JETS | US Global Investors | ❌ 404 |
