# DailyPrice Readiness Probe v0.1

## 1. 목적과 판정 범위

이 문서는 `SV-MATH-DP-READINESS-001` 실행에서 DailyPrice 데이터의 연구 사용 준비도를 읽기 전용으로 점검한 결과다. 근거 문서는 다음과 같다.

- `math_lab/00_foundation/foundation_ko.md`
- `math_lab/01_operating_system/operating_model_ko.md`
- `math_lab/02_methodology/research_methodology_ko.md`
- `math_lab/05_validation/daily_price_validation_basket_v0_1_ko.md`

이 프로브는 데이터 준비도 인벤토리다. 예측 타당성, 경제적 유용성, 거래 가능성, 운영 배포 준비도를 입증하지 않는다.

## 2. 실행 결론

| 항목 | 결과 |
|---|---|
| 실행 상태 | `partial` |
| 데이터베이스 상태 | `unavailable` |
| 읽기 전용 트랜잭션 검증 | 연결 전 실패로 `no` |
| 대표 바스켓 관측 | 0/6 |
| 적대적 실패 모드 평가 | 0/10 |
| 탐색적 사용 | `prohibited_for_declared_use` |
| 확인적 사용 | `prohibited_for_declared_use` |
| 독립 재현 사용 | `prohibited_for_declared_use` |
| 최종 결정 | 최종 바스켓 선정을 유보하고 모든 선언 용도를 차단 |

현재 실행은 **확인 연구 준비도 No-Go**다. 네트워크가 제한된 실행 환경에서 `localhost:5432/stock_vis` 연결이 `OperationalError: Operation not permitted`로 실패했으므로, 배포 스키마와 실제 행을 관측했다는 주장을 하지 않는다. 저장소의 모델·마이그레이션 정보는 Data Gap을 제안하는 정적 근거일 뿐 실제 데이터베이스 상태의 증거가 아니다.

## 3. 읽기 전용 안전장치

프로브 구현은 다음 조건을 만족해야만 데이터 조회를 시작한다.

1. SQL은 단일 `SELECT` 또는 `WITH ... SELECT`만 허용하며 쓰기·DDL·트랜잭션 제어 키워드, 주석, 다중 문장을 거부한다.
2. PostgreSQL 연결 옵션에 `default_transaction_read_only=on`을 요청한다.
3. `REPEATABLE READ READ ONLY` 트랜잭션을 명시적으로 시작한다.
4. 첫 데이터 조회 전에 `transaction_read_only=on`과 `transaction_isolation=repeatable read`를 모두 확인한다.
5. 성공과 실패 모두 `ROLLBACK`으로 종료하며 연결 자원 정리 실패도 별도 실패로 보존한다.
6. 접속 문자열과 오류에는 자격 증명을 기록하지 않는다.

이번 실행은 연결 단계에서 실패했으므로 3~4번의 서버 측 검증까지 도달하지 않았다. 따라서 `read_only_verified=false`가 올바른 결과다.

## 4. 대표 바스켓 DB 준비도

| 심볼 | 대표 축 | 관측 상태 | DailyPrice 행/범위 | 최종 포함 판정 |
|---|---|---|---|---|
| SPY | 시장 벤치마크 ETF | `not_observed` | 관측 안 됨 | `deferred` |
| AAPL | 대형 기술주 | `not_observed` | 관측 안 됨 | `deferred` |
| JPM | 금융 | `not_observed` | 관측 안 됨 | `deferred` |
| XOM | 에너지 | `not_observed` | 관측 안 됨 | `deferred` |
| WMT | 소비/리테일 | `not_observed` | 관측 안 됨 | `deferred` |
| UNH | 헬스케어 | `not_observed` | 관측 안 됨 | `deferred` |

프로브가 연결 가능한 환경에서 수집하도록 구현한 항목은 종목 메타데이터, 행 수와 날짜 범위, `created_at` 범위, 가격 통화 불일치, 비양수 OHLC, 0 거래량, 음수 거래량, OHLC 범위 위반, 분할·배당 이벤트 관측, 결측 기간이다. 달력 테이블이 확인되기 전의 결측치는 명시적으로 **평일 프록시**일 뿐 거래소 영업일 판정이 아니다. 충분한 이력 길이 기준은 사후적으로 발명하지 않고 분포를 먼저 노출한다.

## 5. 적대적 후보 탐색

| 실패 모드 | 탐색 방법 | 이번 실행 |
|---|---|---|
| 반복 분할 | StockSplit 횟수 순위 | `not_run` |
| 대규모·역분할 | 분할 조정 계수 순위 | `not_run` |
| 배당 이력 | 과거 배당 이벤트 순위 | `not_run` |
| IPO·짧은 이력 | DailyPrice 커버리지 오름차순 | `not_run` |
| 장기 결측·거래정지 후보 | 결측 비율·횟수·내부 최대 공백·stale tail을 독립 순위화 | `not_run` |
| OHLCV 무결성 | 구조적 이상 횟수 순위 | `not_run` |
| 티커 변경 | 시점별 심볼 생애주기 해석 | `not_run` |
| 합병·인수 | 인수 생애주기 사건 해석 | `not_run` |
| 분할 신설법인 | spin-off 사건 해석 | `not_run` |
| 상장폐지·terminal return | 종결 사건·수익률 해석 | `not_run` |

모든 항목의 공통 제한은 데이터베이스 접근 실패다. 빈 후보 목록은 “후보 없음”이 아니라 “탐색하지 못함”을 뜻한다. 연결 가능한 경우에도 사건 테이블에 없는 것을 사건 부재로 간주하지 않으며, 기업행동 후보에는 DailyPrice 커버리지 상태를 함께 붙인다.

## 6. Data Eligibility

| 선언 용도 | 판정 | 핵심 이유 |
|---|---|---|
| `exploratory` | `prohibited_for_declared_use` | 스냅샷을 관측하지 못해 최소 인벤토리 근거도 없음 |
| `confirmatory` | `prohibited_for_declared_use` | PIT 재구성, 가용 시점, 제공자 계보, 조정 의미론, 수정 이력을 입증하지 못함 |
| `replication` | `prohibited_for_declared_use` | 확인적 요구사항과 독립성 증거를 모두 입증하지 못함 |

세 판정의 공통 누락 요구사항은 `observed_database_snapshot`, `point_in_time_reconstructability`, `sufficient_availability_confidence`, `content_fingerprint`, `daily_price_provider_provenance`, `price_adjustment_semantics`, `revision_lineage`, `entity_resolution_version`이다. 독립 재현에는 `replication_independence_evidence`도 필요하다.

현재 스냅샷을 조회할 수 있게 되더라도 `created_at`만으로 과거 시점 가용성을 입증할 수 없다. 스키마 컬럼의 존재만으로 제공자 계보·가격 조정·수정 이력의 의미론을 통과시키지도 않는다. 별도의 봉인된 연구 내보내기가 없으므로 DataView `content_fingerprint`는 의도적으로 `null`이며, 결과 문서 자체의 지문과 혼동하지 않는다.

## 7. Data Gap / Opportunity

| ID | 우선순위 | 제안 |
|---|---|---|
| DG-DP-ACCESS-001 | Required | 준비도 실행용 읽기 전용 프로덕션 스냅샷 접근 |
| DG-DP-EXPORT-001 | Required | 봉인되고 재구성 가능한 DailyPrice 연구 내보내기 |
| DG-DP-AVAILABLE-AT-001 | Required | 시장 세션 가용 시각 계약 |
| DG-DP-PROVENANCE-001 | Required | 행 단위 DailyPrice 제공자 계보 |
| DG-DP-ADJUSTMENT-001 | Required | 원시·분할조정·총수익 가격 계약 |
| DG-DP-DIVIDEND-001 | Required | 완전한 PIT 배당·총수익 이력 |
| DG-DP-REVISION-001 | High Value | DailyPrice 정정·빈티지 계보 |
| DG-DP-ENTITY-001 | High Value | 시점별 티커·기업 생애주기 |
| DG-DP-TERMINAL-RETURN-001 | High Value | 상장폐지·terminal return 이력 |
| DG-DP-CALENDAR-001 | High Value | 버전 관리된 거래소 세션 달력 |

각 제안의 연구 필요, 요청 데이터/변환, 현재 제한, 변경 유형, 빈도·기간·유니버스, 재사용성, 예상 비용, 대안, 책임자 권고, 불확실성은 실행 산출물 `data_gaps.json`에 구조화했다.

## 8. 구현과 재실행

- 핵심 판정·쿼리·산출물 생성: `math_lab/runtime/daily_price_readiness.py`
- 읽기 전용 PostgreSQL 실행기: `math_lab/runtime/daily_price_probe.py`
- 단위·SQLite 통합·가짜 PostgreSQL 세션 테스트: `math_lab/runtime/test_daily_price_readiness.py`
- 실행별 원문 산출물: `.lab_automation/runs/SV-MATH-DP-READINESS-001/17239e86-7a44-4077-99e2-0bbbe0852f08/`

연결이 허용된 환경에서 동일 실행기를 다시 수행해야 실제 대표 바스켓 표와 적대적 후보를 채울 수 있다. 그때에도 읽기 전용 상태 확인이 실패하면 데이터 조회 없이 중단해야 한다.

## 9. 해석 제한

- 여섯 종목이 전체 데이터베이스나 역사적 투자 가능 유니버스를 대표한다고 주장하지 않는다.
- OHLC 경계 검사를 통과해도 가격 정확성이나 조정 의미론이 입증되는 것은 아니다.
- 현재 섹터·티커·구성종목 정보가 과거에도 알려져 있었다고 간주하지 않는다.
- 기록된 분할의 처리가 배당 조정 또는 총수익 정확성을 뜻하지 않는다.
- 단위 테스트 통과는 프로덕션 DailyPrice의 준비도 통과가 아니다.
- “이상 미관측”은 점검한 스냅샷과 규칙에 한정되며 완전성의 증명이 아니다.

