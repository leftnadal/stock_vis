# 지시서 — PR8c: 메타 정리 (monorepo 완주)

## 너의 역할 / 현재 위치

- 트랙: monorepo **마지막 조각 PR8c**. main HEAD = `30ba129`. PR8b 트랙 전체 종결.
- 묶음 4건: ① 빈 패키지·디렉토리 ② graph_analysis 자기참조 회귀(⚠️ health ❌ 연관 가능) ③ FMPClient 동명 절대경로 가이드 ④ 도식 잔재.
- 성격: 대부분 위생(위험 0). **단 graph_analysis만 원인 규명(STEP 0) 선행** — 위생 삭제 아님.

## ⛔ 절대 규칙 (위반 시 즉시 HALT)

1. graph_analysis는 **원인 규명 전 삭제·수정 금지.** 회귀가 무엇을 의미하는지 모른 채 지우면 health ❌가 더 꼬일 수 있다.
2. `services/_dormant/graph_analysis/`는 **휴면 자산**(부록 A). 휴면 의도를 깨지 마라 — 정리는 "회귀/자기참조 해소"지 "자산 부활/삭제"가 아니다.
3. 삭제는 git rm(히스토리 복구 가능)만. 각 변경 후 `pytest` + 경계 테스트 GREEN. 빨개지면 그 자리 HALT.
4. 메모리/지시서 경로·건수는 가설 → 실측 우선.

## Part 0 — STEP 0: health ❌ 정체 + graph_analysis 회귀 규명 (★ 보고 후 진행)

**0-1. health ❌ 1건의 정확한 정체**

```bash
poetry run python scripts/health_check.py --json 2>&1 | head -60   # 어떤 check가 ❌이며 메시지가 뭔지
```

→ ❌가 **(a)** "origin/main PROGRESS hash 미반영(자기참조)"인지 **(b)** "graph_analysis 회귀"인지 **(c)** 둘 다인지 판정. **이게 PR8c 스코프를 가름.**

**0-2. graph_analysis 자기참조 회귀 2건 실측**

```bash
ls -R services/_dormant/graph_analysis/ 2>/dev/null | head
grep -rn "graph_analysis" --include="*.py" . | grep -v "_dormant/graph_analysis/" | head -40
# 자기참조(자기 디렉토리를 자기가 가리키는 경로/도식) 형태 확인
grep -rn "graph_analysis" docs/ PROGRESS.md DECISIONS.md *.md 2>/dev/null | head -40
```

→ "회귀 2건"이 (코드 import인지 / 문서 도식 경로인지 / health 스크립트가 검사하는 경로 stale인지) **정체 규명.** 0-1의 ❌와 **같은 뿌리인지** 연결.

**0-3. 분기 판정 보고:**

- ❌ = graph_analysis 회귀 → PR8c로 ❌ 해소 가능. Part 2에서 처리.
- ❌ = PROGRESS hash 자기참조(별개) → graph_analysis 정리로는 ❌ 안 풀림. ❌는 정합성 시스템(Layer 4) 영역으로 분리 보고, PR8c는 위생만.
- 둘 다 → 각각 처리 경로 명시.

→ **Part 0 결과 보고 후 Part 1 진입.** graph_analysis 처리 방법이 불확실하면 HALT.

## Part 1 — 위생 일괄 (위험 0, 즉시)

- **빈 패키지·디렉토리:** `macro/management/commands/__init__.py`(빈 패키지), `marketpulse/` 빈 디렉토리, plan dashboard 도식 잔재 → 실측 후 `git rm`. (빈 디렉토리는 git이 추적 안 하면 잔재 파일만.)
- **FMPClient 동명 가이드:** `FMPClient` 3 모듈(apps/market_pulse/services/fmp_client.py · packages/shared/api_request/providers/fmp/client.py · services/serverless/services/fmp_client.py) → common-bugs에 "동명 3곳, **항상 절대경로 import**" 한 줄 + 각 파일 상단 식별 주석(선택).
- `pytest` GREEN → commit "PR8c-a: 빈 잔재 정리 + FMPClient 절대경로 가이드".

## Part 2 — graph_analysis 회귀 처리 (Part 0 분기 따라)

- 0-2에서 규명된 회귀 형태대로 **최소 변경**으로 해소(휴면 의도 보존). 예: 도식 경로 stale면 도식만 정정 / health 스크립트가 검사하는 stale 경로면 그 항목만 조정 / 죽은 자기참조 import면 그 라인만.
- **health ❌가 0-1에서 graph_analysis로 판명됐다면** → 처리 후 `health_check.py`가 ❌ → ✅ 되는지 확인.
- `pytest` + 경계 GREEN → commit "PR8c-b: graph_analysis 자기참조 회귀 해소".

## Part 3 — monorepo 트랙 종결 처리

- **PROGRESS/DECISIONS:** monorepo 트랙 **완주** 기록. 답습 자산(부록 A + PR3·4·7 + PR8a 4종) 최종 정리.
- health 재실행: 가능하면 **8✅/0⚠/0❌**(❌가 graph_analysis였다면 해소). PROGRESS hash 자기참조가 별개로 남으면 그 1건만 명시(정합성 시스템 영역).
- 회귀 최종: `pytest` 3179 유지(또는 위생 삭제로 테스트 수 변동 시 그 델타 명시) + 경계 ✅ 우회 0 / 동결 5.
- commit "PR8c-c: monorepo 트랙 완주 정착".

## 보고 산출물

- **Part 0(최우선):** health ❌ 정체(a/b/c) + graph_analysis 회귀 정체 + 둘의 연결 여부.
- 위생 정리 목록(삭제 파일, 가이드 추가 위치).
- graph_analysis 처리 내용 + health ❌→✅ 여부.
- monorepo 트랙 종결 상태 + 최종 health/pytest/경계.
- 잔존(있으면): PROGRESS hash 자기참조(정합성 영역), BOUNDARY-1~3(경계 트랙), Beat prod 동기화(운영), macro 모델 보류 등 — "monorepo 외 트랙"으로 분리 명시.
