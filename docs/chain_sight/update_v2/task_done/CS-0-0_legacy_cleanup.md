# CS-0-0: 레거시 정리 + API 테스트 + 스키마 마이그레이션

> **완료일**: 2026-04-18
> **브랜치**: `data_structure_remodeling_V1`

## 1단계: 레거시 코드 제거

### 백엔드 (serverless/)
- `chain_sight_*_api` 6개 뷰 함수: **이미 제거됨** (이전 작업에서 처리)
- `chain_sight_stock_service.py`, `category_generator.py`, `relationship_service.py`: **이미 삭제됨**
- `chain-sight/*` 라우트: **이미 제거됨** (urls.py에 `# LEGACY REMOVED` 주석)
- `StockRelationship`, `CategoryCache` 모델: **보존** — supply_chain_service, institutional_holdings, regulatory_service 등 7개 서비스에서 활발히 사용 중. 별도 마이그레이션 계획 필요
- ETF 모델 3개 (`ETFProfile`, `ETFHolding`, `ThemeMatch`): **보존** — `LEGACY_KEEP_UNTIL_DC2` 태그 유지

### 프론트엔드 (frontend/)
- `components/chain-sight/` (구 컴포넌트): **이미 삭제됨**
- `hooks/useChainSight*.ts`: **이미 삭제됨**
- `services/chainSightService.ts`: **이미 삭제됨** (새 `chainsightService.ts` 사용 중)
- `types/chainSight.ts`: **이미 삭제됨** (새 `chainsight.ts` 사용 중)
- `app/chain-sight/page.tsx`: **이미 삭제됨** (새 `app/chainsight/page.tsx` 사용 중)
- 스크리너 `ChainSightPanel` 참조: **제거 완료** (import, state, 버튼, 패널 렌더 모두 제거)
- 종목 상세 Chain Sight 탭: **유지** (MiniView + "Chain Sight에서 보기" 딥링크)
- TypeScript 빌드 확인: **에러 0건**

## 2단계: API 접근 테스트

| # | 엔드포인트 | 결과 | 영향 |
|---|-----------|------|------|
| 1 | FMP `/stable/stock-peers` | **200** | DC-1 peer 보강 가능 |
| 2 | Finnhub `/stock/supply-chain` | **403** | 6-Phase SEC 파이프라인 유지 |
| 3 | Finnhub `/etf/holdings` | **403** | CSV/SPDR XLSX 방식 유지 |
| 4 | Finnhub `/stock/insider-transactions` | **200** | CS-2-1 InsiderSignal 구현 가능 |
| 5 | FMP `/stable/revenue-product-segmentation` | **200** | CS-2-1 RevenueStructure 구현 가능 |

상세: `decisions/003_api_access_test.md`

## 3단계: 스키마 마이그레이션

### RelationConfidence v2.1
- `neo4j_dirty`, `previous_status`, `neo4j_synced_at` 필드: **이미 적용** (migration 0005)
- `save()` 오버라이드 (상태 전이 추적 + dirty 자동 설정): **구현됨**

### SavedPath / PathAction (v1.4 확정 스키마)
- `chainsight/models/saved_path.py` 생성
- Migration `0006_add_savedpath_pathaction` 적용
- SavedPath: `path_nodes`, `summary_path`, `path_signature`, `edge_snapshot`, `why_now_snapshot`, `source_center`, `source_slot`, `status`, `recheck_count`
- PathAction: `saved_path` FK, `action_type`, `metadata`
- user FK nullable (MVP 단일 사용자)

### normalize_pair
- `chainsight/utils.py`에 **이미 존재** — undirected 사전순 정규화

### 테이블 수
- `showmigrations` → 6개 마이그레이션 전부 [X]
- chainsight 앱 모델: **14개** ✅

## 변경된 파일

| 파일 | 변경 |
|------|------|
| `chainsight/models/saved_path.py` | SavedPath + PathAction 모델 생성 (신규) |
| `chainsight/models/__init__.py` | SavedPath, PathAction import 추가 |
| `chainsight/migrations/0006_add_savedpath_pathaction.py` | 마이그레이션 (자동 생성) |
| `frontend/app/screener/page.tsx` | ChainSightPanel 참조 제거 |

## 완료 체크리스트

```
[x] serverless/ Chain Sight 코드 제거 완료
[x] frontend/ Chain Sight 코드 제거 + 빌드 성공
[x] API 테스트 5개 실행 → decisions/003_api_access_test.md 기록
[x] RelationConfidence v2.1 마이그레이션 완료
[x] SavedPath, PathAction 모델 생성 완료
[x] normalize_pair 유틸 함수 확인
[x] showmigrations → 14개 테이블 [X]
```

→ **다음**: cs_01 (migrations 검증)
