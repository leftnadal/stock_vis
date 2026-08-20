# ADV-COV-TRIAGE-0813 — advisor coverage_n 실패 2건 triage 보고서

> 지시서: DIRECTIVE-MON-ADV-COV-TRIAGE-0813 (2026-08-13 계획 세션 발행, 08-19 집행)
> 브랜치: `monorepo/sess-adv-cov-triage` · **절단 베이스 = `24043cd4`**(origin/main 최신, D-BRANCH-CUT-FROM-LATEST)
> 대상 실패: `tests/monitor/test_advisor_briefing.py::TestBuildContext::test_coverage_denominator_not_hardcoded_9` · `::TestGenerateBriefing::test_creates_note` (coverage_n==0, 기대 2/1)
> 보고 규율: 수치·판정에 명령·출력 verbatim (D-P4-GATE-PROVENANCE)

---

## STEP 0 — 재현 확인

main = `24043cd4`(24043cd4 이후 이동 없음, 절단 베이스와 동일). 실패 재현(verbatim):
```
tests/monitor/test_advisor_briefing.py:63: assert ctx["coverage_n"] == 2  → E assert 0 == 2
tests/monitor/test_advisor_briefing.py:119: assert note.coverage_total == 1 and note.coverage_n == 1  → E assert (1 == 1 and 0 == 1)
2 failed in 7.27s
```
- 두 실패 모두 **분모(coverage_total)는 정상(2·1), 분자(coverage_n=충분 지표 수)만 0**.
- 기준선(직전 259+2/0/923 대조): pytest(monitor) 재현 시 동일 2건 red 확인.

## PART A — 원인 판정 (읽기 전용)

### A-1. 집계 경로 역추적
`coverage_n` 산출(`apps/monitor/services/advisor_briefing.py:85-97`):
```python
inds = list(monitor.indicators.filter(is_active=True, is_paused=False))
coverage_total = len(inds)          # 분모: 등록 지표 수 (정상)
coverage_n = 0
for ind in inds:
    r = score_indicator_dispatch(ind, as_of_date=latest.asof_date)
    if bool(r.get("is_sufficient", False)):
        coverage_n += 1             # 분자: is_sufficient=True 지표만
```
지표 momentum_12_1·volume_ratio는 `scoring_mode="zscore"`(catalog.py:83·113) → `score_indicator_from_model`(indicator_scorer.py:184) 위임. 충분성 **2관문**:
1. **관문1 readings asof 필터**(indicator_scorer.py:186-201): `qs.filter(asof__date__lte=as_of_date)` → `readings_qs` 비면 `is_sufficient=False` 즉시 반환.
2. **관문2 source_n≥min_n**(:222-232): `source_row_count`(:118)가 DailyPrice/EODSignal을 `date__lte=as_of_date`로 카운트.

**coverage_n=0의 정확한 지점 = 관문1.** 픽스처 `add_readings`(conftest.py:46 `base=timezone.now()`)가 readings를 **오늘(2026-08-19) 앵커**로 생성 → 스냅샷 asof는 테스트 하드코딩 **`date(2026,8,7)`**(test:60·109) → `asof__date__lte=2026-08-07` 필터가 오늘자 readings 전량 배제 → `readings_qs` 빈 리스트 → `is_sufficient=False` → coverage_n 미증가 → 0. **관문2(DailyPrice)는 무관** — `stock_aapl` 픽스처(test:28)가 DailyPrice 300행을 **고정 2025-01-01~ 날짜**로 생성(as_of 이하 안전, 주석 명시)하므로 관문2는 정상 통과. 관문1에서 먼저 탈락.

### A-2. 프로덕션 실측 (SELECT만, 1차 증거)
최근 AdvisorNote(최신 asof 2026-08-17) 6종 저장값(verbatim):
```
total notes: 37
asof=2026-08-17 GEV   cn=9 ct=9   asof=2026-08-17 TLN   cn=6 ct=9
asof=2026-08-17 GOOGL cn=9 ct=9   asof=2026-08-17 IREN  cn=6 ct=9 body='6/9'
asof=2026-08-17 IONQ  cn=6 ct=9 body='6/9'   asof=2026-08-17 PLTR cn=9 ct=9
```
- **6종 전체 coverage_n>0**(SP500=9/9, 비SP500 TLN/IREN/IONQ=6/9). TLN 저장값 6/9 정상, 08-14 TLN body "6/9" 문면 생존. **라이브 정상 = 산출 코드·프로덕션 데이터 무결.**

### A-3. 도입 시점 (git log)
```
5ebe7970 2026-08-10 MON-P4-LA 프롬프트 v1.1 …
8418209d 2026-08-10 MON-P4-LA T1 — AdvisorNote + advisor_briefing 서비스
```
테스트·서비스 모두 **2026-08-10 단일 커밋 도입·이후 무변경**. 관문1 통과 조건 = as_of(08-07) 이하 readings ≥5개. readings 날짜 = `[now-9…now]`, 5번째 오래된 것 = `now-5` → `now-5 ≤ 08-07` ⟺ `now ≤ 2026-08-12`. **08-12까지 green, 08-13부터 red** — 코드 변경 없이 경과일 단독 전환(time-bomb).

### A-판정 — **⑴ 픽스처 결함 (fixture time-bomb)**
- **⑵ 프로덕션 회귀 배제**: A-2 라이브 6종 coverage_n>0·문면 생존.
- **⑶ 계약 변경 미반영 배제**: A-3 코드 08-10 이후 무변경, 프롬프트·계약 불변.
- **⑴ 확정 메커니즘**: readings(now 앵커, conftest.py:46) ↔ 스냅샷 asof(고정 08-07, test:60·109)의 시간 커플링. `asof__date__lte` 필터(indicator_scorer.py:190)가 now자 readings 배제 → coverage_n=0. green→red가 `now>2026-08-12` 경과일로 완전 설명됨.

## PART B — 조건부 수리 (판정 ⑴ = 픽스처만)

프로덕션 코드 **무접촉**, 픽스처 시간 커플링만 제거(최소 diff·additive):

**diff 요약**:
- `tests/monitor/conftest.py` `add_readings`: `_add(indicator, values, status="ok", base=None)` — `base` 옵션 파라미터 추가(기본 None→`timezone.now()`, **기존 전 호출자 무영향·backward-compatible**).
- `tests/monitor/test_advisor_briefing.py`: 임포트 `datetime`·`django.utils.timezone` 추가 + 모듈 상수 `_READINGS_BASE = timezone.make_aware(datetime(2026,8,7,12,0))` + 실패 2건이 쓰는 readings 호출 2곳(test_coverage 루프·`_prep`)에 `base=_READINGS_BASE` 전달 → readings가 스냅샷 asof(08-07) 이하로 정합.

**테스트 결과**(verbatim):
```
# 실패 2건: tests/monitor/test_advisor_briefing.py::...test_coverage_denominator_not_hardcoded_9 ...test_creates_note
2 passed in 7.32s
# advisor_briefing 파일 전체
12 passed in 9.13s
# tests/monitor 전체 회귀
261 passed in 62.63s
```
**신규 기준선**: pytest(monitor) **261 passed / 0 failed**(구 259+2 → 261/0). tsc/vitest 무접촉(백엔드 테스트만 수정). 회귀 0.

**게이트**: 판정 ⑴ = 테스트 변경만 → **배포 게이트 비적용**(원문: "판정 ⑴·⑶은 테스트 변경만이므로 배포 게이트 비적용"). 배포·워커 재시작 없음.

## PART C — ADR F-플래그 2건 원문 회수 (읽기 전용, ADR 무수정)

**F-1 (§3.11 통계층 산출) 원문**:
> "IC 이중 트랙(자기 패널 6종×~132일 + 유니버스 520종×~3년)."

CC 소견(1줄): **실질 결함 의심** — 520종은 EODSignal 유니버스로 이력 ~6개월(109 거래일)뿐이고 ~3년 심도는 DailyPrice 747종(RECON A-5). IC 유니버스 트랙의 유니버스/깊이 페어링이 산출에 실영향 → 표기 아닌 실질(v1 통계층 착수 전 정정 권장).

**F-2 (§7 리스크 등재) 원문**:
> "| 상태 축 4원화 | v0.5를 3원화 묶음 결정에 종속 |"

CC 소견(1줄): **내부 표기 불일치(오탈자 개연)** — RECON 실측 상태축 3원(Monitor.status/current_state/MonitorSnapshot.state), ADR §3.2·§4는 "3원화"인데 §7만 "4원화". Claim.status를 4번째로 의도했다면 근거 명기 필요하나 현 문맥상 표기 실수 개연 → 실질 결함 아님. (처분은 계획 세션 판정.)

## 게이트 상태
- **판정 ⑴ → 배포 게이트 비적용.** 배포 승인 대기 없음. 수리 = 테스트-only 커밋으로 종결.

## 미해결·이상 관측
- **동종 time-bomb 잠복(비수리·좌표만)**: 같은 파일 `test_v11_state_display_and_score_precision`(test:73)·`_prep` 기반 나머지 4테스트도 now-앵커 readings를 쓰나 **coverage_n을 assert하지 않아** 현재 green. 본 수리에서 `_prep`은 `base` 정합했으므로 그 4건도 부수 정합됨. test_v11 등 coverage 미assert 테스트는 무접촉(최소 diff). 향후 같은 클래스 재발 방지는 픽스처 `base` 정합 관례화 권장(별건).
- ADR F-플래그 2건은 verbatim 규율로 미수정(§8 미확정 이월, D-SWAP-REVIEW 부기).

---
_전 항목 로컬/DB, 외부 API 0. 프로덕션 코드 무접촉(픽스처 2파일만). 브랜치 삭제 없음._
