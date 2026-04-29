# Validation Report — Slice 1

> 슬라이스: E1 + GARP + 종목 5/15
> 작성일: TBD (실 호출 후 갱신)
> 브랜치: portfolio
> 이전 보고: D-8 결과는 `portfolio/validation_report.md` 참조

---

## 1. Metadata

| 항목              | 값                                                                                                            |
| ----------------- | ------------------------------------------------------------------------------------------------------------- |
| Slice 범위        | E1 GARP, fixture 3종 (garp_tech / garp_misfit / garp_large), 모델 3종 (Gemini Flash / Sonnet 4.5 / Haiku 4.5) |
| 호출 시점 (UTC)   | step8_3way_raw.json metadata.timestamp 복사                                                                   |
| LLMClient git SHA | `git rev-parse HEAD` 결과                                                                                     |
| preset_version    | v1.0                                                                                                          |
| metric_version    | v1.0                                                                                                          |
| scoring_version   | v1.0                                                                                                          |
| prompt_version    | v1.0                                                                                                          |
| universe_version  | v1.0                                                                                                          |
| 누적 LLM 호출     | XX / 50                                                                                                       |
| 누적 비용 (USD)   | $X.XX                                                                                                         |

## 2. Call Log (자동 생성: step8_3way_raw.json 기반)

| #   | Fixture     | Label  | Model                | Input | Output | Latency(ms) | Cost(USD) | Fallback |
| --- | ----------- | ------ | -------------------- | ----- | ------ | ----------- | --------- | -------- |
| 1   | garp_tech   | gemini | gemini-2.0-flash     | ?     | ?      | ?           | ?         | —        |
| 2   | garp_tech   | sonnet | claude-sonnet-4-5    | ?     | ?      | ?           | ?         | —        |
| 3   | garp_tech   | haiku  | claude-haiku-4-5     | ?     | ?      | ?           | ?         | —        |
| 4   | garp_misfit | gemini | …                    | …     | …      | …           | …         | …        |
| 5   | garp_misfit | sonnet | …                    | …     | …      | …           | …         | …        |
| 6   | garp_misfit | haiku  | …                    | …     | …      | …           | …         | …        |
| 7   | garp_large  | gemini | …                    | …     | …      | …           | …         | …        |
| 8   | garp_large  | sonnet | …                    | …     | …      | …           | …         | …        |
| 9   | garp_large  | haiku  | …                    | …     | …      | …           | …         | …        |

## 3. Scoring (자동 생성: step8_3way_scored.json 기반)

### 3.1 1차 필터 (Lexicographic Hard Gate)

조건: `schema_pass = True AND naturalness ≥ 3 AND insight ≥ 3`

| Fixture     | gemini | sonnet | haiku |
| ----------- | ------ | ------ | ----- |
| garp_tech   |        |        |       |
| garp_misfit |        |        |       |
| garp_large  |        |        |       |

통과: X / 9. Mode: efficiency 또는 fallback.

### 3.2 2차 점수 (Efficiency or Fallback)

| Label  | mean score | n   |
| ------ | ---------- | --- |
| gemini |            | 3   |
| sonnet |            | 3   |
| haiku  |            | 3   |

Winner: **TBD**

## 4. Dimension Analysis (수동 작성)

### 4.1 Schema 적합성
- 모델별 통과율 + 실패 원인.

### 4.2 한국어 자연스러움
- 모델별 평균 점수 + fixture별 변화. 어떤 톤이 한국 사용자 친화적인지.

### 4.3 진단 통찰성
- 카드 4요소(무엇이/기준/왜 중요/예외) 충실도. fixture별 비교.

### 4.4 비용
- 모델별 비용 분포. garp_large 영향.

### 4.5 지연
- 모델별 latency 평균/분산. 5초 임계 위반 여부.

## 5. Decision

### 5.1 Slice 2 진입 시 primary provider
- 채택: TBD
- 변경 여부: 유지 / 변경

### 5.2 Slice 2 진입 시 retain 사항
- LLMClient wrapper, services 분리, fixture 3종, scoring 스크립트 모두 유지.

### 5.3 Slice 2 진입 시 change 사항
- TBD (예: 프롬프트 톤 강화, fallback 트리거 조정).

### 5.4 Phase 2 보류 항목
- 자연스러움 평가 자동화 (LLM-as-judge).
- 통찰성 평가 자동화 (rule-based heuristic).
- 토큰 예산 한계 검증 (현재 종목 15개에서 더 큰 사이즈).

## 6. Cost Guard

| 항목                           | 값      |
| ------------------------------ | ------- |
| Slice 1 누적 LLM 호출          | XX / 50 |
| 누적 비용 (USD)                | $X.XX   |
| Step 6 비용                    | $0.000XX |
| Step 8 비용                    | $X.XX (9 calls) |
| Step 8 재시도                  | $X.XX (XX calls) |
| 잔여 호출 한도                 | XX      |
| Slice 2 진입 시 비용 가드 리셋 | 권장 (env 또는 카운터 reset) |
