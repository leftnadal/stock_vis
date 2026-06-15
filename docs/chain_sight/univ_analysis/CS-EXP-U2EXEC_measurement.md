# CS-EXP-U2EXEC — 유니버스 U2 편입 + 백필 + 게이트 통과 (쓰기 세션)

> 세션 브랜치: `monorepo/sess-cs-exp`
> **결과: 게이트 X=8 통과 (실측 중앙값 26 = 예측 26 정확 일치)**

## 실행 요약
| 단계 | 결과 |
|---|---|
| STEP 0 편입 대상 | 136 distinct US 종목 (U2SIM 예측 일치). 제외 16건(숫자코드6·공백접미2·유럽/비US8) |
| C. 편입 (sync_overview) | **created 135 / 실패 1(SLR)** — FMP `/stable/quote` 빈 배열, 실패율 0.74%. 비US 0(전건 NASDAQ96/NYSE39) |
| D. DailyPrice 백필 (90일) | **135/135 성공, 실패율 0%**. 8,329 행. 깊이 min21/med62/max62 거래일 → M1(20일 z-score) 충족 |
| FMP 총 사용 | **283콜** (C 138 + D 135 + 검증 10) ≤ 1,500 |

## 게이트 재측정 (distinct, 최신 snapshot, w≥1.0, 신 유니버스 670)
- 자격 그룹 **9개** (ARKG·LIT 신규 진입)
- 분포 `[5, 8, 12, 23, 26, 30, 33, 42, 45]`, **중앙값 26**
- **게이트 X=8 = 통과 ✅** (X=10도 통과). 예측 26 = 실측 26.
- 유일 편차: ICLN 예측 9 → 실측 8 (SLR=ICLN 전속 holding이 C에서 FMP 소스 부재로 미편입). 중앙값 무영향.

## 검증
- **유니버스: 535 → 670** (+135; SLR 1종 실패로 136 미달)
- 멱등성: overview·price 재실행 시 Stock Δ=0, DailyPrice Δ=0 ✅
- 회귀: `makemigrations --check` No changes / `pytest tests/serverless/` 377 passed·0 failed / 기존 535 종목 무변경(disjoint) / health_check 우회 0
- 코드 diff 0 (변경은 DB 데이터만: Stock 135 created + DailyPrice 8,329)
- **sector/industry 채움: 0/135** — FMP `/stable/quote`가 미반환, `_map_fmp_to_stock` 미매핑. 빈 채로 편입(보드 테마 그룹핑은 ETFHolding 기반이라 게이트 무영향, 단 별도 보강 트랙 권장)

## 잔여/후속 (범위 외)
- **SLR** 미편입: FMP quote 소스 복구 후 재시도 시에만 의미 (ICLN 8 유지, 자격 그룹 영향 없음)
- **sector/industry 빈 채움**: profile 엔드포인트 별도 동기화 트랙
- **BETZ/HACK/KWEB/TAN**: holdings 미적재로 여전히 0 (CS-EXP-P1/P2 선행 필요)
- **Neo4j 그래프 편입**: `ETF_THEME_MAP`(load_themes_to_neo4j.py) 편집 필요 — 본 세션 쓰기 범위 밖, 후속 트랙
