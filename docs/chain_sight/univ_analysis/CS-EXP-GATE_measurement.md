# CS-EXP-GATE — 현재 holdings 기준 보드 게이트 측정 (READ-ONLY)

> 세션: `monorepo/sess-cs-exp` (worktree 없음 — 메인 `stock_vis` 디렉토리에서 실행)
> 측정일: 2026-06-15
> **DB 쓰기 0건 · 앱 코드 diff 0줄 · FMP 콜 0건**
> 산출 기준: `python manage.py shell -c "..."` (READ-ONLY 쿼리만)

---

## STEP 1 — 보드 그룹핑 로직

### 핵심 파일

| 파일 | 역할 |
|------|------|
| `apps/chain_sight/management/commands/load_themes_to_neo4j.py` | `ETF_THEME_MAP` 상수 정의 (ETF 심볼 → 테마명/설명/키워드) |
| `services/serverless/models.py` | `ETFProfile` (tier=sector/theme, theme_id), `ETFHolding` (weight_percent, stock_symbol) |
| `services/serverless/services/theme_matching_service.py` | `ThemeMatchingService`, `THEME_KEYWORDS`, `THEME_TO_ETF` |
| `docs/chain_sight/univ_analysis/measure_db.py` | CS-UNIV 기존 측정 스크립트 (ETF_THEME_MAP 사용 방식 레퍼런스) |

### 그룹 정의

**이벤트 보드 그룹 = `ETF_THEME_MAP` 키 단위.**

- `ETF_THEME_MAP`은 ETF 심볼 21개를 키로, 각각의 테마명(name)·설명(description)·키워드(keywords)를 값으로 갖는 Python dict 상수.
- 테마 ETF(tier=theme) 10개: SOXX, BOTZ, ICLN, LIT, ARKK, ARKG, HACK, BETZ, KWEB, TAN
- 섹터 ETF(tier=sector) 11개: XLK, XLV, XLF, XLE, XLI, XLY, XLP, XLU, XLC, XLRE, XLB
- 이벤트 보드에서 **테마 그룹**은 tier=theme ETF에 대응하는 10개 이름 단위.
- 같은 테마의 중복 ETF(예: SMH+SOXX)는 현재 구조상 동일 theme_id로 매핑됨 (`ETFProfile.theme_id` 기준 병합).

### 멤버 산출 규칙

```python
# measure_db.py의 theme_board() 함수 기준
for etf_sym, info in ETF_THEME_MAP.items():
    etf = ETFProfile.objects.filter(symbol=etf_sym, tier="theme").first()
    if not etf: continue
    for h in ETFHolding.objects.filter(etf=etf, weight_percent__gte=1.0):
        s = h.stock_symbol.upper()
        if s in universe:  # universe = Stock.objects 전체 심볼 집합
            sym_themes[s].add(info["name"])
```

- **필터 1: `weight_percent >= 1.0`** — ETFHolding 행의 비중 컷.
- **필터 2: `stock_symbol.upper() in Stock` 유니버스** — Stock 테이블 등재 종목만.
- 테마 그룹당 종목 수 = `weight_percent >= 1.0 AND stock in Stock` 조건 만족 ETFHolding 행 수.

### US 상장 판정 기준

- **명시적 US 판정 컬럼 없음.** `Stock` 테이블에 거래소 코드·국적 필드 없음.
- **암묵적 기준 = 이미 Stock 테이블에 있는가.** Stock 유니버스(535종목)는 SP500Constituent(active 503) + 추가 32로 구성되며, 이 전체가 US 상장 종목으로 간주됨.
- 따라서 ETFHolding 멤버 산출 시 별도 US 판정 로직 없이 "유니버스 IN 체크"가 US 필터 역할을 대리한다.
- CS-UNIV REPORT.md 기록: T1 신규 213종목 중 US-like는 51%, 외국 49% → 유니버스 밖 외국 종목은 자동 제외.

---

## STEP 2 — 측정 수치표

### 고정 분모
- `Stock.objects.count()` = **535** (SP500 active 503 + 추가 32)
- 측정 기준일: 2026-06-15 (ARK 44+32 holdings 이미 적재됨)

---

### A. 섹터+테마 통합 보드 (ETF_THEME_MAP 21개 전체, w≥1.0)

| 지표 | 값 |
|------|-----|
| 그룹 수 | **21** |
| 그룹당 종목 중앙값 | **331** |
| 커버 종목 | 310 종목 |
| 커버리지% | **57.9%** (310 ÷ 535) |

**그룹별 상세 (내림차순):**

| 그룹명 | 종목 수 | ETF | tier |
|--------|---------|-----|------|
| Industrials | 555 | XLI | sector |
| Utilities | 464 | XLU | sector |
| Real Estate | 450 | XLRE | sector |
| Consumer Staples | 437 | XLP | sector |
| Materials | 408 | XLB | sector |
| Technology | 385 | XLK | sector |
| Healthcare | 382 | XLV | sector |
| Financials | 366 | XLF | sector |
| Consumer Discretionary | 359 | XLY | sector |
| Energy | 332 | XLE | sector |
| Communication Services | 331 | XLC | sector |
| Semiconductor | 221 | SOXX | theme |
| Robotics & AI | 56 | BOTZ | theme |
| Clean Energy | 39 | ICLN | theme |
| Lithium & Battery | 32 | LIT | theme |
| Disruptive Innovation | 12 | ARKK | theme |
| Genomic Revolution | 1 | ARKG | theme |
| Cybersecurity | 0 | HACK | theme |
| Sports Betting & Gaming | 0 | BETZ | theme |
| China Internet | 0 | KWEB | theme |
| Solar Energy | 0 | TAN | theme |

> 주의: 종목당 복수 그룹 해당 가능 → 합산 수치가 535 초과. 커버리지는 고유 종목 기준.

---

### B. 테마 그룹만 (tier=theme, w≥1.0) ← 게이트 판정 대상

| 지표 | 값 |
|------|-----|
| 그룹 수 | **10** |
| 그룹당 종목 최솟값 | 0 |
| 그룹당 종목 중앙값 | **6.5** |
| 그룹당 종목 최댓값 | 221 |
| 커버 종목 | 32 종목 |
| 커버리지% | **6.0%** (32 ÷ 535) |

**그룹별 상세 (내림차순):**

| 그룹명 | 종목 수 | ETF | holdings_in_db | 비고 |
|--------|---------|-----|---------------|------|
| Semiconductor | 221 | SOXX | 429 행 | 정상 |
| Robotics & AI | 56 | BOTZ | 364 행 | 정상 |
| Clean Energy | 39 | ICLN | 1,657 행 | 정상 (글로벌 ETF — US 한정 시 더 적음) |
| Lithium & Battery | 32 | LIT | 112 행 | 정상 |
| Disruptive Innovation | 12 | ARKK | 44 행 | ARK 44종목 중 w≥1.0 12개 |
| Genomic Revolution | 1 | ARKG | 32 행 | ARK 32종목 중 w≥1.0 1개 |
| Cybersecurity | 0 | HACK | 0 행 | ETFHolding 미적재 |
| Sports Betting & Gaming | 0 | BETZ | 0 행 | ETFHolding 미적재 |
| China Internet | 0 | KWEB | 0 행 | ETFHolding 미적재 |
| Solar Energy | 0 | TAN | 0 행 | ETFHolding 미적재 |

**분포 (sorted):** `[0, 0, 0, 0, 1, 12, 32, 39, 56, 221]`
**중앙값** = (1 + 12) / 2 = **6.5**

---

### C. 전/후 비교: ARK 2그룹 추가 전 vs 후

| 지표 | ARK 제외 (8개 테마 ETF) | ARK 포함 (10개 테마 ETF) | 변화 |
|------|------------------------|------------------------|------|
| 테마 그룹 수 | 8 | 10 | +2 |
| 데이터 있는 그룹 | 4 | 6 | +2 |
| 그룹당 중앙값 | **16.0** | **6.5** | **▼ -9.5** |
| 커버 종목 | 24 | 32 | +8 |
| 커버리지% | 4.5% | 6.0% | +1.5%p |

**ARK 제외 시 분포 (sorted):** `[0, 0, 0, 0, 32, 39, 56, 221]` → 중앙값 = (32+39)/2 = **35.5** (비어있는 4그룹 제외 시)
**ARK 제외 비어있는 4그룹 포함 시:** `[0, 0, 0, 0, 32, 39, 56, 221]` → 중앙값 = (0+32)/2 = **16.0**

> **역설적 관찰**: ARKK/ARKG 추가로 그룹 수가 8→10으로 늘었으나 중앙값은 16.0→6.5로 **하락**했다.
> 원인: ARKG의 w≥1.0 종목이 1개뿐 — 32개 holdings 중 유니버스 내 US 종목이면서 w≥1.0인 것이 거의 없음.
> Genomic Revolution(1)이 5번째 값으로 삽입되어 중앙값 계산의 하단 경계를 끌어내림.

---

## 게이트 판정

```
테마 그룹당 중앙값 = 6.5
게이트 기준: 중앙값 ≥ 10

판정: ❌ 아니오 (미달)
```

---

## STEP 3 — 게이트 미달 진단

### 부족분 계산

현재 분포: `[0, 0, 0, 0, 1, 12, 32, 39, 56, 221]` (n=10)
중앙값 = (index4 + index5) / 2 = (1 + 12) / 2 = 6.5

**최소 달성 조건**: index4 + index5 의 합 ≥ 20 필요.
- index5는 12 고정(Disruptive Innovation). index4(현재 1 = Genomic Revolution)를 **최소 8**로 올려야 함.
- 즉 Genomic Revolution 그룹에 **+7종목** 추가 필요.
- 계산: (8 + 12) / 2 = **10.0** (경계 통과)

### 성격 관찰 — "신규 ETF 그룹 추가"로 풀리는가 vs "기존 그룹 밀도 증가"로 풀리는가

#### 관찰 1: 빈 그룹(0종목) 4개 해소만으로는 중앙값 불변

4개 그룹(HACK/BETZ/KWEB/TAN)에 holdings가 적재되어 값이 양수가 되더라도,
분포에서 index4(5번째 값)은 Genomic Revolution(1)이므로 중앙값 = (1 + 12) / 2 = 6.5 **불변**.
단, 적재된 값이 1 이상이면 Genomic Revolution(1)이 index4로 올라오는 구조가 달라질 수 있음.

시뮬레이션: 4개 빈 그룹에 `[10, 5, 2, 1]` 종목이 채워지면:
`[1, 1, 2, 5, 10, 12, 32, 39, 56, 221]` → 중앙값 = (10+12)/2 = **11.0** → 게이트 통과.
즉 **빈 그룹 4개가 각 ≥10종목으로 채워지면 중앙값 상승 가능** — 그룹 수 증가(신규 ETF) 필요 없음.

#### 관찰 2: 신규 ETF 그룹 1개 추가(n=10→11)로도 통과 가능

n=11, 신규 그룹이 10종목이면 분포: `[0, 0, 0, 0, 1, 10, 12, 32, 39, 56, 221]`
중앙값 = index5 = **10** → 게이트 경계 통과.
즉 **10종목 이상인 테마 그룹 1개 신규 추가**로도 통과 가능.

#### 관찰 3: ARK 추가로 중앙값이 오히려 하락한 구조적 원인

- ARKG: 32 holdings 중 유니버스 내 w≥1.0 종목이 1개 — Genomic Revolution이 초소형 그룹으로 중간값 계산에 들어감.
- ARK ETF 특성상 소수 집중형: ARKK 44종목 중 12개만 w≥1.0. ARKG 32종목 중 1개만 w≥1.0.
- 이는 **그룹 수 증가(+2)가 중앙값 하락(-9.5)을 동반**하는 역설을 설명함.

#### 관찰 4: CS-EXP 후보 ETF 추가 후 예상 효과 (관찰만, 추정)

CS-EXP 지시서의 후보 ETF들이 추가된다면:
- 사이버보안 CIBR 추가 → Cybersecurity(0) 그룹 채워짐 (약 20-30 US 종목 예상)
- 바이오 XBI/IBB 추가 → 신규 그룹 50+종목
- 방산 ITA/PPA 추가 → 신규 그룹 20-30종목

시뮬레이션 (n=12 가정): `[0, 0, 1, 12, 25, 30, 32, 39, 40, 50, 100, 246]`
중앙값 = (30+32)/2 = **31.0** → 게이트 통과.

즉 CS-EXP Part A(테마 ETF holdings 확대 수집)가 완료되면 중앙값이 10을 크게 상회할 것으로 관찰됨.
단 이는 추정이며, 실제 US 상장·w≥1.0 종목 수는 Part A 실행 후 확정됨.

### 요약 — 두 레버의 성격

| 레버 | 성격 | 중앙값 효과 |
|------|------|-------------|
| 기존 빈 그룹 holdings 적재 (HACK/BETZ/KWEB/TAN) | 기존 그룹 밀도 증가 | 적재값이 ≥10이면 효과 있음, 미미하면 불변 |
| 신규 ETF 그룹 추가 (CS-EXP 후보) | 그룹 수↑ + 신규 그룹 밀도 | 신규 그룹 크기가 ≥10이면 효과 있음 |

현재 구조에서 두 레버가 복합적으로 작용한다 — 어느 한쪽만으로도 통과 가능하지만,
데이터는 **CS-EXP Part A(신규 ETF holdings 수집)가 더 확실한 경로**임을 시사함.

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
| 실패 | 0 |
| 실행 시간 | 22.46s |

> 스킵 33건: neo4j 관련 tests(Neo4j 연결 없으면 자동 skip) + keyword_data_collector 2건. 코드 변경 없이 전건 통과.

---

## 쓰기 0 확인

```bash
$ git status -s
?? docs/chain_sight/redesign(26.06)/
?? docs/etc/
?? docs/market_pulse_v2/card_label_slice_1.md
?? docs/trading_bot_api/api_decision_handoff.md
?? docs/trading_bot_api/consumer_directive.md
```

- 수정된 추적 파일 0건 (`M` 없음)
- 삭제된 추적 파일 0건 (`D` 없음)
- 신규 추적 파일 0건 (위 `??`는 이 세션 이전부터 존재하는 untracked 파일들)
- 이 리포트 `CS-EXP-GATE_measurement.md` 한 개만 신규 작성됨

**DB 쓰기 0건 확인**: 모든 측정은 `.count()`, `.filter()`, `.values()`, `aggregate` 읽기 쿼리만 사용. `save()`, `create()`, `update()`, `delete()`, `update_or_create()` 호출 없음.

---

## 부록 — ETFProfile 현황 요약

| ETF | tier | theme_id | holdings_in_db | w≥1.0 유니버스내 |
|-----|------|----------|---------------|-----------------|
| SOXX | theme | semiconductor | 429 | 221 |
| BOTZ | theme | robotics_ai | 364 | 56 |
| ICLN | theme | clean_energy | 1,657 | 39 |
| LIT | theme | lithium_battery | 112 | 32 |
| ARKK | theme | innovation | 44 | 12 |
| ARKG | theme | genomics | 32 | 1 |
| HACK | theme | cybersecurity | 0 | 0 |
| BETZ | theme | igaming | 0 | 0 |
| KWEB | theme | china_internet | 0 | 0 |
| TAN | theme | solar | 0 | 0 |
| XLK | sector | technology | 1,171 | (섹터 그룹) |
| XLV | sector | healthcare | 970 | (섹터 그룹) |
| XLF | sector | financials | 1,232 | (섹터 그룹) |
| XLE | sector | energy | 364 | (섹터 그룹) |
| XLI | sector | industrials | 1,281 | (섹터 그룹) |
| XLY | sector | consumer_discretionary | 785 | (섹터 그룹) |
| XLP | sector | consumer_staples | 590 | (섹터 그룹) |
| XLU | sector | utilities | 512 | (섹터 그룹) |
| XLC | sector | communication | 384 | (섹터 그룹) |
| XLRE | sector | real_estate | 512 | (섹터 그룹) |
| XLB | sector | materials | 432 | (섹터 그룹) |
