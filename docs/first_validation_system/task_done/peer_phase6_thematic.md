# Peer Phase 6: Thematic Preset (비즈니스 DNA 기반)

> **완료일**: 2026-04-04

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `validation/services/preset_generator.py` | `_generate_thematic()` 메서드 추가 |

## 로직

```
GrowthStage × CapitalDNA 교차 조합 → 섹터 횡단 DNA 유사 클러스터

예: NVDA (accelerating × balanced) → 같은 DNA인 타 섹터 종목 30개
    MSFT (mature × heavy_investor) → 46개
```

- 같은 (stage, capital_type) 조합 = 비즈니스 DNA 유사
- 다른 섹터 종목 우선 (같은 섹터는 기존 프리셋에서 커버)
- 최소 5개 이상 그룹만 생성

## 결과

- **463/503 종목**에 thematic 프리셋 생성
- 전체 프리셋: **2,282개** (6종류)

| preset_key | 건수 |
|-----------|------|
| default | 514 |
| sector_all | 514 |
| thematic | **463** (신규) |
| quality_top | 392 |
| lifecycle | 392 |
| size_peers | 7 |

## 다음 작업

→ Peer Phase 7: LLM Interactive Peer Adjustment
