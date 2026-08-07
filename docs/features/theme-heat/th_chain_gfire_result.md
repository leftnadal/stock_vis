# TH-TNV-CHAIN-1F §G — G-fire 실전 발화 게이트 결과 (PASS)

**판정:** 2026-08-07 · G-fire **PASS**(A: DB 결정 증거로 ① 취지 충족) · 디렉터 비준
**발화:** theme-heat-daily last_run = **ET 18:00 08-06 = KST 07:00 08-07** (total_run 17, 배포 KST 11:50 08-06 이후 첫 체이닝 발화)

---

## §G 4항 실측표 (machine clock·last_run·DB 기준)

| 항목 | 실측 | 판정 |
|---|---|---|
| ①' **체인 실전 실행**(①의 취지) | TNV 08-06 **4행 created 22:00:00 UTC** = 발화 시각 정확 일치 → 체인 `aggregate_theme_news_volume(08-06)` 실행 | ✅ DB 입증 |
| ① TNV_CHAIN **로그 라인** | 발화 시점 부재 — **선존 LOGGING 갭**(heat_tasks 로거 미라우팅, INFO→last-resort 드롭). **회귀 아님**. S1 수정으로 후속 발화부터 기록(G-obs 실증) | ⚠️→S1 수정 |
| ② 당일 TNV 행 | 08-06 **4행**, corpus **10 keyword 블록**(수) → written 4>0 정합 | ✅ |
| ③ 동일 실행 heat | heat 08-06 **6행 created 22:00:45 UTC** = TNV(22:00:00) **직후 45초** | ✅ 인접 |
| ④ 오류·retry | heat 태스크 0 (로그 retry는 metrics/email SMTP·neo4j 무관 태스크) | ✅ |

**판정 근거**: 체인이 **beat→worker 실전 경로**로 발화 시각에 TNV→heat 순차 기록(45초 간격)·오류 0. ①의 로그 라인은 선존 로깅 갭으로 부재였으나 취지(실전 실행 증거)는 DB로 초과 충족. → **PASS**.

## S1 후속 수정 (관측성 복원)

- `config/settings.py` LOGGING에 `apps` 로거 추가(INFO→file handler·`propagate=True`) → heat_tasks `TNV_CHAIN` 로그가 파일 기록. additive·기존 로거 무변경.
- ⚠️ 최초 `propagate=False`가 pytest `caplog`(root 캡처) 붕괴로 5 테스트 실패 → **`propagate=True`로 교정**(S1 게이트 suite가 포착). 재검증 4608 GREEN/0/53.
- **G-obs**(사후 관찰·게이트 아님): 다음 발화 ET 18:00 08-07에서 `TNV_CHAIN date=2026-08-07` 로그 파일 기록 확인 = S1 실증.

## §C′ 08-05 백필 (동승)

08-05 발화(ET 18:00 08-05·배포 전 구 코드)는 TNV 미체인 → 08-05 TNV=0행·heat는 TNV 없이 계산. §C′로 08-05 1일 백필(TNV+heat 재산출) 동반. 결과는 종결 선언에 병기.
