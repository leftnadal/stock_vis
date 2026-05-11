# Phase B — Keyword Hint Enrichment PR 스펙

> 목표: Keyword 인프라 구축 + source별 collector + 모니터링 + 멀티턴 수정
> 예상: 3-5일
> 선행: Phase A-Hardening 완료, core flow 안정화 확인

---

## 착수 조건

- [ ] Phase A-Hardening 완료
- [ ] fallback 비율 < 15%, 등록 완료율 > 60%
- [ ] normalize/validate가 실 로그 기반으로 안정화됨

---

## PR-8: KeywordCache 인프라

### 파일 생성/변경

| 파일                                           | 내용                                                     |
| ---------------------------------------------- | -------------------------------------------------------- |
| `thesis/models.py`                             | KeywordCache 모델 추가                                   |
| `thesis/admin.py`                              | KeywordCacheAdmin 등록                                   |
| `thesis/services/keyword_cache.py`             | [신규] save_keywords(), collect_from_cache(), SOURCE_TTL |
| `thesis/management/commands/check_keywords.py` | [신규] 종목별 키워드 상태 확인                           |

### KeywordCache 모델

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

### Cache Ops

```python
SOURCE_TTL = {
    'news': timedelta(hours=24),
    'eod': timedelta(hours=24),
    'chain': timedelta(days=7),
}

def save_keywords(target, source, keywords):
    """replace-all: 기존 삭제 후 새로 저장"""
    KeywordCache.objects.filter(target=target, source=source).delete()
    KeywordCache.objects.bulk_create([...])

def collect_from_cache(target, source):
    """freshness cutoff 적용 조회"""
    cutoff = timezone.now() - SOURCE_TTL.get(source, timedelta(hours=24))
    cached = KeywordCache.objects.filter(
        target=target, source=source, updated_at__gte=cutoff
    )[:5]
    if not cached.exists():
        log_event('keyword_stale_or_missing', {...})
    return [ContextKeyword(...) for kw in cached]
```

### check_keywords command

```bash
python manage.py check_keywords 삼성전자
# 출력: source별 키워드 목록 + role + 갱신 시각
```

### 체크리스트

- [ ] KeywordCache 모델 + migration
- [ ] Django Admin 등록 (list_display, list_filter, search_fields)
- [ ] save_keywords() — replace-all 정책
- [ ] collect_from_cache() — source별 TTL cutoff
- [ ] check_keywords management command
- [ ] Admin에서 "삼성전자" 검색 → 키워드 목록 확인 가능

---

## PR-9: News Keyword Collector (첫 번째 source)

News를 가장 먼저 — 데이터 가용성 높고 사용자 체감 효과 큼.

### 파일 생성/변경

| 파일                                         | 내용                                                    |
| -------------------------------------------- | ------------------------------------------------------- |
| `thesis/services/keyword_collectors/news.py` | [신규] extract_news_keywords(), collect_news_keywords() |
| 뉴스 배치 스크립트                           | 키워드 추출 단계 추가                                   |

### 추출 방식: 규칙 기반 (LLM 불필요)

```python
def extract_news_keywords(target: str) -> list[ContextKeyword]:
    """
    News Pipeline의 기존 출력(title + sentiment_label)을 키워드로 변환.
    추가 LLM 호출 없음.
    """
    articles = NewsArticle.objects.filter(
        entities__name__icontains=target,
        published_at__gte=now() - timedelta(days=7),
        relevance_score__gte=0.5,
    ).order_by('-relevance_score')[:3]

    keywords = []
    for article in articles:
        role = {'positive': 'support', 'negative': 'risk', 'neutral': 'theme'}
            .get(article.sentiment_label, 'theme')
        text = article.title[:30]  # 8~30자 규칙
        keywords.append(ContextKeyword(text=text, source='news', role=role))
    return keywords
```

### 배치 통합

```python
# 뉴스 파이프라인 완료 시 키워드 추출 추가
def on_news_pipeline_complete(target):
    try:
        keywords = extract_news_keywords(target)
        save_keywords(target, 'news', keywords)
        log_event('keyword_extracted', {'source': 'news', 'target': target, 'count': len(keywords)})
    except Exception as e:
        log_event('keyword_extraction_failed', {'source': 'news', 'target': target, 'error': str(e)})
```

### 텍스트 규칙 준수 확인

- [ ] 8~30자 명사구
- [ ] role에 맞는 표현 (support=긍정 이벤트, risk=부정 이벤트, theme=중립)
- [ ] 문장형 금지

### 체크리스트

- [ ] extract_news_keywords() 구현
- [ ] 뉴스 배치에 키워드 추출 단계 추가
- [ ] 추출 로그 (keyword_extracted, keyword_extraction_failed)
- [ ] save_keywords() → KeywordCache 저장 확인
- [ ] check_keywords로 news 키워드 확인

---

## PR-10: EOD + Chain Keyword Collectors

### EOD Collector: 규칙 기반 (LLM 불필요)

```python
def extract_eod_keywords(target: str) -> list[ContextKeyword]:
    """숫자 시그널 → 임계값 규칙 → 키워드"""
    signals = load_eod_signals(resolve_ticker(target))
    keywords = []
    rsi = signals.get('rsi_14d')
    if rsi and rsi < 30: keywords.append(ContextKeyword("RSI 과매도 구간", 'eod', 'signal'))
    elif rsi and rsi < 40: keywords.append(ContextKeyword("RSI 과매도 근접", 'eod', 'signal'))
    # ... foreign_net_buy, volume_ratio, price_vs_ma 등
    return keywords
```

### Chain Collector: 템플릿 기반 (LLM 불필요)

```python
CHAIN_TEMPLATES = {
    'SUPPLIES_TO':   lambda t, r: ContextKeyword(f"{r} 공급 관계", 'chain', 'theme'),
    'COMPETES_WITH': lambda t, r: ContextKeyword(f"{r} 경쟁 구도", 'chain', 'risk'),
    'THEMATIC_LINK': lambda t, r: ContextKeyword(f"{r} 테마 연관", 'chain', 'theme'),
    'HELD_BY_ETF':   lambda t, r: ContextKeyword(f"{r} ETF 편입", 'chain', 'support'),
}

def extract_chain_keywords(target: str) -> list[ContextKeyword]:
    """Neo4j 관계 → 템플릿 변환"""
    relations = neo4j_query(target)
    return [CHAIN_TEMPLATES[r['type']](target, r['name'])
            for r in relations if r['type'] in CHAIN_TEMPLATES]
```

### 배치 통합

각 source의 기존 배치(EOD batch, Neo4j 갱신)에 키워드 추출 단계 추가.

### 체크리스트

- [ ] extract_eod_keywords() — 임계값 규칙 5-6개
- [ ] extract_chain_keywords() — 템플릿 4-5개
- [ ] 각 배치에 추출 로그 삽입
- [ ] check_keywords로 eod/chain 키워드 확인
- [ ] source별 경고 기준 확인 (eod 0개 = 주요 종목이면 경고)

---

## PR-11: Keyword Hint 빌더 통합

### 파일 변경

| 파일                                | 변경                                                                             |
| ----------------------------------- | -------------------------------------------------------------------------------- |
| `thesis/services/keyword_hint.py`   | [신규] collect_context_keywords(), dedupe_keywords(), build_keyword_hint_block() |
| `thesis/services/prompt_builder.py` | KEYWORD_HINTS_ENABLED 시 keyword block 추가                                      |
| `thesis/services/thesis_builder.py` | handle_proposal() 로그에 keyword 정보 추가                                       |

### collect_context_keywords()

```python
def collect_context_keywords(target, flags):
    keywords = []
    for source, flag_key in [('chain','CHAIN_KEYWORDS_ENABLED'),
                              ('eod','EOD_KEYWORDS_ENABLED'),
                              ('news','NEWS_KEYWORDS_ENABLED')]:
        if flags.get(flag_key):
            try:
                keywords.extend(collect_from_cache(target, source))
            except Exception as e:
                logger.warning(f"keyword collection failed: {source}: {e}")
    return dedupe_keywords(keywords)[:5]
```

### build_keyword_hint_block()

role별 그룹핑 → `[산업/테마]`, `[찬성 단서]`, `[시장 시그널]`, `[주의 포인트]`

프롬프트 계약:

```
- 사용자의 입력보다 우선하지 마세요.
- 사실로 단정하지 말고, 보조 단서로만 활용하세요.
- 키워드끼리 무리하게 엮지 마세요.
- 찬성 단서와 주의 단서를 함께 반영하세요.
- 노이즈라고 판단되면 과감히 무시하세요.
```

### proposal_generated 로그 확장

```python
'keywords_injected': len(keywords),
'keywords_by_source': {'chain': ..., 'eod': ..., 'news': ...},
'keywords_by_role': {'support': ..., 'risk': ..., 'signal': ..., 'theme': ...},
```

### Feature Flag ON

```python
KEYWORD_HINTS_ENABLED = True
NEWS_KEYWORDS_ENABLED = True   # 첫 번째
EOD_KEYWORDS_ENABLED = True    # 두 번째
CHAIN_KEYWORDS_ENABLED = True  # 세 번째
```

순서: News → EOD → Chain. 하나씩 켜면서 로그로 효과 확인.

### 체크리스트

- [ ] collect_context_keywords() — cache 조회 + 병합
- [ ] dedupe_keywords() — role 우선순위
- [ ] build_keyword_hint_block() — role별 그룹핑
- [ ] prompt_builder에 keyword block 통합
- [ ] proposal_generated 로그에 keyword 정보 추가
- [ ] NEWS flag ON → 키워드 주입 확인
- [ ] EOD flag ON → 키워드 주입 확인
- [ ] CHAIN flag ON → 키워드 주입 확인
- [ ] 키워드 0개 → hint block 미주입 확인
- [ ] source 장애 → silent degrade 확인

---

## PR-12: 멀티턴 수정 대화 (선택적)

Phase B 후반에 여유가 있으면 착수.

### 범위

- [ ] "근거 수정할게요" → Gemini 멀티턴 호출 (history 포함)
- [ ] collected의 premises만 patch (target/direction 변경은 여전히 "다시 만들어줘")
- [ ] MULTI_TURN_EDIT flag ON

### 제한

| 수정 가능           | 여전히 제한        |
| ------------------- | ------------------ |
| premise 문구        | target 변경        |
| indicator 추가/제거 | direction 변경     |
| preset 변경         | thesis_type 대변경 |

---

## Phase B 완료 기준

- [ ] KeywordCache에 news/eod/chain 키워드 저장됨
- [ ] 빌더에서 keyword hint가 프롬프트에 주입됨
- [ ] stale data가 freshness cutoff로 차단됨
- [ ] check_keywords로 종목별 상태 확인 가능
- [ ] Django Admin에서 키워드 조회 가능
- [ ] 로그에 keyword 주입 정보 기록됨
- [ ] keyword ON vs OFF 시 proposal 품질 차이 체감 가능
