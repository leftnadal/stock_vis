# thesis/_reuse — 재사용 부품 격리소 (P1 철거 잔존)

> **의도적 import-broken 상태.** 이 폴더의 파일들은 thesis 모델(ThesisIndicator·IndicatorReading 등)에
> 의존하지만, P1 철거에서 해당 모델·테이블이 drop되므로 **런타임 로드가 되지 않는다.** 정상이다.

## 무엇인가
Monitor 허브 재건(ADR `D-MONITOR-REBUILD`, 2026-07-08)에서 신축에 이식할 **z-score+룰 기반 스코어 엔진 4종**을 폐기 대상 앱과 분리해 보존한 것.

| 파일 | 역할 |
|------|------|
| `indicator_scorer.py` | 지표 판독 → z-score 정규화 + 극단 변동성 감지 |
| `premise_aggregator.py` | 전제/가설 집계 (지표 다양성 가중, Noisy-AND 유사) |
| `arrow_calculator.py` | score → 각도(0~180°) + 색/라벨 매핑 |
| `thesis_state_machine.py` | 룰 기반 상태 판정 + phase 매핑 |

## 수명 (⚠️ 이식 즉시 삭제 규칙 — 이중 사본 drift 방지)
- **P2**: Monitor 모델(`Monitor{scope,...}` + `Claim`)로 **재배선**. **각 파일은 이식·배선이 끝나는 즉시 이 폴더에서 삭제**한다(코어=`apps/monitor`가 유일 소스, `_reuse/`에 사본 잔존 금지).
- **폴더가 비면 즉시 제거** → `thesis/` 디렉터리 처분(디렉터리 제거)으로 연결.
- 결과적으로 P2 진행에 따라 4개 엔진이 하나씩 빠지고, 마지막 엔진 이식 시 폴더 소멸.

## 스캔 제외
- pytest: `testpaths = tests`라 애초 미수집.
- ruff: `pyproject.toml [tool.ruff] extend-exclude`에 `thesis/_reuse` 등록.
