# Phase A-Hardening — PR 스펙

> 목표: MVP 배포 후 실 사용 로그 기반 안정화
> 예상: 2-3일
> 선행: Phase A-MVP 배포 완료 + 최소 2-3일 운영 로그 축적

---

## 착수 조건

- [ ] Phase A-MVP가 배포되어 실 사용자 트래픽을 받고 있음
- [ ] builder_started / proposal_generated / thesis_created 로그가 축적됨
- [ ] 최소 10건 이상의 proposal_generated 로그 확보

---

## PR-4: normalize/validate 보강

실 로그에서 발견된 Gemini 출력 패턴을 normalize에 추가.

### 작업

- [ ] Gemini 실제 응답 로그 수집 → 흔들림 패턴 목록화
- [ ] normalize 보강 (로그 기반):
  - direction 대소문자 혼용 패턴 → 정규화 추가 (필요 시)
  - indicator_db_id 존재하지만 DB에 없는 경우 → null로 교정
  - premise title 공백/특수문자 정리
  - thesis_type에 VALID 목록 외 값 → 제거
- [ ] validate 보강:
  - direction/message 방향 불일치 감지 (간단한 키워드 휴리스틱)
  - indicator 0개인 premise → warning 로그
- [ ] 새로 발견된 패턴마다 normalize/validate에 케이스 추가

### 판단 기준

```
로그에서 이런 패턴이 보이면 normalize에 추가:
- llm_parse_failed 이벤트의 errors 필드
- proposal_generated의 warnings 필드
- fallback_triggered의 reason이 VALIDATION_ERROR인 경우
```

---

## PR-5: fallback 안정화

### 작업

- [ ] LLM ↔ wizard 모드 전환 왕복 테스트
  - LLM 시작 → fallback → wizard 완료 → 정상 저장 확인
  - LLM 시작 → fallback → "다시 시도" → LLM 재시도 → 정상 동작 확인
- [ ] ConversationState 직렬화/역직렬화 edge case
  - 빈 history로 시작 시
  - history가 100개 넘을 때 (turn_count 초과 방어)
  - mode 변경 후 state 구조 호환성
  - FE에서 잘못된 JSON이 올 때 → model_validate 실패 → 적절한 에러 응답
- [ ] fallback 비율 측정: `fallback_triggered / builder_started`
  - 10% 이상이면 프롬프트 또는 스키마 조정 필요

---

## PR-6: 로그 기반 지표 추출

### 작업

- [ ] 지표 추출 스크립트 (management command 또는 간단한 Python 스크립트)

```bash
# 사용 예:
python manage.py builder_stats --days 7
```

출력:

```
=== Builder Stats (최근 7일) ===
builder_started:       42
proposal_generated:    38
  - confidence high:   28
  - confidence medium: 7
  - confidence low:    3
llm_parse_failed:      4  (9.5%)
fallback_triggered:    4  (9.5%)
  - llm_api_error:     1
  - validation_error:  3
preset_selected:       34
confirm_clicked:       31
thesis_created:        31 (등록 완료율: 73.8%)
avg_turn_count:        2.8
auto_matched_ratio:    78.2%
```

- [ ] 주간 단위로 한 번 실행하여 추세 확인
- [ ] 비정상 지표 기준 정의:
  - fallback 비율 > 15% → 프롬프트/스키마 점검
  - 등록 완료율 < 50% → UX 또는 제안 품질 점검
  - auto_matched < 50% → Indicator DB 목록 또는 프롬프트 점검

---

## PR-7: FE 에러 바운더리

### 작업

- [ ] conversation_state 파싱 실패 시 graceful error 표시 (빈 화면 방지)
- [ ] Gemini 응답 지연 시 로딩 UI (2초 이상)
- [ ] fallback 전환 시 기존 wizard UI로 자연스럽게 전환
- [ ] "다시 만들어줘" 후 이전 히스토리 표시 여부 결정 (초기화 vs 유지)

---

## 완료 기준

- [ ] fallback 비율 < 15%
- [ ] 등록 완료율 > 60%
- [ ] normalize/validate가 실 로그 기반으로 보강됨
- [ ] builder_stats command로 핵심 지표 추출 가능
- [ ] LLM ↔ wizard 전환이 안정적
