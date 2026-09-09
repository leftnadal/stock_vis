# DailyPrice Permission / Eligibility Boundary — 수정 후보 v0.1

- Status: Candidate / Not Promoted
- Date: 2026-09-09
- Authority: CEO-approved Chat → Work Decision Handoff, DailyPrice Readiness Follow-up (이 세션에서 제공)
- Parent candidate: 1f5fa8420a02fbd683a31d75a5bd8724d78f188c
- Branch: math-lab/readiness-boundary-fix-v0.1
- Scope: F1/F2 구현·회귀 검증 및 recovery 증거 연결. 원 Job/산출물 수정 없음.

## Executive Summary

DailyPrice 출력의 진단 권한과 선언 용도별 연구 입력 적격성을 분리했다. 실제 가격 행이 없거나 기존 진단에서 fatal OHLCV로 표시된 대표 대상만 있는 경우 연구 입력 사용을 금지한다. 정상 대상을 포함하는 경우에는 적용 가능한 종목을 명시한 exploratory_only만 반환하며, 확인·재현 사용은 계속 차단한다. 이는 새로운 실험 실행이나 최종 바스켓 승인 권한을 부여하지 않는다.

## F1 Before / After

| 항목 | 이전 v0.1 | 수정 후보 v0.2 |
|---|---|---|
| 진단 권한 | 별도 구조 없음 | 최상위 inventory_permission: scope/status/basis |
| 연구 입력 허용 | context-free allowed | 선언 용도별 research_input_permitted 및 permitted_symbols |
| 판정 대상 | 가격 행·fatal 결과가 gate에 전달되지 않음 | 대표 6종목의 존재/관측/행 존재/기존 fatal 진단을 연결 |
| 가격 행 없음 | 조회 성공 시 exploratory_only / allowed=true 가능 | prohibited_for_declared_use / research_input_permitted=false |
| 모든 대표 대상 fatal | 모두 deferred여도 allowed=true 가능 | 연구 입력 사용 금지, 진단 결과 보존 |
| 정상/이상 혼합 | 사용 범위가 불명확 | nonfatal 가격 이력이 있는 대표 종목에만 범위 제한; 제외 종목과 이유 명시 |
| 정상 synthetic | 탐색용 유지 | 범위가 명시된 탐색용 유지; confirmation/replication 금지 |
| 버전 | daily-price-readiness-result/0.1 | daily-price-readiness-result/0.2 |

### 진단 권한

`inventory_permission.status=permitted_read_only`는 승인된 접근 경로에서 읽기 전용 세션을 확인하고 수행한 진단 범위를 뜻한다. 데이터 품질이 나빠도 진단할 수 있다. 연결·검증 실패 시 `not_established`로 남긴다. 이 필드는 DB 권한을 새로 부여하거나 이후 세션까지 허용하지 않는다. 정리 실패 시에도 이미 검증된 세션에서 수행한 진단 사실을 유지하며 실패는 별도 기록한다.

### 연구 입력 범위

`data_eligibility_decisions`의 `decision_scope`, `intended_use`, `eligibility`, `research_input_permitted`, `input_scope`, `permitted_symbols`를 함께 읽어야 한다. `allowed`는 DailyPrice v0.2 출력에서 제거했다. `observed_nonfatal_symbols`는 관측된 구조적 상태이며 승인된 최종 바스켓이 아니다. `excluded_symbols`는 데이터 전제에 의한 제외 목록이며 확인/재현 계약의 미충족 사유는 별도의 reasons/missing_requirements에 남는다.

기존 `_representative_rows`가 이미 부여하는 `fatal_ohlcv_anomaly_observed`만 사용한다. 이 판정은 비양수 OHLC, 음수 거래량, OHLC 경계 위반을 포함한다. 새로운 fatal threshold, 최소 이력·행 수 기준, 결측 허용률, 바스켓 통과 비율을 추가하지 않았다. 행이 존재해야 한다는 전제는 충분한 이력 기준이 아니다. 기존 zero-volume 진단은 별도 policy-review 항목으로 남고 새 fatal 규칙으로 승격하지 않았다.

대표군 밖의 적대적 후보에는 연구 입력 허용을 확장하지 않는다. 누락 가격·이상행을 지우거나 보정하지 않는다. 필수 조회 실패 시 종전처럼 연구 입력을 차단하고 관측된 부분 증거는 보존한다.

공통 `data_eligibility.py`와 다른 Lab 및 Lab Automation 계약은 변경하지 않았다. 저장소에서 이 DailyPrice 결과의 실행 소비자로 발견된 것은 해당 renderer/CLI/test이며 함께 갱신했다. 외부 미확인 소비자는 schema v0.2를 명시적으로 지원해야 하며, 누락된 allowed를 true로 취급해서는 안 된다.

## F2 Error Redaction

새 `error_redaction.py`가 연결·내부 query·정리 오류에서 공통 사용된다. `write_artifacts`에서 최종 오류 subtree를 복사·정제하므로 probe 반환 이후 추가된 오류도 JSON과 Markdown에 같은 경계가 적용된다. 직접 Markdown rendering도 정제한다. 원 in-memory artifact는 최종 직렬화 과정에서 수정하지 않는다.

환경에 선언된 DB_PASSWORD/PGPASSWORD 및 DB URL password의 평문·URL 인코딩 값, 통상적인 credential assignment와 URI userinfo를 처리한다. 모든 임의 문자열의 모든 가능한 비밀을 완벽히 탐지한다는 보장은 아니다. 실제 비밀값은 테스트에 사용하지 않았고 외부 DB 연결도 없었다. 실행 소스 지문에 새 redaction 모듈을 포함했다.

## Regression Results

- 46 tests passed (기존 35개 + 추가 11개).
- 기존 eligibility/provenance 테스트 하나는 원 fixture의 치명적 OHLCV 행을 해당 테스트 내부에서 정상화했다. 이제 fatal 데이터는 F1에 의해 차단되므로, provenance만 격리하는 목적이다. 원 dirty fixture를 그대로 차단하는 새 회귀 테스트도 추가했다.
- 빈 데이터, 대표 6종목 전부 fatal, 원 dirty fixture, 정상 fixture, 혼합군, 미접속 상태, 연결/query/cleanup 오류 정제, 늦게 추가된 오류, credential 형태 정제를 검증했다.
- 단위·SQLite·fake PostgreSQL만 실행했다. 실제 DB 상태/권한/SQL 성능 검증은 수행하지 않았다.
- 테스트 환경은 Linux Python 3.12 / pytest 9.1.1, Django plugin과 저장소 pytest.ini를 제외한 독립 설정이다. 원 Mac recovery 환경과 동일하지 않다.

## Recovery Evidence Addendum

`recovery_evidence_addendum.json` 및 `recovery_evidence/` 참조. 원 terminal failure → recovery started → recovery tests → candidate revision → recovery completed 이벤트를 event_id로 연결했다. Runner 0.1.4, 실제 두 명령/0 실패(8+27 tests), codex_reinvoked=false, push/merge/deploy=false, candidate SHA 및 bundle ref를 확인했다.

원 ledger 업로드는 다른 run도 포함하므로 대상 run 11개 event의 원문 line만 발췌했고 전체 업로드 해시도 기록했다. Recovery tests 업로드는 원 artifact 바이트 끝에 LF 하나가 추가된 형태다. 원 업로드와 ledger 해시와 일치하는 artifact byte form을 각각 보존했다. 원 manifest의 runner 0.1.3 및 tests.json=[]는 그대로다.

확인의 한계: 제공된 upload 및 bundle 기준으로 연결이 완결됐으며 Mac의 현재 external ledger/ref를 실시간 확인한 것은 아니다. Hook stderr/원 Codex raw invocation 전체는 이 패키지의 직접 검증 대상이 아니다.

## Stop Boundary / Next

현재 범위에서 새 방법론 결정이 필요한 구현 충돌은 발견되지 않았다. 후속 실제 관측은 `observation_job_proposal_ko.md`에만 준비하며 실행하지 않는다. Promotion은 별도 승인 대상이다. 실제 데이터 근거가 없으므로 예측·모델·백테스트 단계로 넘어가지 않는다.
