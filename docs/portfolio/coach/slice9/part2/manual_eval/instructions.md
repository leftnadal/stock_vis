# Slice 9 Manual Eval 안내

> Slice 9 Part 2 #46 산출물. 사용자가 26 cases를 평가하는 작업 흐름.

## 평가 작업 흐름

1. `eval_page.html`을 브라우저에서 더블클릭으로 열기 (Chrome / Safari / Firefox 모두 동작)
2. 각 case (S01_haiku ~ S14_sonnet, S13 skip) 한 페이지씩 평가:
   - **Naturalness** (1~5): 한국어 답변 자연스러움 (어색한 번역체, 반복, 어절 깨짐 등)
   - **Insight** (1~5): 4요소(현재 상태/임계값/액션/시점) 충족도 + 통찰력
   - **Comment** (선택): 평가 근거 또는 의문점
3. 모든 평가 완료 시 **Export to JSON** 버튼 클릭 → `slice9_manual_eval_results.json` 다운로드
4. 다운로드한 파일을 `docs/portfolio/coach/slice9/part2/manual_eval/results.json`으로 저장

## 평가 기준 (rubric.md §A/§B 참조)

`rubric.md`의 §A Naturalness / §B Insight / §B.1 Sample 5건을 평가 전 검토 권장.

### Naturalness 요약

| 점수 | 기준                                                            |
| ---- | --------------------------------------------------------------- |
| 1    | 매우 부족 — 기계 번역체, 어색한 영문 직역 (3건+)                |
| 2    | 부족 — 일부 어색 표현 (1~2건)                                   |
| 3    | 보통 — 무난하지만 정형적                                        |
| 4    | 좋음 — 자연스러운 흐름                                          |
| 5    | 매우 좋음 — 사람이 쓴 듯한 자연스러움                           |

### Insight 요약

| 점수 | 기준                                                            |
| ---- | --------------------------------------------------------------- |
| 1    | 통찰 없음 — 숫자 나열만                                         |
| 2    | 약함 — 기본 해석만                                              |
| 3    | 보통 — 지표 1~2개 해석 + 일반적 시사점                          |
| 4    | 좋음 — 지표 간 관계 + preset 의도 + 행동 시사점 1건             |
| 5    | 매우 좋음 — 지표 간 관계 + 위험·기회 균형 + 행동 시사점 2건+    |

## 보조 자료 (참고용, 평가 대상 아님)

- **rationale (Sonnet 자체 평가)**: 각 case 페이지에 회색 박스. Sonnet이 자기 답변을 어떻게 평가했는지 보조 정보.
- **자동 patterns score**: 메타 영역에 표시. P1~P5 자동 검출 결과 (0~5).
- **원본 모델 라벨**: case_id 옆 표시 (claude-haiku-4-5 / claude-sonnet-4-5). 비교 측정 위해 필요.

## 예상 작업 시간

- 평균 case당 1분 = 약 26분
- 길이가 긴 case는 2~3분 가능 → 총 30~45분

## 중간 저장

- 라디오 버튼 클릭 시 localStorage 자동 저장
- 브라우저 종료 후 재개 가능 (동일 URL로 다시 열기)
- 다른 브라우저/기기에서는 처음부터 (localStorage 분리)

## 분포 폭 자가 점검 (rubric.md §C.7)

평가 완료 후 다음을 자가 확인:

- [ ] 분포 폭 (max - min) ≥ 3.0 → PASS (1점부터 5점까지 다양하게 사용)
- [ ] 5점 비율 5~20% 사이
- [ ] 1점 사용 1건 이상 (전 범위 활용)
- [ ] 5~7점 영역에 안전 수렴 회피

분포 폭 < 2.0 → 재평가 권장 (rubric 미숙지 의심).

## 평가 완료 후

평가 결과 JSON을 Claude Code에 전달 → 다음 단계:

- winner 판정 (Haiku vs Sonnet, label_means 비교)
- 글쓰기 가설 6/6 → 7/7 정착 vs 6/7 판정
- 분포 폭 (#49) 재검토 — Sonnet 자체 평가 width=2 vs manual eval width 비교
- Slice 9 전체 종결 + Slice 10 진입 결정
