# CS-0-0: 레거시 정리 + API 테스트

> **작업 번호**: CS-0-0
> **목표**: 기존 Chain Sight 코드 제거, API 접근 테스트, RelationConfidence v2.1 마이그레이션
> **예상 소요**: 2~4시간
> **선행 조건**: 없음 (Phase 0 첫 작업)
> **산출물**: 부록 G 체크리스트 완료 + `decisions/003_api_access_test.md`

---

## 1단계: 레거시 코드 제거

### 1-1. 백엔드 (serverless/)

**제거 대상:**
- views.py → `chain_sight_*_api` 6개 뷰 함수
- services/ → `chain_sight_stock_service.py`, `category_generator.py`, `relationship_service.py` 삭제
- models.py → `StockRelationship`, `CategoryCache` 모델 제거
- urls.py → `chain-sight/*` 라우트 제거

**보존 대상** (DC-2까지 유지):
```python
# LEGACY_KEEP_UNTIL_DC2 — DC-2 완료 시 Neo4j :Theme + HAS_THEME로 대체 후 제거
class ETFProfile(models.Model): ...
class ETFHolding(models.Model): ...
class ThemeMatch(models.Model): ...
```

**실행:**
```bash
# 참조 확인
grep -rn "StockRelationship\|CategoryCache" --include="*.py" .
# 제거 후 마이그레이션
python manage.py makemigrations serverless
python manage.py migrate
# 잔여 확인 (ETF + LEGACY 태그 제외)
grep -rn "chain_sight\|ChainSight\|chain-sight" --include="*.py" serverless/ \
  | grep -v "LEGACY_KEEP_UNTIL_DC2" | grep -v "ETF"
```

### 1-2. 프론트엔드 (frontend/)

**제거 대상:**
- `components/chain-sight/` (8개 파일)
- `hooks/useChainSight*.ts` (3개)
- `services/chainSightService.ts`
- `types/chainSight.ts`
- `utils/relationshipTagStyles.ts`
- `app/chain-sight/page.tsx`
- 종목 상세 Chain Sight 탭 → "Coming Soon" 또는 숨김

**검증:**
```bash
cd frontend && npm run build
grep -rn "chainSight\|chain-sight\|ChainSight" --include="*.ts" --include="*.tsx" frontend/
```

---

## 2단계: API 접근 테스트

5개 엔드포인트 테스트 → `docs/chain_sight/decisions/003_api_access_test.md`에 기록.

### 테스트 1: FMP Stock Peers
```python
import requests; from django.conf import settings
r = requests.get("https://financialmodelingprep.com/stable/stock-peers",
    params={"symbol": "AAPL", "apikey": settings.FMP_API_KEY})
print(f"Status: {r.status_code}\nResponse: {r.text[:500]}")
```
- 200 → DC-1 보강 / 403 → Finnhub만 사용

### 테스트 2: Finnhub Supply Chain
```python
r = requests.get("https://finnhub.io/api/v1/stock/supply-chain",
    params={"symbol": "AAPL", "token": settings.FINNHUB_API_KEY})
print(f"Status: {r.status_code}\nResponse: {r.text[:500]}")
```
- 200 → DC-6 불필요! / 403 → 6-Phase 유지

### 테스트 3: Finnhub ETF Holdings
```python
r = requests.get("https://finnhub.io/api/v1/etf/holdings",
    params={"symbol": "SPY", "token": settings.FINNHUB_API_KEY})
```
- 200 → DC-2 Finnhub 사용 / 403 → CSV 방식

### 테스트 4: Finnhub Insider Transactions
```python
r = requests.get("https://finnhub.io/api/v1/stock/insider-transactions",
    params={"symbol": "AAPL", "token": settings.FINNHUB_API_KEY})
```
- 200 → CS-2-1 InsiderSignal 구현 / 403 → 보류

### 테스트 5: FMP Revenue Segmentation
```python
r = requests.get("https://financialmodelingprep.com/stable/revenue-product-segmentation",
    params={"symbol": "AAPL", "period": "annual", "apikey": settings.FMP_API_KEY})
```
- 200 → CS-2-1 SensitivityProfile 구현 / 403 → 보류

### 결과 기록 템플릿

`docs/chain_sight/decisions/003_api_access_test.md`:
```markdown
# Decision 003: API 접근 테스트 결과
> **테스트 일시**: 2026-04-XX

| # | 엔드포인트 | 상태코드 | 영향 |
|---|-----------|---------|------|
| 1 | FMP Stock Peers | ??? | (기록) |
| 2 | Finnhub Supply Chain | ??? | (기록) |
| 3 | Finnhub ETF Holdings | ??? | (기록) |
| 4 | Finnhub Insider Transactions | ??? | (기록) |
| 5 | FMP Revenue Segmentation | ??? | (기록) |

## 의사결정
- DC-2 방식: (결정)
- CS-2-1 범위: GrowthStage ✅, CapitalDNA ✅, Sensitivity (결과), Insider (결과)
- DC-6 필요 여부: (결정)
```

---

## 3단계: RelationConfidence v2.1 마이그레이션

### 모델 업데이트

`chainsight/models.py`의 RelationConfidence를 v2.1로 수정 (`RELATION_CONFIDENCE.md` 섹션 7 참조).

핵심 필드:
- 식별: symbol_a, symbol_b, relation_type, relation_category(truth/market), canonical_direction
- 상태: relation_status (hidden/weak/probable/confirmed/stale)
- 점수: truth_score, market_score(MVP null), investment_relevance(MVP null)
- 증거: evidence_tier_best(1/2/3), evidence_count_total, evidence_count_independent, evidence_sources(JSONB), bool 7개
- 설명: relation_basis_summary
- 시간: first_observed_at, last_observed_at, last_verified_at, stale_threshold_days
- 동기화: synced_to_neo4j, score_version

### normalize_pair 유틸

```python
# chainsight/utils.py
def normalize_pair(symbol_a: str, symbol_b: str) -> tuple[str, str]:
    if symbol_a <= symbol_b:
        return symbol_a, symbol_b
    return symbol_b, symbol_a
```

### CUSTOMER_OF 코드 제거
```bash
grep -rn "CUSTOMER_OF\|customer_of" --include="*.py" .
```

### 마이그레이션 실행
```bash
python manage.py makemigrations chainsight
python manage.py migrate
python manage.py showmigrations chainsight  # 12개 [X] 확인
```

---

## 완료 기준

```
□ serverless/ Chain Sight 코드 제거 (ETF 3개만 LEGACY 태그 보존)
□ frontend/ Chain Sight 코드 제거 + 빌드 통과
□ API 테스트 5개 실행 → decisions/003 기록
□ RelationConfidence v2.1 마이그레이션 완료
□ normalize_pair 유틸 추가
□ showmigrations 12개 [X]
□ Neo4j 서버 구동 확인 + neo4j-driver 설치
```

→ **다음**: cs_01

**END OF DOCUMENT**
