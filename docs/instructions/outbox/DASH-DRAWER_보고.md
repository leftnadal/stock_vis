판정: **합격(착지 대기·push 전 상신)** — S1~S5 전부 구현 · 게이트 4종 GREEN · DoD 구획 9파일 전량 `components/eod/**` 안 · 육안 5항 확인 · 코드 커밋 전 상신.

① S0 base: origin/main **`76a2b651`**(디렉터 관측 `0eb66df5`에서 +24). worktree `~/worktrees/sv-dash-drawer`(wt-open.sh·브랜치 `monorepo/sess-dash-drawer`). `land.sh`·`approvals/` **부재** → 현행 절차.
② S0 기준선: health **✅21/⚠1/❌0** · vitest eod **14 files/129** · tsc 0.
③ **S0-5 모집단 재측정(카드 12개 `stocks_by_score` 전수, 16일 만)**: 시총 min **$0.00B**(결측 종목 존재) p10 $13.19B p25 $21.96B **med $48.35B** p75 $101.53B · 거래대금 **min $129.9M** p25 $526.0M med $920.7M.
   **★"아무것도 거르지 못하는 옵션" = 50건 / 72(카드12×옵션6)** → **전제 유효, S0 게이트 통과**(0건이 아님).
   거래대금 3옵션은 **12/12 카드 전부 죽음**(최소 거래대금이 $129.9M이라 `$50M+`조차 무력). 시총 `$1B+`는 9/12 카드에서 죽음, `$10B+` 4/12, `$50B+` 1/12(P3).
   09-03 대비: 시총 min $7.03B→**$0.00B**(악화 — `market_cap` 결측/0 종목 유입), 거래대금 min $181M→$129.9M. **전반적으로 09-03보다 더 죽었다.**
④ **S0-6 pip 색 단독 인코딩 = 아님(위반 없음·HALT 불요)**: `RecommendationCard.tsx:20~32`가 `role="img"` + `aria-label="신호 축 6개 중 N축: 라벨…"` + pip마다 `title={SIGNAL_CATEGORY_LABELS[cat]}` + `data-axis`/`data-filled` 보유. → (d)는 "색상만 조정, 낮은 우선순위" 경로 → **이번 슬라이스 미집행**(생략 가능 명시분).
⑤ **S0-7 `formatCompactUSD` 두 구현 = 문자 단위 완전 동일**(diff 0) → (f) 단순 이동 안전. `components/eod/format.ts` 신설, 양쪽 import.
⑥ **S0-8 섹터 표기 13종 · 대문자 변종 2종**: `TECHNOLOGY` 2건(vs `Technology` 186건) · `FINANCIAL SERVICES` 4건(vs `Financial Services` 122건). 라이브 드로어에 **`E-Commerce`**도 관측. 정규화 안 함(baker 소관) — 개수 병기가 `TECHNOLOGY (1)`과 `Technology (36)`을 나란히 드러내 **증거로 남는다**.
⑦ S1 `countByOption(stocks, filters, map, axis, value)` = `applyScannerFilters({...filters,[axis]:value}).length`. **다른 축 현재 선택 유지** · **판정식 복제 0**(재사용). `buildOptionCounts`로 전수 집계, 소비처 `SignalDetailSheet`에서 **useMemo 한 겹**.
⑧ S2 표시 규칙(모두 `<select>/<option>` 기준): 개수 병기 · 못 거르는 옵션 미렌더 · **전체(value 0)와 현재 선택은 절대 미숨김** · 결과 0은 `disabled`+`(0)` · 축 전멸 시 `<select>` 통째 미렌더 · 뉴스 버튼 동일 규칙(켜져 있으면 유지) · **`SORT_OPTS`·임계 상수 `value` 무변경**(라벨 문자열만 조립).
⑨ S3 ⑦-2: 래퍼 `key={`${sortBy}-${minAxes}-${sector}`}` **제거**(행 key `stock.symbol`이 안정적). `animate-fadeIn` **유지**. S4 ⑦-3: `StockRow`를 `memo`(비교 = `symbol` + `axisCount`).
⑩ S5: (f) 복제 해소 · (g) 추천 드로어에 **위험 섹션** 추가(값 없으면 섹션째 생략) · (d) 미집행(④ 사유).
⑪ 게이트: vitest eod **129 → 144**(+15 · 실패 0) · 전체 **181 files / 1413 passed / 0 failed** · tsc **0** · eslint **0** · health **✅21/⚠1/❌0 = 기준선 동일(신규 델타 0)**.
⑫ **DoD 구획(점 3개) = 9파일, 전량 `frontend/components/eod/**` + `__tests__/eod/**`. 구획 밖 0건.** `app/page.tsx`·`types/eod.ts`·`charts/**` 무접촉(지시서 예상과 일치).
⑬ 신규 테스트: 요구 6종 전건 + 추가. `현재 선택된 옵션은 숨김 조건에 걸려도 렌더`(🔴 select value↔DOM 정합) 포함. `optionCounts` 미지정 시 종전 동작 유지도 박제.
⑭ **육안 5항(dev :3100 실데이터)**: ⑴ 거래대금 `<select>` **사라짐** ✅ ⑵ 남은 옵션 개수 병기 ✅(`$50B+ (78)`·`Technology (36)`) ⑶ 합류 2축+ 적용 시 목록 **151→71**인데 **래퍼·첫 행·스파크라인 SVG 노드가 전부 동일**(재생성 0) ✅ ⑷ 래퍼 노드 동일 = `animate-fadeIn` 재생 안 됨(의도된 변화) ✅ ⑸ 추천 드로어 4섹션(한 줄 요약·세 관점·체급·기술·**위험**) ✅.
   **극단 케이스 실증**: 1종목 카드(`매집 의심`)에서 섹터·거래대금·뉴스가 **전부 미렌더**, `시총 전체 (1)`·`합류 전체 (1)`만 남음. 2축+ 적용 후 개수 전량 재계산(`Technology 36→20`·`$50B+ 78→32`), `E-Commerce (0)[disabled]` 관측.
⑮ 배포: **미집행**(push 전 상신). frontend 변경 있음 → 착지 후 `npm run build`만(`npm ci` 금지). 리빌드 직전·직후 서빙 트리 HEAD 대조 예정(2026-09-19 신규 규율).
⑯ 착지 해시: **미착지**. 브랜치 `monorepo/sess-dash-drawer`, base `76a2b651`.
⑰ 채번 후보(번호 미부여): (a) **거래대금 필터 임계 설계 실패가 재확인됨** — 옵션 3개 전부가 12/12 카드에서 무력, 유니버스 기준으로 만든 임계가 S&P500급 목록에 안 맞는다. F5+F6은 증상을 가릴 뿐 임계 재설계는 별건 · (b) **`market_cap` 0/결측 종목 유입**(시총 min $0.00B, 09-03엔 $7.03B) — `$1B+`가 "거르는" 1건이 실은 결측 종목이라 필터 의미가 왜곡 · (c) 섹터 표기 변종 3종(`TECHNOLOGY`·`FINANCIAL SERVICES`·`E-Commerce`, baker 정규화 누락) · (d) **inbox에 `DASH-DRAWER.md` 부재** — 이 지시서는 파일이 아니라 대화로 전달됨(0번 게이트 우회). DASH-RECO-LAND가 "파일로 놓는다"고 정한 규율과 어긋남.

[정정 2026-09-22, 디렉터 실측] (d) "inbox에 DASH-DRAWER.md 부재"는 사실이 아님.
본체 `~/Desktop/stock_vis/docs/instructions/inbox/DASH-DRAWER.md` 는 **12,768바이트로 실재**한다.
다만 **untracked**이므로 origin/main에서 만든 워크트리에는 존재하지 않는다 — 실행자가 보지 못한
것은 정확한 관측이며, 원인은 디렉터가 놓는 inbox 파일이 어느 브랜치에도 커밋되기 전까지
워크트리에서 보이지 않는 구조에 있다. 규율 위반 제기 자체는 옳았음. 처방은 0번 게이트를
"본체 절대경로에서 읽어 복사·커밋"으로 명시하는 것(README 수정은 OPS 트랙 위임).
  ※ 실행자 재실측: 디렉터 문안의 mtime "09-19 04:55"는 실측과 다름 — `stat` 결과 **2026-09-19 13:55:57**.
    바이트 수(12,768)와 untracked 판정은 디렉터 실측과 일치. 시각만 정정한다.

## 착지 (2026-09-22)

판정: **착지·서빙 반영 완료** — 역머지 2회 충돌 0 · 게이트 4종 신규 델타 0 · DoD 10파일 · push ff · 리빌드 교체 확인.

- **착지 해시 `c4f6ea2b`** (커밋 `033a03bf` 슬라이스 + `(d)` 정정 + 역머지 2건). merge-base `76a2b651`→상류 흡수.
- **push 전/후 origin/main**: `82b218fe` → (상류 전진) `14d91d50` → **`c4f6ea2b`** (`14d91d50..c4f6ea2b` **fast-forward** · force 0 · 브랜치/worktree 삭제 0).
- **역머지 충돌 0** (2회 실행: 16 behind → 8 behind → 0). 상류가 `frontend/__tests__/guide/guideAnchors.test.ts`·`lib/guide/dashboard.ts`를 건드렸으나 내 구획과 충돌 없음.
  ⚠ **실행자 자기 정정**: 역머지 전 "겹침 사전 검사"에 **two-dot(`HEAD..origin/main`)을 써서** 내 파일 9건이 "상류가 건드림"으로 오검출됐다. 지시서가 경고한 그 함정을 검사 단계에서 재현한 것이며, 충돌 0이 오검출을 실증했다. **사전 검사도 three-dot이어야 한다.**
- **S2 three-dot 파일 수 = 10** (코드·테스트 9 + outbox 1). 구획 밖 0건. 고정 base 해시 미사용.
- **게이트 재측정(역머지 후)**
  | 게이트 | 상류 기준선(origin/main 트리) | 내 브랜치 | 판정 |
  |---|---|---|---|
  | health | ✅22/⚠2/❌0 | ✅21/⚠3/❌0 | ❌ 0 · **신규 델타 0**. 차이 = "실행 트리 정합" ⚠(미push 아티팩트, #118) |
  | vitest eod | — | **16 files / 144 / 0 fail** | 기준선 129 → +15 |
  | vitest 전체 | — | **181 files / 1413 passed / 0 fail** | |
  | guide 앵커 가드 | — | **41 / 0 fail** | 상류가 건드린 파일 포함 재실행 |
  | tsc | — | **0** | |
  - ⚠ **health 검사 수가 22→24로 증가**(상류 신설). `가격 입력 신선도`·`지표 판독 신선도` ⚠2는 **상류 기준선에 이미 존재 = 선존**, 내 변경 무관. 절대값 비교 금지(#118) 근거가 이번에도 실증됐다.
  - ⚠ vitest 전체 1회 실행에서 `Errors 1 error` 관측(passed/failed 수치는 동일) → **재실행 시 재현 안 됨**. jsdom `Not implemented: navigation to another Document` 경고의 간헐 집계로 판단. 로그 `scratchpad/drawer_vitest.log`.
- **리빌드 전후 서빙 트리 대조(2026-09-19 신규 규율 첫 적용)**
  - 직전: 트리 HEAD **`14c22b93`** · BUILD_ID **`5WlsO_NVJ_E3OHYBaZWGe`** · 내 착지 **미포함** → sync 필요 확정
  - 전진: `checkout --detach origin/main` → **`c4f6ea2b`**(내 착지 포함 YES) · `format.ts` 실존 · `countByOption` 6회
  - `npm run build`만(**`npm ci` 미사용** — lock diff 0 실측) · 로그 `scratchpad/DASHDRAWER_build_20260922.log` · 폴백 `.next.bak-drawer` 보존
  - 직후: 트리 HEAD **`c4f6ea2b`**(불변 — **병렬 세션 덮어쓰기 없음**) · **BUILD_ID `rCQKEBK6452Je8n72s0-R`**
  - 빌드 청크에 슬라이스 고유 문자열 실존(`한 종목이 여러 카드에 걸립니다`·`거래대금 전체` @ `app_page_tsx_0es_sk2._.js`)
  - 스모크 `/`·`/?tab=market`·`/?direction=bull` **전건 200** · **리스너 단독** pid 22743(LISTEN·cwd=런타임 트리·ppid 22720=launchd 등록 pid) · 빌드 11:33:39 → 기동 11:33:47
  - ⚠ **실행자 자기 정정 2**: 처음 `lsof -ti:3000|head -1`이 **Claude Helper의 CLOSED 클라이언트 소켓(pid 63022)**을 집어 "서빙 cwd=/", "리스너 2개(고아 의심)"로 오판했다. `lsof -nP -iTCP:3000 -sTCP:LISTEN`으로 재측정하니 리스너는 **단독**. **서빙 트리 판별은 `-sTCP:LISTEN`을 붙여야 한다**(브라우저·앱의 클라이언트 소켓이 같은 포트로 잡힌다).
- **★ 상신(승인 범위 밖 · 미집행)**: 상류 `14c22b93..origin/main`에 **미적용 Django 마이그레이션 1건** — `packages/shared/stocks/migrations/0019_analystgradechange.py`(`e276337f` SCB-CONTEXT-S2 등급 변경 원장). web(Next.js) 리빌드와 무관하므로 프론트 배포는 안전하나, **DB 쓰기·백엔드 sync는 이 슬라이스 승인 범위 밖**이라 손대지 않았다. api/worker 트리 sync + migrate 판단은 해당 트랙/병진 소관.
- 채번 후보 추가: (e) **`lsof -ti:<port>`만으로 서빙 트리를 판별하면 클라이언트 소켓에 속는다** — 위 자기 정정 2. 런북 1장 "고아 단독 리스너 확인"에 `-sTCP:LISTEN` 명시 필요(OPS 트랙).
