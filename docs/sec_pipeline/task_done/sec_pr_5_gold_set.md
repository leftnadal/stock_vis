# SEC-PR-5: Gold Set 라벨링 + 평가 스크립트

> **완료일**: 2026-04-04

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `sec_pipeline/fixtures/gold_set_schema.py` | GoldSetEntry/SupplyChainRelation dataclass |
| `sec_pipeline/fixtures/gold_set.json` | 10종목 Gold Set (AAPL~AMZN) |
| `sec_pipeline/management/commands/evaluate_gold_set.py` | 평가 management command |

## Gold Set 라벨링 현황

| 종목 | Section | Supply Chain | 비고 |
|------|---------|-------------|------|
| AAPL | ✅ 3/3 | 0 | 10-K에서 회사명 미언급 |
| MSFT | ✅ 3/3 | 3 (LinkedIn, Activision, OpenAI) | |
| NVDA | ✅ 3/3 | 5 (TSMC, Samsung, SK Hynix, Micron, Hon Hai) | |
| GOOGL | ✅ 3/3 | 2 (Apple, Samsung) | |
| JPM | ✅ 3/3 | 0 | 은행 특성 |
| GS | ✅ 3/3 | 0 | |
| JNJ | ✅ 3/3 | 0 | |
| UNH | ✅ 3/3 | 0 | |
| XOM | ✅ 3/3 | 0 | |
| AMZN | ✅ 3/3 | 1 (AWS — 자체) | |

## 현재 평가 결과 (NVDA만 수집됨)

```
Section Extraction: 3/3 = 100.0% (target: ≥90%)
Track A Precision: 5/8 = 62.5% (target: ≥70%)
Track A Recall: 5/11 = 45.5% (target: ≥50%)
```

→ S&P 500 배치(SEC-PR-6) 후 재평가 필요

## 다음 PR

→ SEC-PR-6: S&P 500 배치 실행 + 결과 검증
