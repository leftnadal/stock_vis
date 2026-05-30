PR4 STEP 0 — 대상 확정 + 분할 근거 조사 (fact-check, 결정 아님)

[전제] PR4 대상은 execution_plan_v1.md가 진실의 소스. 메모리 추정 금지.
이 STEP은 조사만 수행하고 결과를 보고. 실제 mv·이관은 다음 프롬프트.

[프롬프트 자체 확인]
① main HEAD = bd4080c 확인 (아니면 STOP·보고)
② tag monorepo-pre-pr4 존재 확인

──────────────────────────────────────────────
STEP 0-A — PR4 대상 확정 (plan에서 읽기)

- cat docs/monorepo_migration/execution_plan_v1.md
- PR4로 지정된 대상 모듈 추출 (apps/ 4개 / packages/web / 모델삭제 / 기타)
- plan에 PR4 명시 없으면 → PR1~3 완료분 제외한 잔여 + plan 순서로 추론, HALT·보고
- 확정 대상을 콘솔에 박음

STEP 0-B — 대상 유형 분기
· 대상 = 단일 모듈 → 결합도 조사 skip, PR3형 단순 이동. STEP 0-D
· 대상 = apps/ 다중 → STEP 0-C (결합도 조사)
· 대상 = 모델 삭제/기타 → HALT·보고 (이동 아닌 작업, 별도 설계 필요)

STEP 0-C — apps/ 4앱 간 import 결합도 조사 (분할 근거)

- 각 앱 쌍에 대해 cross-import grep:
  grep -rn "from \(dashboard\|market_pulse\|chain_sight\|portfolio\)" \
   --include=\*.py <each app dir>
- 결합도 매트릭스 작성 (어느 앱이 어느 앱을 import하는가)
- market_pulse "독립" 메모리 단서 검증: market_pulse ↔ 나머지 3 결합 0건인지
- 외부(apps 밖)에서 각 앱을 import하는 호출처 수도 카운트
- 결과를 표로 박음 (분할 단위 결정 근거)

STEP 0-D — 조사 결과 보고 (여기서 정지)

- 확정 대상 + (다중이면) 결합도 매트릭스 박고 STOP
- 사용자가 결과 보고 분할 전략 결정 → 다음 프롬프트(STEP 1~9) 작성

──────────────────────────────────────────────
HALT 트리거:

1. plan에 PR4 미명시 → 잔여+순서 추론 박고 보고
2. 대상이 모델 삭제 등 비-이동 작업 → 별도 설계 필요, 보고
3. 결합도 조사 중 순환 import 발견 → 분할 복잡도 ↑, 박고 보고
   ──────────────────────────────────────────────
