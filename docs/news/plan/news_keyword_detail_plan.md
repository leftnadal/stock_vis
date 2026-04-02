# 뉴스 오늘의 키워드 — 키워드 상세보기 설계 (v2)

> 작성일: 2026-03-26
> 상태: 설계 확정 → 구현 대기
> 위치: 뉴스 페이지 (`/news`) > 오늘의 키워드 섹션

---

## 1. 배경

"오늘의 키워드"에 키워드 뱃지만 표시되어 맥락 파악이 어려움.

### 해결
- 키워드 클릭 → 바텀시트: **LLM 투자 관점 요약 + 관련 뉴스 원문 제목 + 원문 링크**
- 스크래핑 없이 기존 DB + Gemini 활용

---

## 2. UX 흐름

```
[오늘의 키워드]
  반도체 수출 호조 📈  |  유가 급등 📉  |  금리 동결 📰

클릭 → 바텀시트:
┌──────────────────────────────────────────────┐
│  📈 반도체 수출 호조                          │
│                                              │
│  한국 반도체 수출이 3개월 연속 증가세를       │
│  기록하며 삼성전자·SK하이닉스 실적 개선       │
│  기대감이 높아지고 있습니다.                  │
│                                              │
│  관련 뉴스                                   │
│  ┌─ Samsung's HBM3E Production Ramps Up     │
│  │  seekingalpha.com · 2시간 전    원문 ↗   │
│  ├─ SK Hynix Reports Strong Q1 Guidance     │
│  │  reuters.com · 5시간 전         원문 ↗   │
│  └───────────────────────────────────────    │
│                                              │
│  관련 종목: 삼성전자(005930), SK하이닉스      │
│                              [닫기]          │
└──────────────────────────────────────────────┘
```

---

## 3. 핵심 설계 결정

### 3-1. 한국어 키워드 → 영문 기사 매칭

**문제**: 키워드는 한국어, 기사는 영문 → 직접 텍스트 매칭 불가

**해결**: 키워드 생성 시점에 `search_terms_en` 추가

```json
// DailyNewsKeyword.keywords[] 확장
{
  "text": "반도체 수출 호조",
  "sentiment": "positive",
  "related_symbols": ["005930", "000660"],
  "search_terms_en": ["semiconductor export", "HBM", "Samsung chip"],
  "importance": 0.9,
  "reason": "..."
}
```

- 키워드 추출 Gemini 호출 시 스키마만 확장 (추가 비용 없음)
- 실시간 Gemini 변환 불필요

### 3-2. 기사 검색 쿼리 (2단 매칭)

```
Primary: NewsArticle.entities.symbol IN related_symbols
         AND published_at >= target_date - 1day
Secondary: title ICONTAINS any of search_terms_en
         (primary 결과가 부족할 때만)
```

- `related_symbols` JOIN이 정확도 높음 → primary
- `search_terms_en` title 매칭은 보조

### 3-3. API 파라미터

```
GET /api/v1/news/keyword-detail/?date=2026-03-26&index=0
```

- keyword 문자열 대신 `date + index` 사용 (URL 인코딩/불일치 방지)
- `DailyNewsKeyword.objects.get(date=date).keywords[index]`로 정확 조회

### 3-4. Gemini 실패 처리

- `analysis: null` 반환 → 프론트에서 분석 섹션 숨김
- 기사 목록은 항상 표시 (Gemini 무관)
- 낮은 품질 fallback 텍스트보다 깔끔한 UX

### 3-5. 캐싱 + index 안정성

**index 안정성**: keywords 배열은 `update_or_create`로 저장.
- 기본(`force=False`): 하루 1회 → 이후 불변 → index 안정
- `force=True` 재실행 시: 배열 순서 변경 가능

**대응**: 캐시 키에 `updated_at` 타임스탬프 포함
```
news:keyword_detail:{date}:{index}:{updated_at_epoch}
```
재생성 시 `updated_at` 변경 → 캐시 자동 miss → 별도 무효화 불필요

- **Redis**: 위 키 패턴 / TTL 1시간
- **Frontend**: `useRef<Map>` 세션 내 캐시 (date+index 키)

---

## 4. API 설계

### Request

```
GET /api/v1/news/keyword-detail/?date=2026-03-26&index=0
Authorization: Bearer {JWT}
```

### Response (200)

```json
{
  "keyword": "반도체 수출 호조",
  "sentiment": "positive",
  "analysis": "한국 반도체 수출이 3개월 연속 증가세를 기록하며 삼성전자·SK하이닉스 실적 개선 기대감이 높아지고 있습니다.",
  "articles": [
    {
      "id": "uuid",
      "title": "Samsung's HBM3E Production Ramps Up in Q2",
      "source": "seekingalpha.com",
      "url": "https://...",
      "published_at": "2026-03-26T09:00:00Z",
      "sentiment_score": 0.65
    }
  ],
  "related_symbols": ["005930", "000660"]
}
```

### Gemini 프롬프트

```
아래 키워드와 관련된 뉴스 기사들을 투자자 관점에서 종합 분석해줘.

키워드: {keyword.text}
감성: {keyword.sentiment}
관련 종목: {keyword.related_symbols}

관련 기사 제목들:
1. {article1.title}
2. {article2.title}
...

## 출력 (JSON)
{"analysis": "투자 관점에서 이 키워드가 의미하는 바를 2-3문장 (한국어, 100자 이내)"}

기사 내용 기반으로만 분석. 추측 금지.
```

### 에러 처리

| 상황 | 처리 |
|------|------|
| 날짜/인덱스 없음 | 400 Bad Request |
| DailyNewsKeyword 없음 | 404 |
| 관련 기사 0건 | articles: [] + analysis: null |
| Gemini 실패 | analysis: null (기사 목록만 표시) |

---

## 5. 변경 파일

### Backend

| 파일 | 변경 | 내용 |
|------|------|------|
| `news/services/keyword_extractor.py` | 수정 | Gemini 프롬프트에 `search_terms_en` 추가 |
| `news/api/views.py` | 수정 | NewsViewSet에 `@action keyword_detail` 추가 (~70줄) |

### Frontend

| 파일 | 변경 | 내용 |
|------|------|------|
| `frontend/types/news.ts` | 수정 | DailyKeyword + KeywordDetailResponse 타입 |
| `frontend/services/newsService.ts` | 수정 | getKeywordDetail(date, index) |
| `frontend/components/news/KeywordBadge.tsx` | 수정 | onClick prop 추가 |
| `frontend/components/news/KeywordDetailSheet.tsx` | **신규** | 바텀시트 (~100줄) |
| `frontend/components/news/DailyKeywordCard.tsx` | 수정 | 시트 상태 + 렌더링 |

---

## 6. 구현 순서

1. `keyword_extractor.py` — search_terms_en 프롬프트 확장
2. `views.py` — keyword_detail @action → curl 테스트
3. Frontend 타입 + 서비스
4. `KeywordDetailSheet` 컴포넌트
5. `KeywordBadge` + `DailyKeywordCard` 연동
6. 브라우저 테스트

---

## 7. 검증

- [ ] keyword_extractor: search_terms_en 포함 키워드 생성
- [ ] curl: keyword-detail API → 분석 + 기사 목록 반환
- [ ] Redis 캐시 동작 (2번째 호출 즉시)
- [ ] 키워드 뱃지 클릭 → 바텀시트 열림
- [ ] 분석 + 기사 제목 + 원문 링크 표시
- [ ] Gemini 실패 → 분석 숨김, 기사만 표시
- [ ] 관련 기사 0건 → 적절한 빈 상태 표시
- [ ] TypeScript 타입 체크 통과
