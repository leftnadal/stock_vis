# Slice 16 Step 0 — 부채 정리 + KPI 정의 (LLM 0콜, 신규 비용 $0 목표)

## 분기 / 환경

- slice16 브랜치를 slice15 HEAD cf37855 에서 분기
- 작업 시작 직후 git checkout slice16 확인 (외부 자동화 재발 대비, #71)
- 진행 중 working tree가 iron-trading-api로 전환되면 즉시 HALT·보고

## S16-0-A — #68: ledger entry_point + slice_id 정합

1. portfolio/llm/client.py:117-124 complete() 시그니처에
   entry_point: Optional[str] = None 추가
2. client.py:179 ledger append 호출: entry_point=None → entry_point=entry_point
3. e1~e6_service.py 6곳 client.complete(...) 호출에 entry_point="eN" 추가
4. slice_id 정합 — settings 자동 init 방식 (per-view reset_slice 불채택):
   - settings에 COACH_RUNTIME_SLICE_ID 추가 (기본 "runtime")
   - CostGuard 초기화가 settings 값을 사용 → 실 view 호출 시 slice_id가
     "default" 대신 의미값
   - 개발 하니스는 reset_slice()로 슬라이스별 override 유지
5. 회귀: ledger 관련 기존 테스트 갱신 + entry_point/slice_id 정합 단언 신규 추가

- breaking change 없음 (옵션 인자)

## S16-0-B — #70: AllowAny → IsAuthenticated (6 view)

1. coach e1~e6 view: permission_classes([AllowAny]) → [IsAuthenticated]
2. ⚠ 리플 처리: 인증 없이 호출하던 기존 view 테스트가 401 발생
   → force_authenticate 또는 테스트 토큰 픽스처로 갱신
3. P3-C/프론트 의존: 실 round-trip(Parts)·프론트 호출은 유효 토큰 필요
   → Step 0 범위는 view 변경 + 백엔드 테스트 + 토큰 픽스처 마련까지.
   프론트 토큰 첨부 검증은 각 EP Part에서.
4. HALT 조건: 인증 도입이 예상 외 광범위 변경을 유발하면 중단·보고

## S16-0-C — cost_ledger 1행 수동 보정 (결정 2.a)

- closing.md 기록값으로 P3-C 행 append:
  slice_id="slice15", entry_point="e1", provider="anthropic",
  model="claude-haiku-4-5", input_tokens=1516, output_tokens=1028,
  cost_usd=0.0053248, source="manual_backfill"
- 신규 LLM 지출 아님 (과거 발생 비용의 장부 복원)
- Slice 16 closing에 보정 사실 1줄 기록

## S16-0-D — Slice 16 KPI 매트릭스 정의

- 회귀 no-cost / cost 분리 유지
- #72 KPI 신규: "각 EP(E2~E6) 실 응답 shape == codegen 타입" — 각 Part P3-C로 충족
- IDENTICAL 31/31 유지가 KPI
- 누적 비용 cap $1.00 (Slice 16 예상 $0.03~0.10)

## 검증

- pytest IDENTICAL 31/31, vitest 74 무손실, tsc exit 0
- Step 0 LLM 0콜, 신규 비용 $0

## 커밋 (의미 단위 분리 — Stock-Vis 패턴)

- S16-0-A / S16-0-B / (S16-0-C+D) → 최소 2~3 커밋
