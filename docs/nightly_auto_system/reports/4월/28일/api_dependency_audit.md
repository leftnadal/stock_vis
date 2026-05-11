# 외부 API 의존성 감사 보고서

생성일: 2026-04-28
대상 브랜치: feature/chainsight-graph-v2
감사자: @qa-architect (자동 감사)

---

## 요약 (Executive Summary)

- **FMP 의존 단일 장애점**: `stocks/services/sp500_eod_service.py`가 FMP 실패 시 S&P 500 전종목(503개) EOD 동기화가 전량 중단되며, `macro/services/macro_service.py`는 FMP + FRED 동시 장애 시 메인 Market Pulse 대시보드가 `{'error': str(e)}` 응답을 반환해 페이지 전체가 깨진다.
- **Gemini 429 미처리 핫스팟 3건**: `sec_pipeline/extractor.py`, `sec_pipeline/intelligence.py`, `validation/services/llm_peer_filter.py`는 Gemini 호출 시 429를 별도 처리하지 않고 일반 `Exception`으로 흘려보낸다. Free-tier 15 RPM 제한에서 배치 파이프라인이 자주 충돌할 수 있다.
- **Gemini async/sync 혼용 위험**: `serverless/services/keyword_generator_v2.py`는 `async def _call_llm_batch`를 사용한다. Celery 태스크에서 이 서비스를 호출할 경우 CLAUDE.md 버그 #8 조건에 해당한다 — 실제 Celery 태스크가 `asyncio.run()`으로 래핑하지 않고 직접 `await`하는지 별도 확인 필요.
- **Circuit Breaker 적용 범위 불균형**: `marketpulse/briefing/client.py`는 Gemini에 Circuit Breaker를 적용하고 있으나, 호출 빈도가 더 높은 `news/services/news_deep_analyzer.py`, `serverless/services/llm_relation_extractor.py`, `serverless/services/keyword_service.py` 등에는 미적용이다.
- **즉시 조치 필요**: `macro/services/macro_service.py`의 FRED/FMP 동시 장애 시 fallback 데이터 없음 (메인 페이지 영향), `stocks/services/sp500_eod_service.py`의 FMP 단일 의존 (fallback 없음), `sec_pipeline/extractor.py`의 Gemini 에러 전파 (파이프라인 중단).

---

## 의존성 매트릭스

| 서비스/기능 | FMP | Gemini | FRED | Neo4j | SEC EDGAR | Redis | Fallback |
|-----------|-----|--------|------|-------|-----------|-------|---------|
| S&P 500 EOD 가격 동기화 | ✅ | N/A | N/A | N/A | N/A | 캐시 | ❌ |
| S&P 500 재무제표 배치 | ✅ | N/A | N/A | N/A | N/A | N/A | ❌ |
| Market Movers (daily sync) | ✅ | N/A | N/A | N/A | N/A | ✅ 5분 캐시 | ❌ |
| Market Pulse 대시보드 | ✅ | N/A | ✅ | N/A | N/A | ✅ | 부분 (개별 catch) |
| Screener Enhanced | ✅ | N/A | N/A | N/A | N/A | ✅ | ❌ |
| Stock Profile/Quote | ✅ | N/A | N/A | N/A | N/A | ✅ | ✅ DB 폴백 |
| News 뉴스 키워드 추출 | N/A | ✅ | N/A | N/A | N/A | N/A | ✅ FALLBACK_KEYWORDS |
| News Deep Analyzer | N/A | ✅ | N/A | N/A | N/A | N/A | ❌ (None 반환) |
| Market Movers 키워드 (V2) | N/A | ✅ async | N/A | N/A | N/A | N/A | ❌ (빈 리스트) |
| Keyword Service (Market Movers V1) | N/A | ✅ sync | N/A | N/A | N/A | N/A | ❌ |
| Chain Sight LLM 관계 추출 | N/A | ✅ sync | N/A | ✅ | N/A | ✅ 1시간 캐시 | ❌ (빈 관계) |
| RAG Analysis (스트리밍) | N/A | ✅ async | N/A | N/A | N/A | N/A | ❌ error 이벤트 |
| Thesis Builder | N/A | ✅ sync | N/A | N/A | N/A | N/A | ❌ |
| Market Pulse Briefing | N/A | ✅ sync | N/A | N/A | N/A | ✅ CB | ✅ INSUFFICIENT_DATA |
| Validation Peer LLM 필터 | N/A | ✅ sync | N/A | N/A | N/A | N/A | ✅ `{'error': str}` |
| SEC Pipeline 수집 | N/A | ✅ sync | N/A | ✅ | ✅ | N/A | ❌ (raise) |
| SEC Intelligence 리포트 | N/A | ✅ sync | N/A | N/A | N/A | N/A | ✅ fallback dict |
| Chain Sight 그래프 조회 | N/A | N/A | N/A | ✅ | N/A | ✅ 5분 캐시 | ✅ fallback mode |
| EOD Dashboard (Thesis) | ✅ | N/A | ✅ | N/A | N/A | N/A | ❌ (None 반환) |

---

## FMP 상세

### 호출 지점 인벤토리

| 파일 | 함수/클래스 | 호출 목적 | 위험도 |
|------|-----------|---------|-------|
| `api_request/providers/fmp/client.py` | `FMPClient._make_request` | 기반 HTTP 클라이언트 | 🟢 안전 (재시도 내장) |
| `api_request/providers/fmp/provider.py` | `FMPProvider.*` | Provider 추상화 레이어 | 🟢 안전 |
| `api_request/stock_service.py` | `StockService.*` | 주식 데이터 통합 서비스 | 🟢 안전 (ProviderResponse) |
| `stocks/tasks.py:174` | `sync_sp500_financials` | 재무제표 배치 (101개/일) | 🟡 부분 |
| `stocks/tasks.py:272` | `update_stock_with_provider` | 주식 데이터 업데이트 | 🟡 retry=3 있음 |
| `stocks/services/sp500_eod_service.py:131` | `_sync_single_symbol` | S&P 500 전종목 EOD | 🔴 단일 장애점 |
| `stocks/services/sp500_service.py` | SP500 구성종목 동기화 | 월 1회 배치 | 🟡 부분 |
| `serverless/services/fmp_client.py:_make_request` | `FMPClient.*` | Market Movers/Screener | 🟡 부분 (예외 처리) |
| `serverless/services/enhanced_screener_service.py:90` | `EnhancedScreenerService.screen_enhanced` | 스크리너 100개 배치 | 🟡 부분 |
| `serverless/services/market_breadth_service.py` | 시장 폭 지표 | Market Breadth | 🟡 |
| `serverless/services/sector_heatmap_service.py` | 섹터 히트맵 | 섹터 데이터 | 🟡 |
| `macro/services/fmp_client.py` | `FMPClient.get_all_market_quotes` | Market Pulse (지수/환율) | 🔴 단일 장애점 |
| `macro/services/macro_service.py:214` | `get_global_markets_dashboard` | 메인 대시보드 | 🔴 FRED+FMP 동시 의존 |
| `news/providers/fmp.py` | `FMPNewsProvider.*` | 뉴스 수집 | 🟢 Circuit Breaker 있음 |
| `thesis/tasks/eod_pipeline.py:25` | `_fetch_fmp_value` | 가설 지표 값 수집 | 🟡 FMPPremiumError 처리 |
| `marketpulse/fetchers/fmp_weights.py` | FMP 시장 데이터 | Market Pulse v2 | 🟡 Circuit Breaker 있음 |
| `marketpulse/services/news_aggregator.py` | FMP 뉴스 수집 | Market Pulse 뉴스 | 🟢 Circuit Breaker 있음 |

### 에러 핸들링 패턴 분석

**1. api_request/providers/fmp/client.py (핵심 클라이언트)**

- `FMPPremiumError` (402), `FMPAuthError` (401/403), `FMPRateLimitError` (429) 즉시 전파 — 재시도 스킵.
- 일반 `requests.RequestException` / `FMPClientError`: max_retries=3, exponential backoff (2s, 4s, 6s).
- 일일 콜 카운터(`daily_calls`) 인메모리 추적 — 워커 재시작 시 리셋되며 다중 워커 환경에서는 공유되지 않음.

**2. api_request/providers/fmp/provider.py**

- `FMPRateLimitError` → `RateLimitError` 변환 후 상위 전파.
- `FMPPremiumError` → `ProviderResponse.error_response(error_code="PREMIUM_ONLY")` 로그+무시. 재무제표 3개 엔드포인트에서 처리.
- 나머지 Exception → `ProviderResponse.error_response(error_code="API_ERROR")` — **swallow하여 상위에서 `success=False` 체크 필요**.

**3. serverless/services/fmp_client.py (Market Movers용)**

- `raise_for_status()` 사용 — 402/429 전용 처리 없음.
- `FMPAPIError`로 래핑 후 throw — 호출자(`data_sync.py`)가 catch.
- **Redis 캐시**: 5분(시세), 1시간(히스토리), 24시간(프로필/peers). FMP 장애 시 캐시 TTL이 지나면 캐시 폴백 없이 에러 전파.

**4. macro/services/fmp_client.py (Market Pulse용)**

- `_make_request` 내부: 200 이외 → `raise_for_status()` 호출, 402/429 별도 처리 없음.
- `get_quote()`: `except Exception` 후 `return None` — 부분 폴백.
- `get_batch_quotes()`: 개별 심볼 루프로 처리(402 배치 에러 회피). 일부 실패 시 나머지는 계속.
- **단일 장애점**: `get_all_market_quotes()` — 20개 심볼에 대해 개별 FMP 요청 20회 순차 발행, 일부 실패 데이터는 응답에서 누락되나 시스템은 계속 동작.

**5. stocks/services/sp500_eod_service.py:131**

```
except FMPAPIError as e:
    raise Exception(f"FMP API error for {symbol}: {e}")
```
- `FMPAPIError` catch 후 재raise. 개별 심볼 루프(`sync_eod_prices`)에서 `except Exception` 으로 잡아 `stats['errors']++` 처리.
- **FMP 자체가 완전 다운되면 503개 모든 심볼에서 에러가 발생하며, 해당 날짜의 DailyPrice가 비어있게 된다.** 부분 실패 허용 구조이나 전체 실패 알림 메커니즘은 없음.

### Rate Limit 처리 현황

| 위치 | 처리 방식 | 설정값 | 평가 |
|-----|---------|-------|-----|
| `api_request/providers/fmp/client.py` | `time.sleep(request_delay)` | 0.2초/요청 | 분당 최대 300회 — 사양 준수 |
| `macro/services/fmp_client.py` | `time.sleep(request_delay)` | 0.5초/요청 | 보수적 — 양호 |
| `stocks/services/sp500_eod_service.py` | `time.sleep(REQUEST_DELAY)` | 0.3초/요청 | 분당 200회 안전 마진 |
| `stocks/tasks.py:sync_sp500_financials` | `countdown=i * 7` 분산 | 7초 간격 | 배치 분산 적절 |
| `stocks/tasks.py:bulk_sync_sp500_financials` | `countdown=idx * 2` | 2초 간격 | 분당 30회 — 안전 |
| `serverless/services/fmp_client.py` | 없음 | — | **누락**: 루프 내 연속 호출 시 위험 |

### FMPPremiumError (402) 처리

| 파일 | 처리 방식 |
|-----|---------|
| `api_request/providers/fmp/client.py:149` | 즉시 전파 (재시도 불가 예외로 분류) — 정상 |
| `api_request/providers/fmp/provider.py:247,293,339` | 재무제표 3개 메서드: `PREMIUM_ONLY` 에러 코드로 응답 반환, 로그 경고 |
| `thesis/tasks/eod_pipeline.py:73` | `return None, None` 처리 — 해당 지표 skip |
| `stocks/tasks.py:147` | `.` 포함 심볼 배치에서 사전 제외 — 예방적 처리 |
| `serverless/services/fmp_client.py` | **누락**: `raise_for_status()`가 402를 `httpx.HTTPStatusError`로 처리, `FMPAPIError`로 변환. 호출자가 FMPAPIError를 catch하므로 동작은 하나 의미가 희석됨 |
| `macro/services/fmp_client.py` | **누락**: `requests.exceptions.RequestException`으로 처리됨 |

### 단일 장애점 (FMP)

**🔴 P0 — stocks/services/sp500_eod_service.py**
- S&P 500 전종목 EOD 동기화가 FMP에만 의존. 다른 데이터 소스 폴백 없음.
- FMP 장애 시 EOD 데이터 공백 → Thesis EOD Pipeline의 지표 수집, 기술지표 계산, RAG 컨텍스트 생성 연쇄 실패.

**🔴 P0 — macro/services/macro_service.py**
- `get_global_markets_dashboard()`: FMP 5개 메서드 + FRED 1개 호출. 내부 `except Exception as e: return {'error': str(e)}` — 프론트엔드에서 error 키 확인 없으면 렌더링 실패.
- FRED 또는 FMP 중 하나만 실패해도 전체 섹션이 `{'error': ...}` 반환.

---

## Gemini 상세

### 호출 지점 인벤토리

| 파일 | 클라이언트 방식 | 동기/비동기 | 429 처리 | Timeout | 위험도 |
|------|-------------|-----------|---------|---------|-------|
| `rag_analysis/services/llm_service.py` | `genai.Client` async | 비동기 (Django View) | ✅ retry 3회 | 없음 | 🟡 |
| `rag_analysis/services/adaptive_llm_service.py` | `genai.Client` | 비동기 | 미확인 | 없음 | 🟡 |
| `news/services/keyword_extractor.py:190` | `genai.Client` sync | 동기 | ❌ 일반 except | 없음 | 🔴 |
| `news/services/news_deep_analyzer.py:125` | `genai.Client` sync | 동기 | ❌ `except Exception → None` | 없음 | 🟡 |
| `serverless/services/keyword_service.py:279` | `genai.Client` sync | 동기 (Celery) | ✅ 429 체크+sleep | 없음 | 🟢 |
| `serverless/services/keyword_generator_v2.py:128` | `genai.Client` | **비동기** | ❌ `except Exception → []` | 없음 | 🔴 |
| `serverless/services/llm_relation_extractor.py:384` | `genai.Client` sync | 동기 | ❌ `except Exception → 빈 결과` | 없음 | 🟡 |
| `serverless/services/llm_relation_extractor.py:366` | — | — | ✅ `time.sleep(4)` 배치 간격 | — | 🟢 |
| `serverless/services/relationship_keyword_enricher.py` | `genai.Client` | 미확인 | 미확인 | 없음 | 🟡 |
| `thesis/services/thesis_builder.py` | `genai.Client` | 동기 | 미확인 | 없음 | 🟡 |
| `validation/services/llm_peer_filter.py:79` | `genai.Client` sync | 동기 | ❌ `except Exception → {'error': str}` | 없음 | 🟢 (에러 반환) |
| `sec_pipeline/extractor.py:68,128` | `genai.Client` sync | 동기 | ❌ **`raise` 전파** | 없음 | 🔴 |
| `sec_pipeline/intelligence.py:162` | `genai.Client` sync | 동기 | ❌ fallback dict만 | 없음 | 🟢 |
| `marketpulse/briefing/client.py:68` | `genai.Client` sync | 동기 | ✅ Circuit Breaker | 없음 | 🟢 |
| `marketpulse/tasks/briefing.py:60` | — (client.generate) | 동기 (Celery) | ✅ retry+CB | 없음 | 🟢 |
| `rag_analysis/services/entity_extractor.py` | `genai.Client` | 동기 | 미확인 | 없음 | 🟡 |
| `rag_analysis/services/context_compressor.py` | `genai.Client` | 동기/비동기 | 미확인 | 없음 | 🟡 |
| `stocks/services/korean_overview_service.py` | `genai.Client` | 동기 | 미확인 | 없음 | 🟡 |

### 429 처리 현황

**처리 중 (양호)**
- `rag_analysis/services/llm_service.py:217`: `'rate' in error_str or 'quota' in error_str or '429' in error_str` 체크 → `asyncio.sleep(delay)`, 최대 3회 재시도.
- `serverless/services/keyword_service.py:318`: `'rate' in error_msg or 'quota' in error_msg or '429' in error_msg` 체크 → `time.sleep((attempt+1)*2)`.
- `serverless/services/llm_relation_extractor.py:366`: 배치 처리 시 `time.sleep(4)` 강제 대기 — 15 RPM 준수 설계.
- `marketpulse/briefing/client.py`: Circuit Breaker + tenacity exponential backoff (1s/2s/4s, 3회).

**미처리 (위험)**
- `sec_pipeline/extractor.py:86-91`: `json.JSONDecodeError` 개별 처리 후 `except Exception as e: raise` — 429 포함 모든 예외가 태스크 레벨로 전파.
- `news/services/keyword_extractor.py:152`: `except Exception as e: logger.exception(...)` 후 fallback 키워드 반환 — 에러는 삼킴.
- `news/services/news_deep_analyzer.py:146`: `except Exception as e: logger.error(...) return None` — 에러는 삼키고 분석 누락.
- `serverless/services/keyword_generator_v2.py:139`: `except Exception as e: logger.exception(...) return []` — 에러는 삼킴.
- `validation/services/llm_peer_filter.py:88`: `except Exception as e: return {'error': str(e)}` — 호출자가 error 키 확인 필요.

### 응답 파싱 가드

| 파일 | JSON 파싱 처리 | 평가 |
|-----|-------------|-----|
| `sec_pipeline/extractor.py:86` | `except json.JSONDecodeError` → `{'relationships': [], 'error': ...}` | ✅ |
| `serverless/services/keyword_service.py:332` | `_parse_keywords()`: 잘린 JSON 복구 지원 | ✅ |
| `news/services/keyword_extractor.py` | `_parse_response()` 내부 처리 (미확인) | 🟡 |
| `validation/services/llm_peer_filter.py:86` | `json.loads(text)` — JSONDecodeError 별도 처리 없음 | ⚠️ `text='{}'` 기본값으로 예외 방지 |
| `sec_pipeline/intelligence.py:169` | `json.loads(text)` — JSONDecodeError 별도 처리 없음, `except Exception`이 상위에서 처리 | 🟡 |
| `rag_analysis/services/llm_service.py` | 스트리밍 응답, JSON 파싱 없음 (텍스트 직접) | ✅ |
| `serverless/services/llm_relation_extractor.py` | `response_mime_type="application/json"` 강제 → 파싱 신뢰도 높음 | ✅ |

### Timeout 현황

**전체 Gemini 호출에 timeout 파라미터 설정 없음.**
- `types.GenerateContentConfig`에 `timeout` 필드가 있으나 프로젝트 전반에서 사용하지 않음.
- Gemini 2.5 Flash는 응답이 수십 초까지 걸릴 수 있으며, 특히 `thinking_budget=0`이 아닌 경우 더 길어질 수 있음.
- Celery 태스크에서는 `soft_time_limit`/`time_limit`으로 일부 보완되나 (예: `validation/tasks.py:22`), LLM 단독 서비스(`news_deep_analyzer`, `llm_relation_extractor` 등)는 무한 대기 위험 존재.

### 동기/비동기 현황 (버그 #8 위험)

**안전 (Celery에서 동기 API 사용)**
- `news/services/keyword_extractor.py:190`: `client.models.generate_content(...)` 동기.
- `serverless/services/keyword_service.py:279`: `client.models.generate_content(...)` 동기. 주석에도 "Celery 호환" 명시.
- `serverless/services/llm_relation_extractor.py:384`: `client.models.generate_content(...)` 동기.
- `sec_pipeline/extractor.py:68`: `client.models.generate_content(...)` 동기.
- `marketpulse/briefing/client.py:68`: 동기 API 명시적 사용, 코드 주석에 "Bug #8 회피" 명시.

**주의 필요 (비동기 API 사용)**
- `rag_analysis/services/llm_service.py:182`: `await self.client.aio.models.generate_content_stream(...)` — Django View에서 호출되는 용도이므로 Celery가 아니면 정상.
- `serverless/services/keyword_generator_v2.py:128 (_call_llm_batch)`: `async def` 함수. Celery 태스크에서 이 함수를 호출하는 경로를 확인해야 함. `serverless/tasks.py`에서 `asyncio.run()` 없이 직접 `await`하면 SIGSEGV/이벤트 루프 에러 발생.

### 단일 장애점 (Gemini)

**🔴 P0 — sec_pipeline/extractor.py (GeminiExtractor)**
- `extract_supply_chain`, `extract_business_model`: 429 포함 모든 Gemini 에러가 `raise`로 전파됨.
- Celery 태스크(`sec_pipeline/tasks.py`)에서 catch 구조를 확인해야 하나, 파이프라인 전체가 중단될 위험.

**🟡 P1 — news/services/keyword_extractor.py**
- LLM 실패 시 `FALLBACK_KEYWORDS` 3개를 반환 — 기능 저하는 있으나 서비스는 유지됨. 그러나 Daily 키워드가 fallback으로 채워지면 메인 페이지 키워드 품질이 크게 저하됨.

---

## 기타 의존성

### FRED

**호출 위치**: `macro/services/fred_client.py`

**에러 핸들링**:
- 401/403/404: 즉시 `raise_for_status()`.
- 500/502/503/504 (TRANSIENT_STATUS_CODES): max_retries=3, exponential backoff (2s, 4s, 6s).
- 일반 `RequestException`: 재시도 후 최종 raise.
- `api_request/rate_limiter.py`의 `get_rate_limiter("fred")` 사용 — 분당 120회 준수.

**메인 페이지 장애 영향**:
- `macro/services/macro_service.py`의 `get_fear_greed_index()`, `get_interest_rates_dashboard()`, `get_inflation_dashboard()`: 각각 `except Exception as e: logger.error(); return {'value': 50, ...}` / `return {'error': str(e)}` 처리.
- `get_fear_greed_index()`만 부분 폴백 값(`value: 50, label: '중립'`) 반환, 나머지는 `{'error': ...}` 반환.
- **Market Pulse 메인 대시보드는 FRED 장애 시 공포/탐욕 지수 하드코딩 fallback(`value: 50`)으로 동작하나, 금리/인플레이션/GDP 섹션은 에러 응답.**

### Neo4j

**호출 위치**: `serverless/services/neo4j_chain_sight_service.py`, `chainsight/tasks/`, `sec_pipeline/`

**연결 처리**:
- `rag_analysis/services/neo4j_driver.py`: Lazy Singleton 패턴. 연결 실패 시 `None` 반환, Django 앱은 계속 실행.
- `Neo4jChainSightService.__init__`: `get_neo4j_driver()`가 `None`이면 `logger.warning` — **fallback mode 진입 선언**.
- `is_available()`: driver가 None이면 `False` 반환. 모든 노드/관계 생성 메서드가 `if not self.is_available(): return False` 가드.
- Chain Sight 그래프 조회 (`get_n_depth_graph`): `is_available() → False`이면 빈 그래프 구조 반환.

**평가**: Neo4j 장애 대응은 프로젝트 전반에서 가장 잘 처리된 부분. Lazy Singleton + fallback mode + 캐시(5분) 3단 방어.

**주의**: `_connection_attempted = True`로 한 번 실패하면 재시도 없음. 장기 장애 후 복구 시 워커 재시작 또는 `reset_connection()` 수동 호출 필요.

### SEC EDGAR

**호출 위치**: `sec_pipeline/collector.py`, `api_request/sec_edgar_client.py`

**에러 핸들링**:
- `sec_pipeline/collector.py:89`: `requests.exceptions.RequestException` → `raise`. 파이프라인 중단.
- `sec_pipeline/collector.py:141`: CIK 조회 실패 → `return None` (상위에서 처리).
- `sec_pipeline/collector.py:157`: HTML 다운로드 실패 → `raise`. 파이프라인 중단.
- `api_request/sec_edgar_client.py:164`: 429 → `time.sleep(1)` 후 재귀 재시도. **재귀 호출이므로 429가 연속되면 스택 오버플로 위험**.
- Rate limit: `time.sleep(0.12)` (초당 8회) — SEC 공식 권장(초당 10회) 준수.

**장애 영향**: SEC Pipeline은 10-K 파싱 배치 작업. 수집 실패 시 해당 종목의 Supply Chain 및 Business Model 데이터가 누락됨. 메인 서비스 직접 영향 없음.

### Redis 캐시 장애

**Django cache backend 사용 패턴**: `django.core.cache.cache.get/set/delete`

**장애 시 동작 분석**:

| 패턴 | 위치 | 장애 시 |
|-----|------|---------|
| `cached = cache.get(key); if cached: return cached` | `serverless/services/fmp_client.py` | Redis 장애 시 `cache.get` 예외 발생. try/except 없으면 FMP API 직접 호출 못 하고 에러 전파. |
| Circuit Breaker 상태 저장 | `marketpulse/utils/circuit_breaker.py` | Redis 장애 시 `cache.get` 예외 → CB 상태 읽기 실패 → CLOSED 가정. tenacity 재시도는 계속 작동 |
| Neo4j 그래프 캐시 | `serverless/services/neo4j_chain_sight_service.py` | 캐시 미스로 매 요청마다 Neo4j 직접 조회 (성능 저하는 있으나 서비스 유지) |

**주요 위험**:
- `serverless/services/fmp_client.py`의 `cache.get/set`: try/except 없음. Redis 연결 에러는 Django `cache` 백엔드 설정에 따라 다름 (`CACHE_BACKEND=dummy`이면 자동 무시, Redis이면 Exception 전파).
- Circuit Breaker의 `cache.add/incr` (`marketpulse/utils/circuit_breaker.py:183-190`): ValueError 대비 처리는 있으나 Redis 연결 자체 실패 시 미처리.

---

## Circuit Breaker 후보

| 우선순위 | 호출 지점 | 장애 시 영향 | 도입 근거 |
|---------|---------|------------|---------|
| P0 | `stocks/services/sp500_eod_service.py` FMP | S&P 500 503개 EOD 전량 미수집 | FMP 장애 시 재시도 없이 503개 모든 요청이 실패 루프를 반복. CB로 조기 차단 후 알림 필요 |
| P0 | `macro/services/macro_service.py` FMP+FRED | 메인 Market Pulse 대시보드 렌더링 실패 | 현재 `{'error': ...}` 반환이 프론트엔드 에러 경계에 처리되는지 불명확. CB 상태를 UI에 노출하면 "현재 API 점검 중" UI 처리 가능 |
| P1 | `sec_pipeline/extractor.py` Gemini | SEC 파이프라인 배치 전체 중단 | 429 미처리 + raise 전파. Gemini 장애 시 파이프라인이 완전 중단됨 |
| P1 | `news/services/news_deep_analyzer.py` Gemini | 당일 뉴스 심층 분석 누락 | 현재는 `None` 반환으로 개별 건 skip. 연속 실패 감지하여 배치 일시 중단 필요 |
| P1 | `serverless/services/keyword_generator_v2.py` Gemini | Market Movers 키워드 빈 배열 | async 사용 여부 + 429 미처리로 이중 위험. CB + sync 전환 동시 검토 |
| P2 | `serverless/services/llm_relation_extractor.py` Gemini | Chain Sight LLM 관계 추출 누락 | 배치 간 `time.sleep(4)` 있으나 CB 없음. Redis 캐시(1시간)가 부분 완충 |
| P2 | `enhanced_screener_service.py` FMP key-metrics | 스크리너 Enhanced 필터 실패 | 최대 100개 심볼에 key-metrics 100회 호출. Rate limit 초과 시 전체 스크리너 실패 |

---

## 권장 조치 (Action Items)

### 즉시 처리 (P0)

1. **[🔴 P0] `macro/services/macro_service.py`**: `get_global_markets_dashboard()` FRED + FMP 개별 예외 분리. FMP 실패 시 FRED 데이터만으로 부분 응답 가능하도록 분리. 현재는 하나라도 실패하면 전체 `{'error': ...}` 반환.

2. **[🔴 P0] `stocks/services/sp500_eod_service.py`**: FMP 장애 시 연속 503건 에러 발생 탐지 로직 추가. `error_symbols` 비율이 임계값(예: 50%) 초과 시 조기 중단 + Celery 재시도 스케줄링.

3. **[🔴 P0] `serverless/services/keyword_generator_v2.py`**: Celery 태스크에서 호출 경로 확인. `async def _call_llm_batch`를 동기 래퍼로 변경하거나 `asyncio.run()` 적용 여부 검증. 버그 #8 위험.

### 단기 처리 (P1)

4. **[🟡 P1] `sec_pipeline/extractor.py`**: Gemini 호출에 429/rate limit 처리 추가. `json.JSONDecodeError` 이외 예외도 `{'relationships': [], 'error': ...}` 반환으로 변경 (현재 `raise`).

5. **[🟡 P1] `news/services/keyword_extractor.py`**: `_call_llm` 내에서 429 체크 추가 (현재 `except Exception` 일괄 처리). `keyword_service.py`와 동일한 패턴 적용.

6. **[🟡 P1] 전체 Gemini 호출**: `types.GenerateContentConfig`에 `timeout=60` (초) 설정 표준화. 현재 모든 호출에 timeout 미설정.

7. **[🟡 P1] `api_request/sec_edgar_client.py:164`**: 429 재귀 재시도를 루프 기반 재시도로 변경. 현재 재귀 구조는 연속 429 시 스택 오버플로 위험.

### 중기 처리 (P2)

8. **[🟡 P2] `serverless/services/fmp_client.py`**: `get_market_gainers/losers/actives` 캐시 만료 후 FMP 장애 시 stale 캐시 서빙 패턴 도입 (stale-while-revalidate). 현재 캐시 미스 + API 실패 = 에러 전파.

9. **[🟡 P2] Circuit Breaker 확장**: `serverless/services/llm_relation_extractor.py`, `news/services/news_deep_analyzer.py`에 `news/services/circuit_breaker.py`의 기존 `CircuitBreaker` 클래스 적용.

10. **[🟡 P2] `macro/services/fred_client.py` 인메모리 카운터**: `api_request/providers/fmp/client.py`의 `daily_calls` 카운터가 인메모리(워커별 독립). 다중 워커 환경에서는 일일 한도 공유 안 됨 — Redis 기반 분산 카운터 도입 또는 카운터 제거 검토.

11. **[🟡 P2] Neo4j 재연결**: `rag_analysis/services/neo4j_driver.py`의 `_connection_attempted = True` 단방향 플래그 — 일시 장애 후 복구 시 자동 재연결 불가. 주기적 health check 후 `reset_connection()` 자동 호출 로직 추가.
