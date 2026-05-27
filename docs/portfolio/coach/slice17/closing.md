# Slice 17 Closing — CommentaryCard 분할 종결

## 0. 전제

- 브랜치: slice17, HEAD 09c76f2 (작업 시작 시 checkout 확인, working tree clean)
- baseline: vitest 34 files / 162 tests + tsc exit 0
- 비용: $0 예상 (#21 B는 프론트 타입 1줄 제거 + 테스트, LLM 호출 없음)
- 회귀 게이트: 기존 162 무손실 + tsc exit 0. 감소 시 즉시 HALT.

## 1. C-A — #21 metrics_table 프론트 타입 제거 (커밋: refactor: metrics_table 프론트 타입 제거 #21)

결정: 안 B 확정 — 프론트 CommentaryCardData에서만 제거, 백엔드 스키마 무변경.

1. frontend/lib/coach/types.ts:91 — CommentaryCardData.metrics_table 필드 제거
   - deprecated 주석(#21)도 함께 제거
2. grep 검증 — metrics_table 프론트 사용처 0건 확인
   - 5 Section 컴포넌트 미사용은 Part 4에서 확인됨, 재확인
   - CommentaryCard / 6 화면 page.tsx 미사용 확인
3. tsc exit 0 확인 — 수동 합집합 타입에서 필드 제거는 codegen 진부분집합 관계상
   structural compat 유지 (실측 4번 근거). 백엔드가 해당 필드를 보내도
   프론트 타입이 안 받을 뿐 — 충돌 없음
4. ⚠ 백엔드 portfolio/schemas/commentary_output.py 무변경 (E1Output/E2Output 그대로)
   IDENTICAL 31/31 무관 유지

## 2. C-B — 부채 장부 갱신 (docs 커밋에 포함)

1. #21 — 완전 close 아님. "부분 close — 프론트 제거 완료 / 백엔드 스키마 잔여"로
   갱신 후, 신규 항목으로 축소 재등록:
   "#21-b metrics_table 백엔드 스키마 잔여 — Slice 18+ 백엔드 트랙, PS 1.0"
2. #71 — close. 단 단순 close 아님 — 조건부 close로 기록:
   "#71 close — iron-trading 폴더 분리 회피책으로 해소. Slice 16~17 무재발로
   Slice 16 closing 정의 조건(1슬라이스 추가 모니터링) 충족. ⚠ 근본 해결 아님 —
   외부 자동화 환경 변경 시 재점검 필요."
3. 신규 경량 부채 등록:
   "#73 pre-commit hook 화이트리스트 슬라이스마다 수동 추가 — 자동화 후보, PS 0.5.
   #71과 별개(데이터 손실 리스크 아님, 단순 편의)."

## 3. C-C — §3 경계 규칙 명문화 (docs 커밋에 포함)

docs/portfolio/coach/ 의 §3 설계 결정 문서에 안 B 경계 규칙 명문화:

"[Slice 17 확정] 코치 화면 컴포넌트 공유 경계 규칙:

- 공유 가능 = EP 무관하게 동일 의미를 갖는 원자 표현 요소(ConfidenceBadge 등)
  및 단일 책임 섹션 컴포넌트(QuotedMetricsSection 등).
- 공유 금지 = 카드 wrapper(BaseCard) / 말풍선 wrapper(E4MessageBubble)처럼
  EP 표현 정체성을 결정하는 외형 컨테이너.
- E4MessageBubble은 BaseCard를 import하지 않는다. 향후 통일 시도 금지
  (Slice 16 §3 노트 계승)."

## 4. C-D — Slice 17 closing 문서 (커밋: docs: Slice 17 closing)

docs/portfolio/coach/slice17/closing.md 작성:

1. Slice 17 전체 요약
   - Step 0~Part 4: 컴포넌트 9개 추출 + 신규 테스트 47건
   - CommentaryCard 154줄 비대 컴포넌트 → BaseCard + 4 Section 조립부
   - 회귀: vitest 25/115 → 34/162 (행위 보존 — 5 Part 전 구간 기존 테스트 무손실)
   - HALT 0회, 비용 $0
2. 회귀 최종: vitest 34 files / 162 tests (+ C-A 후 갱신치) + tsc exit 0
   - IDENTICAL 31/31 — 백엔드 전용, Slice 17 무관(실측 5번 확정) — 추적 대상 아님 명시
3. 부채 변동: #71 close / #21 부분 close → #21-b 재등록 / #73 신규 → net 변동 기록
4. Slice 18+ 후보 정리 (택1 아님 — 다음 슬라이스 진입 시 가중합 결정):
   - 응답 지연 UX 차별화 (E3 진행률 — Slice 17 결정 시 Slice 18 유력 후보 예약분)
   - E4 대화 영속화 (zustand — 실수요 신호 확인 후)
   - Pick<CommentaryCardData,...> EP별 타입 좁힘 (Part 4 예고분)
   - #21-b metrics_table 백엔드 스키마 제거
   - 신규 EP 패턴 / codegen 직접 사용 검토
5. ⚠ 로드맵 메모: Slice 18은 종착점 아님 — 후속 트랙 정리 시 ~Slice 20대 초반,
   Phase 2(#12 분석엔진 + Tier 2) 진입 시 그 이상. "MVP 종료 vs Phase 2 진입"은
   Slice 18 진입점 결정 시 별도 판단 필요.
6. slice17-closing-done 태그

## KPI

- vitest 기존 162 무손실 (C-A 테스트 영향 시 +N 또는 동일)
- tsc exit 0
- metrics_table 프론트 grep 0건
- 백엔드 commentary_output.py 무변경 (diff 0 확인)
- 부채 장부 #71/#21/#73 갱신 반영

## HALT 규칙

- 기존 162 통과 수 감소 시 즉시 HALT.
- C-A에서 백엔드 스키마 파일에 손이 가면 즉시 HALT (안 B 위반 — 프론트 전용).
- tsc 에러 발생 시 HALT (codegen 정합 예상과 다름 — 재점검 필요).
