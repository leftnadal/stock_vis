# 지시서: SEC β G1.5 — not_found 437 분해 세션 (재판정 준비)

- 발행: 감독 세션, 2026-07-28
- 선행: G1 Gate 1 비준(dry-run 기준선 not_found 24.96% > 15%). 커버 `sec_beta_kickoff_cover_directive.md`·개정문1·실체 `PR_sec_beta_grounding.md`.
- 성격: 분해·재판정 준비. **전부 결정론, LLM 0콜, dry-run 레벨 무쓰기.** Gate 2 정지 유지.

## STEP 0 — evidence 섹션 메타데이터 실측 (읽기 전용)

evidence 테이블에 인용의 출처 섹션(item) 메타데이터가 있는지 실측.
- 있으면 → 437 × 섹션 교차표가 분해의 등뼈.
- 없으면 → "귀속 불가"를 별도 버킷으로. **추측 귀속 금지.**

## 분해 (전부 결정론, LLM 0콜, dry-run 무쓰기)

- **① 중복 접기**: 437건을 정규화 문장 키로 클러스터 → 유니크 문장 수·클러스터 크기 분포 보고. 전체 1,751에도 동일 접기를 적용한 유니크 기준 분모 병기.
- **② 섹션 귀속**: 각 not_found의 출처가 store 보유 섹션(1/1a/7) 밖인지 판정 → 해당분은 `missing_source_section`으로 재분류(판정 체계 **5종** 확장: verified / normalized_match / not_found / missing_source_doc / missing_source_section). 마이그 0002 상태 필드가 이 값을 수용하는지 확인, 필요시 additive 수정.
- **③ 잔여 규명 샘플**: 재분류 후 잔여 not_found에서 20건 층화 샘플 → 원문 대조 육안 리포트(비-verbatim 패턴 분류: 축약/재서술/합성 등).

## 재판정

- 잔여 순수 not_found율(유니크 기준·명목 기준 병기) 산출 →
  - ≤15%면 V-B 불요 확정, **Gate 2 사인오프 요청으로 직행**.
  - >15%면 V-B 부분도입 결정 사이클 회부(그때 V-B 범위 = 잔여 클러스터만).

## 부수 확인 2건

- ⑴ 빈 store 61건 — 미참조라 무해하나, 왜 비었는지 1행 규명(수집 실패 vs 원래 빈 섹션).
- ⑵ prompt v2 설계 입력 — ③의 비-verbatim 패턴 분류를 v2의 "verbatim 강제" 문구 설계 근거로 리포트에 명기.

## 불변

- 쓰기 0(분해는 전부 리포트·dry-run) · 결정론 위반 신호 시 HALT · 보고 양식 기존 준수.
