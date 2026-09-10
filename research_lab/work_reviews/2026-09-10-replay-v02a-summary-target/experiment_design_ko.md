# Replay v0.2A 실험 계약

## 질문

hard-006에서 historical candidate/critique context의 존재가 protocol completion과 결과의 epistemic profile에 어떤 차이를 만드는가?

## 비교

| 항목 | C-original | C-sanitized |
|---|---|---|
| 평가 대상 | 동일 frozen summary | 동일 frozen summary |
| evidence | 동일 17개, 동일 순서·내용 | 동일 17개, 동일 순서·내용 |
| historical candidate/critique | 2개 포함 | 제거 |
| model/config/system prompt | 동일 | 동일 |
| retrieval | 없음, full context | 없음, full context |

`input_diff.json`이 두 입력의 identity와 제거된 두 문서의 hash를 기록한다. Sanitized arm에 evidence를 추가·삭제·선택·강조하거나 answer key를 넣지 않는다.

## 해석 경계

Primary historical artifact에는 분리 가능한 final answer가 없으므로 이 실험은 v0.1 hard-006/C의 복구 재실행이 아니다. 이미 v0.1 모든 조건에서 사용한 frozen summary를 새 lineage의 공통 evaluation target으로 고정한 `summary-target full-context contamination isolation`이다.

결과는 다음을 분리해 검토한다.

- transport status
- provider finish state
- protocol completion
- visible reasoning-like content
- semantic review state
- material condition preservation/loss
- unsupported assertion/strengthening
- conclusion scope calibration

단일 scalar score를 만들지 않는다. Exposed calibration case이므로 held-out confirmation이나 permanent methodology/runtime/role/model/memory 결정을 지지하지 않는다.
