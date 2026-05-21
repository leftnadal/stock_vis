# Slice 13 / Part 1.5 종결 보고

**작업 범위**: API 경로 버전 세그먼트 도입 (`/api/coach/` → `/api/v1/coach/`)
**완료 일자**: 2026-05-21
**브랜치**: `slice13` (Part 1 commit `44d5e90` 위)
**비용**: $0 (LLM 호출 0건, 경로 문자열 변경만)
**성격**: Part 1 산출물의 경로 교정 패치 (신규 기능 아님)

---

## 1. 라우팅 사실 확인 결과 (작업 1-1)

| 라우팅 소스 | include prefix | 내부 패턴 예시 | 최종 노출 경로 |
|------------|----------------|----------------|----------------|
| **기존 순수 view** (`portfolio/urls.py`) | `api/` | `coach/e1/garp/` | `/api/coach/e1/garp/` |
| **Part 1 DRF API** (`portfolio/api/urls.py`) — 변경 전 | `api/` | `coach/e1/` | `/api/coach/e1/` |
| **Part 1.5 DRF API** — 변경 후 | `api/v1/` | `coach/e1/` | `/api/v1/coach/e1/` ✨ |

**중복 prefix 없음**: `portfolio/` 세그먼트 없음, `coach/` 중복 없이 깔끔.

---

## 2. 경로 결정 근거

### 채택: `/api/v1/coach/{endpoint}/`

- **v1 버전 세그먼트 도입**: 비가역 계약(API)의 미래 호환성 확보 — v2 도입 시 v1과 병존 가능
- **portfolio(앱명) 세그먼트 미채택**: 코드 구조(Django app 이름)와 URL 계약을 결합하면 앱 리네임/리팩토링 시 URL이 깨짐 → 의도적 분리
- **도메인 그룹핑 확장 여지**: 필요 시 `/api/v1/{domain}/`로 확장 가능 (예: `/api/v1/coach/`, `/api/v1/portfolio/`, `/api/v1/insights/`)

### 거부된 대안
- `/api/portfolio/coach/e1/` — 코드-URL 결합 (앱명 노출)
- `/api/coach/e1/` (Part 1 원안) — 버전 세그먼트 부재로 미래 v2 도입 시 충돌
- `/coach/v1/e1/` — REST 관용 위반 (버전은 도메인보다 앞)

---

## 3. 변경 사항

| 파일 | 변경 |
|------|------|
| `config/urls.py` | include prefix `api/` → **`api/v1/`** (1줄) |
| `portfolio/api/urls.py` | docstring 갱신 + E2~E6 확장 자리 표시 주석 (내부 패턴 무수정) |
| `portfolio/tests/api/test_e1_endpoint.py` | `E1_ENDPOINT = "/api/v1/coach/e1/"` 모듈 상수 추출 + 10건 경로 일괄 갱신 |

### 무수정 보증
- `portfolio/views.py` (legacy view): git diff **0 lines** ✅
- `portfolio/urls.py` (legacy 라우팅): git diff **0 lines** ✅
- `portfolio/api/views.py` (DRF view 로직): 무수정 ✅
- `portfolio/api/serializers.py`: 무수정 ✅
- `run_e1_coach` service: 무수정 ✅

---

## 4. 종결 체크리스트

- [x] 회귀 717 passed — **카운트 불변** ★ (Part 1과 동일)
- [x] IDENTICAL 31/31 PASS
- [x] contract test 10건 PASS (새 경로 `/api/v1/coach/e1/`)
- [x] 기존 순수 view 라우팅 무손상 (git diff 0)
- [x] 최종 노출 경로 = `/api/v1/coach/e1/` 정확히 일치
- [x] 라우팅 사실 확인 결과 보고 + 문서 기록
- [x] 비용 $0

---

## 5. 회귀 카운트 추이

| 단계 | 카운트 | Δ |
|------|--------|---|
| Part 1 종결 | 717 passed | — (baseline) |
| **Part 1.5 종결** | **717 passed** | **0 (불변)** ★ |

> 경로 문자열만 변경 → 테스트 증감 없음. 카운트 불변이 곧 "로직 미변경"의 보증.

---

## 6. E2~E6 후속 Part에 미치는 영향

- 신규 endpoint는 동일 패턴 (`/api/v1/coach/e{N}/`)으로 추가 — `portfolio/api/urls.py`에 1줄씩
- `E1_ENDPOINT` 패턴 답습: 각 contract test에 `E{N}_ENDPOINT` 모듈 상수 추출 권장
- v1 버전 인 forte: API 계약 변경 시 v2 분기 도입 가능 (`config/urls.py`에 `api/v2/` include 추가)

---

**Slice 13 Part 1.5 종결**. Part 2 (E2 endpoint) 진입 대기 — `/api/v1/coach/e2/` 패턴 답습.
