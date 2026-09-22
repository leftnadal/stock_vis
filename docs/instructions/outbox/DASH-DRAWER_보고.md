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
