# SLICE 20B-F2 STEP 0 — ground truth 실측 기록 (2026-07-31)

base = origin/main `9750b8bc` · worktree `~/worktrees/sv-20bf2` @ `monorepo/sess-20bf2-goal-create-ui`.

## HALT 게이트 = 통과 (진행)
- **HALT 1 (UserGoal 복수 목표 구조?)** → 불성립. `UserGoal.user = OneToOneField`(related_name `portfolio_goal`, models_my.py:117) = **user당 1개**. B안(POST 생성 + 409 중복) 유효.
- **HALT 2 (폼 코어 추출 행위보존 불가?)** → 불성립. `KnobsPanel.tsx` 입력부(:135-169 KNOB_SPECS.map)와 제출부(:172-192)가 JSX상 분리·순수 useState(폼 라이브러리 없음) → 추출 가능. mutation 주입식 전환만 필요.

## 백엔드 실측
- **UserGoal**(models_my.py:101): 필수 `target_return_pct`(Dec 6,2)·`horizon_months`(PositiveInt) / 선택 `risk_tolerance`(choices conservative·moderate·aggressive, 기본 moderate)·`exclusions`(JSON 기본 {}) / 손잡이 5종(aggressiveness_offset·growth_boost·diversification_weight·concentration_limit·exploration_ratio, 전부 기본값+`KNOB_RANGES` 검증). `save()`→`clean()`가 KNOB_RANGES 강제(기본값은 범위 내라 무영향). target/horizon은 필드타입 검증만.
- **REST**(advisory.py): `advisory/knobs/` = @api_view(["GET","PATCH"]). GET → `{available:False}`(목표 부재) / PATCH → 목표 부재 시 **400**("먼저 투자 목표를 설정하세요(admin)", :173-177). `KnobsUpdateSerializer`(:56) = target+손잡이5종 partial(**horizon_months·risk_tolerance 미포함**). `advisory/summary`·`latest`도 부재 시 `{available:False}`.
- **POST 삽입점 결정**: `advisory_knobs` 뷰에 POST method 추가(GET/POST/PATCH, 같은 URL `advisory/knobs/`) = D0 가산. 신규 `GoalCreateSerializer`(target·horizon 필수 + risk 선택; 손잡이 optional 기본값) 필요 — KnobsUpdate는 horizon/risk 미지원이라 재사용 불가. 생성 시 goal 존재하면 409.

## 프론트 실측
- **KnobsPanel.tsx**: 필드 6개(target 1 + 손잡이 5). 순수 useState(:56-65). 제출 `handleSave`(:84) → `useUpdateKnobs`(PATCH `advisory/knobs/`). risk·horizon 필드 없음.
- **/advisory page.tsx**: 목표 부재 진입점 없음. `:57` isEmpty=latest available===false → `:96` 안내 카드("지갑 탭 [지금 진단]"). `:129` `knobsQuery.data?.available && <KnobsPanel>` → available:false면 KnobsPanel 조용히 생략. **온보딩 카드 최적 지점 = :129 else 분기**.
- **hook/service**(useAdvisory.ts·advisoryService.ts): query 키 `advisoryKeys{latest,summary,knobs}`. 생성 후 전환 = `useRunAdvisory` 패턴(latest+summary invalidate)이나, 목표 생성은 **knobs+latest+summary 3개 invalidate** 필요(updateKnobs는 knobs만이라 재사용 불가).
- **타입**(types/advisory.ts): `horizon_months`·`risk_tolerance` 타입 전무 → 신규 `GoalCreateInput` 필요. 손잡이 shape는 `KnobsUpdateInput`(string 직렬화) 재활용하되 required로 좁힘.
- **테스트 패턴**: service/hook `vi.mock` + `QueryClientProvider` 수동 래핑(MSW 아님). 폼 단위=KnobsPanel.test(hook mock), 페이지 통합=AdvisoryPage.test/HoldingModal.buydate.test(service mock).

## 설계 확정 (Part 1/2 근거)
- POST `advisory/knobs/` 생성(409 중복) · PATCH 무변경(400 유지).
- GoalForm 단일 컴포넌트 2모드: 공통 코어=target+손잡이5, create=+horizon+risk+POST, edit=target+손잡이+PATCH(기존). edit는 horizon/risk 변경 불가=스코프 내.
- 온보딩 = `page.tsx:129` knobs available else → 카드 + GoalForm(create). 성공 → 3-key invalidate.
