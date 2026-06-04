# NT-3 ~ NT-6 — app-scoped 착수 스텁 (핸드오프용)

> **이 파일은 풀 지시서가 아니다.** 각 앱 Claude Project가 STEP 0 후 자기 규약·부록으로 구체화한다 — ops는 앱 결정을 대신하지 않는다(경계 보존, DECISIONS.md 2026-06-03).

- **출처보고서**: 2026-06-04 Daily Report
- **공통 행위보존**: 회귀(pytest / vitest) 전건 통과 + IDENTICAL 대상 유지 + 기존 데이터 파괴 금지(backfill만 허용).

---

## NT-3 — ChainProfile 미생성 31 + 속성 채움률 0% 3건

- **출처**: 보고서 / 🧬 Stock 속성 채움률 + 🔍 ChainProfile 미생성 종목
- **분류**: app-scoped(chainsight)
- **목적지**: `apps/chainsight/` Claude Project
- **한 줄 문제**: `business_model_type=0.0%` · `overall_grade=0.0%` · `theme_tags=0.0%` 3개 속성이 전 종목 미채움 + ChainProfile 자체 미생성 종목 31개. 같은 뿌리(`calculate_all_profiles` 미실행 또는 신규 필드 backfill 누락) 의심.
- **영향 범위(추정)**: `apps/chainsight/models.py` (CompanyChainProfile 필드) / `apps/chainsight/services/profile_calculator.py` (혹은 유사) / `apps/chainsight/tasks/*.py` Beat 트리거. 목적지에서 실측 확정.
- **심각도 / baseline**: HIGH (대시보드 자본 DNA·성장단계 카드 절반 표시 불가) / 🆕신규
- **제안 방향(가설, 확정 아님)**:
  1. 3개 필드가 최근 마이그레이션으로 추가됐는데 backfill 명령이 한 번도 안 돌았다 → 일회성 `manage.py` 커맨드로 전건 채우기.
  2. `calculate_all_profiles` Beat가 DB `PeriodicTask`에 등록 안 됐거나 disable 상태(2026-04-24 사례 패턴) → DB 등록 확인 + 활성화.
- **STEP 0로 확인할 것**:
  - 3개 필드의 마이그레이션 추가 시점 (`git log --all -- apps/chainsight/migrations/`).
  - `PeriodicTask.objects.filter(name__icontains='chainsight')` 활성 여부.
  - `CompanyChainProfile.objects.values_list('symbol', flat=True)` 카운트 vs `Stock.objects.count()` (31 차이 확인).
  - 3개 필드 채움 로직이 `calculate_all_profiles` 안에 정말 있는지(없으면 함수 자체가 신규 필드 미인지).
- **행위보존 제약**: 기존 채움된 다른 속성(`sector` 97.2%, `growth_stage` 93.3% 등) 손상 금지. backfill은 신규 필드 + 미생성 31개 한정.
- **비고**: NT-5(고립 Stock 5개)와 같은 회차에 묶어 단일 Beat 점검으로 동시 해소될 가능성 있음.

---

## NT-4 — SUPPLIES_TO 부족 + UnmatchedCompanyQueue 1011건

- **출처**: 보고서 / 🧬 관계 균형 + 🔍 Unmatched 회사 상위
- **분류**: app-scoped(sec_pipeline)
- **목적지**: `apps/sec_pipeline/` Claude Project
- **한 줄 문제**: SUPPLIES_TO 관계 61개(PEER_OF 8674 대비 0.7%). UnmatchedCompanyQueue **1011건** pending. 상위 빈도: **Flex Ltd. ×4, Compuware Technology ×4, Adyen ×3, exporters ×3, MCOs ×3, third party ×3, JERA ×3, DGD ×3, TD Synnex ×3, Mitsui ×3**. 일부는 ticker 미상장 글로벌 기업(JERA·Mitsui·Adyen), 일부는 일반 명사(`exporters`·`MCOs`·`third party`)로 alias 불가.
- **영향 범위(추정)**: `apps/sec_pipeline/services/company_matcher.py` (혹은 유사) / `apps/sec_pipeline/models.py` UnmatchedCompanyQueue / alias 룰 테이블. 목적지에서 실측 확정.
- **심각도 / baseline**: HIGH (공급망 그래프 핵심 데이터 부족 — Chain Sight 가치 제안 직격) / 🆕신규
- **제안 방향(가설, 확정 아님)**:
  1. **수동 alias 룰 우선**: 상위 빈도 중 매핑 가능한 글로벌 기업(`Flex Ltd.` → `FLEX`, `TD Synnex` → `SNX`, `Adyen` → `ADYEY` ADR, `Mitsui` → `MITSY` ADR, `JERA` → 비상장 → skip) 룰 추가 → 즉시 회수 ~15건.
  2. **일반 명사 필터**: `exporters` · `MCOs` · `third party` · `Compuware Technology, Inc.`(이미 BMC 흡수) 등은 매칭 시도 자체에서 제외하는 stopword 리스트 추가 → 큐 1011→ N건으로 축소.
  3. **fuzzy threshold 재조정**: 상위 fuzzy 후보가 0.55~0.75 폭으로 noise — 임계를 0.85 이상으로 올리고 그 이하는 수동 검토 큐로.
- **STEP 0로 확인할 것**:
  - UnmatchedCompanyQueue 모델 필드(`occurrence_count`, `top_fuzzy_match`, `top_fuzzy_score` 존재 여부).
  - alias 룰 저장 위치(DB? settings? yaml?).
  - 현재 fuzzy threshold 값 + 매칭 함수 시그니처.
  - SEC 10-K backfill 진행도(이미 완료 사이클인지, 신규 filing 처리 중인지).
- **행위보존 제약**: 기존 SUPPLIES_TO 61개 관계 손상 금지. alias 룰 추가는 신규 매핑만 생성하고 기존 관계는 read-only.
- **비고**: NT-2(LLM 분석률) 회복 후 뉴스 기반 공급망 추출 보강 트랙(`packages/shared/`?)도 함께 검토 가능 — 단, **별도 이슈로 분리**.

---

## NT-5 — 고립 Stock 5종목 (관계 0)

- **출처**: 보고서 / 🧬 노드 퀄리티 → 외로운 Stock 노드
- **분류**: app-scoped(chainsight 또는 graph_analysis)
- **목적지**: `apps/chainsight/` Claude Project (price co-movement는 chainsight 영역 — graph_analysis는 미구현 상태)
- **한 줄 문제**: 538개 Stock 중 5개가 관계 0 (PEER_OF · PRICE_CORRELATED · BELONGS_TO_SECTOR 전부 미생성).
- **영향 범위(추정)**: `apps/chainsight/services/price_co_movement.py` (혹은 유사) / `BELONGS_TO_SECTOR` 생성 로직. 목적지에서 실측 확정.
- **심각도 / baseline**: MID (5개 한정 — Chain Sight UI에서 해당 종목 클릭 시 빈 그래프) / 🆕신규
- **제안 방향(가설, 확정 아님)**:
  1. 5개 종목 식별 → 가격 데이터(DailyPrice) 존재 여부 확인 → 없으면 **데이터 누락 원인** 트랙.
  2. 가격 데이터는 있는데 PEER 미생성이면 → `calculate_price_co_movement` Beat 점검 (NT-3과 같은 뿌리 가능).
  3. sector/industry 미할당이면 → Stock.sector 채움률 97.2% 미달의 잔여 2.8%에 해당 → `BELONGS_TO_SECTOR` 자동 생성 룰 점검.
- **STEP 0로 확인할 것**:
  - 5개 종목 심볼:
    ```bash
    poetry run python manage.py shell -c "
    # Neo4j 쿼리로 isolated stock 5개 추출 — 실측 후 본 문서에 박음
    "
    ```
  - 각 심볼의 DailyPrice 건수 + sector/industry 필드 값.
  - `calculate_price_co_movement` 최근 실행 시각.
- **행위보존 제약**: 5개 외 종목 관계 손상 금지.
- **비고**: NT-3과 묶어 chainsight Beat 점검 1회로 동시 해소 가능성 → 목적지에서 우선순위 판단.

---

## NT-6 — 뉴스 커버 9.5% (보류 후보)

- **출처**: 보고서 / 📰 섹터 커버리지 → 종목 커버 51 / 미커버 484
- **분류**: app-scoped(news)
- **목적지**: `apps/news/` Claude Project
- **한 줄 문제**: 24h 신규 뉴스 315건이 535종목 중 51종목만 커버 (**9.5%**). 484종목은 24h 내 관련 뉴스 0건 → 뉴스 기반 시그널·이벤트 추출이 절반 이하 종목에만 적용.
- **영향 범위(추정)**: `apps/news/services/collectors/*.py` (Finnhub / MarketAux / 기타) / `apps/news/tasks/collect_*.py` Beat 수집 큐. 목적지에서 실측 확정.
- **심각도 / baseline**: MID (장기 트랙 — 즉시 운영 영향은 작음) / 🆕신규
- **제안 방향(가설, 확정 아님)**:
  1. **종목별 수집 확장** (Finnhub 종목 단위 호출 추가) — rate limit 한계 확인 필수.
  2. **Sector 단위 broadcast** (sector 뉴스를 해당 sector 모든 Stock에 연결) — 시그널 노이즈 증가 위험.
  3. **하이브리드** (대형주는 종목 단위 / 중소형주는 sector broadcast).
- **STEP 0로 확인할 것**:
  - 현재 수집 카테고리(sector/sub_sector/custom) 활성 분포.
  - Finnhub / MarketAux 일일 호출 카운트 vs 한도.
  - 커버 51종목의 분포(시총 / 섹터 편향 여부).
- **행위보존 제약**: 기존 수집 카테고리 비활성화 금지(현재 51종목 커버 회귀 위험).
- **비고**: **사용자 권장 = 보류 트랙**. NT-2(LLM 분석률) 회복이 먼저 — 수집을 늘려도 분석이 안 따라가면 의미 없음. NT-2 해소 후 재평가.

---

## 핸드오프 절차 (운영자 → 각 앱 Claude Project)

1. 본 파일에서 해당 NT-x 섹션을 복사.
2. 목적지 앱 Claude Project 새 세션 시작 → 섹션 붙여넣기 → "이 스텁으로 STEP 0부터 시작" 지시.
3. 목적지가 STEP 0 결과 + 구체화된 지시서로 회신 → ops가 TASKQUEUE.md NT-x 상태 `라우팅됨` → `진행` 갱신.
4. 완료 시 처리 커밋 해시를 TASKQUEUE.md에 기록.

## 보류·기각 사유 작성 위치

각 NT-x가 보류·기각되면 사유는 **DECISIONS.md**에 신규 항목으로 기록 (TASKQUEUE.md 표는 결정 링크만 박음, DECISIONS.md 2026-06-03 결정 준수).
