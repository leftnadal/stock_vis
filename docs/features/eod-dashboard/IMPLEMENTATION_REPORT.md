# EOD Dashboard 전면 리뉴얼 - 구현 상세 레포트

> 작성일: 2026-02-26
> 상태: 구현 완료, 검증 완료 (83 tests passed)

---

## 1. 개요

기존 메인 페이지(`/app/page.tsx`)의 하드코딩된 샘플 포트폴리오를 **시그널 기반 종목 발굴 대시보드**로 전면 교체했습니다.

### 핵심 철학

- **시그널이 주(主), 뉴스가 종(從)**: 숫자 기반 시그널이 1차, 뉴스는 보조 컨텍스트
- **JSON Baking**: `frontend/public/static/signals/`에 정적 파일 직접 서빙 → API 비용 0원
- **벡터 연산만**: for-loop/iterrows 금지, pandas groupby().transform() 기반
- **멱등성**: 같은 날짜 재실행해도 데이터 중복 없음

### 대상 범위

| Phase | 대상 | 종목수 |
|-------|------|--------|
| Phase 1 (현재) | S&P 500 구성종목 | ~503개 |
| Phase 1.5 (후속) | 전체 US 시장 | ~6,000개 |

---

## 2. 아키텍처

```
DailyPrice(250일) → Calculator(벡터연산) → Tagger → NewsEnricher → JSONBaker → Next.js
                                                                        ↓
                                             public/static/signals/ (Atomic Swap)
                                                                        ↓
                                             DB 백업 (EODDashboardSnapshot)
```

### 파이프라인 8+1 Stage

| Stage | 함수 | 역할 | 소요시간(추정) |
|-------|------|------|--------------|
| 1 | `_stage_ingest()` | DailyPrice 250일분 로드 + 품질 체크 | ~2초 |
| 2 | `_stage_filter()` | volume >= 100K, dollar_vol >= $500K | <1초 |
| 3 | `_stage_calculate()` | EODSignalCalculator 14개 시그널 | ~30초 |
| 4 | `_stage_tag()` | EODSignalTagger primary/sub_tags | ~2초 |
| 5 | `_stage_enrich()` | EODNewsEnricher 5단계 매칭 | ~5초 |
| 6 | `_stage_db_upsert()` | bulk_create(update_conflicts=True) | ~3초 |
| 7 | `_stage_json_bake()` | Atomic Write 3단계 swap | ~2초 |
| 8 | `_stage_accuracy_backfill()` | SignalAccuracy 1d/5d/20d | ~3초 |
| 9 | Health Check | total_signals > 0 확인 | <1초 |
| **합계** | | | **~45초** |

### JSON 서빙 구조

```
frontend/public/static/signals/
├── dashboard.json              ← 메인 대시보드 (시장 요약 + 카드 배열)
├── meta.json                   ← 파이프라인 메타 (duration, run_id)
├── cards/
│   ├── momentum.json           ← 카테고리별 전체 종목 + 정렬 인덱스
│   ├── volume.json
│   ├── breakout.json
│   ├── reversal.json
│   ├── relation.json
│   └── technical.json
└── stocks/
    ├── AAPL.json               ← 종목별 60일 히스토리
    ├── NVDA.json
    └── ...
```

- Next.js가 `/static/signals/dashboard.json`을 직접 fetch
- Django REST API는 admin/debug fallback 전용
- TanStack Query `staleTime: Infinity` → 페이지 새로고침으로만 갱신

---

## 3. 14개 시그널 상세

### 3.1 시그널 목록

| ID | 이름 | 카테고리 | 색상 | 임계값(Normal) | 임계값(VIX>25) |
|----|------|---------|------|---------------|---------------|
| P1 | 연속 상승/하락 | momentum | #F0883E | 3일 연속 | - |
| P2 | 수익률 상위 | momentum | #F0883E | \|change\| > 5% | > 7% |
| P3 | 갭 감지 | momentum | #F0883E | gap > 3% | > 5% |
| P4 | 장대양봉/음봉 | momentum | #F0883E | body_pct > 3% & ratio > 0.6 | body_pct > 5% |
| P5 | 52주 신고가 근접 | breakout | #3FB950 | close >= 52w_high × 0.95 | - |
| P7 | 저가 대비 반등률 | reversal | #A371F7 | bounce > 3% & close > open | > 5% |
| V1 | 거래량 폭발 | volume | #58A6FF | vol_ratio >= 2.0 | >= 3.0 |
| PV1 | 가격-거래량 효율성 | volume | #58A6FF | \|change\| > 2% & vol_ratio < 1.0 | - |
| PV2 | 매집 의심 | volume | #58A6FF | vol_ratio > 2.0 & \|change\| < 1% | - |
| MA1 | 골든/데드크로스 | technical | #8B949E | SMA50/SMA200 교차 | - |
| T1 | RSI 과매도/과매수 | technical | #8B949E | RSI < 30 or > 70 | - |
| S1 | 섹터 상대 강도 | relation | #A371F7 | 섹터 평균 대비 +3%p | - |
| S2 | 섹터 소외주 | relation | #A371F7 | 섹터 상승일 & 대비 -3%p | - |
| S4 | 폭락장 생존자 | relation | #A371F7 | SPY -2%+ & 종목 >= -0.5% | - |

### 3.2 VIX 레짐 분기

```python
THRESHOLDS = {
    'normal': {
        'P2_change_pct': 5.0,
        'P3_gap_pct': 3.0,
        'P4_body_pct': 3.0,
        'P7_bounce_pct': 3.0,
        'V1_vol_ratio': 2.0,
    },
    'high_vol': {
        'P2_change_pct': 7.0,
        'P3_gap_pct': 5.0,
        'P4_body_pct': 5.0,
        'P7_bounce_pct': 5.0,
        'V1_vol_ratio': 3.0,
    },
}
```

- VIX > 25 → `high_vol` 레짐: 임계값 상향으로 노이즈 필터링
- `macro.models.MarketIndex`에서 VIX 데이터 조회
- 조회 실패 시 `normal` 기본값

### 3.3 태그 우선순위

```
relation > volume > momentum > breakout > reversal > technical
```

- `tag_details.primary`: 최우선 시그널 (카드 메인 표시)
- `tag_details.sub_tags`: 나머지 시그널 (서브 태그)

### 3.4 Composite Score

```python
composite_score = (bullish_count - bearish_count) / total_signals
# 범위: -1.0 (강 약세) ~ +1.0 (강 강세)
```

| 점수 범위 | 의미 | UI 도트 |
|----------|------|---------|
| > 0.6 | 강력 강세 | 5/5 녹색 |
| 0.3 ~ 0.6 | 강세 | 4/5 녹색 |
| 0 ~ 0.3 | 중립 | 3/5 회색 |
| -0.3 ~ 0 | 약세 | 2/5 주황 |
| < -0.3 | 강 약세 | 1/5 빨강 |

---

## 4. 뉴스 Enrichment 5단계

| 순위 | match_type | confidence | 매칭 기준 | UI 표현 |
|------|-----------|-----------|----------|---------|
| 1 | `symbol_today` | high | 종목 + 당일 | 강조 (파란색, 볼드) |
| 2 | `symbol_7d` | medium | 종목 + 7일 이내 | 보통 + "N일 전" |
| 3 | `symbol_30d` | low | 종목 + 30일 이내 | 흐림 + "N일 전" |
| 4 | `industry_7d` | context | 산업군 + 7일 이내 | "배경:" 이탤릭 |
| 5 | `profile` | info | 기업 프로필 fallback | "기업정보" 톤 |

**Profile fallback 규칙**:
- 팩트 요약만 (사업/규모/성장률)
- 인과 표현 금지 ("~때문에 올랐다" 등)
- 예: "NVDA: AI 칩 시장 점유율 1위, 매출 $35B, YoY +120%"

---

## 5. Atomic Write 패턴

### 3단계 디렉토리 Swap

```
Step 1: signals/     → signals_old/   (기존 백업)
Step 2: signals_tmp/ → signals/       (새 데이터 승격)
Step 3: signals_old/ 삭제             (백업 정리)
```

### 실패 시나리오별 안전장치

| 실패 지점 | 결과 | 복구 방법 |
|----------|------|----------|
| Step 1 실패 | signals/ 유지 (어제 데이터) | 자동 (변경 없음) |
| Step 2 실패 | signals_old/ → signals/ 복원 | 자동 (코드 내 rollback) |
| Step 3 실패 | signals_old/ 잔존 | 다음 실행 시 자동 정리 |
| Bake 자체 실패 | signals_tmp/ 삭제, signals/ 미변경 | 자동 (어제 데이터 보존) |

---

## 6. 데이터 모델

### 6.1 EODSignal

```python
class EODSignal(models.Model):
    stock = ForeignKey('Stock')              # 종목
    date = DateField()                       # 거래일
    signals = JSONField(default=list)        # [{"id":"V1","category":"volume",...}]
    tag_details = JSONField(default=dict)    # {"primary":"V1","sub_tags":["P1","MA1"]}
    signal_count = IntegerField()            # 시그널 개수
    bullish_count = IntegerField()           # 강세 시그널 수
    bearish_count = IntegerField()           # 약세 시그널 수
    composite_score = FloatField()           # -1.0 ~ +1.0
    news_context = JSONField()              # 뉴스 매칭 결과
    close_price = DecimalField()             # 종가
    change_percent = FloatField()            # 변동률
    volume = BigIntegerField()               # 거래량
    dollar_volume = DecimalField()           # 달러 거래량
    sector = CharField()                     # 섹터 (캐시)
    industry = CharField()                   # 산업 (캐시)
    market_cap = BigIntegerField()           # 시가총액

    class Meta:
        unique_together = ('stock', 'date')  # 멱등성
        # 인덱스: (date, -composite_score), (date, -signal_count),
        #         (stock, -date), (date, sector)
```

### 6.2 SignalAccuracy

```python
class SignalAccuracy(models.Model):
    stock = ForeignKey('Stock')
    signal_date = DateField()
    signal_tag = CharField()                 # "V1", "P1" 등
    signal_value = FloatField()
    close_at_signal = DecimalField()
    return_1d / return_5d / return_20d       # 수익률
    excess_1d / excess_5d / excess_20d       # SPY 대비 초과수익
    vix_at_signal = FloatField()             # VIX 스냅샷
    spy_change_at_signal = FloatField()      # SPY 변동 스냅샷

    class Meta:
        unique_together = ('stock', 'signal_date', 'signal_tag')
```

### 6.3 EODDashboardSnapshot

```python
class EODDashboardSnapshot(models.Model):
    date = DateField(unique=True)
    json_data = JSONField()                  # dashboard.json 전체 데이터
    total_signals = IntegerField()
    total_stocks = IntegerField()
    signal_distribution = JSONField()        # {"V1":23,"P1":12,...}
    generated_at = DateTimeField()
    pipeline_duration_seconds = FloatField()
```

### 6.4 PipelineLog

```python
class PipelineLog(models.Model):
    date = DateField()
    run_id = UUIDField(unique=True)
    status = CharField()                     # running/success/partial/failed
    stages = JSONField()                     # 각 Stage 결과
    ingest_quality = JSONField()             # 품질 메트릭
    total_duration_seconds = FloatField()
    error_message = TextField()
    started_at / completed_at = DateTimeField()
```

### 6.5 StockNews

```python
class StockNews(models.Model):
    stock = ForeignKey('Stock', null=True)
    symbol = CharField()
    headline = TextField()
    summary = TextField()
    source = CharField()
    url = URLField()
    published_at = DateTimeField()
    sector / industry = CharField()
    sentiment = CharField()                  # positive/negative/neutral
```

---

## 7. 파일 목록 및 라인 수

### 7.1 Backend (총 ~2,250줄)

| 파일 | 라인수 | 역할 |
|------|-------|------|
| `stocks/models.py` (EOD 부분) | ~160 | 5개 모델 |
| `stocks/services/eod_signal_calculator.py` | 428 | 14개 시그널 벡터 연산 |
| `stocks/services/eod_signal_tagger.py` | 358 | 태깅 + 교육 팁 + composite score |
| `stocks/services/eod_news_enricher.py` | 200 | 5단계 뉴스 매칭 |
| `stocks/services/eod_json_baker.py` | 461 | Atomic Write + JSON 생성 |
| `stocks/services/eod_pipeline.py` | 551 | 8+1 Stage 오케스트레이터 |
| `stocks/views_eod.py` | 137 | admin/debug API 3개 |
| `stocks/urls.py` (EOD 부분) | ~10 | URL 라우팅 |

### 7.2 Infra (총 ~200줄)

| 파일 | 라인수 | 역할 |
|------|-------|------|
| `stocks/tasks.py` (EOD 부분) | ~50 | Celery 태스크 2개 |
| `config/celery.py` (EOD 부분) | ~15 | Beat 스케줄 2개 |
| `stocks/management/commands/pipeline_status.py` | 120 | CLI 관리 명령 |

### 7.3 Frontend (총 ~1,300줄)

| 파일 | 라인수 | 역할 |
|------|-------|------|
| `frontend/types/eod.ts` | 122 | TypeScript 타입 + 상수 |
| `frontend/services/eodService.ts` | 25 | 정적 파일 fetch |
| `frontend/hooks/useEODDashboard.ts` | 37 | TanStack Query 훅 3개 |
| `frontend/components/eod/DataFreshnessBadge.tsx` | 71 | 데이터 신선도 배지 |
| `frontend/components/eod/MarketSummaryBar.tsx` | 108 | 시장 요약 (SPY/QQQ/VIX) |
| `frontend/components/eod/SignalFilterTabs.tsx` | 83 | 카테고리 필터 탭 |
| `frontend/components/eod/SignalCard.tsx` | 174 | 개별 시그널 카드 |
| `frontend/components/eod/SignalCardGrid.tsx` | 46 | 반응형 그리드 (1/2/3열) |
| `frontend/components/eod/SignalDetailSheet.tsx` | 229 | 슬라이드 패널 (정렬, 종목 목록) |
| `frontend/components/eod/StockRow.tsx` | 100 | 종목 행 (가격, 변동률, 뉴스) |
| `frontend/components/eod/MiniSparkline.tsx` | 65 | 20일 SVG 스파크라인 |
| `frontend/components/eod/ConfidenceBadge.tsx` | 31 | 1-5 도트 composite score |
| `frontend/components/eod/NewsContextBadge.tsx` | 84 | match_type별 뉴스 뱃지 |
| `frontend/components/eod/EODSkeleton.tsx` | 113 | 로딩 스켈레톤 (CLS=0) |
| `frontend/app/page.tsx` | ~100 | 메인 페이지 (전면 교체) |

### 7.4 테스트 (총 ~2,450줄)

| 파일 | 라인수 | 테스트 수 | 범위 |
|------|-------|----------|------|
| `tests/unit/stocks/conftest.py` | 185 | - | 공용 fixture |
| `tests/unit/stocks/test_eod_signal_calculator.py` | 1,118 | 35 | 14개 시그널, VIX, 벡터, NaN |
| `tests/unit/stocks/test_eod_pipeline.py` | 350 | 10 | 통합, 멱등성, 상태 전이 |
| `tests/unit/stocks/test_eod_ingest_quality.py` | 407 | 16 | 품질 메트릭, degrade mode |
| `tests/unit/stocks/test_eod_api.py` | 570 | 22 | REST 3개, JSON 스키마 |
| **합계** | **~2,630** | **83** | |

### 7.5 문서

| 파일 | 역할 |
|------|------|
| `docs/features/eod-dashboard/README.md` | 기능 설계 문서 |
| `sub_claude_md/eod-dashboard.md` | CLAUDE.md 참조용 |

---

## 8. API 엔드포인트

### 8.1 admin/debug 전용 API (프론트엔드 미사용)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/stocks/eod/dashboard/?date=YYYY-MM-DD` | DB 스냅샷 조회 |
| GET | `/api/v1/stocks/eod/signal/<signal_id>/?date=YYYY-MM-DD` | 시그널별 종목 (top 50) |
| GET | `/api/v1/stocks/eod/pipeline/status/` | 최근 7일 파이프라인 로그 |

### 8.2 프론트엔드 서빙 (정적 파일)

| URL | 파일 |
|-----|------|
| `/static/signals/dashboard.json` | 메인 대시보드 |
| `/static/signals/cards/{category}.json` | 카테고리별 종목 |
| `/static/signals/stocks/{SYMBOL}.json` | 종목별 히스토리 |
| `/static/signals/meta.json` | 파이프라인 메타 |

---

## 9. Celery 스케줄

| 태스크 | 스케줄 | 설명 |
|--------|-------|------|
| `run_eod_pipeline` | 월-금 18:30 ET | 전체 파이프라인 실행 |
| `backfill_signal_accuracy` | 월-금 19:00 ET | 정확도 소급 계산 |

### CLI 관리 명령

```bash
# 최근 7일 로그
python manage.py pipeline_status

# 즉시 실행
python manage.py pipeline_status --run

# 특정 날짜 실행
python manage.py pipeline_status --run --date 2026-02-25

# 품질 상세 (최근 10일)
python manage.py pipeline_status --quality --days 10
```

---

## 10. 프론트엔드 UI 계층

```
Level 1: DataFreshnessBadge
         ├─ is_stale=true  → amber 경고 배너 ("어제 데이터입니다")
         └─ is_stale=false → green 정상 배지
         (Baker가 bake 시 초기값 설정 + 프론트에서 generated_at 기준 24시간 경과 시 동적으로 stale 판단)

Level 2: MarketSummaryBar
         ├─ 헤드라인: "503종목에서 87개 시그널 감지"
         ├─ 배지: S&P500 +0.85%, QQQ +1.23%, VIX 15.5
         └─ 비율 바: 강세 34 / 약세 53

Level 3: SignalFilterTabs
         ├─ 전체 | momentum | volume | breakout | reversal | relation | technical
         └─ 각 탭에 카운트 배지

Level 4: SignalCardGrid (반응형 1/2/3열)
         └─ SignalCard × N
             ├─ 카테고리 색상 도트 + 카운트
             ├─ 제목 + 설명
             ├─ [?] 교육 팁 토글 (tip + risk)
             ├─ 프리뷰 종목 3개
             │   ├─ 심볼 + 스파크라인 + 변동률
             │   └─ 뉴스 헤드라인 미리보기
             └─ "+N종목 더 보기" CTA

Level 5: SignalDetailSheet (카드 클릭 시)
         ├─ 정렬: 거래량순 | 수익률순 | 시가총액순
         └─ StockRow × N
             ├─ 심볼 + ConfidenceBadge
             ├─ MiniSparkline (20일)
             ├─ 현재가 + 변동률
             ├─ signal_label + 거래량
             └─ NewsContextBadge (confidence별 차등)
```

### 반응형 레이아웃

| 화면 | 카드 열 수 | 상세 시트 |
|------|----------|----------|
| 모바일 (<640px) | 1열 | 하단 슬라이드업 (85vh) |
| 태블릿 (640-1024px) | 2열 | 하단 슬라이드업 |
| 데스크톱 (>1024px) | 3열 | 우측 슬라이드 패널 (480px) |

---

## 11. 데이터 결측/이상치 처리

| 상황 | 처리 |
|------|------|
| `high == low` | `body_ratio = 0.5` (기본값) |
| `avg_volume_20d == 0` | `vol_ratio = NaN` (해당 시그널 스킵) |
| NaN 전파 | 개별 지표별 독립 처리 (다른 지표에 영향 없음) |
| `pd.to_numeric` 실패 | `errors='coerce'` → NaN 자동 변환 |
| sector null | 해당 종목 S1/S2 시그널 스킵 |
| 뉴스 없음 | profile fallback (기업 프로필 팩트 요약) |

---

## 12. 품질 모니터링

### Ingest Quality 메트릭

```python
{
    'total_symbols': 510,            # 수신 종목 수
    'sp500_universe': 503,           # S&P 500 기준
    'today_rows': 425,               # 당일 데이터 행
    'today_coverage_pct': 84.5,      # 커버리지
    'quality_score': 0.845,          # 종합 점수
    'sector_null_pct': 1.2,          # sector null 비율
    'volume_zero_pct': 0.0,          # 거래량 0 비율
    'vs_prev_day_pct': -0.5,         # 전일 대비 변동
    'degrade_mode': False,           # 품질 저하 모드
    'warnings': []                   # 경고 메시지
}
```

### Degrade Mode 트리거 조건

| 조건 | 임계값 | 동작 |
|------|-------|------|
| 종목수 변동 | \|vs_prev_day_pct\| > 10% | 경고 + 계속 실행 |
| sector null | > 5% | 경고 + 계속 실행 |
| volume zero | > 3% | 경고 + 계속 실행 |
| 빈 DataFrame | 0개 종목 | 경고 + partial 상태 |

---

## 13. 테스트 상세

### 13.1 시그널 계산기 (35개)

| 테스트 클래스 | 수 | 검증 내용 |
|-------------|---|----------|
| TestP1ConsecutiveMoves | 3 | 3일 연속 상승/하락, 2일 불발 |
| TestP2LargeChange | 3 | normal/high_vol 임계값 분기 |
| TestP3Gap | 3 | 갭업/갭다운/소폭갭 |
| TestP4LargeCandle | 2 | 장대양봉, 소형 몸통 불발 |
| TestP5FiftyTwoWeekHigh | 2 | 52주 고가 95% 임계값 |
| TestP7Bounce | 2 | 반등+양봉 조건, close<open 불발 |
| TestV1VolumeSpike | 3 | normal 2배, high_vol 3배 |
| TestPV1/PV2 | 2 | 효율성/매집 의심 |
| TestMA1GoldenCross | 1 | SMA50/SMA200 교차 |
| TestT1RSI | 2 | 과매도/과매수 |
| TestSectorSignals | 2 | S1 상회, S2 소외 |
| TestS4CrashSurvivor | 2 | SPY 폭락일 생존, 상승일 불발 |
| TestVixRegime | 4 | high_vol/normal 판단, fallback |
| TestVectorizedOperations | 4 | 컬럼 존재, NaN, high=low, zero vol |

### 13.2 파이프라인 (10개)

| 테스트 | 검증 내용 |
|--------|----------|
| test_pipeline_creates_pipeline_log | PipelineLog 레코드 생성 |
| test_pipeline_success_status | status=success 또는 partial |
| test_pipeline_idempotent | **동일 날짜 2회 실행 시 중복 없음** |
| test_pipeline_creates_snapshot | Baker.bake() 호출 확인 |
| test_pipeline_stages_logged | stages dict 기록 |
| test_pipeline_failure_sets_failed_status | 예외 시 status=failed |
| test_pipeline_log_has_run_id | UUID 형식 확인 |
| test_pipeline_duration_recorded | duration_seconds 기록 |
| test_bulk_upsert_no_duplicates | update_or_create 멱등성 |
| test_multiple_runs_different_run_ids | 실행마다 고유 run_id |

### 13.3 품질 체크 (16개)

| 테스트 | 검증 내용 |
|--------|----------|
| 6개 degrade 트리거 | 종목수 이탈, sector null, volume zero |
| 4개 정상 범위 | 임계값 이내 → degrade=False |
| 4개 볼륨 필터 | low volume/dollar_volume 제거 확인 |
| 2개 PipelineLog | ingest_quality 저장 확인 |

### 13.4 API (22개)

| 테스트 클래스 | 수 | 검증 내용 |
|-------------|---|----------|
| TestEODDashboardAPI | 5 | 200/404/400, JSON 구조, today 기본값 |
| TestEODSignalDetailAPI | 6 | 200, 빈 응답, 구조, top 50 제한 |
| TestEODPipelineStatusAPI | 7 | 200, 빈 로그, 정렬, max 7, run_id, error |
| TestEODDashboardSnapshotModel | 2 | unique date, str |
| TestEODSignalModel | 2 | unique stock+date, str |

---

## 14. 검증 결과

### 14.1 Backend

```
✅ 모든 서비스/뷰/모델/태스크 import 성공
✅ Management command 정상 동작
✅ Migration 적용 완료 (0005)
```

### 14.2 Frontend

```
✅ tsc --noEmit 에러 0건 (TypeScript strict mode)
✅ 11개 컴포넌트 + 타입 + 서비스 + 훅 정상
```

### 14.3 테스트

```
✅ 83 passed in 1.80s
   - test_eod_signal_calculator: 35 passed
   - test_eod_pipeline: 10 passed
   - test_eod_ingest_quality: 16 passed
   - test_eod_api: 22 passed
```

---

## 15. 교육 팁 시스템

모든 시그널에 `education_tip` + `education_risk` 포함:

| ID | Tip | Risk |
|----|-----|------|
| P1 | 연속 상승은 추세의 강도를 보여줍니다 | 추세 끝자락일 수 있으니 진입 시점에 유의하세요 |
| P2 | 하루 큰 변동은 중요한 이벤트 발생을 시사합니다 | 변동성 확대 구간에서는 손절 기준을 반드시 설정하세요 |
| P3 | 갭은 시간 외에 발생한 강한 이벤트를 반영합니다 | 갭상승 후 되돌림이 빈번합니다 |
| P4 | 장대봉은 한 방향으로 강한 힘을 의미합니다 | 과도한 단기 이동은 반전 가능성이 있습니다 |
| P5 | 52주 신고가 근접은 강한 상승 모멘텀을 시사합니다 | 저항선 돌파 실패 시 급격한 조정이 올 수 있습니다 |
| P7 | 저가 반등은 매수세 유입을 시사합니다 | 하락 추세 중 반등은 일시적일 수 있습니다 |
| V1 | 거래량은 시장 관심의 크기를 보여줍니다 | 단기 과열일 수 있으니 추격 매수에 주의하세요 |
| PV1 | 적은 거래량으로 큰 움직임은 효율적 매매를 시사합니다 | 유동성이 낮아 스프레드가 넓을 수 있습니다 |
| PV2 | 거래량 급증+횡보는 큰 손의 매집 가능성입니다 | 매집이 아닌 블록딜일 수도 있습니다 |
| MA1 | 이동평균 교차는 중기 추세 전환 신호입니다 | 후행 지표이므로 이미 상당 부분 반영되었을 수 있습니다 |
| T1 | RSI 극단값은 과매수/과매도 영역 진입을 의미합니다 | 강한 추세에서는 극단값이 오래 유지될 수 있습니다 |
| S1 | 섹터 대비 강세는 종목 고유의 호재를 시사합니다 | 섹터 전체 약세 전환 시 함께 하락할 수 있습니다 |
| S2 | 섹터 상승에서 소외는 종목 고유 리스크 가능성입니다 | 뒤늦게 따라 오르는 경우도 있으므로 원인 파악이 중요합니다 |
| S4 | 하락장 생존은 방어적 특성이나 고유 호재를 시사합니다 | 다음 하락에서도 생존한다는 보장은 없습니다 |

---

## 16. 후속 계획 (미구현)

### Phase 1.5: 전체 US 시장 확장

- 대상: ~8,000종목 → 필터 후 ~6,000종목
- 추가 필터: OTC 제외, 시총 하한, 하위 20% 제거
- 성능: 벡터 연산 최적화 필요 (현재 45초 → 목표 120초 이내)

### Phase 2: 시그널 정확도 대시보드

- `SignalAccuracy` 데이터 축적 후 시그널별 승률 표시
- 초반 전략: "최근 30일 가장 많이 발생한 시그널" 설명형 지표
- `accuracy_available: false` 플래그로 프론트엔드 분기

### Phase 3: 알림 시스템

- Watchlist 종목에 시그널 감지 시 푸시 알림
- 사용자별 관심 시그널 구독

---

## 17. 실행 가이드

### 파이프라인 수동 실행

```bash
# CLI로 즉시 실행
python manage.py pipeline_status --run

# 특정 날짜
python manage.py pipeline_status --run --date 2026-02-25

# 품질 확인
python manage.py pipeline_status --quality
```

### JSON 파일 확인

```bash
# dashboard.json 생성 확인
cat frontend/public/static/signals/dashboard.json | python -m json.tool | head -20

# 시그널 카드 확인
cat frontend/public/static/signals/cards/volume.json | python -m json.tool | head -20

# 종목별 히스토리 확인
cat frontend/public/static/signals/stocks/NVDA.json | python -m json.tool | head -20
```

### API fallback 확인

```bash
curl localhost:8000/api/v1/stocks/eod/dashboard/ | python -m json.tool
curl localhost:8000/api/v1/stocks/eod/signal/V1/ | python -m json.tool
curl localhost:8000/api/v1/stocks/eod/pipeline/status/ | python -m json.tool
```

### 테스트 실행

```bash
# EOD 테스트만
pytest tests/unit/stocks/ -v

# 전체 테스트
pytest tests/ -v
```

### 프론트엔드 확인

```bash
cd frontend && npm run dev
# localhost:3000 접속 → EOD 대시보드 렌더링 확인
# 브라우저 콘솔: fetch('/static/signals/dashboard.json').then(r => r.json()).then(console.log)
```
