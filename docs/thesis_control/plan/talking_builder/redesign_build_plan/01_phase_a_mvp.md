# Phase A-MVP — PR 스펙

> 목표: "삼성전자 반등" → 3턴 → 가설 등록. 이것만 되면 배포.
> 예상: 구현 2-3일 + 안정화 1-2일
> 선행: Spike 완료 (Gemini Structured Output 검증)

---

## Spike (착수 전 1일)

Gemini Playground에서 반드시 먼저 검증:

- [ ] System Prompt + Indicator DB 목록(id 포함) + Structured Output 스키마 테스트
- [ ] 5-6개 시나리오 입력: "삼성전자 반등", "나스닥 하락", "원화 약세", "비만치료제", "금리 인하", "주식"
- [ ] indicator_db_id 반환 정확도 측정 (목표: 70%+)
- [ ] 응답 시간 측정 (목표: 2초 이내)
- [ ] 실제 Indicator 테이블 레코드 수 확인 → 프롬프트 토큰 추정
- [ ] thesis_type이 list[str]로 반환되는지 확인 (문자열이면 normalize에서 변환)
- [ ] confidence 필드가 정상 반환되는지 확인

**Spike 결과에 따른 판단:**

- indicator_db_id 정확도 50% 미만 → 프롬프트 조정 or PK 방식 재검토
- 응답 시간 3초+ → 프롬프트 길이 축소 검토
- Indicator 100개+ → 카테고리별 상위 N개 필터링 추가

---

## PR-1: 백엔드 기반 구조

### 파일 생성

| 파일                                 | 내용                                                                                                  |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `thesis/services/builder_state.py`   | ConversationState, ChatMessage, BuilderPhase, BuilderMode, FallbackReason, CollectedData, PremiseData |
| `thesis/services/prompt_builder.py`  | build_base_instruction(), build_type_guide_block(), build_indicator_block()                           |
| `thesis/services/llm_postprocess.py` | normalize_llm_output(), validate_llm_output(), merge_to_collected()                                   |
| `thesis/services/builder_events.py`  | log_event() + 이벤트 카탈로그 상수                                                                    |
| `thesis/feature_flags.py`            | FEATURE_FLAGS dict + get_feature_flags()                                                              |

### 구현 상세

**builder_state.py:**

```
- BuilderMode: LLM / WIZARD
- BuilderPhase: PROPOSAL / PRESET / CONFIRM / COMPLETE / FALLBACK
- FallbackReason: LLM_API_ERROR / SCHEMA_PARSE_ERROR / VALIDATION_ERROR / STATE_ERROR
- ChatMessage: role (Literal['user','assistant']) + content
- PremiseData: title + description + recommended_indicators (list[dict])
- CollectedData: direction, target, target_type, thesis_type (list[str]),
                 premises, timeframe, magnitude, sensitivity
- ConversationState: conv_id, entry_source, mode, phase, history (list[ChatMessage]),
                     collected, turn_count, source_news_id
- VALID_THESIS_TYPES = {'earnings','flow','macro','chain','event'}
- MONITORING_PRESETS = {short/medium/long}
```

**prompt_builder.py:**

```
- build_base_instruction(): 역할 + 출력 규칙 (한국어, One-shot, 버튼 3-4개)
- build_type_guide_block(): 5개 타입 가이드 (earnings/flow/macro/chain/event)
- build_indicator_block(): Indicator DB에서 PK 포함 목록 생성
  - 카테고리별 "지표명(id:N)" 형태
  - "indicator_db_id에 id 숫자 포함" 지시
- build_system_prompt(): flags 기반 블록 조합
```

**llm_postprocess.py:**

```
- normalize_llm_output():
  - thesis_type str → list 변환 ("earnings+chain" → ["earnings","chain"])
  - premise title 중복 제거
  - (Hardening에서 추가: direction 정규화, indicator_db_id DB 확인)

- validate_llm_output() → (validated, warnings, errors):
  - direction 필수 확인
  - target 필수 확인
  - premises 최소 1개 확인
  - premises 5개 초과 시 자름 (warning)
  - errors 있으면 fallback 트리거

- merge_to_collected(): validated update → CollectedData 필드별 병합
```

**builder_events.py:**

```
- log_event(name, data): 구조화된 JSON 로그
  logger.info(json.dumps({'event': name, 'timestamp': ..., 'data': data}))
```

**feature_flags.py:**

```
- LLM_BUILDER_ENABLED: True
- INDICATOR_CONTEXT_ENABLED: True
- 나머지 전부 False
```

### 체크리스트

- [ ] builder_state.py — 모든 모델 정의 + model_dump/model_validate 테스트
- [ ] prompt_builder.py — 3개 블록 함수 + 조합 함수
- [ ] llm_postprocess.py — normalize + validate + merge
- [ ] builder_events.py — log_event
- [ ] feature_flags.py — 기본 플래그
- [ ] Gemini 호출 함수 (call_gemini) + Structured Output 스키마

---

## PR-2: 백엔드 로직

### 파일 변경

| 파일                                   | 변경                                                                          |
| -------------------------------------- | ----------------------------------------------------------------------------- |
| `thesis/services/thesis_builder.py`    | process_llm_turn(), handle_proposal(), handle_preset(), handle_confirm() 추가 |
| `thesis/services/indicator_matcher.py` | match_indicators() — PK 우선 2단계                                            |
| `thesis/views.py`                      | builder_start, builder_respond에 mode 분기 추가                               |

### 구현 상세

**process_llm_turn():**

```
1. history.append(ChatMessage)
2. turn_count++
3. phase 기반 분기:
   - PRESET → detect_preset() → handle_preset() or reprompt
   - CONFIRM → is_confirm_intent() → handle_confirm() or is_restart_intent() → 초기화
   - PROPOSAL → handle_proposal()
```

**handle_proposal():**

```
1. build_system_prompt(state, flags)
2. call_gemini(prompt, history)
   - None → fallback(LLM_API_ERROR)
3. normalize → validate
   - errors → fallback(VALIDATION_ERROR)
4. merge_to_collected
5. match_indicators (PK → 문자열 2단계)
6. history.append(ChatMessage)
7. confidence → phase 전이 (low→PROPOSAL, else→PRESET)
8. log_event('proposal_generated')
9. 응답 반환
```

**handle_preset():**

```
1. MONITORING_PRESETS에서 매핑
2. collected에 timeframe/magnitude/sensitivity 설정
3. phase → CONFIRM
4. log_event('preset_selected')
5. 확인 메시지 + [등록/다시 만들기] 버튼
```

**handle_confirm():**

```
1. log_event('confirm_clicked')
2. validate_collected_for_save() — direction, target, premises, timeframe 필수
3. create_thesis_from_llm() — 기존 _create_thesis() 래핑
4. phase → COMPLETE
5. log_event('thesis_created')
```

**match_indicators():**

```
1순위: indicator_db_id → Indicator.objects.get(id=db_id, is_active=True)
2순위: match_indicators_for_premise(premise_text, indicator_hint, target)
결과: {premise_title, indicator, indicator_name, why, signal_type, auto_matched, match_method}
```

**fallback_to_wizard(state, user_input, reason):**

```
1. mode → WIZARD, phase → FALLBACK
2. log_event('fallback_triggered', reason=reason.value)
3. [단계별로 진행 / 다시 시도] 버튼
```

**views.py:**

```
builder_start: ConversationState 생성 → log_event('builder_started') → process_llm_turn()
builder_respond: model_validate(raw_state) → mode 분기 (llm/wizard)
```

### 체크리스트

- [ ] process_llm_turn — phase 분기 동작
- [ ] handle_proposal — Gemini 호출 → normalize → validate → merge → match
- [ ] handle_preset — 3개 프리셋 매핑
- [ ] handle_confirm — validate → DB 저장
- [ ] fallback_to_wizard — FallbackReason 포함
- [ ] match_indicators — PK 우선 2단계
- [ ] views.py — mode 분기
- [ ] 기존 wizard 모드 정상 동작 확인

---

## PR-3: 프론트엔드

### 파일 변경/생성

| 파일                                            | 내용                                                                                     |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `frontend/lib/thesis/types.ts`                  | BuilderPhase, ConversationState, ConversationResponse, IndicatorRecommendation 타입 확장 |
| `frontend/app/thesis/new/page.tsx`              | mode='llm' 분기, phase 기반 UI                                                           |
| `frontend/components/thesis/PresetSelector.tsx` | [신규] 3개 프리셋 카드                                                                   |
| `frontend/components/thesis/IndicatorCard.tsx`  | [신규] 지표 + why + auto_matched 표시                                                    |
| `frontend/lib/thesis/mock.ts`                   | LLM 모드 Mock 2개 (기본 + fallback)                                                      |

### 구현 상세

**타입:**

```typescript
type BuilderPhase = "proposal" | "preset" | "confirm" | "complete" | "fallback";

interface ConversationResponse {
	message: string;
	buttons: { id: string; label: string }[];
	conversation_state: ConversationState; // 그대로 에코
	confidence?: "high" | "medium" | "low";
	indicator_recommendations?: IndicatorRecommendation[];
	needs_preset?: boolean;
	is_complete?: boolean;
	created_thesis?: { thesis_id: number; title: string; dashboard_url: string };
}
```

**UI 분기:**

```
phase === 'proposal' → ChatArea + TextInput + ButtonGroup
phase === 'preset'   → ChatArea + PresetSelector + TextInput
phase === 'confirm'  → ChatArea + ButtonGroup ([등록/다시 만들기])
phase === 'complete' → ChatArea + [대시보드/새 가설] 버튼
phase === 'fallback' → 기존 wizard UI
```

**PresetSelector:**

- 3개 카드 (⚡ 단기 / 📈 중기 / 🔭 장기)
- 카드 클릭 → 해당 프리셋 키워드를 user_input으로 전송

**IndicatorCard:**

- 지표명 + why 한 줄
- auto_matched: true → ✅ / false → ⚠️ (수동 매핑 필요 안내)
- signal_type 뱃지 (leading / coincident / lagging)

**Mock 2개:**

1. 기본 경로: "삼성전자 반등" → proposal → preset → confirm → complete
2. fallback: proposal 실패 → wizard 전환

### 체크리스트

- [ ] 타입 확장 — phase, confidence, indicator_recommendations
- [ ] TextInput 항상 표시
- [ ] PresetSelector 컴포넌트 — phase=preset 일 때만 렌더
- [ ] IndicatorCard 컴포넌트 — why 시각적 강조
- [ ] phase 기반 UI 분기
- [ ] Mock 2개 (기본 + fallback)
- [ ] USE_MOCK && mode === 'llm' 분기

---

## 검증 (PR 전체 통합 후)

- [ ] "삼성전자 2분기 반등" → 3턴 이내 등록 완료
- [ ] "원화 약세" 모호 입력 → confidence: low → 질문 모드 확인
- [ ] "주식" 극도 모호 → 가이드 메시지 확인 (turn_count≥3)
- [ ] Gemini 실패 (네트워크 차단) → wizard fallback 확인
- [ ] validate 에러 (스키마 불일치) → fallback 확인
- [ ] 기존 wizard 모드 정상 동작 확인
- [ ] indicator_db_id 매칭률 측정
- [ ] 이벤트 로그 7개 모두 정상 기록 확인
