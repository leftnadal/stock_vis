# Mini-Slice Pattern (Slice 10 Step 0 신설)

> Slice 10이 첫 사례로 정착한 슬라이스 운영 패턴. 단일 도구 부채 격리를 위해
> Step 0 단독으로 종결한다.

## 1. 정의

**Mini-slice** = 다음 조건을 모두 충족하는 슬라이스 운영 모드:

- **Step 구성**: §0(환경) ~ §7(종결)만 사용. Step 9 슬롯(라이브 evaluation, multi-step
  매트릭스) 비움.
- **cap**: $0.50 (정식 슬라이스 cap $3.00의 1/6).
- **부채 격리**: 단일 부채 ID만 처리. 다른 부채 동반 금지.
- **시간 부하**: 1 세션 (~5h) 안에 종결.

## 2. 적용 기준

mini-slice를 적용해도 좋은 작업:

- **도구류 부채** — estimator, classifier, measurement util, dump 스크립트 등.
  production endpoint 영향이 0.
- **단일 책임 + 명확한 KPI** — "에러 ≤ X%", "신규 dump N≥M" 등 단일 숫자로 종결 판정.
- **회귀 영향 ≤ +20** — 정식 슬라이스(예상 +30~50) 절반 이하.

부적합한 작업:

- production endpoint 신설 (Step 9 evaluation 필수).
- 다중 부채 묶음 (단일 격리 원칙 위반).
- LLM 호출 > 10/50 예상 (cap $0.50 위협).

## 3. 회귀 격리 KPI

mini-slice는 회귀 분류기에 **`data-prep`** 카테고리를 추가하여 격리한다.

- **data-prep**: dump 스크립트, 정규화 함수 테스트, raw 자산 빌드. 회귀 ±50%.
- **cost**: estimator, prompt, service. 회귀 ±30%.
- **no-cost**: 문서/테스트만. 회귀 ±50%.

mini-slice 전용 KPI 매트릭스(예: Slice 10 §8)는 11~12건 내외로 정형화한다.

## 4. 첫 사례 — Slice 10 (#48 estimator v3)

- **부채**: #48 한국어 systematic underestimate 60.83% 보정.
- **수단**: Anthropic `count_tokens` API 도입 (무료, ±2% 실측).
- **scope**: input만 보정. output_tokens estimator는 #51로 이연 (Slice 11+).
- **회귀**: 496 → ~510 (+14 예상).
- **비용**: $0 (count_tokens 무료).
- **세션**: 1세션 (~5h).

## 5. 차후 후보

mini-slice로 격리할 만한 부채:

- **#50** — classifier 룰 보강 (rationale_category 분기 정밀화).
- **#51** — output_tokens estimator v3 (Slice 10에서 D-4로 이연).
- **#47** — S13 trigger_case service layer 일부 (도구성 부분만).
- **#52** — messages 보존 정책 수립 (Slice 10 Fallback A에서 발생).

## 6. 종결 체크리스트

mini-slice 종결 시 정식 슬라이스와 동일하게 다음을 갱신한다:

- [ ] `step0_closing.md` (mini-slice는 step0이 전체)
- [ ] `kpi_step0.md` (11건 매트릭스)
- [ ] 회귀 분류 PASS (data-prep + cost + no-cost)
- [ ] DEBT.md 부채 ID close + 신규 부채 등록
- [ ] PROGRESS.md / DECISIONS.md / 적용 시 contracts/
- [ ] git 커밋 메시지: `[slice<N>] mini-slice 종결: #<debt-id>`

## 7. 참조

- `docs/portfolio/coach/COST_POLICY.md` — mini-slice cap $0.50 정책 문서.
- `docs/portfolio/coach/slice10/step_0.md` — 첫 사례 지시서.
- `docs/portfolio/coach/slice10/step0_closing.md` — 첫 사례 종결 보고.
