# 지시서 DSS-RECON-1 — TH-DSS-IMPL 설계 정찰 (EstimateSnapshot 실태 + 함정 A~D)

- 발행: 감독 세션, 2026-08-13
- 성격: 혼합 — Part A(read-only 정찰 7종) + Part B(정찰 보고서·지시서 커밋)
- 목적: TH-DSS-IMPL(수요 축 DSS) 설계 사이클 입력 — 커버리지·C8 재사용 표면·함정 A~C 측정.

## 세션 계약

- 쓰기 범위: `docs/features/theme-heat/` 정찰 보고서 1건(신규) / `scripts/` 정찰 스크립트 1건(신규, 결정론·DB 읽기 전용) / 지시서 파일. 그 외·코드·스키마·설정·테스트 수정 금지.
- DB: 전 구간 read-only(SELECT만). 외부 API: FMP 실호출은 ⑦ 확인용 최대 3회. HALT-0 기본. behind>0 조우 시 D-PUSH-DELEG 무조건 HALT.

## 격리 (사전 승인)

- 브랜치 `monorepo/sess-dss-recon1` + 격리 worktree(실측 origin/main 분기). 원격 세션 브랜치 생성 금지 — push는 HEAD:main 직행. 사후 정리 = D-BRANCH-DELETE-MANUAL(TASKQUEUE 등재만).

## STEP 0

- 0-1 base 실측 / 0-2 health(환경·동기화 WARN=보고 후 진행, 시스템 검사 신규 WARN/FAIL=명목 HALT) / 0-3 채번 자격(정찰=없음) / 0-4 EstimateSnapshot 회차 전수(6회차 08-14 발화 여부 실측 시점 명기) / 0-5 TH-DSS 항목 확인.

## Part A — 정찰 실측 7종 (판정 없이 사실만)

- ① DSS 사전 흔적 전수(grep). ② 커버리지(회차별·종목·섹터·BRK.B/BF.B). ③ C8 재사용 표면(estimate_revision.py 함수·lag 하드코딩·ThemeHeatScore 스키마). ④ WoW 매칭(7일 쌍·고아 07-29·검산). ⑤ 함정 A 회계기간 롤오버(fiscal 필드·수집 파싱·|diff| 상위 20·전환 건수). ⑥ 함정 B 컨센서스 구성(analyst count 필드·변동 분포). ⑦ 함정 C 발표 일정(earnings calendar grep·FMP client·실호출 최대 3회 200/403). ※ 함정 D(크기 정규화)=설계 선택, 실측 불요(⑤ |diff| 분포가 D 입력 겸함).

## Part B — 산출물 커밋

- [커밋 1] 지시서 등재 `docs/instructions/DSS-RECON-1.md`.
- [커밋 2] 정찰 산출물: `scripts/theme_heat/dss_recon_survey.py`(②④⑤⑥ 결정론) + `docs/features/theme-heat/dss_recon_report.md`(①~⑦, 판정 없음·각 항목 실측 시점·데이터 기준일 명기). git add 명시 지정(-A 금지).

## 금지 사항

- 설계 확정·구현 착수 금지(측정만). 스키마 변경·마이그레이션 금지(필드 부재도 보강은 후속). DB 쓰기 금지·FMP ⑦ 한정 최대 3회. push=D-PUSH-DELEG("push" 명시 대기, behind>0 HALT, HEAD:main 직행·원격 세션 브랜치 미생성). 브랜치·worktree 삭제 금지·machine clock(#89).

## 집행 결과 요지 (2026-08-13 CC 집행)

- STEP 0: base=origin/main `afc8246b`. health 15/0/0(WARN 0). 회차 **5회 확정**(07-17/24/29/31/08-07), **6회차 08-14 미발화**.
- Part A: ② 99.2%+/코어499/섹터 10·11 100%/BRK.B·BF.B 08-07만. ③ lag 56/63 하드코딩(WoW 리팩터 필요)·`ThemeDemandScore` 테이블 기존재. ④ 7일 3쌍·고아 07-29. ⑤ fiscal_year(연도)만 저장·월/일 폐기·전환 0건(잠재)·의심 13. ⑥ num_analysts 존재·변동 ≈29%. ⑦ earnings-calendar 미배선·FMP 200 접근 가능(2회 호출). 보고 `docs/features/theme-heat/dss_recon_report.md`.
