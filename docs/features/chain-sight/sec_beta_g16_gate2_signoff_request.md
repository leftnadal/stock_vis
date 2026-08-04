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

---

## 부록 (2026-08-01 CC 회신 대응 — 감독 심사 포인트 P1⑶·P3 + 사실 정정)

### 부록 C — 마이그 상태 정정 (§1 갱신)
- **실측(2026-08-01, read-only)**: stock_vis `django_migrations` sec_pipeline = `0001`·**`0002` 적용 완료**(G1 이후 어느 세션이 적용). 즉 grounding 3필드는 **prod에 이미 존재**.
- 따라서 §1 "0002 미적용분"은 **정정**: 잔여 = **`0003`만**(grounding_status choice에 partial_match 추가, AlterField·**스키마 중립** = 컬럼 불변, Django 상태 전용). 0003은 `sess-secb-g16` 전용(미착지).
- 함의: 백필(item 2)은 이미 존재하는 grounding_status 컬럼에 기록. 0003 미적용이어도 choices는 DB 미강제라 partial_match 저장 가능하나, **정합상 0003 랜딩 후 적용 권장**.

### 부록 A — 실패 시 부분 상태 정의 (P1⑶)
| 게이트 | 부분 실패 상태 | 복구/재개 |
|--------|----------------|-----------|
| G-b 마이그(0003) | migrate는 트랜잭션·0003=스키마중립 → 부분상태 없음(전/후 이분). 실패=적용 전(자동 롤백) | 재시도 안전 |
| G-c 백필 | `select_for_update`+`bulk_update` 배치 원자 + **skip-already-grounded** → 중단 시 `grounding_status IS NOT NULL` 행 수 = 진행률(N/1751), 부분 기록 유효 | 재실행이 **미기록분만 이어감(멱등 재개)**. 완전 롤백=아래 |
| G-d flag-on 1 filing | 1 filing scope, 부분 실패=노출 0 유지 | `SEC_GROUNDING_ENABLED=False` 즉시 |
| G-e prompt v2 | 1 배치 재추출 부분 실패=v1/v2 혼재 | `prompt_version` 태그로 v2분 식별·격리 재처리 |
- **부분 상태 판정 쿼리**: `SELECT count(*) FILTER (WHERE grounding_status IS NOT NULL), count(*) FROM sec_supply_chain_evidence;`

### 부록 A′ — 백필 롤백 삭제 기준 정밀화 (P1⑴)
- 전역 `SET NULL`이 아닌 **표적 삭제**: 이번 배치 기록분만 = `UPDATE sec_supply_chain_evidence SET grounding_status=NULL, grounding_method=NULL WHERE grounding_method='deterministic_v1'`(백필이 부여하는 method 마커 기준). read-path 무의존이라 즉시 무해화. 대안=G-a 덤프 복원(전량).

### 부록 B — 랜딩 순서 (P3, 제안 — 랜딩 자체 착수 금지)
- **원 요청서에 랜딩 시점 명문 부재** → 본 부록으로 명문화.
- **랜딩은 Gate 2 실행의 前(전) 전제**(일부 아님): Gate 2의 migrate 0003·백필 로직·`STATUS_PARTIAL_MATCH`/models choice가 `sess-secb-g16`에 있음 → runtime 트리에 코드가 있어야 `migrate`/backfill 가능.
- **제안 순서**: ① `sess-secb-g16`(4커밋) → origin/main **no-ff 랜딩**(감독 승인) → ② `worker_sync`(sv-worker-runtime 동기화) → ③ Gate 2 G-a~G-e.
- dry-run 산출물(스크립트·리포트·요청서·원장)은 이미 커밋/푸시 — 랜딩 목적 = **Gate 2 실행 코드를 runtime에 올림**. 랜딩 실행은 **감독 비준 후 별도**(본 세션 착수 금지).
