# Replay v0.2A 결과 보고

상태: completed working calibration evidence. Approved/Effective 또는 architecture adoption이 아니다.

동일 frozen summary와 동일 evidence 17개를 사용한 한 쌍의 hard-006 실행에서, historical candidate/critique 두 문서를 포함한 original arm은 8,192 completion tokens를 모두 사용하고 final JSON 도중 종료됐다. 두 문서를 제거한 sanitized arm은 2,085 tokens에서 valid final JSON을 생성했다.

| 항목 | Original | Sanitized |
|---|---:|---:|
| Prompt tokens | 14,387 | 4,903 |
| Completion tokens | 8,192 | 2,085 |
| Total tokens | 22,579 | 6,988 |
| Latency | 53.598s | 16.399s |
| Protocol | Incomplete | Complete |
| Semantic review | Unassessed | Working review completed |

Sanitized output은 frozen summary의 `Unsupported → 달성 가능성이 낮다`라는 과도한 강화를 제거했다. 전력 인가 시점, 설치 일정, 인가 전 출하 가능성, 금액 mix 불확실성을 상당 부분 보존하고 최종 결론을 Unsupported 범위에 뒀다.

그러나 E12의 표준 장비와 맞춤형 모듈 간 매출 인식 조건 차이를 누락했다. E13의 금액 mix 불확실성을 limitation에 적었지만 매출 시점 추론과 연결하지 않았다. E8/E13/E17의 내용을 limitations에서 사용하면서 `used_source_ids`에서 빠뜨렸고, E5의 공급사→람다그리드 부품 배정 문제를 람다그리드→고객 배정 문제와 묶은 provenance 오류가 있다.

따라서 이 결과는 “이 실행에서는 historical payload 제거 후 protocol completion과 결론 범위가 개선됐다”는 방향성 evidence다. 하지만 제거된 context가 prompt 9,484 tokens를 차지하므로 semantic contamination과 context-size burden을 분리하지 못한다. 한 건의 exposed calibration pair이며 original arm의 final artifact가 없으므로 semantic net effect의 대칭 비교도 불가능하다.

Artifact 8개는 GitHub 저장본을 대상으로 SHA-256 8/8 재검증했다. 두 request의 system prompt, frozen summary, evidence 17개, evidence 순서와 generation config가 동일하고 candidate_output 두 문서의 포함 여부만 다른 것도 확인했다. Model invocation은 2회, retry는 0회, requested/returned model identity는 일치했다. 실제 비용은 확인되지 않았다.
