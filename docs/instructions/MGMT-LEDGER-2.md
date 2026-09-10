# 지시서 MGMT-LEDGER-2 — 장부 일괄 정산 + 관찰 소음원 수정 2건

- 발행: 감독 세션, 2026-09-08
- 트랙: ops/mgmt 배치 — 장부 승격/개정 + TASKQUEUE 등재 + 관찰 소음원 코드 수정 2건
- 세션: mgmt(채번 자격 有) / worktree `~/worktrees/sv-mgmt-ledger2` · 브랜치 `monorepo/sess-mgmt-ledger2`(origin/main `be235750` 기점)

## 쓰기 허용 (이외 전면 금지)
- **(W1) docs**: 본 지시서 · `DECISIONS.md` · `TASKQUEUE.md` · `PROGRESS.md` · `sub_claude_md/common-bugs.md`
- **(W2) code 2표면 한정**: TL;DR System 줄 생성부(`packages/shared/metrics/services/agent_reports.py` `_build_tldr_backend`) · dogfood `check_quant`의 EOD 지연 산식(`auto_agent_system/dogfood/check_quant.py check_freshness`) + 각각의 테스트. 그 외 코드 무접촉.
- DB read-only · FMP 0 · LLM 0 · dogfood/리포트 실발송 금지(검증=유닛 테스트) · foreground · `git add` 명시(-A 금지) · force 금지 · push=D-PUSH-DELEG(behind 흡수=D-PUSHDELEG-REBASE-ABSORB 5조건).
- 커밋 순서: 1=0게이트(지시서) → 2=장부(T1·T2) → 3=TL;DR 수정 → 4=EOD 산식 수정 (코드 커밋 분리 — 혼재 금지). HALT-0.

---

## STEP 0 실측 결과 (2026-09-08 12:57 KST, base `be235750`)

| # | 결과 |
|---|---|
| 0-1 | health **16 OK / 2 WARN / 0 ERROR**. WARN = (i) runtime_check(24h 로그·양성) + "실행 트리 정합 #47"(세션 워크트리를 behind origin/main 대비 측정한 **문서화된 거짓양성**·`lesson_land_health_measure_in_target_tree`). **신규 (ii)형 0 → HALT 아님**. ※ origin/main이 STEP 0 도중 `be235750`→`2548dfc` **2 behind**(SWAP-P1 monitor duel FE·`frontend/components/monitor/duel/*`만·장부/코드표면/채번 무영향) → 흡수는 위임 push 시점(D-PUSHDELEG-REBASE-ABSORB). |
| 0-2 | common-bugs 최대 번호 = **#129**(HUB-V02-S1 2026-09-03). 후보 3건 현위치: ① dispatch 규율 = L1798(DSS-BEAT-1) · ② 일련번호 금지 = L1802(DSS-BEAT-1) · ③ 크레딧 교훈 = L1911(DUAL-OBS-1). 승격 = **#130/#131/#132** 연속. |
| 0-3(a) | health json mtime = **각자 날짜 05:40**(9/4→Sep 4 … 9/8→Sep 8) → **"매일 실행" 확정, catch-up 해석 기각**. (T2③ LOG-FORMAT-DATE 근거) |
| 0-3(b) | tier3 09-07 밤분 = 로그(`tier3_audits_20260907_230004.log`) **존재하나 즉시 HALT**("전용 worktree에 미커밋 변경 존재 — 직전 run 커밋/push 실패 잔재 보호. 격리·커밋 중단"). **감사 산출물 부재** — 마지막 성공 감사 = 09-03(reports `9월/3일`). **09-04~ 매일 HALT**(launchd 23:00 발화는 확인 = 스케줄 미스 아님). 원인 = nightly repo worktree(`~/stock-vis-nightly/repo`) 미커밋 `?? frontend/docs/` 잔재. → **산출물 부재 → NIGHTLY-AUDIT-MISS 등재(④ 발동)**. 원인 판정·복구(runtime op)는 디렉터. |
| 0-4⑴ | TL;DR System 줄 = `agent_reports.py:257-262` `_build_tldr_backend`. **부재 키** `celery_beat_running`/`neo4j_reachable` 읽음 → `.get(...,False)` 항상 False → **항상 "beat=DOWN neo4j=DOWN"·h_emoji 항상 ⚠️**. health 소스 = `daily_report.py:560 collect_system_health`(실키 `celery_beat_alive`:623 · `neo4j_alive`:624). 상세 표 = `daily_report.py:1171-1172`(올바른 키 사용). 이중 산식이 아니라 **구 스키마 키 잔재** → 단일 출처(health dict 실키) 재사용으로 수리. 재현 확증(`beat_alive=True/neo4j_alive=True`에도 "beat=DOWN neo4j=DOWN"). |
| 0-4⑵ | check_quant 지연 산식 = `check_quant.py:140-141`(`lag=(session-trading).days` = **달력일** + `MAX_FRESHNESS_LAG_DAYS=1`:42 비교). 휴장 판정 재료 = `auto_agent_system/dogfood/market_calendar.py`(`previous_trading_day` **기존재**·AGENT-CAL-1) → 재사용, 새 캘린더 소스 도입 없음. |
| 0-4⑶ | **수정 파일 목록 확정**: T3 = MODIFY `packages/shared/metrics/services/agent_reports.py`(257-258행 키 정정) + NEW `tests/unit/metrics/test_agent_reports_tldr.py` / T4 = MODIFY `auto_agent_system/dogfood/check_quant.py`(140-143 산식 + 42 상수) + MODIFY `tests/dogfood/test_quant_schema.py`(신규 픽스처 2건). **목록 밖 수정 필요 없음 → HALT 불요.** |

---

## 반영 항목

### T1 — 장부 승격·개정 (커밋 2)
- **common-bugs**: 후보 3건 → 실번호 승격(#130/#131/#132). ①②(dispatch 규율·일련번호 금지)는 기존 문안 verbatim + 라벨만 실번호. ③(크레딧)은 디렉터 확정 개정 문안으로 본문 교체(이중 공급자=별개 실패 도메인·공급자별 감시/비용 분리).
- **DECISIONS**: D-DSS-EPSILON 부기 1줄(정의 개정 09-08 — 첫 회차 07-17 종단 쌍 판정불가·영구 제외, 클린쌍 정본 4, 6/6 성숙=09-18, 디렉터 비준 09-07).

### T2 — TASKQUEUE 등재만 (구현 금지, 커밋 2)
① EOD-ISSTALE-DEF(베이커 is_stale 정의 프로브·도메인 이관) · ② LOG-ROTATE(대형 로그 로테이션·상신 필요) · ③ LOG-FORMAT-DATE(nightly 로그 타임스탬프 날짜 포함·0-3(a) 근거) · ④ NIGHTLY-AUDIT-MISS(0-3(b) 부재 확정 → 발동) · ⑤ T3·T4 실효 조건 명기(착지≠실효·다음 sv sync 후 아침 메일 2종 검증·MIG-BUNDLE-1 배포창 동반 참조).

### T3 — REPORT-TLDR-SYSLINE 수정 (커밋 3)
TL;DR System 줄이 health dict 실키(`celery_beat_alive`/`neo4j_alive`)를 재사용(구 키 잔재 삭제·단일 출처). 유닛 테스트로 alive=True→"DOWN" 불출현 / 실제 down→출현 잠금.

### T4 — DOGFOOD-EOD-LAG-TRADINGDAYS 수정 (커밋 4)
달력일 → 거래일 기준. `trading >= previous_trading_day(session)` 이면 ok(직전 거래일 = 방금 닫힌 세션 미베이크 정상태 포함), 미만 = fail. 휴장·주말은 기존 market_calendar 재사용. 회귀 픽스처 2건(주말 개재·Labor Day 개재) 고정.

## HALT 트리거
(ii)형 health / 0-4 목록 밖 수정 필요 / 후보 3건 grep이 전제와 모순 / 테스트 회귀 / 예상 밖 일체.
