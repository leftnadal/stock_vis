# 지시서 — 위생 확인 2건 → PR8b STEP 0 (macro 분배 fact-check)

## 너의 역할 / 현재 위치

- 트랙: monorepo, **PR8b 진입 직전**
- main HEAD = `61b1d97` (PR8a 머지 완료)
- 롤백 tag = `monorepo-pre-pr8b`
- 이번 작업 범위 = **PR8b STEP 0 = 조사(fact-check)만.** 분배 실행은 별도 사이클.

## ⛔ 절대 규칙 (위반 시 즉시 HALT)

1. **읽기 전용 조사다.** `git mv` / `mv` 금지, 코드 수정 금지, `commit` / `push` 금지. 파일 시스템을 바꾸지 마라.
2. 목표는 "어느 조각이 어디로 가야 하는지" **보고서 작성까지**. 실행은 0.
3. 이 지시서·메모리에 적힌 경로/조각명(`apps/macro`, `fred/fmp client`, `모델 3개` 등)은 전부 **가설**이다. 실측으로 검증하고, 어긋나면 무조건 실측을 신뢰하라.
4. 막히거나 예상과 다르면 추정으로 진행하지 말고 **HALT + 발견 보고**.
5. `shared` 멤버 추가 안전성(1-4)은 PR2 이후 처음 건드리는 경계다. 여기서 위반이 1건이라도 나오면 분배안을 멈추고 별도 보고.

---

## Part 0 — 위생 확인 2건 (PR8b 안 막음, baseline 청소용)

**0-1. commit 수 실측** — baseline의 "9 vs 8 ahead" 표기 불일치 정정

```bash
git log 3b74782..61b1d97 --oneline | wc -l
git log 3b74782..61b1d97 --oneline
```

→ 실수치 보고. 9든 8이든 기능 영향 0.

**0-2. PR #30 자동 머지 확인**

```bash
gh pr view 30 --json state,mergedAt,title
```

→ `state=MERGED` 기대. 아니면 사유 한 줄 기록(수동 처리는 별도 트랙).

→ Part 0 결과 2줄 보고 후 Part 1 진입.

---

## Part 1 — PR8b STEP 0 (macro 분배 경계 조사)

조사 없이는 경계를 못 긋는다. 1-0 ~ 1-4 실측으로 **1-5 표를 채우는 것**이 목표.

**1-0. macro 실제 위치 확정 (경로 가정 금지)**

> 메인 4앱(dashboard·market_pulse·chain_sight·portfolio)에 macro는 없다. 루트인지 `apps/macro`인지 어디 해체됐는지부터 찾는다.

```bash
find . -type d -name "macro" -not -path "*/node_modules/*" -not -path "*/.git/*"
git ls-files | grep -i macro | head -50
```

→ 확정된 실제 경로를 `<MACRO_DIR>`로 삼아 이후 명령에 대입.

**1-1. macro 인벤토리** — 안에 뭐가 들었나 전수

```bash
find <MACRO_DIR> -type f -name "*.py" | sort
tree <MACRO_DIR> -L 2 2>/dev/null || find <MACRO_DIR> -maxdepth 2 -type f | sort
```

**1-2. 외부 → macro 역방향 의존** — 누가 macro를 끌어쓰나 (분배 경계의 1차 근거)

```bash
ast-grep run -p 'from macro.$$$ import $$$' --lang python .
ast-grep run -p 'import macro' --lang python .
ast-grep run -p 'from apps.macro.$$$ import $$$' --lang python .
# ast-grep가 못 잡는 동적 참조 보강
grep -rn "macro" --include="*.py" . | grep -i "import\|getattr\|importlib" | grep -v "<MACRO_DIR>"
```

→ **단일 소비자**면 그 앱으로 동거, **다수 소비자**면 `packages/shared` 후보.

**1-3. macro → 외부 정방향 의존** — macro가 뭘 끌고 나가나 (순환/누수 위험 점검)

```bash
grep -rn "^from \|^import " <MACRO_DIR> --include="*.py" \
  | grep -v "from macro\|from \.\|import macro"
```

**1-4. shared 멤버 추가 안전성 (★ 최우선 게이트 ★)**

> shared는 `apps/*`를 import하면 안 되는 단방향 경계. fred/fmp client류가 shared로 가도 이 규칙을 안 깨는지 확인.

```bash
ls -la packages/shared/
# 아래 결과는 "비어야" 정상 (출력이 있으면 = 위반 검출)
ast-grep run -p 'from apps.$$$ import $$$' --lang python packages/shared/
ast-grep run -p 'import apps' --lang python packages/shared/
```

→ 위반 0이면 PASS. 1건이라도 나오면 그 라인 전부 보고 + 분배안 HALT.

**1-5. 조각별 목적지 분류표** — 아래는 **가설**이다. 1-0~1-4 실측으로 채우고 검증할 것:

| 조각               | 종류   | 외부 참조처(실측) | 목적지          | 근거                                        |
| ------------------ | ------ | ----------------- | --------------- | ------------------------------------------- |
| (fred client?)     | client | ?                 | shared / 단일앱 | 다수 소비자면 shared                        |
| (fmp client?)      | client | ?                 | shared / 단일앱 | 동상                                        |
| (진입점 view/api?) | entry  | market_pulse?     | 해당 앱 동거    | 단일 소비자면 동거                          |
| 모델 3개           | model  | DB 테이블         | **보류**        | DROP은 데이터 백업/공실 확인 트리거 후 별도 |

**1-6. STEP 0 보고 산출물 (이 5개로 보고 마무리)**

1. 확정 분배 경계표 (조각 → 목적지, 근거 포함)
2. 보류 조각 명시 (모델 3개 + DROP 트리거 조건)
3. shared 멤버 추가 안전성 판정 (위반 0 여부 — PASS/FAIL)
4. 발견된 사각·리스크 (순환 의존, 동적 참조, 예상 밖 소비자 등)
5. 분배 실행 시 예상 커밋 경계 / 롤백 지점 후보 (제안만, 실행 아님)

→ 이 보고를 받으면 사용자가 **분배 실행 결정 사이클**(분할 순서·커밋 경계 확정)을 별도로 돌린다. STEP 0는 여기서 끝.

---

## 출력 형식

- Part 0 결과 → Part 1 각 단계 raw 출력 → 1-5 표 → 1-6 보고 5항목 순으로.
- 명령 출력이 길면 핵심만 요약하되, 의존 맵(1-2/1-3/1-4)은 누락 없이 전건 표기.
