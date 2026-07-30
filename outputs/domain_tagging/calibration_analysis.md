# ⑳-3 S2-B 캘리브레이션 CSV 분류 분석 (read-only)

소스 review_batch.csv 270건. LLM·DB·코드 무접촉.

## 1. type_change 실체 (raw 119건)
- **진짜 타입변경(제안≠현재) 33건 = 실효 12%** (raw 44%는 과대 — 아래 포함)
- 자가모순(match=False인데 같은 타입 제안) 53건 = LLM 노이즈(무시 가능)
- 미지정(match=False·제안없음) 33건 = 약신호
- SUPPLIES_TO↔DEPENDS_ON 상호 플립 8건(방향 컨벤션 충돌)
- 주요 실제 변경: SUPPLIES_TO→PARTNER_WITH 9 · SUPPLIES_TO→DEPENDS_ON 5 · PARTNER_WITH→COMPETES_WITH 4 · PARTNER_WITH→DEPENDS_ON 4 · DEPENDS_ON→COMPETES_WITH 3

## 2. target_not_in_basis
- raw False 169건(63%!) — 원인: SEC evidence 100자 캡+타깃이 나열 밖
- (a)center존재·타깃없음 14 / (b)둘다없음 83 / (c)나열형 절단추정 72
- 완화안(심볼 a 또는 b 실존) → pending중 auto 이동 **5건뿐**(type_match/confidence 게이트가 지배 → 룰① 완화 단독 효과 미미)

## 3. 태그 정규화
- 118종 → 10군집 흡수 59종 + 롱테일 59종. 목표 30~50 달성 가능

## 4. 검수 3구획
- A 패턴일괄 20 · B 개별 195 · C auto스팟 55
- 예상 ~108분(A 5s·B 30s·C 10s/건)
- ⚠️ B가 195건(72%)로 과다 → **기계검증 룰 튜닝 선행**(target 나열 인식·type_match 자가모순 필터)이 auto_candidate를 늘려 검수량을 줄이는 핵심 레버
