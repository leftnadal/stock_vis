# QUAD-IMPL-1 — 섹터 사분면 화면 구현 지시서

## 계약 헤더
- 트랙: DSS-QUADRANT / 세션: 구현(코드 쓰기·DB 무변경) / ID: QUAD-IMPL-1
- worktree ~/worktrees/sv-quad-impl1 · 브랜치 monorepo/sess-quad-impl1
- 확정 결정 (DECISIONS 등재, 문안 변경 금지): D-DSS-QUAD-PLACE · D-DSS-QUAD-TEMPORAL ·
  D-DSS-QUAD-ENCODE · D-DSS-TAU 종결 · 커버리지 방침 + 가이드 JSON 초안 2문항 부기.
- 쓰기 허용: (W1) docs — 본 지시서·DECISIONS·TASKQUEUE (PROGRESS 제외 — BOUNDARY-TRIAGE-1
  트리아지가 수행). common-bugs 쓰기 금지(D-NUMBERING-MGMT-ONLY, 비대상).
  (W2) backend read-only API 모듈+테스트. (W3) frontend 신규 컴포넌트+테스트+대시보드 1파일 최소 수정.
  DB 쓰기 0·FMP 0.
- 실행: foreground · add 명시 · force 금지 · push=D-PUSH-DELEG.
- 커밋: 1=0게이트(지시서+DECISIONS+TASKQUEUE) → Slice 1~3 연속. HALT-0.

## 슬라이스
- Slice 1 (커밋 2): GET 단일 엔드포인트, 11섹터 × {sector, heat(null), heat_date, breadth_curr,
  breadth_prev, denom_curr, denom_prev, anchor_curr, anchor_prev, arrow_suppressed}. 서비스 분리·뷰 얇게.
  suppression 서버측(§2 재사용). pytest 3+(정상/heat null/suppression).
- Slice 2 (커밋 3): 공용 컴포넌트(props만)·순수함수(중앙값·구역·suppression). ② teal·④ 경보색,
  점+화살표(suppressed 숨김+각주), 미산출 하단 목록, 가이드 ? 버튼 자리 예약. vitest(중앙값/구역/suppression/null).
- Slice 3 (커밋 4): app/page.tsx 최상단 삽입(diff 최소). 빌드+전 테스트. API 11행 덤프 첨부.
  TASKQUEUE 편승 QUAD-VISUAL-CHECK 등재.

---

## 집행 결과 (QUAD-IMPL-1, 재개 2026-08-27)

> 최초 STEP 0(08-27 오전)에서 origin/main shared 경계 FAIL(EODUNIV-P15 7ec24c62) HALT →
> BOUNDARY-TRIAGE-1이 동결 격리·착지(origin/main `7abf8671`, green 회복) → 재개.

### STEP 0 (0-2~0-6 최초 실측값 재사용, 0-1만 재실측)
| # | 결과 |
|---|---|
| 0-1(재측) | health 15 OK / 1 WARN((i) runtime_check) / **0 ERROR** — shared 경계 ✅ OK(우회 0/동결 잔여 1). HALT 미발동 |
| 0-2 | 라이브 대시보드 = `app/page.tsx`(root `/`). `/dashboard`=redirect 스텁. 삽입점=`max-w-6xl` 컨테이너 최상단 |
| 0-3 | ThemeHeatScore(apps.chain_sight) 최신 08-26 · 6/11 섹터 · **경계 x=heat 중앙값 50** |
| 0-4 | ThemeDemandScore anchor 08-21·08-14 각 11행. flat_ratio 08-21=7.49% / **08-14=99.60%(≥90%)** → 08-14→08-21 화살표 suppressed |
| 0-5 | BE chain_sight `api/heat_views.py`(APIView·inline dict)·prefix `/api/v1/chainsight/`·테스트 `tests/unit/chainsight/`. FE vitest·`hooks/`·`types/`·`components/charts/` |
| 0-6 | 파일 목록 = 아래 슬라이스 확정 목록 |

### 가이드 JSON 초안 2문항 (가이드 렌더러 트랙 착지 시 첫 콘텐츠로 소비 예약)
```json
[
  {
    "id": "quad-what",
    "q": "이 사분면은 무엇을 보여주나요?",
    "a": "11개 GICS 섹터를 두 축으로 배치합니다. 가로축=Heat(시장 관심도, 경계=당일 비null 중앙값), 세로축=수요 breadth(애널리스트 EPS 컨센서스 방향, 경계=0). 점=당주, 화살표=전주→당주 이동."
  },
  {
    "id": "quad-zones",
    "q": "teal(②)·경보색(④) 강조 구역은 무엇인가요?",
    "a": "② 저Heat+수요개선 = 저평가·개선 기회 후보. ④ 고Heat+수요악화 = 과열·전망 악화 주의. 강조는 주목 유도일 뿐 매매 신호가 아닙니다. 화살표가 숨겨진 섹터는 해당 주 컨센서스 변화가 미미(flat≥90%)함을 뜻합니다."
  }
]
```
