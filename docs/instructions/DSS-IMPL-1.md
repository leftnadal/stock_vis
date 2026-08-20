# 지시서 DSS-IMPL-1 — DSS(재무 지지 점수) 구현

- 발행: 감독 세션, 2026-08-16
- 트랙: TH-DSS-IMPL / 세션 종류: 구현(쓰기) / worktree `~/worktrees/sv-dss-impl1` · 브랜치 `monorepo/sess-dss-impl1`(origin/main `94a5c260` 기점)
- 선행: DSS-RECON-1 정찰(2026-08-13, `7b4775d2`) — 커버리지·C8 재사용 표면·함정 A~C 실측.

## DB 쓰기 허용 범위 (이 3가지 외 read-only)
- (a) 신규 테이블 1개 생성 마이그레이션(additive만) (b) 신규 테이블 INSERT (c) ThemeDemandScore INSERT.
- 기존 행 UPDATE/DELETE 절대 금지. FMP 0회. git: add 명시·force 금지·자가 rebase 금지·push=D-PUSH-DELEG.

## STEP 0 실측 결과 (2026-08-16 09:35 KST, base 94a5c260)
- health 15/0/0. 6회차(07-17·24·29·31, 08-07, 08-14 발화)·WoW 7일 쌍 4. HONA no_data 해소(08-14 유입).
- **A-매칭 성립**: 인접 4쌍 차기FY(2027) 조인 가능 **99.8% ≥ 95%** → 동일-FY 조인 진행(강등 미발동).
- ThemeDemandScore(행0) `components`(jsonb)로 breadth 분모 수용(기존 테이블 무변경). SymbolDemandSignal 모델명 무충돌. dry-run "No changes detected". C8 66 pass·전종목 all-none(cold-start)·SHA256 `f1245b5e6891c9dec7cc5c23c4c49248922b184e79bd86a9b81043cb6c7ce160`(회귀 앵커).

## Slice 1 — lag 파라미터화 (코드만)
- `eps_diff_at`에 `lag_days` 파라미터 추가, 기본값 = 기존 상수(56/63 로직 보존). 호출부 무변경. **회귀: 0-7 SHA256·66테스트 IDENTICAL**(불일치 HALT). **기본값 경로 단위 테스트 1건 추가**(인자 생략 ≡ 상수 명시). 보고에 504종목(유니버스 503 대비 +1) 출처 1줄.

## Slice 2 — SymbolDemandSignal + 마이그레이션
- 필드: symbol, anchor_date, fiscal_year, eps_prev, eps_curr, direction(smallint), num_analysts_prev, num_analysts_curr, excluded(bool), exclude_reason. unique(symbol, anchor_date). index(anchor_date). migrate 적용(쓰기 (a)).

## Slice 3 — 계산 + 적재
- 종목 방향 순수 함수: 동일-FY 조인(이번 주 차기 FY=anchor.year+1, 지난주 동일 FY 탐색) → 부재 excluded=fy_mismatch. |Δnum_analysts|≥2 → analyst_delta. 지난주 부재 → missing_prev. 나머지 direction=sign(Δeps).
- 섹터 breadth = (상향−하향)/유효분모(excluded=false 수). ThemeDemandScore 적재(쓰기 (c)), 분모 동반(components).

## Slice 4 — 백필 + 검산 + Δ분포
- 가용 전 인접 쌍(실측 4) 일괄. date-scoped invariant 검산(상향+하향+불변+제외 = 시도 수 / breadth∈[−1,+1] / 유효분모>0 / HONA 행 부재). Δ분포 분위수(p50/75/90/99)·0비율 → `docs/features/theme-heat/dss_impl_report.md`.

## 결정 (DECISIONS 5건 = 커밋 1)
- D-DSS-AGG=1-B(breadth (up−down)/valid_denom) · D-DSS-SIGNAL=2-A(direction=sign Δeps) · D-DSS-LAGPARAM=3-A(eps_diff_at lag_days 파라미터·기본 보존) · D-DSS-FY-MATCH(동일 차기FY 조인·미스매치 제외) · D-DSS-ANALYST-FILTER(|Δnum_analysts|≥2 제외).

## HALT 트리거
health FAIL / dry-run 잉여 변경 / 모델명 충돌 / C8 회귀 불일치 / 빈 스키마 불일치 / FMP 필요 / 예상 밖. (0-3 미달만 승인된 강등 예외 — 본 세션 미발동.)
