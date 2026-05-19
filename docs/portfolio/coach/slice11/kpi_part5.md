# Slice 11 Part 5 — KPI Matrix

| #   | KPI                              | 측정값                                 | 기대값                          | PASS/FAIL |
| --- | -------------------------------- | -------------------------------------- | ------------------------------- | --------- |
| 1   | manual_eval_rubric.md            | 88 lines, D1-D 3축 명시                | 존재                            | PASS      |
| 2   | shuffle 스크립트 (seed=42)       | scripts/manual_eval_shuffle.py 생성    | 존재                            | PASS      |
| 3   | shuffled view Case # count       | 24/24                                  | 24                              | PASS      |
| 4   | label_mapping.json 항목 수       | 24                                     | 24                              | PASS      |
| 5   | seed 재현성 md5sum               | `5e3dca8f3dc0641a541f6a9aa212860f` 동일 | 동일                          | PASS      |
| 6   | blind 마스킹                     | Case 헤더 라벨 노출 없음                | 없음                          | PASS      |
| 7   | 병진 평가 완료                   | 24/24 점수 입력 완료                   | 24/24                           | PASS      |
| 8   | naturalness 분포 폭              | **3** (min 2, max 5)                   | ≥3 (Slice 9 폭 2 대비 개선)     | PASS      |
| 9   | insight 분포 폭                  | **3** (min 2, max 5)                   | ≥3                              | PASS      |
| 10  | actionability OK rate            | 9/12 (75%)                             | -                               | INFO      |
| 11  | inter-rater actionability 일치   | 10/12 (83%)                            | -                               | INFO      |
| 12  | Claude 사후 비교 dump 생성       | claude_eval.json + .md (비공개)        | 존재                            | PASS      |
| 13  | winner 확정 (병진 ground truth)  | **haiku 압승** (nat +0.5, ins +0.33, actn +17%p) | sonnet 또는 haiku | PASS (확정) |
| 14  | 글쓰기 가설 7/7                  | D2.B 외삽 확정 (Slice 1·3·4·5·6·7·8·11) | 7/7                          | PASS      |
| 15  | 회귀 (Phase A + B 후)            | 571 → 571 (±0)                         | 571 또는 +α                     | PASS      |
| 16  | IDENTICAL                        | 7/7 PASS                               | 7/7                             | PASS      |
| 17  | LLM 비용 (Phase A+B 단독)        | $0                                     | 0                               | PASS      |
| 18  | Slice 11 누적 비용               | $0.2669 / $1.00 cap (마진 73.3%)        | ≤ $0.80                         | PASS      |
| 19  | 전체 누적 임계                   | $2.6444 / $4.00 (마진 33.9%)            | ≤ $4.00                         | PASS      |
| 20  | 부채 처리 (#41, #58, #59)        | #41 keep_open, #58/#59 확정 등록       | 처리 완료                       | PASS      |

---

## §1. 핵심 발견

### winner 확정: **haiku (double win)**
- **품질** (병진 평가, ground truth): nat 3.583 > sonnet 3.083, ins 3.750 > 3.417, actn 5/6 > 4/6
- **Efficiency** (Part 4 매트릭스): cost 3.2× cheaper, latency 1.85× faster
- **글쓰기 가설 7/7 확정**: D2.B "글쓰기 차원 = haiku" 일관 외삽 (Slice 1·3·4·5·6·7·8·11)

### Anchor bias 회피 정책 (D2-A blind) 정당화
- Claude 사후 평가는 sonnet 우위 예측 (정반대)
- 만약 anchor로 노출했다면 병진 평가도 sonnet 쪽으로 기울 위험
- inter-rater agreement nat=25%, ins=21%, actn=83% — 정성 축 두 평가자 시각 매우 다름
- Ground truth는 병진 (한국어 native, 실제 사용자 관점)

### Slice 9 분포 폭 → Slice 11 개선
- Slice 9 nat 폭 2 → Slice 11 nat 폭 3 / ins 폭 3
- Rubric 가이드 "분포 폭 ≥3 의식적 사용"이 효과 확인
