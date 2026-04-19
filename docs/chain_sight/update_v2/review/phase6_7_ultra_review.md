# Chain Sight v2 Ultra Review — Phase 6+7 종합 리포트

> **리뷰일**: 2026-04-18
> **범위**: CS-6-1 ~ CS-7-3 (9개 커밋, 백엔드 + 프론트엔드)
> **리뷰 관점**: 코드 리뷰 + 아키텍처 리뷰 + 제품 전략 리뷰 + UX 디자인 리뷰

---

## Executive Summary

| 관점 | 점수 | 요약 |
|------|------|------|
| **코드 품질** | 7.5/10 | Cypher 파라미터화 안전, 테스트 54개. CRITICAL 3건 (AllowAny, int() 캐스트, isalpha 검증) |
| **아키텍처** | 7.0/10 | 서비스 분리 우수(9/10). 트랜잭션 안전성(6/10), 에러 전파(5/10) 미흡 |
| **제품 전략** | 8.0/10 | 관계 기반 Watchlist은 진정한 차별화. 자동 모니터링 부재가 최대 리스크 |
| **UX 디자인** | 5.8/10 | 기능적으로 동작. 접근성(3/10), 에러 상태(4/10) 심각하게 부족 |

**종합: 7.1/10** — MVP로서 기능 완성도는 높으나, 프로덕션 릴리즈 전 P0 이슈 7건 수정 필요.

---

## 1. PR Diff 코드 리뷰

### CRITICAL (머지 전 필수 수정) — 3건

| # | 이슈 | 파일 | 설명 |
|---|------|------|------|
| C-1 | `AllowAny` 퍼미션 | `watchlist_views.py:24` | 미인증 사용자가 write 엔드포인트 접근 가능. Neo4j 쿼리 폭주 DoS 벡터. `IsAuthenticatedOrReadOnly` + throttle 필요 |
| C-2 | `int()` 캐스트 미검증 | `watchlist_views.py:156,192` | `{"limit": "abc"}` → 500 에러. try/except 또는 serializer 검증 필요 |
| C-3 | `isAlpha()` ticker 검증 | `serializers/path_watchlist.py:68` | 유니코드 허용 + `BRK.B` 같은 정당한 티커 거부. `re.match(r'^[A-Z]{1,5}$')` 사용 |

### IMPORTANT — 8건

| # | 이슈 | 카테고리 |
|---|------|----------|
| I-1 | 목록 API 페이지네이션 없음 | 확장성 |
| I-2 | edge snapshot N+1 Neo4j 쿼리 (10노드 → 9 round trip) | 성능 |
| I-3 | `_fetch_current_snapshot` ↔ `build_edge_snapshot` 중복 코드 | DRY 위반 |
| I-4 | Neo4j 실패 시 500 에러 (GraphQueryError 미처리) | 에러 처리 |
| I-5 | `_compute_bridge_scores` 빈 입력 가드 없음 | 방어 코딩 |
| I-6 | `formatRelativeTime`에서 `new Date()` — hydration 불일치 | FE 버그 #24 |
| I-7 | WatchButton `isWatched` 리마운트 시 초기화 → 중복 저장 가능 | FE 상태 |
| I-8 | FullPathView edge 라벨 off-by-one (`edge_snapshot[i]` → `[i-1]`) | FE 버그 |

### MINOR — 7건

M-1 `typing.List/Dict` → 내장 타입 (Python 3.12), M-2 f-string logger, M-3 `_score` dict 변이, M-4 PathCard 드롭다운 외부 클릭 미닫힘, M-5 `REL_LABELS` 중복, M-6 cascade delete API 테스트 없음, M-7 custom target_ticker expand 테스트 없음

### 안전 확인

| 영역 | 상태 |
|------|------|
| Cypher 인젝션 | `$param` 파라미터화 사용. **안전** |
| XSS | React 자동 이스케이핑. **안전** |
| Race condition | `run_recheck` 에 `transaction.atomic()`. **허용 수준** |
| URL 라우팅 충돌 | 고정 경로 우선, router 마지막. **정상** |

---

## 2. 엔지니어링 아키텍처 리뷰

### 차원별 점수

| 차원 | 점수 | 핵심 소견 |
|------|------|----------|
| 데이터 흐름 | 8/10 | 단방향 흐름 깔끔. `build_path_signature`만 Neo4j+PostgreSQL 이중 의존 |
| 관심사 분리 | 9/10 | 4개 서비스 분리 우수. DRY 위반 1건 |
| 트랜잭션 안전성 | **6/10** | `create()`, `archive()`, `resolve()`에 `atomic()` 없음 → 부분 실패 시 고아 레코드 |
| Neo4j 쿼리 효율 | 7/10 | N-1 순차 쿼리. UNWIND로 배치 가능 |
| 에러 전파 | **5/10** | **최약점.** `GraphQueryError` 미처리 → raw 500. 기존 `api/views.py`는 이미 처리하는 패턴 |
| 확장성 | 7/10 | AllowAny + 무제한 결과 + prefetch 낭비 |
| 테스트 용이성 | 8/10 | mock 기반 서비스 테스트. 에러 경로 테스트 부족 |
| 엣지 케이스 | 6/10 | isalpha 검증 + int() 캐스트 미검증 |

### 프론트엔드 아키텍처

| 차원 | 점수 | 소견 |
|------|------|------|
| 캐시 무효화 | 8/10 | 키 팩토리 구조 양호. expand/alternatives가 detail 쿼리 무효화 안 함 |
| 상태 관리 | 7/10 | FullPathView에서 서버 상태를 로컬에 복제 — 불일치 위험 |
| 컴포넌트 경계 | 8/10 | 현재 범위에 적절. FullPathView 349줄은 분해 임계점 근접 |

---

## 3. 제품 전략 리뷰 (CEO Mode)

### MVP 스코프 평가: 적절 (약간 좁음)

**강점:**
- Watch → Recheck → Expand → Alternatives 핵심 루프 완성
- 상태 라이프사이클 (watching → active → archived/resolved) 깔끔
- Summary path landmark 압축 (+N) 가변 길이 처리

**약점:**
- **모니터링이 전적으로 수동** — 사용자가 직접 돌아와서 Recheck해야 함 → "Watch"가 아니라 "Bookmark"
- 저장 이유 메모 없음 — 30개 경로 쌓이면 왜 저장했는지 기억 불가
- Portfolio/Thesis Control 연결 없음 — 고립된 기능

### 10-Star 비전

| 별 | 경험 |
|----|------|
| 5 (현재) | 경로 저장, 수동 Recheck, strengthened/weakened 확인 |
| 6 | 자동 일일 Recheck + 푸시 알림 (경로 변화 시) |
| 7 | 경로별 자동 "Chain Thesis" 생성 (관계 변화에 따라 업데이트) |
| 8 | 경로 기반 포트폴리오 시뮬레이션 |
| 9 | 교차 경로 패턴 감지 ("반도체 경로 3개 모두 ASML 약화 — 섹터 신호") |
| 10 | 선제적 경로 발견 — 뉴스/이벤트 전에 영향 받을 체인 자동 추천 |

### 최대 차별화 포인트

> **관계 기반 Watchlist은 소매 투자 도구에서 진정으로 독창적.** 일반 Watchlist은 개별 종목 추적, Path Watchlist은 종목 간 *관계* 추적. 이것이 Stock-Vis의 경쟁 해자.

### 미충족 사용자 니즈

| 우선순위 | 니즈 |
|---------|------|
| **HIGH** | 자동 모니터링 + 알림 |
| **HIGH** | 투자 액션 연결 ("가설에 추가") |
| **HIGH** | 최초 사용자 온보딩 |
| MEDIUM | 티커 기반 경로 검색 |
| MEDIUM | Recheck 이력 타임라인 |

---

## 4. UX 디자인 리뷰

### 차원별 점수

| 차원 | 점수 | 소견 |
|------|------|------|
| 정보 위계 | 7/10 | Summary path 체인 명확. FullPathView에서 Recheck/노드/Expand 동일 시각 무게 |
| 인터랙션 패턴 | 6/10 | 핵심 동작 OK. 노드 탭 Alternatives 발견성 문제. "Expand" 이중 의미 |
| 시각 일관성 | 8/10 | Tailwind 일관 사용. 상태 뱃지 색상 분화 양호 |
| 에러 상태 | **4/10** | 제네릭 토스트만. 재시도 메커니즘 없음 |
| 로딩 상태 | 5/10 | 페이지 로드 스피너만. 카드 스켈레톤, Expand/Alternatives 섹션 로딩 없음 |
| 빈 상태 | 7/10 | Watchlist 빈 상태 CTA 양호 |
| 모바일 반응성 | 6/10 | 노드 체인 가로 스크롤 정상. 4-버튼 액션 바 좁은 화면 줄바꿈 |
| **접근성** | **3/10** | ARIA 라벨 전무. 키보드 네비게이션 없음. 색상 외 상태 표시 없음 |

### 주요 UX 이슈

| 심각도 | 이슈 | 수정 난이도 |
|--------|------|-----------|
| Critical | "Expand" 이중 의미 (PathCard = 상세 열기, FullPathView = API 호출) | 10분 — PathCard "Expand" → "열기"로 변경 |
| Critical | PathCard 드롭다운 외부 클릭 미닫힘 | 30분 — useEffect clickOutside |
| Critical | ARIA 라벨 전무 (접근성 최소 기준 미달) | 1시간 |
| Major | Archive/Resolve 확인 대화상자 없음 (반파괴적 동작) | 30분 |
| Major | PathCard Recheck 결과 미표시 (스피너 후 아무 변화 없음) | 20분 |
| Major | 페이지네이션/무한 스크롤 미구현 (스펙에 명시됨) | 1시간 |
| Minor | `formatRelativeTime` hydration 불일치 위험 | 20분 |
| Minor | 마지막 Recheck 시점 미표시 | 30분 |

---

## 5. P0 수정 사항 (머지 전 필수)

| # | 이슈 | 파일 | 수정 방향 |
|---|------|------|----------|
| **1** | AllowAny 퍼미션 | `watchlist_views.py` | `IsAuthenticatedOrReadOnly` + throttle |
| **2** | int() 캐스트 미검증 | `watchlist_views.py` | try/except ValueError → 400 |
| **3** | isAlpha() 유니코드 허용 | `serializers/path_watchlist.py` | `re.match(r'^[A-Z]{1,5}$')` |
| **4** | GraphQueryError 미처리 → 500 | `watchlist_views.py` | try/except → 503 |
| **5** | create/archive/resolve 트랜잭션 없음 | `watchlist_views.py` | `transaction.atomic()` 래핑 |
| **6** | FullPathView edge 라벨 off-by-one | `FullPathView.tsx` | `edge_snapshot[i]` → `edge_snapshot[i-1]` |
| **7** | "Expand" 이중 의미 | `PathCard.tsx` | "Expand" → "열기" 또는 제거 |

---

## 6. P1 수정 사항 (조기 수정 권장)

| # | 이슈 | 카테고리 |
|---|------|----------|
| 1 | edge snapshot N+1 쿼리 → UNWIND 배치 | 성능 |
| 2 | `_fetch_current_snapshot` 중복 → `build_edge_snapshot` 재사용 | DRY |
| 3 | 목록 API 페이지네이션 | 확장성 |
| 4 | WatchButton `isWatched` 서버 확인 (중복 저장 방지) | 정합성 |
| 5 | PathCard 드롭다운 외부 클릭 닫기 | UX |
| 6 | ARIA 라벨 추가 | 접근성 |
| 7 | Archive/Resolve 확인 대화상자 | UX |
| 8 | PathCard Recheck 결과 토스트 | UX |
| 9 | `formatRelativeTime` hydration 안전 처리 | FE 버그 |
| 10 | 목록 queryset에서 불필요한 `prefetch_related('actions')` 제거 | 성능 |

---

## 7. 전략적 권고 (v1.5+)

| 우선순위 | 기능 | 비즈니스 임팩트 |
|---------|------|---------------|
| **1** | 자동 Recheck + 인앱 알림 (Celery Beat) | Bookmark → 진정한 Watchlist 전환 |
| **2** | Thesis Control 연결 ("가설에 추가" 버튼) | 전략 루프 완성 |
| **3** | 경로 메모/주석 기능 | 사용자 맥락 보존 |
| **4** | 티커 기반 경로 검색 | 사용성 |
| **5** | Recheck 이력 타임라인 | 패턴 인사이트 |

---

## 결론

Chain Sight v2 Path Watchlist은 **독창적인 관계 기반 투자 분석 도구**로서 핵심 기능 구현이 완료되었습니다. 백엔드 54개 테스트 통과, 프론트엔드 TypeScript 컴파일 성공.

**MVP 릴리즈 전 P0 7건 수정이 필수**이며, 특히 보안(AllowAny), 에러 처리(500→503), 프론트엔드 버그(edge off-by-one, Expand 이중 의미)가 최우선입니다.

제품 전략적으로는 **자동 모니터링 + 알림**이 "Watchlist"라는 이름의 약속을 지키기 위한 최우선 후속 과제입니다.
