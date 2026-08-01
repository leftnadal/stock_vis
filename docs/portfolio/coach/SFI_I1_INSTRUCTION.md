# 지시서: SIGNAL-FORWARD-INFRA I-1 — FMP 애널리스트 신호 ingest 배관

> repo 배치본. 실행 세션 = 브랜치 `monorepo/sess-sfi-i1`, worktree `~/worktrees/sv-sfi-i1`.
> 선행 = SIGNAL-FORWARD-INFRA 프리플라이트(recon 브랜치 `monorepo/sess-signal-fwd-recon`, `0790c8f8`).

## 세션 계약 헤더
- 종류: 실행(기능 슬라이스) — worktree, 브랜치 monorepo/sess-sfi-i1
- 범위: shared FMP 래퍼 신호 메서드 + EstimateSnapshot 모델 + 유령 필드 writer +
  nightly ingest 태스크. **화면·advisory 엔진·기대수익 로직 일절 무접촉**
- **절대 규칙(공유 DB):** migrate = prod-write = 병진 수동. beat 등록(DB row) = 병진 수동.
  Claude Code는 마이그레이션 파일 생성·검증까지만. 게이트 실패 = 즉시 정지

## Part 0 — 지시서 repo 배치 (docs/portfolio/coach/SFI_I1_INSTRUCTION.md, 첫 커밋)

## Part A — 거버넌스·정리 (선행 커밋)
1. recon 브랜치(monorepo/sess-signal-fwd-recon, 0790c8f8 docs 3건)를 이 브랜치 base에
   병합 — 랜딩 시 함께 착지
2. **RUN-TOTAL-PERSIST 판별:** `git log -S "RUN-TOTAL" origin/main` + f2 병합(022f796c)
   시점 TASKQUEUE diff 실측 → ①등재 확인되면 종결 ②미등재면 재등재 + common-bugs에
   "보고-착지 불일치" 패턴 등재 ③판별 결과를 DECISIONS 1줄 기록
3. common-bugs: get_rating 404 오경로(→ratings-snapshot) / analyst-estimates period
   필수(누락=400, 6월 audit "http-400"은 오진) 2건 등재
4. DECISIONS: D-I1-1(shared 저장)·D-I1-2(append 전용)·D-I1-3(수집까지만) 등재

## STEP 0 — ground truth 측정 게이트
1. worktree·origin/main HEAD·recon 병합 상태 확인.
2. FMP 래퍼 실구조: _make_request 시그니처·self-throttle·일일카운터 위치, 기존 메서드
   명명 관례.
3. **유니버스·콜 예산 실측:** ingest 대상 = WalletHolding ∪ WatchlistItem 실제 심볼 수
   측정 → ×5엔드포인트 = 일일 콜 수 산출. 일일 카운터 여유(10000) 대비 10% 초과 시 HALT.
4. Stock.analyst_* 필드 타입 vs FMP 응답 타입 정합(Decimal 자릿수 등) — 불일치 시
   가산 전용으로 흡수 가능한지 판정, 기존 필드 변경 필요하면 HALT.
5. django_celery_beat 기존 등록 패턴(F1 beats 2행) 실측 — 동일 방식 재사용.

## Part 1 — shared FMP 래퍼 신호 메서드 (BE, 모델 무접촉)
- 신규 5메서드: ratings_snapshot / price_target_summary / price_target_consensus /
  grades_consensus + grades_historical / analyst_estimates(period="annual" 고정,
  quarter는 402이므로 파라미터로 열지 않음)
- get_rating 오경로 교정(/stable/ratings-snapshot) — 기존 호출처 전수 grep 후 회귀 확인
  (항상 None이었으므로 행위 변화는 "None→값"뿐임을 테스트로 명시)
- pytest: 메서드별 응답 파싱(recon 실측 필드 기준 fixture) + period 누락 방어

## Part 2 — EstimateSnapshot 모델 + 유령 필드 writer (마이그레이션 생성까지)
- packages/shared/stocks: EstimateSnapshot(symbol FK, captured_at, source="fmp",
  신호 페이로드 컬럼 — recon 표의 5신호, numAnalysts 포함) **append 전용**
- makemigrations → **신규 테이블 생성만인지 --dry-run·sqlmigrate로 증명**(기존 테이블
  변경 감지 시 HALT). migrate는 하지 않는다 — 병진 수동 구간으로 절차서 출력
- writer 서비스: EstimateSnapshot append + Stock.analyst_* 최신값 반영(이건 최신
  스냅숏 미러 — 시계열은 EstimateSnapshot이 정본)
- pytest: append 불변(동일 심볼 재수집 시 행 증가)·미러 갱신·부분 실패 격리(1종목
  실패가 전체 중단 안 됨)

## Part 3 — nightly ingest 태스크 (등록 제외)
- celery 태스크: 유니버스 순회 수집, self-throttle 존중, 실패 심볼 로깅 후 계속
- beat 등록은 하지 않는다 — 등록 절차서(스케줄 제안: 18:30 ET, snapshot 19:00 앞)를
  병진 수동 구간으로 출력
- pytest: 태스크 단위(수집 mock) + 카운터 소진 시 중단 방어

## Part 4 — 병진 수동 구간 절차서 출력 (Claude 집행 금지)
① migrate(신규 테이블) ② beat 1행 등록 ③ 1회 수동 태스크 실행 → EstimateSnapshot
행 수·Stock.analyst_target_price 채움을 **확인 쿼리로 증명**(#78) ④ 익일 아침 자동
발화 확인 쿼리 — F1 판정 패턴 재사용

## Closing 게이트
pytest·vitest 전체 green(vitest는 무접촉 증명용 회귀) / 경계 가드(신규 위반 0 —
shared에 넣었으니 apps import 금지 자동 검증) / --check(신규 테이블 외 0) /
health / cost_ledger 기입 / 의미 단위 분리 커밋 / 닫기 보고
