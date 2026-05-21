# Slice 13 종결 보고서 — E1~E6 API 엔드포인트 추출

## 1줄 요약

진단 엔진 6종(E1~E6)을 DRF REST API(`/api/v1/coach/eN/`)로 추출.
legacy view 무손상 ADDITIVE 방식. 8커밋, 회귀 +99, 비용 $0.

## 핵심 수치

- HEAD: ae4aca4
- 회귀: 668 → 767 (+99), +1 skipped
- IDENTICAL 회귀: 31/31 PASS (E4 carrier 20/31)
- 비용: $0 (LLM 무접촉 — API 추출 슬라이스 특성)
- legacy views.py / urls.py: git diff 0 (무변경 확인)

## 커밋별 회귀 증분

| 커밋    | Phase                                                          | Δ   | 누적 |
| ------- | -------------------------------------------------------------- | --- | ---- |
| f7fd62b | Step 0a (3단 gate_tiers additive + estimator multivariate fit) | +27 | 695  |
| 22d1e99 | Step 0b (estimator→CostGuard non-blocking)                     | +12 | 707  |
| 44d5e90 | Part 1 (E1)                                                    | +10 | 717  |
| 28d19c4 | Part 1.5 (API 경로 v1 도입)                                    | 0   | 717  |
| 50c6313 | Part 2 (E2)                                                    | +10 | 727  |
| ae0a9e1 | Part 3 (E3)                                                    | +10 | 737  |
| 54cc47f | Part 4 (E5+E6)                                                 | +20 | 757  |
| ae4aca4 | Part 5 (E4)                                                    | +10 | 767  |

## 6 endpoint 매트릭스

| 진입점 | DRF URL           | Legacy view              | 비고                                                    |
| ------ | ----------------- | ------------------------ | ------------------------------------------------------- |
| E1     | /api/v1/coach/e1/ | coach_e1_garp            | Part 1                                                  |
| E2     | /api/v1/coach/e2/ | coach_e2_diagnostic_card | Part 2                                                  |
| E3     | /api/v1/coach/e3/ | coach_e3_metric_comment  | Part 3 — preset 점수는 #66                              |
| E4     | /api/v1/coach/e4/ | (부재)                   | Part 5 — legacy view 없는 유일 진입점, 마이그 대상 아님 |
| E5     | /api/v1/coach/e5/ | coach_e5_adjustment      | Part 4                                                  |
| E6     | /api/v1/coach/e6/ | coach_e6_comparison      | Part 4                                                  |

## 아키텍처 패턴

DRF serializer ↔ Pydantic schema ↔ run_eN_coach 표준 함수.
ADDITIVE — 새 API endpoint를 legacy view 옆에 추가, legacy 무손상.
contract test가 EN Output 계약 위반 시 FAIL → drift 안전망.

## 부채 변동

신규 5건:

- #61 게이트 calibration (3단 gate_tiers 임계 잠정치 → 실측 보정). Slice 14 Step 0 1순위.
- #63 cost ledger 파일 부재 (누적 비용 미검증 문제).
- #64 blocking 차단 (CostGuard non-blocking 보강).
- #65 legacy view 5건 처리 (유지/제거/wrapper 미결정). Slice 13 종결 후 진입.
- #66 E3 preset 점수 API 노출 (분석엔진 #12 Phase 2 의존, PS 2.0).
  close 1건:
- #62 estimator→CostGuard non-blocking integration (Step 0b).

## 다음 진입점

1. #65 — legacy view 5건 최종 처리. frontend 연동 미정이므로
   wrapper / 유지 우선 검토, '제거'는 후순위.
2. Slice 14 Step 0 — #61 게이트 calibration 1순위.
