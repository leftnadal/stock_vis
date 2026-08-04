# SEC β G1.6 — partial_match 재분류 리포트 (dry-run)

> 세션 `monorepo/sess-secb-g16` · 2026-07-31 · 결정론 V-A · LLM 0콜 · DB 쓰기 0
> 스크립트: `scripts/sec/grounding_g16_partial_reclassify.py` (커밋 `91b2f643`)
> 기준 사전 고정: Gate 0 `1c41a7e5` (partial = raw source 접두비율 ≥70%, 절단/tail 발산)

## §2 — 재분류 후 4분포 (raw source · 상호배타 · 전수합 명목 1751)

| 등급 | 명목 | 명목% | 유니크 |
|------|------|-------|--------|
| verified | 1273 | 72.70% | 722 |
| normalized_match | 41 | 2.34% | — |
| **partial_match** | **410** | **23.42%** | **163** |
| not_found (잔여) | 27 | 1.54% | 19 |
| missing_source | 0 | 0.00% | — |
| **합계** | **1751** | | |

- G1 베이스라인 재현: verified 1273 / normalized 41 / not_found 437 / missing_source 0 (일치).
- partial은 접지 성공(verbatim)에 **합산 안 함** — 별도 등급.

## 잔여 순수 not_found율 (partial 제외, missing_source=0 → 분모=명목)

- **명목 = 27 / 1751 = 1.54%**
- **유니크 = 19 / 937 = 2.03%**
- 임계 15% — **충족(≤15%). 단 최종 판정·비준은 감독 세션 몫**(실행 세션 자체 판정 아님).

## H4 — 정합성 교차 (G1.5 분해와)

- G1.5: not_found 437 → 유니크 182 = tail 발산 169 + 재서술 5 + 합성 8.
- G1.6: not_found 437 → partial_match 유니크 **163** + 잔여 not_found 유니크 **19** = **182** (정확 일치).
- pm 유니크 163 ≈ tail 발산 169(차 6 = 70% 하한이 prefix64보다 엄격해 긴 인용 일부가 잔여로). **구조적 정합 — H4 PASS(HALT 아님).**

## §3 — partial_match 층화 20건 (패턴 입증)

지배 패턴 = **경쟁사/공급사 리스트**: "…include, but are not limited to, the following: [회사]" 형태.
- 접두 214자(문장 stem + 리스트 도입부)가 원문에 **verbatim** 존재(r=0.79~0.93).
- tail = 리스트 내 특정 회사명(예: Johnson & Johnson, CMR Surgical Ltd., Karl Storz) — **원문 리스트에 실재**(다른 위치), LLM이 리스트에서 선택/재배열.
- → "**접두 verbatim + tail 절단/발산**"이며 **조작(합성) 아님**. 전문 샘플은 스크립트 재실행으로 재현(결정론).

## 불변 확인

- **V-A 결정론 · LLM 호출 0** (순수 문자열 접두 계산).
- **DB 쓰기 0** (raw SELECT만).
- 판정 임계(15%)·partial 하한(70%) **사후 조정 없음**(Gate 0 고정값 사용).
- §4 마이그 0003(status choice additive) 생성, **stock_vis 미적용**(Gate 2).
