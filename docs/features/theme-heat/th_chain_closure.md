# TH-TNV-CHAIN — 트랙 종결 선언 (초안)

**작성:** 2026-08-07 · TH-TNV-CHAIN-1 + 1F 완결 · 착지 origin/main `8a41c842`
**전제:** TH-SESSION-1(TNV 백필·재동결 해소)의 후속 — 재동결을 **구조적으로 차단**.

---

## 선언

**TNV 집계가 theme-heat-daily 태스크에 체이닝되어, TNV 재동결이 구조적으로 차단됐다.** 매 heat 발화가 당일 TNV를 선(先)갱신하므로, TNV 집계 beat 부재로 인한 정지(07-25 재동결 사태)가 재발하지 않는다.

## 트랙 호(弧)

| 단계 | 결과 |
|---|---|
| **결정** | D-TH-TNV-CHAIN — 3안 중 (B)체이닝 확정(가중합 4.15·마진 1.30, #28 beat drift 회피가 채택 근거) |
| **구현** | compute_theme_heat_task 선두에 `aggregate_theme_news_volume(당일)` 삽입(+18줄 additive)·실패 전파·written=0 통과·TNV_CHAIN 로그. 단위 3케이스(순서·전파·0통과) |
| **행위보존** | heat 산식·기존 테스트 무손상. suite 4608 GREEN/0/53(신규 +3) |
| **갭 백필** | §C 08-02→08-04(TNV 08-04 6행·heat 재산출) + §C′ 08-05(TNV 0→4·heat 재산출). override 215·corpus 무접촉 입증 |
| **배포** | worker-runtime `8a41c842` 전진 + celery-worker/beat 재기동. 3요소(코드착지·트리전진·프로세스재기동) 체크 완료 |
| **G-fire** | **PASS** — ET 18:00 08-06 실전 발화·TNV 22:00:00→heat 22:00:45 DB 입증·오류 0 |
| **관측성 수정(S1)** | LOGGING에 `apps` 로거(INFO→file·propagate=True) 추가 → TNV_CHAIN 파일 기록. 선존 갭 해소(common-bugs #90) |

## 교훈 (common-bugs)
- **#88b**: 긴 병진 명령 = 붙여넣기 소프트랩 잘림 → 짧은 셸 스크립트 파일화
- **#89**: 발화/배포 선후는 machine clock·last_run 실측 전용(chat 날짜 가정 금지·KST-ET 13h)
- **#90**: LOGGING 로거 미라우팅 = logger.info ≠ 파일 기록. propagate=False는 caplog 붕괴

## 잔여 (게이트 아님)
- **G-obs**(사후 관찰): 다음 발화 **ET 18:00 08-07**에서 `TNV_CHAIN date=2026-08-07` 로그 **파일 기록** 확인 = S1 수정 실증(병진 "게이트 확인해줘" 한 마디). 통과 시 임시 스크립트 3종 정리.
- **TH-TNV-BEAT-SPLIT**(보류): TNV·heat 주기 분화 필요 시 A안(독립 beat) 승격.
- **CORPUS-SUNMON-EMPTYKW**(관찰): 주말/월 빈 키워드 → 해당일 TNV 0(별도).

## 롤백 (미실행·G-obs 통과 시 폐기)
- 체이닝 커밋 revert 무충돌 확인됨. 절차 = revert→push→worker-runtime 전진·재기동.
