# execution_plan_v1.md

monorepo 폴더 이동 **실행 계획서**. blueprint_v1.md의 결정 ①②③를 입력으로 받아, 실제 폴더 이동의 절차·검증·롤백·세션 격리·이관 슬롯·통과 기준을 명세한다.

| 메타 | 값 |
|------|------|
| 버전 | v1 |
| 작성일 | 2026-05-29 |
| 입력 | blueprint_v1.md §7 (결정 정착 현황 + 실행 입력 6 ✅) |
| 출력 | 8 PR 청사진 (PR1 → PR8) |
| 진입 단위 | 옵션 A (트랙 단위 ~7 PR, 실측 8 PR) |
| 첫 PR 정책 | A1 (services/_dormant 먼저, 학습 곡선 우선) |
| origin 기점 | origin/main HEAD = `9b48d37` (③ 빌드도구 보류) |

---

## 0. 입력 — blueprint_v1.md 결정 ①②③

| 결정 | 내용 | commit |
|------|------|--------|
| ① | import path = dotted-path (`services.stocks` 형태) | `4f01cb7` |
| ② | 분류 = **세션 충돌 방지** 기준 (apps 메인 4 + integrations + packages + services/_dormant + 루트 메타) | `118f899` → `7e42193` |
| ③ | 빌드 도구 보류 (CI 부재 = 가치 0, 재검토 트리거 = CI 도입/frontend 다중화/빌드 저해) | `9b48d37` |

목표 구조 (결정 ②):

```
apps/                              # 메인 4 트랙
  dashboard/    (stocks·users·news 등 통합)
  market_pulse/ (독립 트랙)
  chain_sight/  (chainsight)
  portfolio/    (coach·thesis·metrics·validation·sec_pipeline 등)
integrations/
  iron_trading/ (외부 자동화 격리)
packages/
  shared/       (공통 유틸·LLMClient·CostGuard)
  web/          (frontend 공통)
services/
  _dormant/
    graph_analysis/ (휴면, 미사용)
[루트 메타: pyproject.toml · settings · docs · scripts]
```

---

## 1. 이동 순서 — 8 PR (의존성 역방향 + 학습 곡선 우선)

| PR | 트랙 | 의존도 | 위험 | 슬라이스 병행 | 세션 추정 |
|----|------|--------|------|--------------|----------|
| **PR1** | `services/_dormant/graph_analysis/` | 없음 (휴면) | 최저 | ✅ 가능 | 1 세션 |
| **PR2** | `packages/` (shared + web) | 다른 모든 트랙이 의존 | 중상 | ⚠️ 단독 권장 | 1 세션 |
| **PR3** | `integrations/iron_trading/` | 독립 (외부 도구) | 낮음 | ✅ 가능 | 1 세션 |
| **PR4** | ~~`apps/dashboard/`~~ **보류 → `apps/market_pulse/` 승계** | packages 의존 | 중 | ⚠️ 단독 권장 | 1 세션 |
| ~~**PR5**~~ | ~~`apps/market_pulse/`~~ **→ PR4로 흡수 (2026-05-31)** | — | — | — | — |
| **PR6** | `apps/chain_sight/` | packages 의존 | 중 | ✅ 가능 | 1 세션 |
| **PR7** | `apps/portfolio/` (coach 포함) | packages 의존 | **최고** | ❌ **금지** | 1 세션 |
| **PR8** | 루트 메타 정리 + 이관 5건 잔여 | 모든 트랙 정착 후 | 낮음 | ✅ 가능 | 1 세션 |

**역방향 근거**: import 경로 변경 시 "참조하는 쪽"은 "참조되는 쪽"이 신경로에 정착한 뒤 옮겨야 깨짐 최소. packages → integrations → apps 순서.

**PR1의 예외**: _dormant는 휴면(import 호출처 없음)이라 의존성 그래프에서 빠짐. 학습 곡선 슬롯으로 PR1 배정.

**PR4 dashboard 보류 (2026-05-31)**: `apps/dashboard/` 실 디렉토리/Django 앱 부재 확인 (코드 fact-check). blueprint §② 정의는 신규 트랙. **monorepo 트랙 외로 이연**, 트리거 = 독립 배포 또는 모듈 경계 명시 필요 시. PR4는 **PR5 원안 `apps/market_pulse/`로 승계** (결번 방지, 원안 PR5는 PR4에 흡수).

**PR 순번 재배치 (2026-05-31)**: PR4=market_pulse / PR5(원안 market_pulse) 결번 / PR6/PR7/PR8 그대로. dashboard 부활 시 PR9 또는 별도 슬롯.

---

## 2. 검증 단위 — PR별 차등

| PR | 검증 항목 | 사유 |
|----|---------|------|
| PR1 | smoke (`pytest -k dormant`) + import lint | 휴면이라 IDENTICAL 영향 없음. PR1 목적은 **패턴 정착** |
| PR2 | pytest 759/1 + vitest 95+ + import smoke | packages 변경은 광범위 영향 → 풀 회귀 |
| PR3 | pytest (integrations 해당 분만) + import smoke | 독립 트랙 |
| PR4 | pytest + vitest (dashboard 분) + IDENTICAL 31/31 | apps 메인 진입 — IDENTICAL 첫 가동 |
| PR5 | pytest + vitest (market_pulse 분) + IDENTICAL 31/31 | |
| PR6 | pytest + vitest (chain_sight 분) + IDENTICAL 31/31 | |
| PR7 | **풀 회귀** (pytest + vitest + IDENTICAL 31/31 + cost_ledger 임계) | **코치 31 응답 byte-level 동일 검증의 핵심 PR** |
| PR8 | health_check 6✅/0⚠/1❌ + 전체 회귀 1회 | cleanup 후 baseline 재확인 |

**IDENTICAL 31/31 적용 시점**: PR4부터 (apps 메인 진입). PR1~3은 코치 응답 영향 없어 smoke로 충분.

**누적 비용 임계** (PR2 이후 매 PR):
- 풀 회귀 비용 < $0.01 (현재 누적 $0.0153 기준 마진 충분)
- 단, PR7은 코치 31 응답 재생성 → cost_ledger.jsonl 기록 필수

---

## 3. 롤백 지점

**전략**: 매 PR 직전 git tag → 실패 시 tag로 hard reset 또는 revert PR.

| 시점 | git tag | 명령 |
|------|---------|------|
| PR1 직전 | `monorepo-pre-pr1` | `git tag monorepo-pre-pr1 origin/main` |
| PR2 직전 | `monorepo-pre-pr2` | `git tag monorepo-pre-pr2 origin/main` |
| ... | ... | ... |
| PR8 직전 | `monorepo-pre-pr8` | `git tag monorepo-pre-pr8 origin/main` |

**롤백 절차**:
1. PR 머지 후 검증 실패 발견 시 → `git revert -m 1 <merge-sha>` (revert PR)
2. revert PR도 실패하면 → `git reset --hard monorepo-pre-pr{N}` + force push (최후 수단)
3. 어느 경우든 DECISIONS에 롤백 사유·SHA 기록

**복구 후 재진입**: 실패 원인 분석 → 동일 PR 번호로 재작성 (`PR{N}-v2`). PR 번호는 재사용.

---

## 4. 세션 격리

**원칙**: 1 세션 = 1 PR (검증·머지·DECISIONS 갱신·PROGRESS 갱신까지 한 세션 안에 종결).

**슬라이스 작업과 시간 분배**:
- PR1, PR3, PR5, PR6, PR8: 코치 슬라이스(Slice 18 등)와 시간 분배 가능
- PR2, PR4: 영향 범위 큼 → 단독 세션 권장
- PR7: **금지** (코치 코드 직접 영향 → 슬라이스 작업과 같은 세션 절대 불가)

**세션 시작 체크리스트** (매 PR 진입 시):
1. `health_check.py` 실행 → 6✅/0⚠/1❌ 확인
2. `origin/main` 최신 동기화
3. 이전 PR의 DECISIONS 기록·PROGRESS 갱신 확인
4. 해당 PR의 git tag 생성
5. branch 생성: `monorepo/pr{N}-{track-name}`

---

## 5. 이관 5건 슬롯 배정

DECISIONS "monorepo 재배치 ②" 의 3단계 실행 이관 미해결 5건을 8 PR 중 어느 슬롯에 끼울지 매핑.

| # | 이관 항목 (DECISIONS § ② 발췌) | 매핑 PR | 근거 |
|---|----------------------------|---------|------|
| 1 | `macro/services/macro_service.py` 위치 (packages vs services) — marketpulse v2 분리 코드 정독 후 판정 | **PR2** (packages) + **PR5** (apps/market_pulse 진입 시 재확인) | macro 해체 시 packages 후보 검토는 PR2에서 결정. market_pulse가 직접 흡수해야 한다면 PR5에서 재배치 |
| 2 | macro v1 API 10개 deprecate 범위 — frontend 실사용 grep 후 판정 | **PR5** (apps/market_pulse) | macro v1 진입점이 market_pulse 흡수 대상이므로 그 시점에 frontend 실사용 확정 + deprecate |
| 3 | 삭제 후보 3 model 실 제거 (`EconomicEvent`·`SectorIndicatorRelation`·`IndicatorCorrelation`) — `makemigrations --check` 후 | **PR8** (cleanup) | macro 해체가 PR5에서 완료된 후 마지막 정리 단계. 마이그레이션 영향 검증이 필요해 끝에 모음 |
| 4 | `frontend/` 최종 위치 — `packages/web/` vs 루트 유지 (세션 충돌 분석 + import 비용 측정 후) | **PR2** (packages 진입 시 결정) | packages 트랙 진입 시 `packages/web/` 디렉토리 자체를 생성할지가 PR2 범위. 결정 산출 = "packages/web 채택" 또는 "루트 유지 + 본 PR에서 packages/web 디렉토리 생성 보류" |
| 5 | `iron_trading`이 읽는 앱 인터페이스 계약 — `integrations/`로 격리하려면 contract 명시 필요 | **PR3** (integrations/iron_trading) | iron_trading 트랙 진입 자체가 contract 정의 시점. 격리 전 read-only 인터페이스 grep + `contracts/iron_trading.yaml` 신설 |

**매핑 원칙** (재확인):
- 트랙별 변경에 자연스럽게 동반되는 이관 → 해당 트랙 PR에 흡수 (별도 PR 만들지 않음)
- 어디에도 매핑 안 되는 이관(예: 마이그레이션 영향 검증) → PR8 cleanup에 통합

**미확정 영역** (PR 진입 시 사용자 확정 후 진행):
- 이관 1의 분할(PR2 vs PR5)이 정확히 어디서 끝나는가
- 이관 4의 "루트 유지" 결정 시 PR2 범위 축소 가능성

---

## 6. 통과 기준 — PR 머지 조건

모든 PR 공통 통과 기준 (8개 항목 전건 충족):

| # | 항목 | 측정 |
|---|------|------|
| 1 | 검증 항목(§2) PASS | 해당 PR의 검증 단위 통과 |
| 2 | IDENTICAL 31/31 (PR4 이상) | byte-level 동일 |
| 3 | health_check ❌ 신규 발생 0 | 기존 ❌(자기참조)만 잔존 |
| 4 | 누적 비용 임계 미초과 | PR7 한정, cost_ledger.jsonl 확인 |
| 5 | DECISIONS에 commit SHA 기록 | `monorepo PR{N}: SHA={...}` 형식 |
| 6 | PROGRESS.md 갱신 | 16일 stale 사고 재발 방지 (common-bugs #30) |
| 7 | git tag 생성 (`monorepo-pre-pr{N+1}`) | 다음 PR 롤백 지점 선제 확보 |
| 8 | 회귀 카운트 기록 | pytest·vitest 카운트 누적 추적 |

**실패 시 처리**: 1건이라도 미충족 → 머지 보류 → 원인 분석 → 동일 세션 또는 다음 세션에 수정 후 재검증.

---

## 7. 작업 시작 권고 — PR1 진입 시 4가지 점검

PR1은 "패턴 정착" PR. 다음 4가지를 PR1에서 동시 점검하여 PR2~PR8 기반 확보:

| 점검 항목 | 목적 | 산출물 |
|----------|------|--------|
| ① import 변경 도구 워크플로 | `ast-grep` 또는 `ruff` 기반 일괄 변경 패턴 정착 | 도구 명령 + 검증 절차 문서화 |
| ② git tag 롤백 절차 | tag 생성 → 실패 시뮬레이션 → reset 동작 확인 | DECISIONS에 절차 기록 |
| ③ DECISIONS 갱신 형식 | `monorepo PR{N}` 항목 표준화 | PR1 entry가 PR2~PR8의 템플릿 |
| ④ health_check 트랙별 출력 | 트랙 정합성이 health_check에 자동 감지되는지 | 출력 형식 + 알림 정책 |

이 4가지가 PR1에서 정착되면 PR2 이후는 패턴 답습으로 가속됨.

---

## 8. 다음 단계

1. **execution_plan_v1.md 위치 확정**: `docs/monorepo_migration/execution_plan_v1.md` (blueprint_v1.md와 동일 디렉토리, 일관성 유지)
2. **이관 5건 매핑 확정**: §5에 1차 매핑 박음. 미확정 영역(이관 1 분할 / 이관 4 PR2 범위) PR 진입 시 사용자 확정
3. **PR1 지시서 작성**: 본 execution_plan_v1.md를 입력으로 `docs/monorepo_migration/pr1_dormant_지시서.md` 작성 (Claude Code 실행용)
4. **PR1 진입**: 별도 세션에서 PR1 작업 시작 (학습 곡선 + §7 4가지 점검)

---

## 부록: 가중합 결정 이력

| 결정 | 옵션 | 가중합 | 일자 |
|------|------|--------|------|
| 이동 단위 | A 트랙 단위 | 4.15 | 2026-05-29 |
| | B 폴더 단위 | 3.30 | |
| | C 빅뱅 | 2.65 | |
| 첫 PR 위치 | A1 _dormant 먼저 | 4.00 | 2026-05-29 |
| | A2 packages 먼저 | 3.20 | |

격차 < 1.00 결정(A vs B, A1 vs A2)은 사용자 확정 거침. DECISIONS 참조.
