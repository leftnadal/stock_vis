# SEC β G1 — grounding 백필 dry-run 분포 리포트 (v1 기준선)

- 작성: 2026-07-28 (Gate 1, flag-off)
- 실측: `scripts/sec/grounding_dryrun_report.py` (read-only, 공유 DB 스키마 무변경, 쓰기 0건)
- 계약: V-A 결정론 매칭, **LLM 0콜**. 판정 4종(개정문1).

## 분포 (실 evidence 1,751건, prompt_version=v1)

| 판정 | 건수 | 비율 |
|------|------|------|
| verified (원문 그대로 substring) | 1,273 | 72.7% |
| normalized_match (정규화 후 일치) | 41 | 2.3% |
| not_found (소스 있으나 부재) | 437 | 25.0% |
| missing_source (원문 소스 부재) | **0** | 0.0% |
| **합계** | **1,751** | 100% |

- **not_found 비율(순수) = 437 / (1273 + 41 + 437) = 24.96%** (missing_source 제외).
- **verified+normalized (접지 성공) = 1,314 / 1,751 = 75.04%.**

## 임계 판정 (개정문2, dry-run 전 고정)

- **not_found(순수) 24.96% > 15% 임계 → ⚠ V-B 부분 도입 재판정 회부** (진행 차단 아님, 감독 재판정 사안). 아래 §샘플 20건 첨부.
- **missing_source = 0 → 목록 보고 불요** (개정① G1 STEP 0 커버리지 대조 예측대로: evidence 1,751 전건이 비어있지 않은 원문 store 참조, source_row_missing 0·evidence_on_empty_store 0).

## not_found 샘플 20건 (회부 첨부)

| evidence_id | 인용 앞부분 |
|---|---|
| 60 | We also notify the Irish Data Protection Commission (IDPC), our lead European Union privacy regulator… |
| 62 | Built on a cloud-based architecture, our Acceptance Platform solutions such as Cybersource and Authorize.net… |
| 63 | (62 중복 — 동일 문장 다관계 추출) |
| 65 | In fiscal 2024, we acquired SRS, a leading residential specialty trade distribution company… |
| 130–135 | These products are generally marketed and sold directly to blood banks, hospitals, commercial laboratories… (6중복) |
| 47 | The BRRD establishes a framework for the recovery and resolution of financial institutions in the E.U., such as GSBE. |
| 141 | Abbott's laboratory facilities, home monitoring services, and durable medical equipment suppliers… |
| 144 | Depreciation and amortization increased in fiscal 2025 due to the WorkForce Software acquisition… |
| 175 | In June 2020, the San Francisco District Attorney filed an action in the Superior Court of California… |
| 142 | For example, third-party intellectual property disputes, including those initiated by patent assertion entities… |
| 156 | For example, our acquisition of Horizon resulted in the addition of more than 30 contract manufacturing organizations… |
| 157 | As we continue our expansion efforts in emerging markets around the world, through acquisitions and licensing… |
| 200 | failing to keep our information technology systems and our customers' sensitive information secure… |
| 149 | The Invisalign System competes primarily against traditional wires and brackets… |
| 155 | In 2024, Change Healthcare, a large U.S. insurance claim and co-pay card processing clearinghouse… |

## 해석 노트 (회부 판단 재료 — 단정 아님)

- not_found 관찰 패턴: ⑴ **동일 문장 다중 추출**(62/63, 130~135)이 각각 카운트 → 고유 문장 기준이면 실 비율은 다를 수 있음(중복 제거 분석은 V-B 회부 후속). ⑵ 일부는 **item 1/1a/7 밖 섹션**(예: 175 법적절차=item 3 미저장) 출처 가능성 → 소스 커버리지 한계(진짜 접지 실패와 구분 필요, 그러나 store엔 1/1a/7만 존재). ⑶ 나머지는 **LLM self-report의 비-verbatim**(paraphrase/절단) = grounding이 잡으려던 바로 그 대상.
- 이 해석은 **V-B(native-citation 2콜) vs prompt v2(verbatim 보강) vs 현행 유지** 재판정의 입력이며, 본 리포트는 분포·샘플 제시까지다(결정 아님).

## Gate 1 체크 결과

- [x] 매처 단위 테스트 (verified/normalized_match/not_found/missing_source + 유니코드 대시·스마트따옴표·말줄임·공백 엣지) — 10 GREEN
- [x] 백필 dry-run/write + skip-already-grounded — 3 GREEN
- [x] 마이그 0002 additive (3 AddField·null·`--check` clean·AddField는 행수 불변)
- [x] flag-off 파이프라인 무영향 (sec 회귀 25 passed, SEC_GROUNDING_ENABLED 플래그 미도입=G2)
- [x] dry-run 분포 산출 (쓰기 0건)
- [x] V-A 결정론, LLM 0콜

## 정지점 (게이트별 사인오프)

**Gate 1에서 정지.** Gate 2(백필 실기록·flag-on 1 filing·prompt v2)는 **본 분포 감독 비준 + not_found 24.96% V-B 재판정 후**에만 착수. 사인오프 없이 Gate 2 진입 금지(개정문1).
