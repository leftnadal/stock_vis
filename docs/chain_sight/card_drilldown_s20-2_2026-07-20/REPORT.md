# ⑳-2 — 관계 카드 드릴다운 (C안: 카드 기본 + 그래프 토글) 보고서

- **세션**: 실행 · 브랜치 `monorepo/sess-20-2-card-drilldown`
- **배포**: origin/main `2c74160` (마이그레이션 0 — 계약 준수)
- **결론**: ego 드릴다운 기본 화면을 **관계 카드 리스트**로 교체, 그래프는 [지도] 토글로 격하. 카드 필드·이벤트 보드 티커·리더보드 delta 전건 라이브 검증 완료.

---

## STEP 0 — 실측

| 항목 | 결과 |
|---|---|
| worktree 최신성 | origin/main `3fa59b6` 일치(behind 8→브랜치 생성) |
| **ego 필드 3분류** | `relation_type`·`confidence`(truth_score) **응답에 있음** / `evidence_count`(`RelationConfidence.evidence_count_total`)·`last_mentioned`(`last_observed_at`) **모델에 있으나 미노출→additive**. **근원 부재 0 → HALT 없음** |
| **SymbolCentrality max(as_of)** | **2026-07-20**, 매일 555행(07-16~20 연속) → **중심성 beat 정상 실행((b) 미실행 아님)**. ⑳-V "—"는 rank_delta 0 추정(S5로 검증) |
| ego 웜 | cold 444ms → warm 20~62ms(off)·35ms(on). ⑳-D 405ms=콜드 워밍업, 회귀 아님 |
| 이벤트 보드 티커 | `get_event_board` 양쪽 경로에 members 티커 **로컬 보유·응답 미노출** → additive(신규 쿼리 0) |
| baseline | pytest chainsight 222 · vitest chainsight 172 |

## S1 — 백엔드: ego API 카드 필드 additive

- `edge_qs.values()`에 `evidence_count_total`·`last_observed_at` 컬럼 추가(동일 쿼리·N+1 없음). 응답 `edges[]`에 `evidence_count`·`last_mentioned`(YYYY-MM-DD) 가산. 기존 필드 불변.
- 테스트: 카드 필드 존재·기본값·쿼리 수 상수(≤8) 3종.

## S4 백엔드 — 이벤트 보드 members

- `get_event_board` 양쪽 경로(event_groups·theme_tags)에 `members` 티커 목록 가산(로컬 보유). serializer `members` 필드 추가. 테스트 3종(ON/OFF/serializer).

## S2 — 프론트: 관계 카드 리스트 (기본 뷰, C안)

- `EgoDrilldown`(토글 래퍼): ego 모드에서 `[목록][지도]` 토글, **기본=목록**. 비-ego는 MarketGraphCanvas 그대로(불변).
- `RelationCardList`(ego API 소비): 관계 배지(RELATION_STYLES 재사용=신규색0)·**신뢰도 숫자+바**·근거 N건·최근 언급일·**신뢰도 내림차순 기본**·**절단 총량 "전체 M개 중 N개"**·더 보기·카드 클릭 드릴다운. 빈/오류는 GraphStatePanel 재사용.
- `cardListConfig` 상수 분리(정렬·표시·배지 매핑).
- `RelationCardPanel`: 구 Neo4j(`useNeighbors`) ego 브랜치 **제거**(중복·동결로 깨진 경로) — 섹터 프리-포커스 시드 카드는 보존.
- 테스트: cardListConfig(정렬·배지·노드맵) 8 + RelationCardList(정렬·절단·더보기·빈/오류·클릭) 6 + EgoDrilldown(토글·기본목록·지도전환) 3.

## S3 — 그래프 최소 튜닝 ([지도] 토글 내부)

- **②뭉침**: `onEngineStop`에서 fx/fy 주입 시 `node.x/y`도 radial 좌표로 동기화 → `zoomToFit`이 force 위치가 아닌 **실제 렌더(radial) 배치** 기준으로 fit(초기 뭉침·좌측 치우침 해소). padding 80→90.
- **④원위치 회귀**: 안정화 후 fx/fy 고정(재가열 방지)은 기존 유지, 드래그·줌 보존.
- 굵기·라벨 회피는 OUT(수렁 방지). 시각 검증=S6.

## S4 표시 — 이벤트 보드 카드 제목 티커 병기

- `formatMemberTitle`(상위 4 + "외 N", 대문자)로 티커 병기를 주표기, 기존 키워드 라벨은 부제 강등. members 부재 시 폴백(구버전 응답 호환). 표시 가공만·데이터 무변경.

## S5 — 리더보드 "—" 의미 분리

- `RankDelta`: `null`(전일 없음)=**NEW**, `0`(불변)=**—**, `±n`=▲▼. 표시층만(API가 이미 null/0 구분 제공).

## S6 — 라이브 렌더 검증 (배포 후 즉시)

| # | 캡처 | 결과 |
|---|---|---|
| ① | NVDA 카드 리스트 | ✅ 기본=목록, "전체 224개 관계 중 12개 표시(상위 50개까지 제공)", 관계 배지·신뢰도85+바·근거N건·날짜, 신뢰도 정렬 |
| ② | [지도] 토글 그래프 | ✅ NVDA **중앙 정렬**(⑳-V 좌측 치우침 개선), 방사 배치. 중앙 라벨 겹침 잔존(OUT) |
| ③ | 이벤트 보드 제목 | ✅ "HUBB·WAB·LYV·CPAY 외 2" / "KLAC·LRCX·AMAT·TER 외 3" 티커 병기 + 키워드 부제 |
| ④ | 리더보드 delta | ✅ 전 행 "—" — **API `rank_delta` 실측 전부 0**(null 아님, as_of 07-20) → S5가 정확히 "—"(불변) 렌더. **⑳-V "—"=데이터 부재 아님 확정**. NEW/▲▼은 단위 테스트로 검증(라이브엔 null-delta 심볼 부재로 미발생) |

- **이상 0 · fix-forward 불요**.

## 배포 (규칙 A 대행 — 지시서 명시 인가)

- 지시서 "배포 — 규칙 A 대행. migrate 무발생 계약" + §H 안전 게이트. 6 커밋 main 머지(ff)·push → `sv sync` 3트리 `2c74160`+celery/daphne 재기동.
- **★ :3000 = prod 빌드(`npm run start`)** ([[reference_web_runtime_prod_build]]) → sv sync만으론 미반영, **`npm run build` 재빌드 + `npm run start` 재시작** 수행(FE 배포 필수 절차). daphne 401·:3000 200 확인.

## 테스트 결과

- pytest chainsight: 222 → **228**(+6: ego 카드 3·이벤트 members 3). 회귀 0.
- vitest chainsight: 172 → **192**(+20: cardListConfig 8·RelationCardList 6·EgoDrilldown 3·eventBoardTitle 4·RelationCardPanel 갱신 −1). 회귀 0.
- tsc 0 · 마이그레이션 0(계약).

## 잔여/후속 (⑳-3 이관)

- 백본 전체 조망 + 섹터 모드 거취 통합 → ⑳-3(TASKQUEUE). "지도는 원할 때만" 철학 하 재설계.
- 이벤트 보드 제목 본개선(LLM 네이밍) = CS-P2-LLM(BOUNDARY-LLM 종속).
