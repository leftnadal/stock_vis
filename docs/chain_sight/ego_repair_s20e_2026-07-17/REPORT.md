# ⑳-E — ego 동선 복구 (URL 계약 교정 + 시드 게이트 해제) 보고서

- **세션**: 실행 · 브랜치 `monorepo/sess-20e-ego-repair`
- **배포**: origin/main `bea1de0` (마이그레이션 0 — 계약 준수)
- **결론**: 리더보드→ego 동선 **완전 복구**. 비-시드 심볼(NVDA 등)도 PG ego 직행 렌더. 빈-이웃/로드실패/섹터불가 3상태 명시 분리. ⑳-D 복구 후보 ①②③⑤ 구현·라이브 검증 완료(④는 ⑳-2로 OUT).

---

## STEP 0 — 실측

- **worktree 최신성**(⑳-D stale 교훈): 진입 시 HEAD=4f346c8, origin/main=87dc92e(behind 8) → `git checkout -b … origin/main`로 **87dc92e 정합 확인 후 착수**. 진행 중 origin/main이 87dc92e→…→bea1de0로 다중 전진, 매 push 전 fetch+merge(union, 충돌 0).
- **근인 재확인**(87dc92e): fetchEgo `/chainsight/${sym}/ego/`(chainsightService.ts:85) vs BE `ego/<sym>/`(urls.py:36); page.tsx:24 시드 게이트.
- **ego 웜 재측정**(⑳-D 405ms vs ⑰ 13ms 괴리 해명): NVDA 연속 3회 — cross_edges=off `891ms→41ms→111ms`, on `138ms→36ms→35ms`. **cold #1 워밍업(891ms)이 괴리 원인, 웜 ~35ms 건강**. 회귀 아님(관찰만).
- **baseline**: pytest chainsight ego 14 passed · vitest chainsight 15파일 160 passed.

## S1 — URL 계약 교정 + 계약 테스트 (후보 ①)

- `frontend/services/chainsightPaths.ts` 신설 — `egoPath(symbol)` **단일 소스**(`/chainsight/ego/${SYM}/`). fetchEgo가 이를 경유(하드코딩 제거).
- 계약 테스트: FE `chainsightPaths.test.ts`(경로 문자열·회귀 가드) + BE `test_ego_api.py::TestEgoRouteContract`(FE 경로가 EgoGraphView로 resolve, 구 `<sym>/ego/`는 Resolver404).

## S2 — 시드 게이트 해제 (후보 ②)

- `initializeFocusExploration(sector: string|null, symbol)` — sector nullable. `page.tsx` focus 핸들러가 시드 여부 무관 초기화(비시드=sector null → 종목만 trail, 시드=섹터 브레드크럼 보존 = additive).
- 테스트: `explorationStoreFocus.test.ts`(null/시드 분기) + `focusEgoGate.test.tsx`(페이지 effect 비시드/시드).

## S3 — 빈 상태 2분리 (후보 ③)

- `GraphStatePanel.tsx` 신설 — `empty-neighbors`(관계 0·오류 아님) / `load-error`(ego 실패·재시도) / `sector-unavailable`(S4). "테마" 미사용.
- MarketGraphCanvas: useEgo/useSectorGraph의 `isError`·데이터로 분기(조용한 빈 캔버스 금지). 테스트 `GraphStatePanel.test.tsx`.

## S4 — SectorGraphView 예외 견고성 (후보 ⑤) + 라이브 후속 2건

- **BE**: `except (GraphConnectionError, GraphQueryError)` → 503 `{code:"graph_unavailable"}`(500 누출 차단). 테스트 `test_sector_graph_resilience.py`(파라미터 2종).
- **FE 후속(라이브 실증)**: 배포 후 실화면에서 섹터 클릭 시 sector-unavailable이 **미발화**(조용한 빈 캔버스) 발견. 진단(react-query 캐시 실측): sector 쿼리가 첫 503 후 **`fetchStatus='paused'`(status='pending')** 에 갇혀 `isError` 미도달 — onlineManager 오프라인 오판(navigator.onLine=true인데도). ego/seeds는 첫 시도 성공이라 무영향, **실패 쿼리의 retry 직전에만 pause**.
  - 수정: useSectorGraph·useEgo에 **`networkMode:'always'` + `retry:false`**. retry:false가 첫 실패를 즉시 error 확정(retry-pause 경로 제거) → 패널 발화. 사용자 재시도는 "다시 시도" 버튼 제공.

## S5 — 라이브 렌더 검증 (DoD 게이트)

| # | 시나리오 | 결과 |
|---|---|---|
| BEFORE | `?focus=NVDA` (구 코드) | 빈 "섹터를 선택하세요" — 고장 재현 |
| #1 | NVDA(비시드) 리더보드 "관계망 →" → ego | ✅ ego 그래프 렌더(center NVDA + 이웃 48) |
| #2 | AAPL(비시드) 직접 URL focus | ✅ ego 그래프 렌더 |
| #3 | ABCB(관계 0) focus | ✅ "아직 확인된 관계가 없어요"(empty-neighbors) |
| #4 | Healthcare 섹터 칩(Neo4j 동결) | ✅ "섹터 관계망은 현재 이용할 수 없어요" + 재시도(자연 흐름) |

- 검증 방식: react-query 캐시를 실측(fiber에서 QueryClient 추출)해 status/fetchStatus 확인 → 좌표가 아닌 실제 상태·렌더 판정. #4는 강제 error 주입으로 패널 렌더 코드 선검증 후, retry:false 배포로 **자연 흐름** 재현.

## 배포 (규칙 A 대행 — 지시서 명시 인가)

- 지시서 "배포 (규칙 A 대행) … 머지 → push → sv sync → daphne·web 재시작" 인가. §H D-DEPLOY-DELEGATE 안전 게이트(worktree clean·자기 세션 브랜치·MERGE_HEAD 부재·마이그레이션 0) 준수.
- 절차: 4(+2 후속) 커밋 main 머지 → push → `sv sync`(런타임 3트리 origin/main 정합 + celery/daphne 재기동) → next dev :3000 재시작(훅 옵션 변경은 Fast Refresh가 놓쳐 클린 재시작 필요) → 라이브 재확인.
- **마이그레이션 0 확인**(계약): 모델 무변경(S4=뷰 예외처리).

### DoD 편차(정직 기록)

- **S5(라이브)를 배포 전 완결하지 못하고 배포-후-검증으로 수행**. 이유: 편집 worktree는 node_modules 심링크로 `next dev` 기동 불가(#48), JWT는 localStorage(포트별 격리)라 별도 포트 인증 승계 불가 → 미머지 프론트의 격리 검증이 런타임상 불가. 대안으로 **배포 전 :3000에서 BEFORE(고장) 캡처 → 배포 → AFTER 캡처**. 코드는 배포 전 tsc0·vitest172·pytest222 GREEN. 라이브에서 S4 결함 2건을 잡아 fix-forward(후속2)로 종결 — feedback_ui_slice_live_screenshot 규약의 가치 재실증.

---

## 테스트 결과

- vitest chainsight: 160 → **172 passed**(+12: chainsightPaths 3·explorationStoreFocus 2·focusEgoGate 2·GraphStatePanel 5). 회귀 0.
- pytest chainsight: **222 passed**(+4: ego contract 2·sector resilience 2). 회귀 0.
- tsc: 0 error. 신규 red 0.

## 잔여/후속

- next dev :3000은 **유지**(병진 5관점 메모용). 단 세션 백그라운드 프로세스가 하네스에 리핑되는 정황 있음(재기동 반복) → TASKQUEUE에 "프론트 서빙 방식 정리(LaunchAgent 편입)" 이관.
- 섹터 모드 거취(PG 전환 vs 숨김)는 ⑳-2로 이관(TASKQUEUE).
