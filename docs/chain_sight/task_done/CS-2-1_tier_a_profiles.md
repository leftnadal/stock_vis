# CS-2-1: Tier A 프로파일 계산

> **완료일**: 2026-04-02

## 생성/수정된 파일

- chainsight/tasks/profile_tasks.py (calculate_growth_stages, calculate_capital_dna, calculate_all_profiles)

## 결과

| 프로파일 | 성공 | 실패 | 상태 |
|---------|------|------|------|
| GrowthStage | 480 | 0 | ✅ |
| CapitalDNA | 473 | 0 | ✅ |

### GrowthStage 분포
- declining: 18, accelerating: 82, turnaround: 16, mature: 364

### CapitalDNA 분포
- balanced: 332, heavy_investor: 65, cash_hoarder: 76

## 발견된 이슈

- Decimal(8,4) overflow: buyback_yield/dividend_payout 값이 범위 초과 → _clamp_decimal() 헬퍼로 해결

## 다음 작업

→ CS-2-2: CoMentionEdge 추출
