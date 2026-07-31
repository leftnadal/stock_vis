# SEC β — Gate 2 사인오프 요청서 (감독 비준 대상)

> 발행: 실행 세션 `monorepo/sess-secb-g16` · 2026-07-31
> 성격: **문서 산출물 — 판정 선언 아님.** ≤15% 최종 판정·Gate 2 실행 비준 권한은 **감독 세션**에 있다(base §6·커버 정합 조정). 본 요청서는 base §6 "잔여율 ≤15% 시 요청서 작성·커밋" 조항의 이행이다.

## 근거 (G1.6 dry-run 실측)

- 재분류 후 4분포(명목 1751): verified 1273 / normalized 41 / **partial_match 410** / not_found 27 / missing_source 0.
- **잔여 순수 not_found: 명목 1.54% · 유니크 2.03%** (임계 15% ≤ 충족).
- H4 정합 PASS(pm 유니크 163 + 잔여 nf 19 = 182 = G1.5). V-A 결정론·LLM 0·DB 쓰기 0.
- 상세: `sec_beta_g16_reclassify_report.md`. 스크립트 `scripts/sec/grounding_g16_partial_reclassify.py` (`91b2f643`). 기준 고정 `1c41a7e5`.

## 요청 배치 (한 배치, 감독 비준 후에만 실행)

### 구성 4항
1. **마이그 stock_vis 적용**: `sec_pipeline` 0002(grounding 3필드 additive, 미적용분) + **0003**(grounding_status choice에 partial_match 추가, AlterField·스키마 중립). `migrate sec_pipeline`.
2. **백필 실기록**: `grounding_backfill`(select_for_update + bulk_update, skip-already-grounded)로 1,751행 grounding_status/method 기록. partial_match 부여 로직 = 본 세션 §1 규칙(raw source 접두 ≥70%)을 백필 경로에 이식(결정론·LLM 0 유지).
3. **flag-on 1 filing**: `SEC_GROUNDING_ENABLED`(기본 False) → 대표 1 filing 한정 on, read-path 노출 스모크(회귀 0 확인) 후 판단.
4. **prompt v2 (한 배치)**: 추출 프롬프트 v1→v2(tail 발산 방지 verbatim 규율, TASKQUEUE `SECB-PROMPT-V2`). partial_match 410의 리스트 절단 재발 억제 표적.

### 실행 계획 (순서·게이트)
- G-a 백업: `sec_supply_chain_evidence`·`sec_raw_document_store` 덤프(pg_dump 스코프).
- G-b 마이그: 0002→0003 적용, `showmigrations` 확인.
- G-c 백필 dry-run→실기록: 4분포 재현(1273/41/410/27) 대조 후 write.
- G-d flag-on 1 filing 스모크: read-path 회귀 0.
- G-e prompt v2: 1 배치 재추출 후 grounding 재측정(partial↓·verified↑ 기대).
- 각 게이트 사이 **감독 확인** 지점.

### 롤백 절차
- 백필: grounding_status/method는 additive null 필드 → `UPDATE … SET grounding_status=NULL, grounding_method=NULL`(read-path 무의존이라 즉시 무해화). 또는 G-a 덤프 복원.
- 마이그 0003: choice AlterField는 스키마 중립 → 코드 revert만으로 무효(DB 컬럼 불변). 0002: `migrate sec_pipeline 0001`로 3필드 제거(데이터 없으면 무손실).
- flag: `SEC_GROUNDING_ENABLED=False` 원복(즉시).
- prompt v2: prompt_version 태그로 v1/v2 분리 → v2 배치만 식별·재처리.

## 미결 (감독 판정)

- ≤15% 충족 여부 **최종 판정**.
- 위 4항 배치 **비준/부분 비준/보류**.
- V-B: 현 미발동(잔여 ≤15%), `SECB-V-B-STANDBY` 대기 유지 확인.

**실행 세션은 여기서 정지.** Gate 2 어떤 항목도 착수하지 않음(DB 쓰기 0·flag 불변·prompt 불변 유지).
