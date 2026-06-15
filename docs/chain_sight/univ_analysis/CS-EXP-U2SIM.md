# CS-EXP-U2SIM — 게이트 기준 재평가 + U2 편입 규모 시뮬 (READ-ONLY)

> 세션 브랜치: `monorepo/sess-cs-exp` (worktree `stock_vis_cs_exp`)
> **외부 호출 0 / DB 쓰기 0 / 코드 diff 0** — 이미 적재된 DB holdings만 사용
> pytest serverless: **377 passed, 33 skipped / 0 failed**
> git status: 리포트 파일(CS-EXP-U2SIM.md) 1개만 untracked (하단 검증 참조)

---

## 집계 방식 (명시)

- **최신 snapshot 고정**: 각 ETF별 `ETFHolding.snapshot_date` 최신 1개만 사용.
  복수 snapshot이 있는 ETF(BOTZ 16개, ICLN 13개, LIT 16개, SOXX 13개)는 `order_by('-snapshot_date').first()`로 최신 1개 고정.
- **distinct symbol 기준**: `{h.stock_symbol.strip().upper() for h in holdings}` set 연산으로 중복 제거.
- **유니버스 교집합**: `set(Stock.objects.values_list('symbol', flat=True))` (N=535)와 교집합 후 길이.
- **weight 필드**: `weight_percent` (모델 실제 필드명; `weight`로 쓰면 FieldError 발생 — 세션 내 확인).

---

## Part A — distinct 기준 현황 재확정

### 측정 결과

| ETF | 최신 snapshot | w≥1.0 총 행 | distinct 유니버스 멤버 | 자격(≥3) |
|---|---|---|---|---|
| PAVE | 2026-06-15 | 30 | **22** | ✅ |
| SOXX | 2026-05-11 | 23 | **17** | ✅ |
| ARKK | 2026-06-15 | 33 | **12** | ✅ |
| XBI | 2026-06-15 | 45 | **7** | ✅ |
| KRE | 2026-06-15 | 42 | **5** | ✅ |
| BOTZ | 2026-06-08 | 12 | **4** | ✅ |
| ICLN | 2026-05-11 | 23 | **3** | ✅ |
| LIT | 2026-06-08 | 5 | **2** | ❌ |
| ARKG | 2026-06-15 | 28 | **1** | ❌ |
| BETZ | (적재 없음) | 0 | 0 | ❌ |
| HACK | (적재 없음) | 0 | 0 | ❌ |
| KWEB | (적재 없음) | 0 | 0 | ❌ |
| TAN | (적재 없음) | 0 | 0 | ❌ |

### 직전 보고와 비교

| 항목 | 직전(CS-EXP-LOAD) | 이번 재측정 | 일치 |
|---|---|---|---|
| 자격 그룹 수 | 7 | **7** | ✅ |
| 분포 | [3,4,5,7,12,17,22] | **[3,4,5,7,12,17,22]** | ✅ |
| 중앙값 | 7 | **7** | ✅ |
| 게이트(자격≥6 ∧ 중앙값≥10) | ❌ 미달 | **❌ 미달** | ✅ |

**정합 확인**: 직전 보고와 완전 일치. 수치 오류 없음.

### 커버리지

자격 그룹 7개(PAVE·SOXX·ARKK·XBI·KRE·BOTZ·ICLN)의 w≥1.0 유니버스 종목 합집합 = **63개**.
커버리지 = 63 / 535 = **11.8%**.

---

## Part B — 게이트 기준 재평가 (UX 역산)

### UX 시나리오별 충족 현황

보드 UX: 테마 선택 시 "관심 집중 상위 N + 관심 소외 하위 M" 노출.
현재 자격 그룹: ICLN(3), BOTZ(4), KRE(5), XBI(7), ARKK(12), SOXX(17), PAVE(22)

| 시나리오 | 필요 최소 멤버 | 충족 그룹 | 미충족 그룹 |
|---|---|---|---|
| N=3, M=2 (합5) | 5 | **5개** ICLN❌ BOTZ❌ → KRE(5)·XBI·ARKK·SOXX·PAVE | ICLN(3), BOTZ(4) |
| N=5, M=3 (합8) | 8 | **3개** ARKK(12)·SOXX(17)·PAVE(22) | ICLN(3), BOTZ(4), KRE(5), XBI(7) |
| N=5, M=5 (합10) | 10 | **3개** ARKK(12)·SOXX(17)·PAVE(22) | ICLN(3), BOTZ(4), KRE(5), XBI(7) |

### 중앙값 X 후보별 게이트 통과 분석

현재 상태: 자격 그룹 수=7 (≥6 ✅), 중앙값=7.

| X 후보 | 자격≥6 | 현재 중앙값(7)≥X | 현재 게이트 | 비고 |
|---|---|---|---|---|
| X=5 | ✅ | ✅ (7≥5) | **통과** | 자격≥6 ∧ 중앙값≥5 → 현재 이미 만족 |
| X=7 | ✅ | ✅ (7≥7) | **통과** | 현재 경계값 — 중앙값이 7이므로 딱 걸침 |
| X=8 | ✅ | ❌ (7<8) | **미달** | XBI(7)가 8로 올라야 중앙값 8 달성 |
| X=10 | ✅ | ❌ (7<10) | **미달** | ICLN·BOTZ·KRE·XBI 모두 10 이상이어야 |

**UX 역산 요약**:
- N=3,M=2(합5) 시나리오 → X=5 충분 → **현재 이미 통과**
- N=5,M=3(합8) 시나리오 → X=8 필요 → **U2 13개 편입 필요** (Part C 시뮬 2a)
- N=5,M=5(합10) 시나리오 → X=10 필요 → **U2 20개 편입 필요 + ICLN 구조 한계 주의** (Part C 시뮬 2b)

권고(1줄): N=5,M=3(합8) 시나리오가 편입 부담(13종목)과 UX 풍부도의 균형이 가장 좋아 보입니다. 결정은 디렉터 몫.

---

## Part C — U2 편입 규모 시뮬 (distinct)

### US 상장 판정 휴리스틱

**허용 패턴**: `^[A-Z][A-Z0-9]{1,5}$` (영문+숫자, 2~6자, 시작은 영문)

**제외 처리**:
1. **KNOWN_NON_US 명시 목록** (16개 카테고리):
   - 통화 코드: `TWD`, `DKK`, `JPY`, `CHF`, `TRY`, `HKD`, `IDR`, `NOK`, `CAD`, `GBP`, `NZD`, `INR`, `SEK`, `CNY`, `CNH`, `ILS`, `KRW`, `EUR`, `BRL`, `CLP`
   - 선물/파생: `VGM6`, `ESM6`, `MESM6`, `HBCFT`
   - 브라질 B3 심볼: `EQTL3`, `NDX1`, `ENGI11`, `CPFE3`, `AURE3`, `EGIE3`
   - 유럽 상장: `VWS`, `ORSTED`, `SUZLON`, `ENLT`, `EDP`, `ERG`, `RNW`, `ANE`, `VER`, `BLX`, `NOFR`, `ENRG`, `ENELAM`, `MEL`, `CEN`, `BREN`, `DORL`, `S92`
   - 인도 NSE: `NTPCGREEN`, `NHPC`, `SJVN`, `WAAREEENER`, `PREMIERENE`, `INOXWIND`
   - 기타: `XTSLA`, `PGEO`, `MLISW`, `VBK`, `REX`
2. **숫자만인 코드**: `^\d+$` (중국 A주 등: `600900`, `9502`, `336260` 등)
3. **공백/마침표/하이픈 포함**: `ARCT UQ`, `ATAI UQ`, `MAGEN.E`, `EA.R` 등

**제외 사례** (w≥1.0, 실제 걸러진 16건):
`ARCT UQ(ARKG)`, `ATAI UQ(ARKG)`, `600900(ICLN)`, `VWS(ICLN)`, `EQTL3(ICLN)`, `SUZLON(ICLN)`, `EDP(ICLN)`, `9502(ICLN)`, `336260(ICLN)`, `ORSTED(ICLN)`, `ENLT(ICLN)`, `ENGI11(ICLN)`, `2208(ICLN)`, `601012(ICLN)`, `600905(ICLN)`, `NDX1(ICLN)`

**허용 판단 근거**: SHOP(NYSE), SQM(NYSE ADR), RIO(NYSE ADR), ASML(NASDAQ), BIDU(NASDAQ ADR), BABA(NYSE ADR), XPEV(NYSE ADR) — 모두 US 거래소에서 실제 거래되므로 US 상장으로 취급. US 기반 ETF holdings이라는 컨텍스트가 이 판단을 뒷받침.

### U2 후보 총계

| ETF | U2 후보 수 |
|---|---|
| XBI | 38 |
| KRE | 37 |
| ARKG | 25 |
| ARKK | 21 |
| ICLN | 6 |
| BOTZ | 8 |
| PAVE | 8 |
| SOXX | 6 |
| LIT | 3 |
| **distinct 합계** | **136** |

### 시뮬 1 — 전체 편입 (136종목 추가)

새 유니버스 크기: 535 + 136 = **671**

| ETF | 현재 멤버 | 전체 편입 후 멤버 | 자격(≥3) |
|---|---|---|---|
| PAVE | 22 | **30** | ✅ |
| KRE | 5 | **42** | ✅ |
| XBI | 7 | **45** | ✅ |
| SOXX | 17 | **23** | ✅ |
| ARKG | 1 | **26** | ✅ (신규 자격) |
| ARKK | 12 | **33** | ✅ |
| ICLN | 3 | **9** | ✅ |
| BOTZ | 4 | **12** | ✅ |
| LIT | 2 | **5** | ✅ (신규 자격) |
| BETZ | 0 | **0** | ❌ (holdings 미적재) |
| HACK | 0 | **0** | ❌ (holdings 미적재) |
| KWEB | 0 | **0** | ❌ (holdings 미적재) |
| TAN | 0 | **0** | ❌ (holdings 미적재) |

- **새 자격 그룹 수**: 9개 (현재 7개 → +2: ARKG, LIT 신규 진입)
- **새 분포**: [5, 9, 12, 23, 26, 30, 33, 42, 45]
- **새 중앙값**: **26** (인덱스 4)
- **신규 편입 종목 수**: 136 (distinct)

#### ARK 역설 / 경계 재점검

BETZ·HACK·KWEB·TAN는 holdings 자체가 미적재(snapshot=0)이므로 전체 편입 후에도 멤버 0 유지.
"ARK 역설"(holdings 있으나 교집합 없음)이 아니라 **holdings 미적재 ETF**가 정확한 표현.
→ 이 4개는 별도로 데이터 적재가 선행되어야 자격 그룹 진입 가능.

### 시뮬 2 — 최소 편입

각 자격 그룹을 목표 X까지 채우는 데 필요한 최소 신규 종목 (w≥1.0 기준 상위 weight 순 선택).

#### 시뮬 2a (X=8)

| ETF | 현재 | 필요 | 추가 가능 | 새 크기 |
|---|---|---|---|---|
| ICLN | 3 | 5 | 5 | **8** |
| BOTZ | 4 | 4 | 4 | **8** |
| KRE | 5 | 3 | 3 | **8** |
| XBI | 7 | 1 | 1 | **8** |
| ARKK | 12 | 0 | 0 | **12** |
| SOXX | 17 | 0 | 0 | **17** |
| PAVE | 22 | 0 | 0 | **22** |

새 분포: [8, 8, 8, 8, 12, 17, 22] / 새 중앙값: **8**
추가 심볼(13개): `AUR, AVAV, BE, BIDU, BPOP, CGNX, CWEN, EWBC, PLUG, SEDG, SHLS, TGTX, ZION`

#### 시뮬 2b (X=10)

| ETF | 현재 | 필요 | 추가 가능 | 새 크기 | 비고 |
|---|---|---|---|---|---|
| ICLN | 3 | 7 | 6 | **9** | ⚠️ w≥1.0 US 후보 6개뿐 (X=10 달성 불가) |
| BOTZ | 4 | 6 | 6 | **10** | |
| KRE | 5 | 5 | 5 | **10** | |
| XBI | 7 | 3 | 3 | **10** | |
| ARKK | 12 | 0 | 0 | **12** | |
| SOXX | 17 | 0 | 0 | **17** | |
| PAVE | 22 | 0 | 0 | **22** | |

새 분포: [9, 10, 10, 10, 12, 17, 22] / 새 중앙값: **10**
추가 심볼(20개): `ALKS, AUR, AVAV, BE, BIDU, BPOP, CGNX, CWEN, EWBC, JBTM, PLUG, SEDG, SHLS, SLR, TGTX, TVTX, UMBF, VLY, XPEV, ZION`

**ICLN 구조 한계 상세**:
ICLN은 글로벌 청정에너지 ETF로, w≥1.0 holdings 중 유니버스 내 US 종목 3개(FSLR·NXT·ENPH) + U2 US 후보 6개 = 합계 최대 9개. w≥1.0 기준에서 ICLN은 X=10 달성 불가. 중앙값은 9와 10의 평균인 **9.5**가 아니라 정렬 [9,10,10,10,12,17,22]의 인덱스3(0-based) = **10** (7개 그룹, 홀수).

### 비교표

| 항목 | 현재 | 시뮬 1 (전체, 136종목) | 시뮬 2a (최소, X=8, 13종목) | 시뮬 2b (최소, X=10, 20종목) |
|---|---|---|---|---|
| 신규 종목 수 | 0 | **136** | **13** | **20** |
| 자격 그룹 수 | 7 | **9** | **7** | **7** |
| 새 분포 | [3,4,5,7,12,17,22] | [5,9,12,23,26,30,33,42,45] | [8,8,8,8,12,17,22] | [9,10,10,10,12,17,22] |
| 새 중앙값 | 7 | **26** | **8** | **10** |
| 게이트(자격≥6) | ✅ | ✅ | ✅ | ✅ |
| 중앙값≥8 통과 | ❌ | ✅ | ✅ | ✅ |
| 중앙값≥10 통과 | ❌ | ✅ | ❌ | ✅ (중앙값=10, ICLN=9) |
| ICLN 달성 크기 | 3 | 9 | 8 | 9 (한계) |
| BETZ/HACK/KWEB/TAN | 0 | 0 | 0 | 0 |

---

## 검증

### 외부 호출 / DB 쓰기 / 코드 diff

```
외부 HTTP 호출: 0건
DB save/create/update/delete: 0건
코드 파일 변경: 0건 (manage.py shell -c 인라인 스크립트만 사용)
```

### git status

```
(리포트 작성 전) git status -s → (empty) — working tree clean
(리포트 작성 후) CS-EXP-U2SIM.md 1개만 untracked
```

### pytest serverless

```
377 passed, 33 skipped, 0 failed (22.11s)
```

---

## 다음 단계 (디렉터 결정 사항)

1. **게이트 X 값 확정**: X=7(현재 통과), X=8(13종목 편입), X=10(20종목 편입 + ICLN 한계 9)
2. **U2 편입 결정**: 결정 시 Stock 유니버스에 신규 종목 추가(쓰기 세션 필요)
3. **BETZ·HACK·KWEB·TAN**: holdings 적재 여부 결정 (별도 쓰기 세션)
4. **ETF_THEME_MAP(Neo4j)**: PAVE·XBI·KRE의 `load_themes_to_neo4j.py` 편집 (별도 쓰기 세션)
