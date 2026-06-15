# CS-EXP-LOAD — 신규 테마 ETF 3종 적재 + 게이트 재측정 (쓰기 세션)

> 세션 브랜치: `monorepo/sess-cs-exp` (worktree `stock_vis_cs_exp`)
> 결정: PAVE·XBI·KRE 등록·적재 (URA 제외 — 교집합 경계값). 파서 코드 수정 0.
> **결과: 적재 성공 / 보정 게이트 미달 (중앙값 7 < 10) → HALT**

## 적재 결과
| ETF | parser | 적재 holdings 행 | snapshot |
|---|---|---|---|
| XBI (SPDR S&P Biotech) | spdr | 144 | 1 |
| KRE (SPDR S&P Regional Banking) | spdr | 146 | 1 |
| PAVE (Global X US Infrastructure) | globalx | 100 | 1 |

- ETFProfile 3개 생성(tier=theme), `ETF_CSV_SOURCES` 1파일 편집, 파서 코드 diff 0, 마이그레이션 0.
- 멱등성 ✅ (재적재 동일 144/146/100), makemigrations No changes, pytest serverless 377 passed/0 failed.

## 보정 게이트 재측정 (자격 그룹 = tier=theme ∧ w≥1.0 ∧ 유니버스내 distinct 멤버 ≥3)
유니버스 N = 535. **최신 snapshot 기준 distinct 유니버스 멤버 수:**

| ETF | 멤버 | 자격(≥3) |
|---|---|---|
| PAVE [신규] | 22 | ✅ |
| SOXX | 17 | ✅ |
| ARKK | 12 | ✅ |
| XBI [신규] | 7 | ✅ |
| KRE [신규] | 5 | ✅ |
| BOTZ | 4 | ✅ |
| ICLN | 3 | ✅ |
| LIT | 2 | ❌ |
| ARKG | 1 | ❌ |
| BETZ·HACK·KWEB·TAN | 0 | ❌ |

- 자격 그룹 수 = **7** (≥6 ✅)
- 자격 그룹 분포 = `[3, 4, 5, 7, 12, 17, 22]`, **중앙값 = 7** (≥10 ❌)
- **게이트 = 자격≥6 ∧ 중앙값≥10 → 미달 ❌** (중앙값에서 실패)
- 신규 3개는 **전부 자격 그룹**이 됨(깡통 없음, ARK 역설 미발생). 자격 그룹 수는 5→7로 증가.

## ⚠️ 이전 리포트 수치 오류 정정
CS-EXP-GATE·CS-EXP-SOURCE가 보고한 멤버 수(SOXX 221·BOTZ 56·ICLN 39·LIT 32)는 **유니버스 내 distinct 멤버가 아니라 다중 snapshot_date 누적 행 수**였다.
- SOXX 실측: snapshot 13개 누적 총 429행 → w≥1.0 행 ~221 (≠ distinct 유니버스 멤버 17)
- ICLN: snapshot 13개, 총 1657행 → 부풀림. distinct 유니버스 멤버는 3.
- ARKK(12)·ARKG(1)만 snapshot 1개라 이전 수치와 일치했음.
- **SOURCE의 "PAVE 1개로 중앙값 35.5 통과" 예측은 이 부풀린 수치에 근거한 오류.** 실제 중앙값은 7.

## 구조적 결론 (HALT 사유 + 다음 방향)
- 테마 ETF는 대부분 **SP500 외 중·소형주**를 담아, 535 SP500 유니버스와의 교집합 멤버가 그룹당 한 자릿수에 그친다.
- 따라서 **ETF를 더 추가해도 자격 그룹 "수"는 늘지만 "중앙값"은 오르지 않는다**(밀도가 유니버스에 의해 상한).
- 중앙값 ≥10은 **ETF 추가가 아니라 유니버스 편입(U2 = CS-EXP Part C)** 으로만 도달 가능 — ETF holdings의 비SP500 US 종목을 Stock 유니버스에 편입해야 그룹 밀도가 오른다.
- 이는 GATE 리포트가 언급한 "기존 그룹 밀도 증가(유니버스 편입)" 경로가 실제 해법임을 데이터로 확정.

## 처리
- 적재 데이터는 유효(3개 자격 그룹, 보드 개선)하므로 보존(DELETE 금지 계약 + 데이터 자체 유효). 등록은 커밋.
- 게이트는 미달 → DECISIONS에 "게이트 통과" 대신 "미달 + U2 필요"로 기록.
- Neo4j 그래프 편입은 `ETF_THEME_MAP`(load_themes_to_neo4j.py) 편집 필요 → 본 세션 쓰기 범위(ETF_CSV_SOURCES 1파일) 밖 → 후속.
