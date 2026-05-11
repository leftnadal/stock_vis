# Phase C — 고급 기능 PR 스펙

> 목표: 사용자 피드백 축적 후 품질 개선 + 고급 기능
> 예상: 각 항목 1-3일
> 선행: Phase B 완료 + 최소 2주 운영 로그

---

## 착수 조건

- [ ] Phase B 완료, keyword enrichment 안정적 운영 중
- [ ] 최소 50건 이상의 thesis_created 로그 축적
- [ ] keyword ON/OFF 효과 비교 데이터 확보

---

## C-1: Daily Health Report

### 작업

- [ ] `thesis/management/commands/keyword_health_check.py`
- [ ] cron으로 일 1회 실행 (기존 EOD 배치 뒤에 붙이기)

### 리포트 내용

```
source별 최신 갱신 시각
source별 오늘 생성 건수
0-keyword target 비율 (source별 차등 기준)
stale target 상위 10개
```

### 경고 기준

```
chain: 48시간+ 갱신 없음 → ⚠️
eod: 24시간+ 갱신 없음 → 🔴
news: 24시간+ 갱신 없음 → ⚠️ (0개는 정상일 수 있음)
```

---

## C-2: Keyword 효과 분석 (가벼운 cohort 비교)

### 작업

- [ ] builder_stats command 확장

```bash
python manage.py builder_stats --keyword-analysis --days 14
```

### 비교 항목

```
keyword ON vs OFF:
  - 등록 완료율 차이
  - 평균 turn 수 차이

source별:
  - news 키워드 있을 때 vs 없을 때
  - eod 키워드 있을 때 vs 없을 때

injected count별:
  - 0개 / 1~2개 / 3~5개 cohort
```

---

## C-3: Keyword strength 필드

### 작업

- [ ] ContextKeyword에 `strength: str = 'medium'` 추가 (high/medium/low)
- [ ] source별 strength 할당 규칙 정의
- [ ] 프롬프트에 strength 반영 (high → "중요한 참고 단서", low → "약한 힌트")
- [ ] KeywordCache에 strength 컬럼 추가

---

## C-4: thesis_type 기반 keyword 필터링

### 작업

- [ ] `_estimate_thesis_type_from_input()` 사전 추정 함수
- [ ] thesis_type별 keyword role 가중치

```python
# earnings 가설 → support/theme 우선, signal은 보조
# flow 가설 → signal 우선, theme은 보조
```

- [ ] collect_context_keywords()에 thesis_type 필터링 추가

---

## C-5: batch_run_id / extractor_version

### 작업

- [ ] KeywordCache에 `extractor_version`, `batch_run_id` 필드 추가
- [ ] 배치 실행 시 version/run_id 기록
- [ ] Admin에서 "어느 배치에서 생성됐는지" 확인 가능

---

## C-6: MiniDashboardPreview

### 작업

- [ ] 등록 완료 후 미니 대시보드 프리뷰 표시
- [ ] 대시보드 컴포넌트 (ThesisBadge, HealthBar) 미니 버전 재사용
- [ ] MINI_DASHBOARD_PREVIEW flag ON

---

## C-7: Guided Suggestion

### 작업

- [ ] confidence: low 2회 연속 → 대중적 가설 템플릿 4개 제안
- [ ] POPULAR_TEMPLATES 상수 (반도체 회복, 금리 인하, 원화 약세, 고금리 리스크)
- [ ] GUIDED_SUGGESTION flag ON

---

## C-8: 스트리밍 응답 (SSE)

### 작업

- [ ] Gemini stream=True 옵션
- [ ] Django SSE 또는 StreamingHttpResponse
- [ ] FE에서 실시간 타이핑 효과
- [ ] STREAMING_RESPONSE flag ON

---

## C+ (장기)

- [ ] micro-fact hint ("외국인 수급이 최근 매수 우위로 전환됨")
- [ ] keyword scoring system (recency × relevance × type_fit)
- [ ] 과거 가설 패턴 맥락
- [ ] Advanced Mode (전문가용 파라미터 직접 조정)
- [ ] confirm율과 keyword의 정교한 attribution 분석
