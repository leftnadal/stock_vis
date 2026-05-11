# CS-2-1b: SensitivityProfile 계산

> **완료일**: 2026-04-04

## 생성/수정된 파일

| 파일 | 역할 |
|------|------|
| `chainsight/tasks/sensitivity_tasks.py` | calculate_sensitivity_profiles (신규) |
| `chainsight/tasks/profile_tasks.py` | calculate_all_profiles에 sensitivity 추가 |

## 결과

- **503건** 전체 성공, 실패 0건

### rate_sensitivity 분포
- low: 304, medium: 191, 미계산: 8

### forex_sensitivity 분포
- high: 182, medium: 129, low: 99, 미계산: 93 (Geo API 미제공 종목)

### debt_maturity_risk 분포
- low: 364, medium: 75, high: 56, 미계산: 8

### regulation_type 분포
- none: 301, financial: 69, fda: 61, environmental: 55, telecom: 17

### 샘플 (AAPL)
```
D/E: 1.338, rate_sensitivity: medium
foreign_revenue_pct: 57.14%, forex_sensitivity: high
beta: 1.109, beta_sector_adj: -0.588
regulation: none
```

## 다음 작업

→ CS-2-1c: InsiderSignal 계산
