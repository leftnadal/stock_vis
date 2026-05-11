# Slice 6 Part 3 Step 7 — 매트릭스 10 cases 결과

> 실행: 2026-05-11T03:51:00.690496+00:00
> 매트릭스: 5 fixture × 2 model = 10 cases

## 합계

- 총 호출: 10/10
- schema PASS: 10/10
- completeness PASS: 10/10
- fallback: 0
- 총 비용: $0.110054
- max haiku cost: $0.004727 / max sonnet cost: $0.018033
- cost_per_call_pass: ✓
- total_cost_pass: ✓

## case별 결과

| # | fixture | model | schema | comp | output_tokens | cost | latency | preset_alignment LLM | vs expected |
|---|---|---|---|---|---|---|---|---|---|
| 1 | v1_concentrated_balanced | haiku | ✓ | ✓ | 378 | $0.00454 | 7259ms | partial | ✓ |
| 2 | v1_concentrated_balanced | sonnet | ✓ | ✓ | 366 | $0.01684 | 8233ms | partial | ✓ |
| 3 | v2_concentrated_misfit | haiku | ✓ | ✓ | 405 | $0.00466 | 4065ms | misaligned | ✓ |
| 4 | v2_concentrated_misfit | sonnet | ✓ | ✓ | 428 | $0.01784 | 6674ms | misaligned | ✓ |
| 5 | v3_concentrated_large | haiku | ✓ | ✓ | 373 | $0.00472 | 5030ms | partial | ✓ |
| 6 | v3_concentrated_large | sonnet | ✓ | ✓ | 335 | $0.01711 | 4177ms | partial | ✓ |
| 7 | v4_concentrated_value | haiku | ✓ | ✓ | 419 | $0.00473 | 4376ms | partial | ≠ (aligned) |
| 8 | v4_concentrated_value | sonnet | ✓ | ✓ | 376 | $0.01708 | 7652ms | partial | ≠ (aligned) |
| 9 | v5_concentrated_dividend | haiku | ✓ | ✓ | 351 | $0.00450 | 4986ms | aligned | ✓ |
| 10 | v5_concentrated_dividend | sonnet | ✓ | ✓ | 427 | $0.01803 | 7175ms | aligned | ✓ |

## CostGuard

- call_count: 10/50
- 마진: 40
- 누적 비용: $0.110100