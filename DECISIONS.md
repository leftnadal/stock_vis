# StockVis Decisions

## D-RESEARCH-WORK-BOUNDARY — Research Chat/Lab와 Research Work 역할 분리

**Date:** 2026-09-20  
**Status:** Active  
**Owner approval:** Approved by Project Owner

**Decision**

Research Chat/Lab은 연구의 의미·구조·실험 설계·해석과 material한 의사결정을 책임진다. Research Work는 승인된 설계를 구현하고 실험을 실행하며, 실행 중 발생한 기술 결함을 승인 범위 안에서 자율적으로 보완하고 결과를 집계·검증·패키징한다.

Work는 모든 기술 수정마다 Chat 승인을 요청하지 않는다. 새 권한·비용·데이터 전달이 필요하거나 연구 질문·실험 contrast·평가 의미·해석 경계를 바꿔야 하는 경우, 또는 연구 방향을 흔드는 material result/blocker가 있는 경우에만 Chat으로 escalation한다.

**Why**

반복적인 Chat↔Work 인계가 Project Owner를 수동 중계자로 만들고 Research Lab의 연구 설계 집중도를 낮췄다. 공식 Research Methodology도 Research Design과 Investigation을 구분한다. 따라서 연구 의미와 설계를 Chat/Lab에, 승인된 설계의 실행과 기술적 완성을 Work에 두어 책임을 명확히 하고 불필요한 승인 ping-pong을 줄인다.

**Boundary**

이 결정은 기존의 승인되지 않은 모델/API 호출, 유료 비용, private payload 전송, push/merge/deploy 같은 권한을 새로 부여하지 않는다. Research Knowledge admission, 공식 Methodology 변경, 연구 결론의 일반화는 Work가 독자 확정하지 않는다.


## [2026-09-22] PRICE-FRESH-1 LANDED — `14c22b93` (가격 신선도 수리 + 자가 노출 2종) [monitor][harness]

> 블록 PRICE-FRESH-1-B. base `eb326796` → 착지 `14c22b93`, push 완료. 배포 = `worker_sync.sh` 3트리 `14c22b93` 정렬 + celery-worker·beat·daphne 재기동, 사후 health ❌0. 마이그레이션 없음.

**근본원인**: 가드(`pipeline.ensure_price_freshness`)는 **DailyPrice만** 보장하는데 reader(`scenario.latest_close`)는 **EODSignal을 무조건 우선**하고 행 유무만 봤다. 두 소스의 신선도가 독립이라 EODSignal이 뒤처진 종목에서 묵은 종가가 zone 판정에 그대로 들어갔다. **쓰는 쪽과 지키는 쪽이 다른 소스를 본 것**이 결함의 형태다.

**실해**: 2026-09-17 배치에서 TLN이 EODSignal 09-14(286.52)로 손절 접근 **거짓 발화**. 실제 09-17 종가 293.31이면 필요버퍼 8.15% > 밴드 7.07%로 무발화였다. 방향은 양쪽이다 — 반대로 실제 접근을 놓칠 수도 있다.

**수리**: 두 소스의 `(최신 date, close)`를 각각 구해 **더 최신 날짜** 쪽 반환(동일 날짜면 EODSignal 우선 — 기존 동작 보존). `as_of` 컷오프 양쪽 적용. `latest_close_with_date` 신설 + `latest_close`는 래퍼 → **시그니처 불변, 기존 6개 호출부 무변경**(G-2 158 passed로 확증).

**자가 노출 2종** — 수리보다 이쪽이 본질이다. 이 결함은 ✅ 사이에 숨어 있었다:
- **메일 종가 날짜** `종가 286.52 (09-14)` — 09-18 실물 메일은 헤더 `as_of=09-17`인데 종가는 09-14 값이었고 메일만으로 알 수 없었다. 공용 헬퍼 `_close_with_date`로 텍스트·HTML 동시(3-A `_near_stop_suffix` 선례).
- **health_check 2항목** — 09-18 하네스 메일의 monitor 2항목은 모두 ✅ 였으나 둘 다 "배치가 돌았는가"만 봤다. `가격 입력 신선도`(수집 층) + `지표 판독 신선도`(이식 층). **한 항목으로 묶지 않는다 — 실패 지점이 다르다**: 가격이 도착해도 ingest가 밀리면 판독값만 묵는다. 임계 3일(1거래일을 달력일로 흡수).

**§C 측정 (수리는 범위 밖)**: 활성 monitor **6/6이 EODSignal 계열 지표 3종**(`eod_composite`·`change_percent`·`dollar_volume`) 보유 — `catalog.py`가 `stocks.EODSignal.*`에 직접 결박. technical 6종은 DailyPrice 소스라 무관. 갭은 **SP500 편입과 무관하고 종목 사이를 옮겨 다닌다**(09-19 TLN·GOOGL 4일 → 09-22 GEV 4일). 09-22 실측에서 GEV는 `MonitorSnapshot.asof=09-21`로 최신처럼 보이는데 구성 지표 3종이 09-17 값이었다 — **스냅샷 날짜만으로는 구분 불가**. 신규 B-2 점검이 이것을 잡는다(라이브 ⚠ 3/54지표).

**게이트**: G-1 monitor **420 passed**(역머지 기준선 395 + 신규 25, 회귀 0) · G-2 소비자 6곳 158 passed · G-3 변경 = `scenario.py`·`alerts.py`·`health_check.py`·테스트 3파일 · G-4 evidence 0 · G-5 마이그레이션 없음.

### 디렉터 전달 결함 3건 (블록 PRICE-FRESH-1-B 자인) [harness]

⑴ rev2 전달 실패(§3-B·§3-C 미도달) ⑵ 1-A 초안/최종 전달 실패(2회째) ⑶ 1-A §E 머리글("멈춰라")과 항목("계속해라") 모순.

**대책**: 블록 첫 줄에 **BLOCK-ID**를 달고, 집행자의 **첫 동작은 그 줄을 그대로 되읊는 것**으로 한다. 불일치면 낡은 블록이므로 즉시 상신. 이 블록부터 적용했고 이번 회차에서 정상 작동했다.

**집행자 측 파생**: 모순된 지시를 만났을 때 자율 해석하지 않고 정지·상신한 것이 옳았다(1-A §E에서 §A·§B 진행 여지를 자의로 택하지 않음). cf. [[feedback_surface_await_disposition]]
