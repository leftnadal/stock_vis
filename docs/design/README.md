# docs/design — 설계 목업 정착소 (D-DOCS-PERSIST)

> 완료 슬라이스의 설계 목업(HTML 등)을 정착시킨다. 진실의 소스는 구현 코드 + `DECISIONS.md`이며,
> 목업은 시각 의도의 이력 참고물이다.

## MP2-ANALOG 카드 목업

| 목업 | 파일 | 상태 |
|------|------|------|
| 유사 국면 카드 | `analog_card_mockup.html` | ❌ 미전달 — 세션에 파일로 전달되지 않음. 디렉터 재전달 대기 |
| L2/L3 라벨 | `label_l2l3_mockup.html` | ❌ 미전달 — 세션에 파일로 전달되지 않음. 디렉터 재전달 대기 |

> C-core는 목업 부재 하에 진행: L2 태그 시각 구조는 기존 `AnalogCard`의 슬롯 + 기존
> `meaning.ts::REGIME_TONE`(D-COLOR-SYSTEM 검수 팔레트) 재사용으로 구현. 목업 전달 시 대조·정착.
