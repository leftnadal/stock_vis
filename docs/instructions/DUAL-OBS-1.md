# DUAL-OBS-1 — DSS 첫 자동 발화 + LLM 크레딧 회복 이중 검증

## 계약 헤더 (요지)
- 트랙: DSS-BEAT 관찰 게이트 + LLM-CREDIT-OUTAGE 종결 판정 / 기발부 DSS-BEAT-OBS-1 대체(흡수)
- worktree ~/worktrees/sv-dual-obs1 · 브랜치 monorepo/sess-dual-obs1
- W1 docs / W2 [§A 발화 실패 시만] load_dss_week 폴백(append-only) · **LLM 호출 0**(관측 전용) · FMP 0 · DB read-only(W2 외) · push=D-PUSH-DELEG(docs-only)
- 커밋: 1=0게이트 → 2=장부. HALT-0.

## 정본 절차 = 지시서 원문 (STEP 0 / §A DSS 발화 / §B LLM 크레딧 / §C 부수 / §D 장부)

---

## 집행 결과 (DUAL-OBS-1, 2026-09-07 machine clock)

### STEP 0
- 0-1: worktree @ origin/main `087c7cd8` · clock 2026-09-07 09:27 KST(09-04 19:00 ET 경과·조기 아님) · health 17 OK/1 WARN((i))/0 ERROR → HALT 아님.
- 0-2: 9회차 09-04 발화 ✅ rows=1004·syms=503(16:30–16:40 ET).

### §A DSS 첫 자동 발화 — ✅ 성공 (DB 행 증거)
- A-1: SymbolDemandSignal anchor 09-04 **501행** · ThemeDemandScore **11행** · Signal created_at **09-04 19:04 ET**(beat 19:00 ET 첫 자동 발화).
- A-2: invariant PASS(합=n·breadth∈[-1,1]·유효분모>0·Score11) · **flat_ratio 42.15%(정상<60)** · **arrow_suppressed=False**(curr 42.15%·prev 08-28 52.85%) · excl analyst_delta 17.
- A-3: 오프셋 = 스냅샷 완료 16:40 ET → DSS 19:04 ET = **+2h24m ≥2h ✅** · 가드 skip 없음(행 적재).
- A-4: 행 존재 → 폴백 미발동.
- A-5: 클린 WoW 쌍 **4**(pair-based 양끝 비축퇴: 07-31·08-07·08-28·09-04 clean / 08-14 self-축퇴·08-21 prev-축퇴 오염 제외 / 07-24 prev-미평가 판정부재). 단순 anchor 카운트=6/7. 6/6 성숙 ≈ 09-18(예상 09-11은 5/6 가정분).

### §B LLM 크레딧 회복 — ⏸️ 미회복 · 디렉터 판정 대기
- B-1: 분석률(`daily_report.collect_news_metrics`: llm_analyzed/today_new) 일자별 = 09-01 0.3%·09-02 0.1%·09-03 0.1%·09-04 0.1%·09-05 0.2%·09-06 0.0% — **0%대 고착**(충전 후 미탈피). 절대 임계 미적용(수치만).
- B-2: **실경로 = Gemini**(`news_deep_analyzer` MODEL=gemini-2.5-flash·GEMINI_API_KEY), **anthropic 아님**. 워커로그 gemini 8675 / anthropic 139(advisor 별도). Gemini 실패 마커 지배: quota/429/RESOURCE_EXHAUSTED/billing.
- B-3: 백로그 09-01~03 미분석 **7798/7807**. 소급 스윕 = `analyze-news-deep-batch`(top-15%·max50 미분석 대상)이나 Gemini quota로 진척 미미. 최근 분석완료 09-04 18:30 ET.
- B-4: **미회복**(0%대 고착) → 종결 기입 금지. 재료: beat enabled·dispatch 정상(quota 병목)·충전 대상 provider 오인 가능성(anthropic≠Gemini). → 디렉터 판정 대기.

### §C 부수 관찰
- C-1: 야간 감사 `docs/nightly_auto_system/reports/` 09-04~07 산출물 부재(구독 경로·크레딧 분리).
- C-2: Celery NotRegistered 09-01 이후 0건(08-31 5회 = 재시작 창 일회성 확증).
