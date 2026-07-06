# FMP filings·IPO·estimates 프로브 보고서 (지시서 2호)

- **실행일시**: 2026-07-05
- **실행 주체**: 지시서 `verify_fmp_filings_estimates_access` (읽기 전용 audit)
- **총 API 호출 수**: **26회** (스모크 1 + Track A 5 + Track B 20) — 예산 30회 이하 준수 ✅
- **플랜**: FMP Starter / 베이스 `https://financialmodelingprep.com` / stable 전건 성공(v3·v4 폴백 미실행)

---

## Track A 판정: **PASS**  ← C2b 원천 = FMP 단일

A2(폼타입 시장 전체 검색) + A4(IPO 캘린더) 모두 OPEN, 날짜 필터 정상 동작, 시장 전체 최신값 신선도 = 3일(캘린더)이나 07-03 공휴일(Independence Day 관측)·07-04·05 주말 제외 시 **영업일 지연 0** → 합격. `collect_theme_filings_task`는 FMP 소비로 설계.

> ⚠️ **품질 단서 2건 (설계 시 반영 필수)**:
> 1. **폼타입 필터는 exact가 아닌 prefix/family 매칭** — `formType=S-1` 요청 시 응답에 `S-1`(43) 외 `S-1/A`(22), `S-1MEF`(3), `ABS-15G`(32)가 혼입(n=100 중). → **소비 측에서 `formType` 정확 일치 자체 필터 필요** (C2b는 원발행 S-1만 카운트하므로 S-1/A 개정·ABS-15G 제외). 반면 `424B4`는 67건 전건 정확 일치(오염 0).
> 2. **기본 응답 ~100건 캡** — A2가 요청 범위 2026-06-01~07-04 중 실제로는 06-29~07-02만 반환(최근 100건에서 잘림). 90일 창 전량 수집엔 **페이지네이션 필요**.

## Track B 판정: **FULL**  ← C8·C1 폴백 파라미터

대형 100%(8/8) & 소형 100%(8/8) & 중형 100%(4/4) 커버, 전 종목 차기연도(2027) Forward EPS 존재. C8 전 테마 적용 가능, C1 Fwd P/E 유지.

> ⚠️ **갱신 신선도 계측 한계**: annual estimates 엔드포인트는 예측 **대상기간 종료일**(`date`, 미래연도)만 제공하고 **리비전 갱신 타임스탬프 필드가 없다**. 단일 스냅샷으로 "월 단위 갱신"을 직접 입증 불가. → **C8(60일 리비전)은 FMP 원장을 우리 파이프라인이 주기 스냅샷 후 diff 하여 산출**하는 것이 올바른 설계(엔드포인트는 컨센서스 스냅샷 공급원 역할). 이 전제 하에 커버리지 강도만으로 FULL 판정.

---

## Track A 결과표 (A1~A5 × 분류 × 품질)

| # | 목적 | Stable 엔드포인트 | HTTP | 분류 | 품질 비고 |
|---|------|------------------|------|------|-----------|
| A1 | 종목별 filing 목록 | `/stable/sec-filings-search/symbol` | 200 | **OPEN** | NVDA 38건, 날짜필터 동작(04-27~07-02 ⊂ 요청). 필드: symbol/cik/filingDate/acceptedDate/formType/**link**/finalLink |
| A2 | **폼타입 전체 검색(핵심)** | `/stable/sec-filings-search/form-type` (S-1) | 200 | **OPEN** | 필터 prefix 오염(S-1/A·S-1MEF·ABS-15G 혼입) → 자체 필터 필요. 100건 캡 |
| A3 | 424B 폼타입 | 동경로 (424B4) | 200 | **OPEN** | 67건 전건 `424B4` 정확 일치(오염 0). `424B4`로 동작 → `424B` 변형 시도 불요 |
| A4 | IPO 캘린더(증분) | `/stable/ipos-calendar` (2026 YTD) | 200 | **OPEN** | 895건, 날짜필터 동작(01-02~07-02 전건 2026), 최신 07-02 |
| A5 | IPO 과거(백필) | 동경로 (2024 H1) | 200 | **OPEN** | 906건 전건 2024 H1 → **3년 백필 가능**(C2b IPO 성분 백필 확보) |

**dedup_key 재료 (A1/A2)**: `symbol` + `cik` + `link`(=`.../{accession}-index.htm`, accession 번호 내포) 모두 존재 → `ThemeFilingCount.dedup_key` 구성 가능.

**신선도(시장 전체 재고, 1호 교훈 적용)**: A2 최신 filingDate `2026-07-02`, A4 최신 date `2026-07-02` = 직전 거래일(07-03 공휴일·주말 제외) → 영업일 지연 ≈ 0, ≤3영업일 합격.

## Track B 커버리지 표

| 버킷 | 표본 | 커버율 | Fwd EPS율 | 애널리스트수(EPS) 중앙값 | 비고 |
|------|:---:|:---:|:---:|:---:|------|
| 대형 | 8 | **100%** (8/8) | 100% | 26 | AMZN 43, NVDA 33 등 두터움 |
| 중형 | 4 | **100%** (4/4) | 100% | 14 | ETSY 19, TOST 12 |
| 소형 | 8 | **100%** (8/8) | 100% | 8 | 최소 BBAI 2~3, IONQ 4~6 — 얇지만 non-null |

- 측정 기준: 당기(2026)+차기(2027) `epsAvg` non-null & `numAnalystsEps` > 0.
- 필드: `epsAvg/epsHigh/epsLow`, `numAnalystsEps`, `numAnalystsRevenue`, `revenue*/ebitda*/ebit*/netIncome*/sgaExpense*`. `limit=10` → 연간 10개 회계연도(과거 실적~미래 예측) 반환.
- Forward P/E(C1) 재료: 전 종목 차기연도 EPS 추정 존재(적자 소형주는 음수 EPS로, C1에서 Fwd P/E 무의미 → EV/Sales 폴백 대상임을 별도 인지).

---

## PLAN_LOCKED 응답 원문

**없음.** Track A·B 전 항목 200 OPEN. (지시서 1호에서 잠긴 13F institutional-ownership는 본 프로브 범위 밖.)

---

## theme_heat_design.md 반영 초안

**§5.2 (C2b 원천 확정)**:
> C2b 발행 신호 원천 = FMP `sec-filings-search/form-type`(S-1·424B4) + `ipos-calendar` 단일. 단 form-type 필터는 prefix 매칭이므로 소비 측 `formType` 정확 일치 필터 + 페이지네이션(100건 캡) 적용, dedup_key = symbol+cik+accession(link 내포).

**§2 C8 폴백 문구**:
> analyst-estimates 커버리지 = 전 버킷(대형/중형/소형) 100%로 C8 전 테마 적용·C1 Fwd P/E 유지. 단 엔드포인트에 리비전 타임스탬프가 없어 C8 60일 리비전은 우리 파이프라인의 주기 스냅샷 diff로 산출(엔드포인트는 컨센서스 스냅샷 공급).

---

## DECISIONS.md 기록 초안

> **[2026-07-05] FMP filings·IPO·estimates 프로브 = Track A PASS / Track B FULL.**
> C2b 원천 = FMP sec-filings-search(form-type S-1/424B4)+ipos-calendar 단일 확정, EDGAR 폴백 불요(산식 불변). 단 form-type prefix 오염 → 자체 정확일치 필터 + 100건 캡 페이지네이션 필수, IPO 3년 백필 확인(A5).
> C8/C1: estimates 커버리지 전 버킷 100%(소형 포함)로 C8 전 테마 적용·C1 Fwd P/E 유지. 리비전 타임스탬프 부재 → C8은 자체 주기 스냅샷 diff로 산출(설계 전제 명문화).

---

## 검증 종료 확인

- ✅ Track A 판정 **PASS**, Track B 판정 **FULL** 각 1개 확정
- ✅ 설계서 반영 초안(§5.2·§2) + DECISIONS 초안 포함
- ✅ 총 API 호출 **26회** (예산 30회 이하 준수)
- ✅ 코드베이스 변경 없음 — 기존/추적 파일 수정 0건, 신규 산출물은 이 보고서(untracked) 1개, git 커밋 미생성
- ✅ API 키 평문 미노출 (`$FMP_API_KEY` 참조, URL `apikey=` 마스킹, `len=32, head=qA1W***` 형식만 기록)
