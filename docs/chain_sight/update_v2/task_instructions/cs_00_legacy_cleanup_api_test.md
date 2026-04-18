# CS-0-0: 레거시 정리 + API 테스트

> **작업 번호**: CS-0-0
> **로드맵 버전**: v1.4
> **목표**: 기존 Chain Sight 코드 제거, API 접근 테스트, RelationConfidence v2.1 + SavedPath/PathAction 마이그레이션
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
grep -rn "StockRelationship\|CategoryCache" --include="*.py" .
python manage.py makemigrations serverless
python manage.py migrate
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

| 테스트 | 엔드포인트 | 200 시 영향 | 403 시 영향 |
|--------|-----------|-----------|-----------|
| FMP Stock Peers | `/stable/stock-peers` | DC-1 보강 | Finnhub만 사용 |
| Finnhub Supply Chain | `/stock/supply-chain` | DC-6 불필요! | 6-Phase 유지 |
| Finnhub ETF Holdings | `/etf/holdings` | DC-2 간단 해결 | CSV 방식 |
| Finnhub Insider Transactions | `/stock/insider-transactions` | CS-2-1 InsiderSignal 구현 | 보류 |
| FMP Revenue Segmentation | `/stable/revenue-product-segmentation` | CS-2-1 SensitivityProfile 구현 | 보류 |

---

## 3단계: 스키마 마이그레이션

### 3-1. RelationConfidence v2.1 업데이트
- `RELATION_CONFIDENCE.md` 섹션 7 참조
- `normalize_pair` 유틸 함수 추가 (undirected 사전순 정규화)
- CUSTOMER_OF 관련 코드 제거 (있으면)

### 3-2. SavedPath / PathAction 모델 생성 ← v1.4 신규

**Canonical 스키마: CS-6-1 (cs_61_saved_path_model.md) 참조.**
CS-6-1에 상세 필드 정의, 테스트 코드, 설계 판단 근거가 있음. 여기서는 요약만 기술.

```python
# chainsight/models.py에 추가

class SavedPath(models.Model):
    class Status(models.TextChoices):
        WATCHING = 'watching', 'Watching'
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'
        RESOLVED = 'resolved', 'Resolved'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             null=True, blank=True, related_name='saved_paths')
    # MVP: 단일 사용자 가정 — user nullable

    path_nodes = models.JSONField(help_text='ticker 배열. 예: ["NVDA", "TSM", "ASML"]')
    summary_path = models.JSONField(blank=True, null=True, help_text='landmark ticker 배열')
    path_signature = models.CharField(max_length=80, blank=True, null=True,
        help_text='경로 성격 태그: "공급망 중심 · 반도체 장비"')
    edge_snapshot = models.JSONField(blank=True, null=True,
        help_text='저장 시점 관계 스냅샷')
    why_now_snapshot = models.JSONField(blank=True, null=True)

    source_center = models.CharField(max_length=10, blank=True, null=True)
    source_slot = models.CharField(max_length=40, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.WATCHING, db_index=True)
    recheck_count = models.PositiveIntegerField(default=0,
        help_text='Recheck 횟수. 2회 이상 + 24h → watching→active')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = 'chainsight_saved_path'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['status', '-updated_at']),
        ]

class PathAction(models.Model):
    class ActionType(models.TextChoices):
        WATCH = 'watch', 'Watch'
        EXPAND = 'expand', 'Expand'
        ALTERNATIVES = 'alternatives', 'Alternatives'
        RECHECK = 'recheck', 'Recheck'
        ARCHIVE = 'archive', 'Archive'
        RESOLVE = 'resolve', 'Resolve'

    saved_path = models.ForeignKey(SavedPath, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=20, choices=ActionType.choices, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'chainsight_path_action'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['saved_path', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]
```

⚠️ **cs_00 ↔ cs_61 통일 완료 (v1.4)**:
- `full_path` → `path_nodes` (의미 명확화)
- `path_length` 제거 (SerializerMethodField로 제공)
- `action` → `action_type` (Django 내장 패턴 충돌 방지)
- `primary_intent` 제거 (MVP 불필요, source_slot으로 충분)
- `recheck_count` 추가 (watching→active 전이 효율화)
- `user` nullable (MVP 단일 사용자)

### 3-3. 마이그레이션 실행

```bash
python manage.py makemigrations chainsight
python manage.py migrate
python manage.py showmigrations chainsight  # → 14개 테이블 [X] 확인
```

---

## 완료 기준

```
□ serverless/ Chain Sight 코드 제거 완료
□ frontend/ Chain Sight 코드 제거 + 빌드 성공
□ API 테스트 5개 실행 → decisions/003_api_access_test.md 기록
□ RelationConfidence v2.1 마이그레이션 완료
□ SavedPath, PathAction 모델 생성 완료
□ normalize_pair 유틸 함수 추가
□ showmigrations → 14개 테이블 [X]
```

→ **다음**: cs_01 (migrations 검증)

**END OF DOCUMENT**
