# Theme Heat Cycle 1 — PR 프롬프트 묶음 (5건)

- **앵커 문서**: `theme_heat_design.md` **v1.2 FINAL** (이하 "설계서" — repo 내 위치:
  `docs/chain_sight/theme_heat/theme_heat_design.md`, TH-1 착수 전 커밋 필수). 모든 산식·
  규칙·모델은 설계서가 단일 진실이며, 본 프롬프트는 실행 순서·범위·종료 조건만 정의한다.
  충돌 시 설계서 우선.
- **실행 순서**: TH-1 → TH-2 → TH-3 → (TH-4 ∥ TH-5). TH-4/5 는 TH-3 의 API 완성 후 병렬 가능.
- **트랙 귀속**: TH-1~4 = 마켓 뷰 트랙, TH-5 = Market Pulse 트랙 (설계서 §11).
- **공통 규율**: 활성 브랜치 최대 2개 준수 / `wip:` 커밋 / 각 PR 완료 시 설계서 §11 표 체크 +
  PROGRESS.md 1줄 / 산식·가중치·모델 변경이 필요해지면 **코드가 아니라 설계서를 먼저 개정**
  (버전 증가) 후 재착수.

---

## PR-TH-1: 스키마 마이그레이션 (독립)

### §1 목적

온도계 2축(Heat/DSS)의 전 데이터 모델을 **독립 마이그레이션**으로 생성한다 (앱 경로
`apps/chain_sight`, 현행 최신 0015 뒤에 이어짐). Cycle 2 모델(DSS)까지 선반영해 후속
마이그레이션을 제거한다. ~~마켓 뷰 PR-1 동승~~ — 설계서 v1.2 §14 결정으로 폐기
(SeedHeatScore 미착수 실측, 가짜 의존성 절단).

### §2 범위

설계서 §6.0~§6.6 의 7개 모델: HeatEntity, ThemeHeatScore, ThemeDemandScore,
InsiderTransactionRecord, ThemeEtfMap, ThemeFilingCount, EstimateSnapshot.
**설계서 v1.2 는 자기완결** — 7모델 전부 필드 표가 §6 에 인라인되어 있으며, 외부 버전
참조 없음. 표에 없는 필드는 만들지 않는다.

### §3 구현 지시

1. 모델 정의는 설계서 §6 의 필드 표를 그대로 따른다. 임의 필드 추가 금지 — 특히
   **HeatEntity 는 3필드 초과 금지** (설계서 §6.0 잠금장치 1).
2. 데이터 시드: HeatEntity 에 `kind=sector` 11행 (GICS 11개 섹터). `kind=theme` 행 생성
   금지 (잠금장치 2).
3. unique 제약: 설계서 §6 표의 unique_together·dedup_key 전건 반영.
4. ThemeEtfMap 초기 데이터는 설계서 **§6.4 초기 시드**를 적용하되, 검수 미완(§12-2)
   플래그를 fixture 주석으로 명기.
5. docs 동승: 설계서 v1.2 + 지시서 1·2·3호 + 프로브 보고서 3종을
   `docs/chain_sight/theme_heat/` 로 커밋 (설계서 §11 문서 편입 규칙).
6. **조율 의무 기록**: 마켓 뷰 PR-1(SeedHeatScore) 착수 시 cs_44 개념 조율 + HeatEntity
   재사용 검토가 선행 의무임을 TASKQUEUE.md 에 1줄 등재 (설계서 §11).

### §4 안전·제약

정식 마이그레이션 PR. 기존 테이블 무접촉(추가만), 기존 행 무손상 검증 필수(0015 까지의
13,697행 등). 마이그레이션 파일은 본 PR 산출물 1개.

### §5 종료 조건

`migrate` 정상 + 역마이그레이션 동작 + HeatEntity 11행/theme 0행 검증 테스트 GREEN +
7모델 각 최소 1건 생성·조회 단위 테스트 GREEN + docs 동승 확인 + TASKQUEUE 조율 의무 등재.

---

## PR-TH-2: 내부자 파이프라인 (백필 + 방어 필터 + 증분)

### §1 목적

C2a(내부자, 배분 0.12)의 원장을 구축한다 — FMP E1/E2 를 InsiderTransactionRecord 로
적재하는 백필 커맨드와 일간 증분 수집.

### §2 선행

PR-TH-1 병합.

### §3 구현 지시

1. `backfill_insider_transactions` management command (1회성, beat 아님): 대상 = EOD
   스크리닝 유니버스(S&P 500) ∪ 테마 구성종목, 깊이 3년, E1 페이지네이션 순회.
2. dedup_key = 설계서 §5.1 해시 구성 그대로, upsert 멱등 (재실행 안전 테스트 필수).
3. **방어 필터를 적재가 아닌 조회(집계) 계층에 구현** — 원본 레코드는 전건 보존하고
   (transaction_type 공란 포함), C2a 집계 함수가 설계서 §5.1 필터(매도=S-Sale·매수=
   P-Purchase 만 / price=0 금액가중 제외 / type_of_owner 가중 1.0·0.7·0.5)를 적용한다.
   근거: 필터 규칙 튜닝 시 재수집 없이 재집계만으로 대응.
4. 증분: E2(latest) 기반 일간 수집 함수 (beat 등록은 TH-3 에서 일괄).
5. E3 sanity check: 자체 분기 집계 vs E3 statistics ±10% 대조 함수 (경고 로그만, 차단 없음).

### §4 종료 조건

백필 dry-run(표본 10종목) 검증 → 전체 실행 → 건수·기간 리포트 출력. 방어 필터 4규칙
각각의 단위 테스트 GREEN (특히 A-Award 를 매수로 오인하지 않는 케이스). 멱등 테스트 GREEN.

---

## PR-TH-3: Heat 8성분 배치 + beat 3종

### §1 목적

온도계의 심장 — C1~C8 성분 계산기, 합성기, beat 3종(`compute_theme_heat_task`,
`collect_theme_filings_task`, `snapshot_analyst_estimates_task`)을 구현한다.

### §2 선행

PR-TH-2 병합.

### §3 구현 지시

1. **성분 계산기 8개** (설계서 §2 표의 산식·lookback 그대로): 각 계산기는 독립 함수 +
   개별 try/except (설계서 §7 실패 격리). 반환 = {z, s, raw, missing_reason}.
2. C2b: 일 단위 날짜 창 순회 + `formType` 정확 일치 필터(424B5)·IPO 거래소 필터
   (NYSE/NASDAQ)·symbol 결측 제외+결손률 기록 (설계서 §5.2 전건).
3. C8: EstimateSnapshot 주간 적재 → 60일 diff. **콜드 스타트 분기 구현** (설계서 §5.3):
   스냅샷 <60일 = 결측 / 60일~365일 = cross_sectional z / ≥365일 = time_series z 전환.
   components 에 `z_mode` 기록.
4. 합성기: 시그모이드 → 가중합(가중치는 설계서 §2 표를 **상수 모듈**로 — 합 1.00 검증
   assert) → 결측 비례 재분배(§3-5) → 밴드 판정(§3-4).
5. C2b·C8 백필: filings 3년(일 창 순회), IPO 3년. estimates 는 백필 불가 — 스냅샷 beat 를
   본 PR 배포일부터 즉시 가동 (설계서 §7).
6. beat 3종 `register_chainsight_beats` 명시 등록 (Bug #28 패턴), ops_verify 대상 등록.
7. API: 섹터 목록 엔드포인트에 `heat_score`·`heat_status` 필드 추가 + Market Pulse 용
   `GET /api/market-pulse/theme-heat/` (설계서 §10.2 필드 계약, DSS 필드는 `not_computed`
   고정 반환).

### §4 종료 조건

성분 8개 단위 테스트(정상/결측/경계) GREEN. 합성 가중치 합 1.00 assert. 콜드 스타트 3분기
(결측/cross/time) 전환 테스트 GREEN. 1개 섹터 대상 end-to-end 배치 실행 → ThemeHeatScore
행 생성 확인. beat 등록 검증(`check_last_tick_succeeded` 대상 포함).

---

## PR-TH-4: 버튼바 온도 게이지 (마켓 뷰 FE PR 흡수분)

### §1 목적

Chain Sight 마켓 뷰 섹터 버튼바에 Heat 게이지를 붙인다 — 탐색 중 0.5초 판독.

### §2 선행

PR-TH-3 병합 (API 필드).

### §3 구현 지시

1. 섹터 버튼: 기존 증감율 아래 온도 게이지 바 + 점수 (본 대화 A안 목업 참조). 색 =
   과열 red / 주의 amber / 냉각 teal (ui_ux_design.md 팔레트).
2. **DSS 미노출** (설계서 §10.1 표시 절제 원칙 — Heat 단일).
3. 과열(≥70) 섹터의 시드 노드에 온도 링 (seed_node_design.md 의 SeedHeatScore 시각 문법
   과 통일 — 공용 `ThemeHeatBadge` 컴포넌트로 추출해 TH-5 와 공유).
4. 결측/미산출 상태: 게이지 자리 빈 dash (오류 표시 아님).

### §4 종료 조건

스토리북 또는 로컬 검증 스크린샷 3상태(과열/주의/냉각) + 미산출 상태. 기존 버튼바
동작(섹터 탭 전환) 회귀 없음.

---

## PR-TH-5: 2축 카드 (Market Pulse)

### §1 목적

Market Pulse 대시보드에 2축 카드를 출시한다 — **Cycle 1부터 2축 레이아웃**, DSS 열은
"수집 중" 상태 (설계서 §10.2, UI 재작업 제거 전략).

### §2 선행

PR-TH-3 병합. TH-4 와 병렬 가능 (공용 컴포넌트는 먼저 병합되는 쪽이 생성).

### §3 구현 지시

1. 카드 레이아웃: 본 대화 2축 목업 참조 — 행당 [상태 뱃지 | 테마명 | Heat 게이지·점수 |
   DSS 게이지·점수(수집 중) | evidence 한 줄], Heat 내림차순.
2. evidence line: 설계서 §10.3 결정론적 템플릿 — |z| 상위 2개 성분, LLM 미사용,
   C8 cross_sectional 기간은 "테마 간 상대" 표현 분기.
3. quadrant 필드는 DSS 가동 전 미표시 (필드는 API 에 이미 존재 — not_computed 처리).
4. 행 → Chain Sight 딥링크 (`chainsight_deeplink`).
5. `ThemeHeatBadge` 공용 컴포넌트 사용 (TH-4 와 공유).

### §4 종료 조건

카드 렌더 검증(Heat 실데이터 + DSS 수집 중 상태) 스크린샷. 딥링크 동작. evidence 템플릿
단위 테스트(상위 2성분 선정·z_mode 분기) GREEN.
