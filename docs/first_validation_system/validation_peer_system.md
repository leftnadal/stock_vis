# Peer 프리셋 + 커스텀 시스템 — 최종 설계서 v2

> 작성일: 2026-03-31
> 상태: 최종안 (GPT/Gemini 피드백 반영)

---

## 0. 핵심 설계 원칙

**"프리셋은 종목 묶음이 아니라, 해석 프레임(Interpretive Frame)이다."**

- 프리셋 개수를 늘리는 것이 목적이 아님
- 각 프리셋은 **서로 다른 분석 질문**에 답해야 함
- 사용자가 "왜 이 종목들이 묶였지?" 묻기 전에 이유를 먼저 보여줌

---

## 1. 아키텍처: 하이브리드 (프리셋 + Compute-on-Read)

```
┌─ Stock 영역 (배치, 공용) ──────────────────────────┐
│  PeerPreset              종목당 2~6개 프리셋         │
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

### DB 분리 원칙 (변경 없음)

- Stock 영역 ↔ User 영역은 서로 쓰지 않음
- Stock 영역: 배치만 write
- User 영역: 해당 사용자만 write
- CompanyMetricSnapshot(원천 데이터)은 읽기 전용으로 양쪽이 공유

---

## 2. 프리셋 최종 목록 (6개 + custom)

각 프리셋이 답하는 **분석 질문**이 겹치지 않도록 설계.

### 2.1 프리셋 정의

| #   | preset_key    | 디스플레이 이름      | 분석 질문                                | Phase      |
| --- | ------------- | -------------------- | ---------------------------------------- | ---------- |
| 1   | `default`     | 업종 표준            | "내 업종·체급 기준으로 평균 수준인가?"   | Phase 1 ✅ |
| 2   | `sector_all`  | 섹터 전체            | "섹터 전체에서 내 상대 위치는?"          | Phase 2    |
| 3   | `size_peers`  | 체급 동종            | "비슷한 규모끼리만 비교하면?"            | Phase 2    |
| 4   | `quality_top` | 우량주 비교          | "1등급 기업들 사이에서도 경쟁력 있는가?" | Phase 3    |
| 5   | `lifecycle`   | 성장단계 유사        | "같은 성장 단계의 기업과 효율성 비교"    | Phase 3    |
| 6   | `thematic`    | 비즈니스 테마 (beta) | "섹터 달라도 사업모델이 비슷한 기업"     | Phase 5    |
| -   | `custom`      | 직접 설정            | "내가 생각하는 진짜 라이벌"              | Phase 4    |

### 2.2 제외/보류한 것들

| 후보                           | 판단                          | 이유                                                                                           |
| ------------------------------ | ----------------------------- | ---------------------------------------------------------------------------------------------- |
| 자본집약도 (capital_intensity) | Phase 3 이후 재검토           | quality_top, lifecycle과 축이 일부 겹침. 단독 프리셋보다는 quality_top 내부 변형으로 흡수 가능 |
| 섹터 내 시총 상위 10개         | 사용자 노출 프리셋으로 부적합 | 사업모델 혼재 위험. thematic 후보 생성기의 내부 input으로만 활용                               |
| 사용자 투표 기반               | Phase 6 이후                  | 충분한 사용자 데이터 축적 필요                                                                 |

---

## 3. 프리셋별 생성 규칙

### 프리셋 1: `default` (업종 표준) — 모든 종목

현재 BenchmarkCalculator.select_peers 로직 그대로.

```
IF industry peers >= 8: industry + adjacent size bucket
ELIF industry peers >= 5: industry 전체
ELSE: sector fallback
```

- logic_summary 예: "Consumer Electronics 업종 내 유사 시가총액 24개"

### 프리셋 2: `sector_all` (섹터 전체) — 모든 종목

```
같은 sector의 S&P 500 전체 (size 무관)
```

- logic_summary 예: "Technology 섹터 전체 82개와 비교"
- 참고: sector 평균은 outlier 영향이 크므로 median 사용 권장

### 프리셋 3: `size_peers` (체급 동종) — mega/large cap만

```
같은 sector + 같은 size bucket
```

- 생성 조건: market_cap bucket이 mega 또는 large인 종목만
- mid/small은 default와 거의 동일하므로 생성 안 함
- logic_summary 예: "대형 기술주(mega cap) 7개와 비교"

### 프리셋 4: `quality_top` (우량주 비교) — sector 내 충분한 종목 있을 때

```
같은 sector 내에서 아래 지표 상위 퍼센타일 종목 추출:
  - ROIC (핵심)
  - Operating Margin
  - FCF Margin

방법: 3개 지표의 percentile rank 평균 → 상위 20% 추출
최소 peer 5개 이상이어야 프리셋 생성
```

- 생성 조건: sector 내 종목 >= 25개 (상위 20% = 5개 이상)
- logic_summary 예: "Technology 섹터 내 수익성 상위 15개와 비교"
- ⚠️ 금융/REIT: ROIC 대신 ROE 사용, Operating Margin 대신 Efficiency Ratio 사용

### 프리셋 5: `lifecycle` (성장단계 유사) — sector 내 충분한 데이터 있을 때

```
같은 sector 내에서 성장 단계 유사 그룹:
  기준 지표:
    - Revenue CAGR 3Y (핵심)
    - EBIT 흑자 여부 (보조)
    - FCF 흑자 여부 (보조)

그룹핑:
  고성장: Revenue CAGR 3Y > sector 75th percentile + EBIT 흑/적 무관
  안정형: Revenue CAGR 3Y = sector 25th~75th + EBIT 흑자
  저성장/턴어라운드: 나머지

해당 종목이 속하는 그룹의 종목들이 peer가 됨
최소 peer 5개 이상이어야 프리셋 생성
```

- logic_summary 예: "고성장 기술주 12개와 비교 (매출 CAGR 상위 그룹)"
- ⚠️ Revenue CAGR 데이터 없는 종목은 프리셋 미생성

### 프리셋 6: `thematic` (비즈니스 테마) — Phase 5, 선별

```
Phase 5에서 LLM(Gemini) 큐레이션으로 생성
수동 검증 후 활성화
UI에서 "(beta)" 표시
```

- 초기에는 사용자 노출 프리셋으로 바로 승격하지 않음
- "추천 비교군 (beta)" 형태로 보조 제공

---

## 4. DB 모델

### PeerPreset (Stock 영역, 배치 관리)

```python
class PeerPreset(models.Model):
    symbol = models.ForeignKey(
        'stocks.Stock', on_delete=models.CASCADE, to_field='symbol'
    )
    preset_key = models.CharField(max_length=30)
    # "업종 표준", "섹터 전체" 등
    display_name = models.CharField(max_length=50)
    # 사용자에게 노출할 생성 근거 한 줄 요약
    # 예: "Consumer Electronics 업종 내 유사 시가총액 24개"
    logic_summary = models.CharField(max_length=200)
    peer_symbols = ArrayField(models.CharField(max_length=10))
    peer_count = models.IntegerField(default=0)
    generation_method = models.CharField(max_length=20, choices=[
        ('auto_industry', '업종 자동'),
        ('auto_sector', '섹터 자동'),
        ('auto_size', '규모 자동'),
        ('auto_quality', '품질 자동'),
        ('auto_lifecycle', '성장단계 자동'),
        ('curated', '큐레이션'),
    ])
    # 비교 신뢰도 점수 (0.0~1.0)
    # peer_count, 업종 순도, 지표 커버리지 등으로 배치에서 자동 계산
    confidence_score = models.FloatField(default=1.0)
    is_default = models.BooleanField(default=False)
    # 비활성 프리셋 (데이터 부족 등) — UI에서 gray-out 또는 숨김
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['symbol', 'preset_key']
        db_table = 'validation_peer_preset'
```

### 기존 테이블 확장 (변경 없음, 원안 유지)

```python
# CompanyBenchmarkDelta, PeerMetricBenchmark, CategorySignal에 preset_key 추가
preset_key = models.CharField(max_length=30, default='default', db_index=True)

# unique_together 변경
# CompanyBenchmarkDelta: ['symbol', 'fiscal_year', 'metric_code', 'preset_key']
# CategorySignal: ['symbol', 'category', 'fiscal_year', 'preset_key']
```

### UserPeerPreference (User 영역, 개인 관리) — 변경 없음

```python
class UserPeerPreference(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    symbol = models.ForeignKey(
        'stocks.Stock', to_field='symbol', on_delete=models.CASCADE
    )
    mode = models.CharField(max_length=10, choices=[
        ('preset', '프리셋'),
        ('custom', '커스텀'),
    ], default='preset')
    preset_key = models.CharField(max_length=30, default='default')
    custom_peers = ArrayField(
        models.CharField(max_length=10), default=list, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'symbol']
        db_table = 'validation_user_peer_preference'
```

---

## 5. confidence_score 계산 기준

배치에서 프리셋 생성 시 자동 계산. 사용자에게는 "높음/보통/낮음"으로 변환.

```python
def calculate_confidence(preset) -> float:
    score = 1.0

    # 1. peer 수 패널티
    if preset.peer_count < 5:
        score -= 0.3
    elif preset.peer_count < 10:
        score -= 0.1

    # 2. 업종 순도 (같은 industry 비율)
    same_industry_ratio = count_same_industry(preset) / preset.peer_count
    if same_industry_ratio < 0.5:
        score -= 0.2

    # 3. 지표 커버리지 (peer들의 데이터 완성도)
    coverage = avg_metric_coverage(preset.peer_symbols)
    if coverage < 0.7:
        score -= 0.2

    # 4. 특수 산업 패널티 (금융, REIT, 유틸리티)
    if is_special_sector(preset.symbol):
        score -= 0.15

    return max(0.0, min(1.0, score))

# UI 변환
# >= 0.7: "높음" (기본 표시)
# 0.4~0.7: "보통" (주의 문구)
# < 0.4: "낮음" (gray-out, 프리셋 비활성 후보)
```

---

## 6. 프리셋 생성 행렬

| 조건                  | default            | sector_all       | size_peers   | quality_top    | lifecycle      |
| --------------------- | ------------------ | ---------------- | ------------ | -------------- | -------------- |
| industry >= 8 종목    | ✅ industry+size   | ✅               | mega/large만 | sector>=25     | sector>=25     |
| industry 3~7 종목     | ✅ industry        | ✅               | mega/large만 | sector>=25     | sector>=25     |
| industry 1~2 종목     | ✅ sector fallback | ✅               | mega/large만 | sector>=25     | sector>=25     |
| 특수 산업 (금융/REIT) | ✅ + confidence↓   | ✅ + confidence↓ | ❌           | ✅ (지표 변환) | ✅ (지표 변환) |

### 저장량 추정

| 프리셋      | 종목 수 | 설명                          |
| ----------- | ------- | ----------------------------- |
| default     | 503     | 전체                          |
| sector_all  | 503     | 전체                          |
| size_peers  | ~200    | mega+large만                  |
| quality_top | ~450    | sector >= 25종목 조건 충족    |
| lifecycle   | ~400    | Revenue CAGR 데이터 있는 종목 |
| thematic    | ~50     | Phase 5, 선별                 |

총 프리셋: ~2,100건
배치 계산: 2,100 × 34 지표 × 5년 = ~357,000건 (관리 가능)

---

## 7. API (변경 없음, 원안 유지)

### 조회

```
GET /api/v1/validation/{symbol}/summary/

1. UserPeerPreference 조회 (user + symbol)
2-A. 없음 or preset/default → 기존 배치 데이터
2-B. preset/{key} → 배치 데이터 + preset_key 필터
2-C. custom → Redis 캐시 → 미스면 on-the-fly 계산
```

### 프리셋 목록

```
GET /api/v1/validation/{symbol}/presets/
→ [
    {
      preset_key: "default",
      display_name: "업종 표준",
      logic_summary: "Consumer Electronics 업종 내 유사 시가총액 24개",
      peer_count: 24,
      confidence_score: 0.85,
      confidence_label: "높음",
      is_selected: true,
      is_active: true
    },
    ...
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

## 8. UI

```
┌──────────────────────────────────────────────────┐
│ 📊 비교 기준                                      │
│                                                  │
│ [업종 표준 ✓]  [섹터 전체]  [체급 동종]            │
│ [우량주 비교]  [성장단계 유사]                      │
│                                                  │
│ [직접 설정...]                                    │
│                                                  │
│ Consumer Electronics 업종 내 유사 시가총액 24개    │
│ 비교 신뢰도: 높음                                  │
└──────────────────────────────────────────────────┘
```

- 프리셋 탭 클릭 → 즉시 전환 (배치 데이터, DB 인덱스 조회)
- "직접 설정" → 모달에서 종목 추가/제거 → Compute-on-Read
- 비활성 프리셋 (is_active=False) → gray-out + 툴팁 "데이터 부족"
- confidence < 0.4 → 프리셋 자동 비활성

---

## 9. 구현 우선순위

```
Phase 1 (완료): default 프리셋 1개 (자동, 배치)
Phase 2: PeerPreset 모델 + sector_all/size_peers 프리셋 추가 + 기존 테이블 preset_key 확장
Phase 3: quality_top + lifecycle 프리셋 (배치 확장) + confidence_score 계산
Phase 4: UserPeerPreference 모델 + 프리셋 선택 API + 프리셋 전환 UI
Phase 5: 커스텀 mode (Compute-on-Read) + Redis 캐시
Phase 6: thematic 프리셋 (LLM 큐레이션, beta 표시)
Phase 7: LLM 대화형 peer 조정 (Thesis Control 연동)
```

---

## 10. 원안 대비 변경 요약

| 항목                           | 원안                                            | 최종안                              | 이유                                                           |
| ------------------------------ | ----------------------------------------------- | ----------------------------------- | -------------------------------------------------------------- |
| 프리셋 수                      | 4개 (default, sector_all, size_peers, thematic) | 6개 (+quality_top, lifecycle)       | "해석 프레임 다양성" — 축이 겹치지 않는 프리셋만 추가          |
| PeerPreset.description         | 일반 설명                                       | → `logic_summary` (생성 근거 한 줄) | 사용자에게 "왜 이 비교군인지" 즉시 전달                        |
| confidence_score               | 없음                                            | 추가 (0.0~1.0)                      | 프리셋 품질 관리, gray-out 판단, 기본 추천 근거                |
| is_active                      | 없음                                            | 추가                                | 데이터 부족 프리셋 비활성 처리                                 |
| thematic 위치                  | Phase 2 프리셋                                  | Phase 5 + "(beta)" 보조             | 자동생성 품질 미검증 시 신뢰 하락 위험                         |
| thematic 자동안 (시총 상위 10) | 사용자 노출 프리셋                              | 내부 후보 생성기로만 사용           | 사업모델 혼재 위험                                             |
| 자본집약도 프리셋              | 없음                                            | Phase 3 이후 재검토                 | quality_top과 축 겹침, 별도 프리셋보다 내부 변형으로 흡수 가능 |
| Phase 순서                     | 6단계                                           | 7단계 (Phase 2에 모델 생성 포함)    | UserPeerPreference와 프리셋 선택 UI를 Phase 4로 분리           |

---

## 11. 성능 목표 (변경 없음)

| 시나리오                   | 응답 시간 | 방법                             |
| -------------------------- | --------- | -------------------------------- |
| 프리셋 조회 (배치 데이터)  | < 50ms    | DB 인덱스 조회                   |
| 프리셋 전환                | < 50ms    | DB 인덱스 조회 (preset_key 필터) |
| 커스텀 첫 요청 (캐시 미스) | < 200ms   | 벌크 쿼리 1회 + numpy            |
| 커스텀 재요청 (캐시 히트)  | < 10ms    | Redis GET                        |
| 리셋                       | < 50ms    | DB DELETE + 캐시 삭제            |
