# Peer 프리셋 + 커스텀 시스템 설계서

> 작성일: 2026-03-31
> 상태: 설계 초안

---

## 1. 아키텍처: 하이브리드 (프리셋 + Compute-on-Read)

```
┌─ Stock 영역 (배치, 공용) ──────────────────────────┐
│  PeerPreset              종목당 3~5개 프리셋         │
│  CompanyBenchmarkDelta   프리셋별 배치 계산 결과     │
│  CategorySignal          프리셋별 신호등             │
│  CompanyMetricSnapshot   원천 데이터 (peer 무관)     │
│                                                    │
│  ※ 주 1회 배치가 관리. 사용자 코드가 건드리지 않음   │
└────────────────────────────────────────────────────┘

┌─ User 영역 (개인, 격리) ──────────────────────────┐
│  UserPeerPreference      프리셋 선택 or 커스텀 peer │
│                                                    │
│  ※ User 모델에 종속. Stock 테이블과 무관            │
└────────────────────────────────────────────────────┘

┌─ 계산 영역 (임시) ────────────────────────────────┐
│  Redis 캐시              커스텀 계산 결과 (TTL 1h)  │
│  ※ 커스텀 mode일 때만 사용                         │
└────────────────────────────────────────────────────┘
```

### DB 분리 원칙

- **Stock 영역 ↔ User 영역은 서로 쓰지 않음** → DB 꼬일 일 없음
- Stock 영역: 배치만 쓰기 (write)
- User 영역: 해당 사용자만 쓰기 (write)
- Snapshot(원천 데이터)은 읽기 전용으로 양쪽이 공유

---

## 2. DB 모델

### PeerPreset (Stock 영역, 배치 관리)

```python
class PeerPreset(models.Model):
    symbol = models.ForeignKey('stocks.Stock', on_delete=models.CASCADE, to_field='symbol')
    preset_key = models.CharField(max_length=30)
    display_name = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    peer_symbols = ArrayField(models.CharField(max_length=10))
    peer_count = models.IntegerField(default=0)
    generation_method = models.CharField(max_length=20, choices=[
        ('auto_industry', '업종 자동'),
        ('auto_size', '규모 자동'),
        ('auto_sector', '섹터 자동'),
        ('curated', '큐레이션'),
    ])
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['symbol', 'preset_key']
        db_table = 'validation_peer_preset'
```

### 기존 테이블 확장

```python
# CompanyBenchmarkDelta, PeerMetricBenchmark, CategorySignal에 preset_key 추가
preset_key = models.CharField(max_length=30, default='default', db_index=True)

# unique_together 변경
# CompanyBenchmarkDelta: ['symbol', 'fiscal_year', 'metric_code', 'preset_key']
# CategorySignal: ['symbol', 'category', 'fiscal_year', 'preset_key']
```

### UserPeerPreference (User 영역, 개인 관리)

```python
class UserPeerPreference(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    symbol = models.ForeignKey('stocks.Stock', to_field='symbol', on_delete=models.CASCADE)
    mode = models.CharField(max_length=10, choices=[
        ('preset', '프리셋'),
        ('custom', '커스텀'),
    ], default='preset')
    preset_key = models.CharField(max_length=30, default='default')
    custom_peers = ArrayField(models.CharField(max_length=10), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'symbol']
        db_table = 'validation_user_peer_preference'
```

---

## 3. 프리셋 전략: Sector → Industry → Stock

### 3.1 데이터 현황 (S&P 500)

| 구분 | 수치 |
|------|------|
| 총 sector | 11개 |
| 총 industry | 124개 |
| 종목 1~2개 industry | 62개 (50%) — sector fallback 필수 |
| 종목 3~5개 industry | 33개 |
| 종목 6개 이상 industry | 30개 |

### 3.2 프리셋 유형 (종목당 최대 4개)

```
프리셋 1: "업종 기본" (default) — 항상 생성
  → 현재 BenchmarkCalculator의 select_peers 로직 그대로
  → industry + size bucket, fallback: industry → sector

프리셋 2: "섹터 전체" (sector_all) — 항상 생성
  → 같은 sector 전체 (size 무관)
  → 넓은 비교 관점

프리셋 3: "규모 동종" (size_peers) — mega/large cap만 생성
  → 같은 sector + 같은 size bucket만
  → "비슷한 규모끼리만 비교"

프리셋 4: "테마/비즈니스" (thematic) — 선별 종목만 생성
  → LLM 또는 수동 큐레이션
  → AAPL: "서비스 전환 기업", JPM: "대형 은행"
```

### 3.3 프리셋 생성 규칙

#### 프리셋 1: "업종 기본" (default)

모든 종목에 자동 생성. 현재 로직 그대로.

```
IF industry peer >= 8: industry + adjacent size → "업종+규모"
ELIF industry peer >= 5: industry 전체 → "업종 전체"
ELSE: sector 전체 → "섹터 전체"
```

#### 프리셋 2: "섹터 전체" (sector_all)

모든 종목에 자동 생성.

```
같은 sector의 S&P 500 전체 (size 무관)
예: Technology 82개, Financial Services 67개
```

#### 프리셋 3: "규모 동종" (size_peers)

market_cap bucket이 mega 또는 large인 종목만 생성.

```
같은 sector + 같은 size bucket
예: AAPL(mega) → Technology + mega = [MSFT, GOOGL, META, NVDA, AMZN, ...]
예: CRM(large) → Technology + large = [ADBE, NOW, INTU, WDAY, ...]
```

mid/small은 프리셋 1(default)과 거의 동일하므로 생성하지 않음.

#### 프리셋 4: "테마/비즈니스" (thematic)

선별적으로 생성. 3가지 생성 방식:

**방식 A: Industry 교차 (자동)**
```
같은 sector이지만 다른 industry에서 비즈니스 모델이 유사한 종목
예: AAPL(Consumer Electronics) + MSFT(Software-Infrastructure) → "하드웨어+소프트웨어 통합"
방법: sector 내에서 market_cap 상위 10개 (industry 무관)
```

**방식 B: LLM 큐레이션 (배치)**
```
Gemini에게 "AAPL의 진짜 경쟁사는?" 질문 → peer 목록 생성
주 1회 배치에서 생성, 수동 검증 후 활성화
Phase 2에서 도입
```

**방식 C: 사용자 투표 (장기)**
```
사용자들이 자주 커스텀하는 peer 조합을 분석 → 인기 프리셋으로 승격
Phase 3에서 도입
```

### 3.4 프리셋 생성 행렬

| 조건 | default | sector_all | size_peers | thematic |
|------|---------|------------|------------|----------|
| industry >= 8 종목 | ✅ industry+size | ✅ | mega/large만 | Phase 2 |
| industry 3~7 종목 | ✅ industry | ✅ | mega/large만 | Phase 2 |
| industry 1~2 종목 | ✅ sector fallback | ✅ | mega/large만 | Phase 2 |
| 특수 산업 (금융/REIT) | ✅ + gray 표시 | ✅ + gray | ❌ | ❌ |

### 3.5 저장량 추정

| 프리셋 | 종목 수 | 설명 |
|--------|---------|------|
| default | 503 | 전체 |
| sector_all | 503 | 전체 |
| size_peers | ~200 | mega+large만 |
| thematic | ~50 | Phase 2, 선별 |

총 프리셋: ~1,250건

배치 계산 데이터: 1,250 프리셋 x 34 지표 x 5년 = ~212,500건 (현재 ~85,000건의 2.5배, 충분히 관리 가능)

---

## 4. API 흐름

### 조회

```
GET /api/v1/validation/{symbol}/summary/

1. UserPeerPreference 조회 (user + symbol)
2-A. 없음 or preset/default → 기존 배치 데이터 (현재 코드)
2-B. preset/{key} → 배치 데이터 + preset_key 필터
2-C. custom → Redis 캐시 → 미스면 on-the-fly 계산
```

### 프리셋 목록

```
GET /api/v1/validation/{symbol}/presets/
→ [
    {preset_key: "default", display_name: "업종 기본", peer_count: 24, is_selected: true},
    {preset_key: "sector_all", display_name: "섹터 전체", peer_count: 82},
    {preset_key: "size_peers", display_name: "메가캡 동종", peer_count: 7},
  ]
```

### 프리셋 선택 / 커스텀 설정

```
POST /api/v1/validation/{symbol}/peer-preference/
body: {mode: "preset", preset_key: "size_peers"}
  or: {mode: "custom", custom_peers: ["MSFT", "GOOGL", "META"]}

DELETE /api/v1/validation/{symbol}/peer-preference/
→ default로 리셋
```

---

## 5. UI

```
┌──────────────────────────────────────────────────┐
│ 📊 비교 기준                                      │
│                                                  │
│ [업종 기본 ✓]  [섹터 전체]  [메가캡 동종]          │
│                                                  │
│ [직접 설정...]                                    │
│                                                  │
│ Consumer Electronics 업종 내 유사 규모 24개        │
│ 비교 신뢰도: 높음                                  │
└──────────────────────────────────────────────────┘
```

- 프리셋 탭 클릭 → 즉시 전환 (배치 데이터, DB 조회)
- "직접 설정" → 모달에서 종목 추가/제거 → ~100ms 재계산

---

## 6. 구현 우선순위

```
Phase 1 (현재 완료): default 프리셋 1개 (자동, 배치)
Phase 2: sector_all + size_peers 프리셋 추가 (배치 확장)
Phase 3: UserPeerPreference 모델 + 프리셋 선택 UI
Phase 4: 커스텀 mode (Compute-on-Read) + Redis 캐시
Phase 5: thematic 프리셋 (LLM 큐레이션)
Phase 6: LLM 대화형 peer 조정 (Thesis Control 연동)
```

---

## 7. 성능 목표

| 시나리오 | 응답 시간 | 방법 |
|---------|----------|------|
| 프리셋 조회 (배치 데이터) | < 50ms | DB 인덱스 조회 |
| 프리셋 전환 | < 50ms | DB 인덱스 조회 (preset_key 필터) |
| 커스텀 첫 요청 (캐시 미스) | < 200ms | 벌크 쿼리 1회 + numpy |
| 커스텀 재요청 (캐시 히트) | < 10ms | Redis GET |
| 리셋 | < 50ms | DB DELETE + 캐시 삭제 |
