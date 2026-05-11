# THESIS_CONTROL 가설 빌더 재설계 — 상세 설계 계획서 v4

> 작성일: 2026-03-19
> 개정: v4 — Keyword Monitoring & Cache Ops 추가
> 상태: 설계 확정 → Spike 착수 가능
> 선행 조건: Phase 3 대시보드 PR (FE-PR-7~11) 완료 후 착수
> Phase별 PR 스펙: 별도 파일 참조

---

## 1. 설계 철학

### 핵심 전환

```
AS-IS: "AI가 묻고, 사용자가 답한다" (위자드형)
TO-BE: "사용자가 의견을 던지고, AI가 설계하고, 사용자가 승인한다" (제안형)
```

### 제품 원칙

| 원칙                   | 설명                                              |
| ---------------------- | ------------------------------------------------- |
| One-shot Proposal      | 사용자 한 줄 입력 → AI가 가설 전체를 한 번에 제안 |
| Explainable Auto-setup | 자동 설정된 모든 항목에 "왜" 한 줄 이유 노출      |
| Graceful Fallback      | LLM 실패 시 기존 위자드로 자동 전환               |
| Effortless Flow        | 사용하면서 투자 분석 프레임을 자연스럽게 학습     |

### 1인 개발 생존 규칙

| 원칙                    | 설명                                    |
| ----------------------- | --------------------------------------- |
| Smallest Shippable Unit | Phase A-MVP는 2-3일 내 배포 가능        |
| Validate Before Trust   | LLM 출력은 normalize → validate → merge |
| State Simplicity        | Typed model + 명시적 상태 전이          |
| Observable by Default   | 핵심 이벤트는 초기부터 로그             |

### Enrichment 원칙 (v3~)

| 원칙                               | 설명                                            |
| ---------------------------------- | ----------------------------------------------- |
| Optional Hint, Not Core Dependency | 부가 맥락 없어도 핵심 흐름 정상 동작            |
| Unified Keyword Interface          | Chain/EOD/News → ContextKeyword 단일 인터페이스 |
| Silent Degrade                     | 로드 실패 시 조용히 생략                        |
| Typed Hint > Raw Keyword           | role이 붙은 키워드가 LLM에게 더 잘 먹힌다       |

### Monitoring 원칙 (v4 추가)

| 원칙                                                | 설명                                    |
| --------------------------------------------------- | --------------------------------------- |
| DB를 진실의 원천으로                                | KeywordCache가 운영 기준점, 로그는 보조 |
| 잘못된 힌트보다 힌트 없음이 낫다                    | stale data는 코드 레벨에서 차단         |
| 문제가 보이고, 추적되고, 손으로 고칠 수 있어야 한다 | Admin + command + 로그 조합             |

---

## 2. MVP 범위

### 포함 (Phase A-MVP)

- LLM one-shot proposal (Gemini 1회)
- Indicator DB context (PK 포함)
- 프리셋 (단기/중기/장기)
- confirm → DB 저장
- wizard fallback
- normalize/validate
- 최소 이벤트 로깅

### 제외 → Phase별 도입

| 항목                                                | Phase  |
| --------------------------------------------------- | ------ |
| Keyword Hint Enrichment + KeywordCache + Monitoring | B      |
| 멀티턴 수정 대화                                    | B      |
| Daily Health Report / batch versioning              | B 후반 |
| MiniDashboardPreview                                | C      |
| 스트리밍, Guided Suggestion                         | C      |
| keyword strength / micro-fact / scoring             | C+     |

---

## 3. 전체 아키텍처

```
사용자 입력
    │
    ▼
views.py (mode 분기: llm / wizard)
    │
    ▼
Prompt 조립 (모듈화)
  ├─ [항상] base instruction
  ├─ [항상] type guide
  ├─ [항상] indicator block (PK 포함)
  └─ [Phase B~] keyword hint block
       └─ KeywordCache 조회 (freshness cutoff 적용)
           └─ role별 그룹핑 → 프롬프트 끝에 힌트
    │
    ▼
Gemini 2.5 Flash (Structured Output, 1회)
    │
    ▼
normalize → validate → merge → indicator match
    │
    ▼
프론트엔드 응답
```

### 턴 구조 (MVP)

```
Turn 1: 입력 → Gemini One-shot → 가설 초안 (Gemini 1회)
Turn 2: 프리셋 선택 → 서버 매핑 (Gemini 0회)
Turn 3: 등록 확인 → DB 저장 (Gemini 0회)
```

---

## 4. 백엔드 상세 설계

### 4-1. State Model

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Literal, Optional

class BuilderMode(str, Enum):
    LLM = 'llm'
    WIZARD = 'wizard'

class BuilderPhase(str, Enum):
    PROPOSAL = 'proposal'
    PRESET = 'preset'
    CONFIRM = 'confirm'
    COMPLETE = 'complete'
    FALLBACK = 'fallback'

class FallbackReason(str, Enum):
    LLM_API_ERROR = 'llm_api_error'
    SCHEMA_PARSE_ERROR = 'schema_parse_error'
    VALIDATION_ERROR = 'validation_error'
    STATE_ERROR = 'state_error'

class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str

class PremiseData(BaseModel):
    title: str
    description: str = ''
    recommended_indicators: list[dict] = Field(default_factory=list)

class CollectedData(BaseModel):
    direction: Optional[str] = None
    target: Optional[str] = None
    target_type: Optional[str] = None
    thesis_type: list[str] = Field(default_factory=list)
    premises: list[PremiseData] = Field(default_factory=list)
    timeframe: Optional[str] = None
    magnitude: Optional[str] = None
    sensitivity: Optional[str] = None

class ConversationState(BaseModel):
    conv_id: str
    entry_source: str = 'free_input'
    mode: BuilderMode = BuilderMode.LLM
    phase: BuilderPhase = BuilderPhase.PROPOSAL
    history: list[ChatMessage] = Field(default_factory=list)
    collected: CollectedData = Field(default_factory=CollectedData)
    turn_count: int = 0
    source_news_id: Optional[str] = None
    class Config:
        use_enum_values = True
```

### 4-2. 상태 전이

```
PROPOSAL → PRESET     (confidence != low)
PROPOSAL → PROPOSAL   (confidence: low)
PROPOSAL → FALLBACK   (Gemini 실패)
PRESET   → CONFIRM    (프리셋 선택)
CONFIRM  → COMPLETE   (등록)
CONFIRM  → PROPOSAL   ("다시 만들어줘")
```

**Low-confidence 계약**: message 질문형 1개, buttons 2~3개, needs_preset=false, indicator_recommendations=[], phase PROPOSAL 유지. turn_count≥3이면 가이드 메시지 추가.

### 4-3. thesis_type

내부 `list[str]`, DB는 JSONField. `VALID_THESIS_TYPES = {'earnings','flow','macro','chain','event'}`.

### 4-4. Prompt Builder (모듈화)

```python
def build_system_prompt(state, flags):
    blocks = [build_base_instruction(), build_type_guide_block()]
    if flags.get('INDICATOR_CONTEXT_ENABLED'):
        blocks.append(build_indicator_block())
    if flags.get('KEYWORD_HINTS_ENABLED'):
        keywords = collect_context_keywords(state.collected.target, flags)
        hint = build_keyword_hint_block(keywords)
        if hint:
            blocks.append(hint)
    return "\n\n".join(blocks)
```

### 4-5. Keyword Hint Enrichment

**데이터 구조:**

```python
@dataclass
class ContextKeyword:
    text: str           # 8~30자 명사구
    source: str         # "chain" | "eod" | "news"
    role: str = 'theme' # "support" | "risk" | "signal" | "theme"
```

**텍스트 규칙:**

| role    | 표현 가이드                        | 예시                   |
| ------- | ---------------------------------- | ---------------------- |
| support | 가설 방향을 뒷받침하는 사실/이벤트 | "HBM3E 양산 발표"      |
| risk    | 반대/주의 단서                     | "200일선 하단 위치"    |
| signal  | 시장 반응/수급 변화                | "외국인 순매수 전환"   |
| theme   | 산업/내러티브 배경                 | "엔비디아 공급망 연결" |

- 8~30자 명사구 또는 짧은 구문
- 문장형 금지, 한 줄 키워드
- role에 맞는 톤 유지

**프롬프트 주입 (role별 그룹핑):**

```
## 참고 키워드
아래는 최근 시장 맥락에서 참고할 수 있는 힌트입니다.
- 사용자의 입력보다 우선하지 마세요.
- 사실로 단정하지 말고, 가설의 보조 단서로만 활용하세요.
- 키워드끼리 무리하게 하나의 서사로 엮지 마세요.
- 찬성 단서와 주의 단서를 함께 반영하세요.
- 논리적으로 충돌하거나 노이즈라고 판단되면 과감히 무시하세요.

[산업/테마]
  - 엔비디아 공급망 연결
[찬성 단서]
  - HBM3E 양산 발표
[시장 시그널]
  - 외국인 순매수 전환
[주의 포인트]
  - 200일선 하단 위치
```

### 4-6. KeywordCache 모델 & Cache Ops (v4 추가)

```python
class KeywordCache(models.Model):
    target = models.CharField(max_length=100, db_index=True)
    source = models.CharField(max_length=20)    # chain / eod / news
    text = models.CharField(max_length=200)
    role = models.CharField(max_length=20)      # support / risk / signal / theme
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['target', 'source', 'text']
        indexes = [models.Index(fields=['target', 'source'])]
```

**Cache Lifecycle 정책:**

| 정책      | 규칙                                                      |
| --------- | --------------------------------------------------------- |
| 저장 방식 | replace-all — source+target 단위로 기존 삭제 후 새로 저장 |
| 이유      | partial append는 캐시 누적 오염 위험                      |

```python
def save_keywords(target: str, source: str, keywords: list[ContextKeyword]):
    """replace-all: 해당 target+source의 기존 키워드 삭제 후 새로 저장"""
    KeywordCache.objects.filter(target=target, source=source).delete()
    KeywordCache.objects.bulk_create([
        KeywordCache(target=target, source=kw.source, text=kw.text, role=kw.role)
        for kw in keywords
    ])
```

**Freshness 정책 (source별 TTL):**

| Source | TTL    | 이유                      |
| ------ | ------ | ------------------------- |
| news   | 24시간 | 뉴스는 빠르게 낡음        |
| eod    | 24시간 | 시그널은 매일 갱신        |
| chain  | 7일    | 구조적 관계는 느리게 변함 |

```python
SOURCE_TTL = {
    'news': timedelta(hours=24),
    'eod': timedelta(hours=24),
    'chain': timedelta(days=7),
}

def collect_from_cache(target: str, source: str) -> list[ContextKeyword]:
    """freshness cutoff 적용 — stale data 차단"""
    ttl = SOURCE_TTL.get(source, timedelta(hours=24))
    cutoff = timezone.now() - ttl

    cached = KeywordCache.objects.filter(
        target=target, source=source, updated_at__gte=cutoff
    ).order_by('-updated_at')[:5]

    if not cached.exists():
        log_event('keyword_stale_or_missing', {'target': target, 'source': source})

    return [ContextKeyword(text=kw.text, source=kw.source, role=kw.role) for kw in cached]
```

**Source별 경고 기준 (zero-keyword 판단):**

| Source | 0개 = 경고?           | 이유                                   |
| ------ | --------------------- | -------------------------------------- |
| news   | ⚠️ 약한 경고          | 뉴스 없는 종목은 정상적으로 0개 가능   |
| eod    | 🔴 주요 종목이면 경고 | 유니버스 내 종목은 시그널이 있어야 함  |
| chain  | 🔴 커버 종목이면 경고 | Neo4j에 등록된 종목은 관계가 있어야 함 |

### 4-7. Keyword Monitoring (v4 추가)

**3계층 모니터링:**

```
Layer A. 존재 확인 — 키워드가 추출되고 저장되고 있는가
Layer B. 신선도 확인 — stale data가 차단되고 있는가
Layer C. 주입 확인 — 빌더에서 어떤 키워드가 프롬프트에 들어갔는가
```

**Layer A: 추출 로그 (배치 시점)**

```python
# 각 source 배치에 삽입
def run_keyword_extraction(target, source, extract_fn):
    try:
        keywords = extract_fn(target)
        save_keywords(target, source, keywords)
        log_event('keyword_extracted', {
            'source': source, 'target': target,
            'count': len(keywords),
            'roles': [kw.role for kw in keywords],
        })
    except Exception as e:
        log_event('keyword_extraction_failed', {
            'source': source, 'target': target, 'error': str(e),
        })
```

**Layer B: Freshness 차단 (서빙 시점)**

`collect_from_cache()`에 TTL cutoff 내장 (4-6 참조). stale 시 `keyword_stale_or_missing` 로그.

**Layer C: 주입 로그 (빌더 요청 시점)**

```python
# handle_proposal() 내부
log_event('proposal_generated', {
    'conv_id': state.conv_id,
    'confidence': ...,
    'premise_count': ...,
    'keyword_hints_enabled': flags.get('KEYWORD_HINTS_ENABLED', False),
    'keywords_injected': len(keywords),
    'keywords_by_source': {'chain': ..., 'eod': ..., 'news': ...},
    'keywords_by_role': {'support': ..., 'risk': ..., 'signal': ..., 'theme': ...},
})
```

**운영 도구:**

```bash
# 종목별 키워드 상태 확인
python manage.py check_keywords 삼성전자

# 출력:
# --- chain (4개) ---
#   [theme   ] 엔비디아 공급 관계 (갱신: 2.1시간 전)
#   [risk    ] SK하이닉스 경쟁 구도 (갱신: 2.1시간 전)
# --- eod (3개) ---
#   [signal  ] RSI 과매도 근접 (갱신: 0.5시간 전)
# --- news (0개) ---
#   (없음)
```

**Django Admin:**

```python
@admin.register(KeywordCache)
class KeywordCacheAdmin(admin.ModelAdmin):
    list_display = ['target', 'source', 'role', 'text', 'updated_at']
    list_filter = ['source', 'role']
    search_fields = ['target', 'text']
    ordering = ['-updated_at']
```

### 4-8. Gemini Structured Output 스키마

v3와 동일. thesis_type `list[str]`, indicator `indicator_db_id` 포함.

### 4-9. LLM 후처리 (normalize / validate / merge)

v3와 동일. 3단계 파이프라인.

### 4-10. 핵심 엔진 / 프리셋 / 확인 / Fallback

v3와 동일. process_llm_turn → handle_proposal/preset/confirm/fallback.

### 4-11. Edit Flow (MVP)

"다시 만들어줘"로 제한. partial edit은 Phase B.

---

## 5. 프론트엔드 설계

v3와 동일.

---

## 6. Feature Flag

```python
FEATURE_FLAGS = {
    'LLM_BUILDER_ENABLED': True,
    'INDICATOR_CONTEXT_ENABLED': True,
    'KEYWORD_HINTS_ENABLED': False,
    'CHAIN_KEYWORDS_ENABLED': False,
    'EOD_KEYWORDS_ENABLED': False,
    'NEWS_KEYWORDS_ENABLED': False,
    'MINI_DASHBOARD_PREVIEW': False,
    'GUIDED_SUGGESTION': False,
    'MULTI_TURN_EDIT': False,
    'STREAMING_RESPONSE': False,
}
```

---

## 7. Observability

### 이벤트 카탈로그

| 이벤트                          | Phase | 시점                     |
| ------------------------------- | ----- | ------------------------ |
| `builder_started`               | A     | API 진입                 |
| `proposal_generated`            | A     | 후처리 완료              |
| `llm_parse_failed`              | A     | validate 에러            |
| `fallback_triggered` (+ reason) | A     | wizard 전환              |
| `preset_selected`               | A     | 프리셋 선택              |
| `confirm_clicked`               | A     | 등록 확인                |
| `thesis_created`                | A     | DB 저장                  |
| `keyword_extracted`             | B     | 배치 추출 완료           |
| `keyword_extraction_failed`     | B     | 배치 추출 실패           |
| `keyword_stale_or_missing`      | B     | freshness cutoff 빈 결과 |

### 후순위

- `session_abandoned` — Hardening 이후 배치 분석
- `keyword_confirm_correlation` — Phase B 후반 cohort 비교

---

## 8. 단계별 구현 계획

각 Phase의 상세 PR 스펙은 별도 파일 참조.

| Phase       | 기간  | 핵심 목표                                  | PR 스펙                |
| ----------- | ----- | ------------------------------------------ | ---------------------- |
| Spike       | 1일   | Gemini Structured Output 검증              | —                      |
| A-MVP       | 2-3일 | 기본 경로: 입력→제안→프리셋→등록           | `phase-a-mvp.md`       |
| A-Hardening | 2-3일 | normalize 보강, fallback 안정화, 로그 지표 | `phase-a-hardening.md` |
| B           | 3-5일 | Keyword Enrichment + Cache + Monitoring    | `phase-b-keywords.md`  |
| C           | 이후  | 고급 기능                                  | `phase-c-advanced.md`  |

---

## 9. 리스크

| 리스크                 | 완화                                 |
| ---------------------- | ------------------------------------ |
| Gemini 출력 흔들림     | normalize/validate + fallback        |
| indicator_db_id 오매칭 | PK→문자열 2단계                      |
| State 직렬화 오류      | Pydantic + fallback                  |
| Keyword 과해석         | role 그룹핑 + 프롬프트 계약          |
| Keyword stale data     | source별 TTL cutoff                  |
| Keyword cache 오염     | replace-all 정책                     |
| 프롬프트 토큰 초과     | 목록 크기 모니터링, keyword 5개 제한 |

---

## 부록 A. 지금 / 나중에

| Phase A-MVP                     | Phase B                   | Phase C+          |
| ------------------------------- | ------------------------- | ----------------- |
| ConversationState + ChatMessage | KeywordCache 모델 + Admin | keyword strength  |
| Prompt builder (3 blocks)       | source별 collector        | micro-fact hint   |
| Gemini Structured Output        | build_keyword_hint_block  | keyword scoring   |
| normalize → validate → merge    | freshness TTL             | MiniDashboard     |
| PK 우선 지표 매칭               | replace-all cache 정책    | Guided Suggestion |
| 프리셋 3개                      | 추출/주입 로그            | 스트리밍          |
| confirm → DB 저장               | check_keywords command    | confirm 상관관계  |
| fallback + FallbackReason       | source별 경고 기준        |                   |
| log_event (7 이벤트)            | 멀티턴 수정               |                   |

## 부록 B. 위험 복잡도 Top 5

1. **LLM 출력 흔들림** (★★★★★) — normalize 필수
2. **State 직렬화 왕복** (★★★★☆) — Pydantic model_validate
3. **Edit Flow 상태 폭발** (★★★★☆) — "다시 만들어줘"로 제한
4. **Keyword 과해석** (★★★☆☆) — role + 프롬프트 계약
5. **Keyword stale/오염** (★★★☆☆) — TTL + replace-all

## 부록 C. Keyword 업그레이드 경로

```
Phase B 초반: plain keyword + role, 최대 5개
Phase B 후반: source별 collector 최적화, Daily Health Report
Phase C:      strength 추가, thesis_type 필터링
Phase C+:     micro-fact hint, scoring system
```
