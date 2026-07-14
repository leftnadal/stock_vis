# SLICE 19B 지시서 — FX·KRW 기준 통합 (토대 슬라이스, 좁게)

> **세션 종류:** 실행. 로드맵(19b=FX·KRW 좁게 → 19c=가중치+다이얼+FX매크로 → 20=화면) 디렉터 4.70/3.70/2.90(마진 1.00) + 사용자 확정(2026-07-14). 게이트 1 HALT는 `SLICE19B_GATE1_RESOLUTION.md`로 해소.
>
> **numéraire = KRW** (`OBJECTIVE_KRW_NUMERAIRE.md`). base `7b7927e`→ 재측정.

## 0. DoD
1. FX 데이터 모델 신설(`packages/shared`): USD/KRW spot + 과거 일간 시계열. 수집=shared FMP 래퍼 경유. dev 마이그레이션(prod 미적용).
2. 백필: FMP 가용 범위(실측 5년) idempotent 커맨드.
3. 19a 갭 KRW 교정(의도된 의미 변경): 진행/배치 갭·매수여력 = KRW 환산. USD→현재환율 KRW 평가, KRW→무환산. 테스트 갱신 커버.
4. FX 맥락 factor: 현재 USD/KRW 역사적 백분위(사실, 예측 아님) 근거 표시.
5. 예측 금지: 환율 방향·타이밍 베팅 0.
6. 산출 계약 v2: KRW 수치 + FX factor + 취득원가 출처 라벨.
7. 테스트: FX CRUD·수집·백필 idempotency / KRW 환산 / 백분위 / 경계 + 게이트1 우선순위 3분기·휴장일·precedence.
8. 부채 종결: `FX-PERSIST-ABSENT`. 부채 등재: `FX-ACQ-RATE-WEIGHTED-UPDATE`.
9. 회귀: 592 → 의도 갱신 외 깨짐 0, architecture·동결 0, apps→shared 유지.

## 1. 절대 규칙 (HALT)
- 환율 방향 예측 금지. 19c 범위(가중치·다이얼·FX매크로) 침범 금지. 수치 재측정. 한 방향(FX 모델=shared, apps.* import 0, FMP 래퍼 경유). 행위보존+명시예외(§0-3 KRW 교정·게이트1 필드). prod 유보. 결정 재오픈 금지. acquisition_fx_rate 외 마이그레이션 변경 시 HALT.

## 2. STEP 0 (완료, base bb91c98)
- baseline 592 green. 게이트1=불가→해소(우선순위 로직). 게이트2=통과(spot+5년 1373건). 게이트d=중복0. 소비처0(Slice20 미착수). 상세=GATE1_RESOLUTION §STEP0.

## 4. 닫힌 결정 (Part A 기록)
로드맵·KRW numéraire·FX 정직성 4원칙·FX 모델 shared 소속·게이트 판정·의도된 의미변경 선언·19c 이월. + 게이트1 해소(①+수동정정).

## 5. 실행 계획
- A: 결정·방향문서(OBJECTIVE·GATE1_RESOLUTION) 커밋 + DECISIONS + TASKQUEUE. 문서-only.
- B: shared FX 모델(pair,date,close,source, unique(pair,date)) + FMP 래퍼 수집 + 백필 커맨드(idempotent) + spot 조회 경로(영업일 fallback). dev 마이그레이션. 회귀.
- C: KRW 교정 — 평가 환산 계층 + 진행/배치 갭 KRW화 + 게이트1 우선순위 취득원가. 테스트 갱신. 회귀.
- D: FX 백분위 factor + 산출 계약 v2(출처 라벨). 회귀.
- E: 테스트 전수(경계) + FX-PERSIST-ABSENT 종결. 전체 pytest.
- F: 닫기 보고 + health_check + architecture.

## 7. HALT 트리거
게이트 실패 / baseline·종료 red(의도 갱신 제외) / makemigrations 기존 재생성 / shared→apps 역참조 / FMP 직접호출 / 환율 예측 필요 / 19c 범위 / acquisition_fx_rate 외 마이그레이션 변경 / 파괴적 작업.

## 8. 다음
19c(가중치 합=1.00 + 공격성 다이얼 + FX매크로) → Slice 20 화면.
