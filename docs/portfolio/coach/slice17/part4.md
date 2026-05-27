# Slice 17 Part 4 — KeyObservationsSection 추출 + E5 조합 검증 (분할 최종 게이트)

## 0. 전제

- 브랜치: slice17, HEAD d7626fb (작업 시작 시 checkout 확인, working tree clean)
- baseline: vitest 32 files / 152 tests + tsc exit 0
- 분할 순서: 실측 4순위 (최종) — E5 = action_items + quoted_metrics 양쪽 보유,
  분리 Section 조합 회귀의 자연 게이트
- 회귀 위험: 검증 핵심 — 조합 회귀 발생 시 여기서 잡힘
- 비용: $0 (프론트 리팩터링, LLM 호출 없음)
- 안 B 경계 규칙 유지: 외형 wrapper 신규 생성 금지 / 섹션·원자 단위 공유 OK
- 회귀 게이트: 기존 152 무손실 + tsc exit 0. 감소 시 즉시 HALT.

## 0.1 실측 확정 사실

- key_observations: CommentaryCard L74-86, 조건 observations.length>0, 아이콘 Target
- CommentaryCard 잔여 (Part 3 종료 시점): <BaseCard> 안에
  key_observations 인라인 1건 + ActionItemsSection + QuotedMetricsSection
  - RiskFlagsSection. import 잔재 = Target lucide 1건.
- key_observations 보유 EP: 6 EP 전부 (optional, base 필드)
- E5: 6화면 중 유일하게 action_items + quoted_metrics 동시 보유 (risk_flags 없음)
- Step 0 산출 자산: SectionHeader, CardSection 사용 가능

## 1. P4-A — KeyObservationsSection 추출 (커밋: refactor: KeyObservationsSection 추출)

대상: frontend/components/coach/

1. components/coach/KeyObservationsSection.tsx 신규
   - props: { keyObservations: string[] }
   - CommentaryCard L74-86 key_observations 렌더 블록 이전
   - SectionHeader(icon=Target, title) 사용
   - 조건부 렌더는 CardSection 패턴 유지
2. CommentaryCard.tsx 재구성
   - key_observations 인라인 블록 → <KeyObservationsSection> 치환
   - Target lucide import 제거 확인
   - ⚠ 이 단계 후 CommentaryCard는 인라인 렌더 로직 0건이어야 함 —
     <BaseCard> + 4개 Section 조립부만 남음. 확인 후 보고.
3. 단위 테스트 — **tests**/coach/KeyObservationsSection.test.tsx 신규
   - keyObservations 있을 때 렌더 / 빈 배열 미렌더

## 2. P4-B — E5 조합 검증 (분할 최종 게이트, 커밋 없음 — 검증 단계)

E5는 action_items + quoted_metrics + key_observations 동시 보유.
분리된 Section들이 한 화면에서 함께 렌더돼도 회귀 0인지 확인.

1. E5 page 테스트 testId='commentary-card' 단언 무변경 통과
2. E5 화면에서 4개 Section(KeyObservations/ActionItems/QuotedMetrics)이
   기존과 동일 순서·동일 렌더 결과인지 행위 보존 확인
   (E5는 risk_flags 미보유 → RiskFlagsSection 미렌더 확인)
3. 6화면 전체 회귀 확인 — E1·E2·E3·E6 testId 단언 + E4 e4-bubble 단언
   전부 무변경 통과 (분할 전체 누적 회귀 0 최종 확인)

## 3. P4-C — Section 조합 통합 테스트 (커밋: test: CommentaryCard 조합 통합 테스트)

1. **tests**/coach/CommentaryCard.test.tsx 신규 또는 보강
   - 4개 Section 전부 데이터 있는 경우 → 4 섹션 모두 렌더
   - optional 일부만 있는 경우(E5 형태: risk_flags 없음) → 해당 섹션만 미렌더
   - 전부 없는 경우 → BaseCard 헤더만
   - CommentaryCard가 조립부로서 Section 배치 순서 보장 단언

## 4. P4-D — Part 4 closing (커밋: docs: Slice 17 Part 4 closing)

1. docs/portfolio/coach/slice17/part_4/closing.md — P4-A/B/C 산출, KPI, vitest 갱신
2. Slice 17 closing 진입 메모 — 아래 3건 closing에서 처리 예정:
   - §3 경계 규칙 명문화 (공유=원자·섹션 / 비공유=외형 컨테이너)
   - #21 metrics_table deprecated 처리 판단
   - #71 외부 자동화 부채 해소 검토 (+ pre-commit 화이트리스트 수동 추가 패턴 기록)

## KPI

- vitest 기존 152 무손실 + KeyObservationsSection·CommentaryCard 조합 테스트 +N
- tsc exit 0
- CommentaryCard 인라인 렌더 로직 0건 (조립부만 — grep으로 확인)
- Target lucide import — KeyObservationsSection으로만 이동 확인
- 6화면 전체 testId 단언 무변경 통과 (분할 누적 회귀 0 최종 확인)
- E5 4-Section 조합 행위 보존 확인

## HALT 규칙

- 기존 152 통과 수 감소 시 즉시 HALT.
- E5 조합에서 Section 순서·렌더 결과 변동 발견 시 즉시 HALT (조합 회귀 — Part 4 핵심 검증 대상).
- CommentaryCardData 타입 계약 변경 발견 시 HALT (Slice 18+ 범위).
- CommentaryCard에 인라인 렌더 로직이 남으면 HALT (분할 미완 — Part 4 목표 미달).
