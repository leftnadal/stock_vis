# shared 경계 가드 (Shared Boundary Guard)

`packages/shared/` 은 단방향 base 경계다. **상위 앱(`apps/*`, `macro`)을 import하면 안 된다.** 이 문서는 그 규칙을 강제하는 감시 장치와 동결 부채를 정리한다.

## 규칙

- `packages/shared/**/*.py` 안에서 다음 import는 금지:
  - `from apps.* import ...`, `import apps`, `import apps.*`
  - `from macro.* import ...`, `import macro`
- top-level / 함수 내 lazy 구분 없음. `ast.walk`로 전수 검출.
- 상대 import (`from . import ...`, level ≥ 1)는 shared 내부 이동이므로 허용.
- 세그먼트 단위 매칭이므로 `macrodata`, `appsmoke` 같은 prefix-clash는 오탐 아님.

## 검문소 (검출)

1. **pytest 아키텍처 테스트** — `tests/architecture/test_shared_boundary.py`
   - 모든 PR/머지 전 자동 차단. 새 위반은 즉시 FAIL.
   - source를 `ast.parse`만 함 (import 실행 X → Django 셋업 무관).

2. **health_check 8번째 항목** — `scripts/health_check.py:check_shared_boundary`
   - 일상 점검에서 우회 발생을 보조 추적.
   - 야간(`run_health_check_nightly.sh`)이 `--ledger`로 호출 → `docs/harness/boundary_ledger.jsonl`에 burn-down 기록.

## 동결 (KNOWN_VIOLATIONS — 묵은 부채 5건)

| # | 파일 (packages/shared/ 기준) | import module | 형태 | 청소 PR |
|---|---|---|---|---|
| ~~1~~ | ~~`stocks/services/sp500_eod_service.py`~~ | ~~`apps.market_pulse.utils.circuit_breaker`~~ | ~~top-level~~ | **CLOSE 2026-06-01 BOUNDARY-1**: circuit_breaker → `packages/shared/api_request/` 승격, shared→shared로 정합 |
| ~~2~~ | ~~`stocks/services/sp500_service.py`~~ | ~~`apps.market_pulse.utils.circuit_breaker`~~ | ~~top-level~~ | **CLOSE 2026-06-01 BOUNDARY-1**: 동 |
| ~~3~~ | ~~`metrics/services/daily_report.py`~~ | ~~`apps.chain_sight.models`~~ | ~~lazy~~ | **CLOSE 2026-06-01 BOUNDARY-2**: `apps.get_model("chainsight", "CompanyChainProfile")` 동적 lookup (cross-app aggregator 표준) |
| 4 | `stocks/services/eod_regime_calculator.py` | `macro.models` | lazy | TASKQUEUE: BOUNDARY-3 (소비자 이동/방향1, 모델 이동 아님) |
| 5 | `stocks/services/eod_pipeline.py` | `macro.models` | lazy | TASKQUEUE: BOUNDARY-3 (소비자 이동/방향1, 모델 이동 아님) |

**burn-down**: 5(2026-06-01 STEP 0 초기) → 3(BOUNDARY-1 close) → **2** (2026-06-01 BOUNDARY-2 close). 잔여 = #4·#5.

**SSOT**: `tests/architecture/test_shared_boundary.py:KNOWN_VIOLATIONS`.
`scripts/health_check.py:_BOUNDARY_KNOWN_VIOLATIONS`는 동기 복사본 — 양쪽을 같이 갱신해야 함(감시 장치는 작아서 중복 허용).

## 소진 절차

1. 해당 위반 청소 PR을 별도로 머지.
2. `KNOWN_VIOLATIONS` 키 2곳에서 동시 삭제 (tests + health_check).
3. `test_known_violations_still_present`가 "사라진 키"를 잡아주므로 누락 시 RED.
4. ledger의 `frozen` 카운트가 자연 감소(burn-down) — 야간 추세 곡선이 우하향.

## 야간 ledger 스키마

`docs/harness/boundary_ledger.jsonl` — JSON 한 줄/일:

```json
{"timestamp": "ISO8601 UTC", "frozen": <int>, "bypass": <int>, "total": <int>}
```

- `frozen` = 현재 코드에 살아있는 동결 항목 수 (소진하면 줄어듦).
- `bypass` = KNOWN_VIOLATIONS에 없는 신규 위반 (항상 0이어야 정상).
- `total` = frozen + bypass.

## 금지 사항

- 야간이 자동 청소·자동 커밋을 만드는 코드 금지. ledger 적재 외 행위 0.
- pytest 테스트가 shared 모듈을 import해서 검사하지 마라. Django 셋업/순환 폭발한다. **반드시 `ast.parse`**.

## 관련 문서

- 결정: `DECISIONS.md` "shared 경계 검문소 (2026-06-01)"
- 부채 기록: `sub_claude_md/common-bugs.md` "shared 역방향 import 5건 (동결)"
- 소진 큐: `TASKQUEUE.md` `BOUNDARY-1/2/3`
