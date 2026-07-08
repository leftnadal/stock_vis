# PR 계보: ops verify 강화 — verify_pair_aggregation 관찰 정확도

- 성격: #28 Gate 2 자율 틱 관찰 도구(`scripts/verify_pair_aggregation.py`)의 오탐 수리 계보.
- 트랙: Chain Sight — RelationPairSnapshot 궤적(#28) 관찰 하네스.
- 원칙: 관찰 도구는 관찰 대상(파이프라인)을 바꾸지 않는다. 판정 정확도만 손본다.

---

## E1 — tail-window 오탐 수리 (2026-07-03)

- 승인: 사용자 (option 1 + 제약: 수정은 경계-timestamp 스캔으로 한정 / 로그 폭주는 등재만).
- 커밋: `261b5e3`(1차) → 후속 한정 커밋(redemption 원복).

### 증상
2026-07-03 02:30 KST 자율 verify가 정상 발화한 틱을 **ALERT(오탐)** 판정.
실제 파이프라인은 정상: beat `00:30:00` 발송 → worker `00:30:38 succeeded {'pairs':9562,'updated':9562}`
→ DB period 07-01·07-02 정상 누적.

### 근본 원인
`check_last_tick_succeeded`가 worker 로그 **고정 `[-5000:]`줄**만 읽음. `celery-worker-error.log`가
시간당 ~2,700줄(heartbeat + task received)로 폭주 → 틱 +2h 예약 실행(02:30) 시점엔 성공 로그가
창 밖(파일 끝에서 5,396 > 5,000줄)으로 스크롤아웃. tz 비교 로직(Asia/Seoul)은 정상 — 성공 라인
자체가 읽은 바이트 범위 밖이라 미검출.

### 수리 (경계-timestamp 스캔으로 한정)
- `log_check(boundary)` / `check_last_tick_succeeded(boundary, succeeded)`:
  고정 tail창 폐기 → `grep`으로 `aggregate_relation_pairs` 매칭 라인만 전수 추출 후
  **직전 11:30 ET 경계(`last_et_tick_boundary`) 이후 timestamp만 집계**.
- 로그 폭주와 무관하게 증거 누락 없음. 전수 스캔 부작용(해소된 과거 unregistered 부활)은
  boundary 이전 라인 제외로 봉인(별도 verdict 규칙 없이 경계 게이트만으로 충족).
- **범위 한정 준수**: verdict 의미(unregistered→FAIL 등)는 원본 유지. 스캔 범위 정의만 교체.

### 검증
재실행 **PASS / C(tick) OK / A(log) succeeded=1 unregistered=0 / exit 0** (2026-07-03).

### 교훈 (common-bugs [관찰 도구 함정] 등재)
로그 기반 관찰 도구의 스캔 범위는 "최근 N줄"이 아니라 **"관심 이벤트 시각 경계 이후"**로 정의하라.
고빈도 로그에서 N줄 tail은 시간창이 아니라 이벤트-밀도창이라 시각 기준 판정이 오염된다.

---

## 등재(수리 안 함) — 로그 폭주

- **관찰**: `celery-worker-error.log`가 모든 INFO 로그 + `missed heartbeat from neo4j`(고빈도) +
  15분 주기 regime task 등을 전량 수신 → **126MB, 시간당 ~2,700줄**. 파일 하나에 stdout/stderr가
  뒤섞여 적재.
- **영향**: (a) 로그 grep/스캔 비용 증가 (b) tail-window 방식 도구의 오탐 유발(E1의 근인) —
  E1이 스캔 방식으로 회피했으므로 verify 판정 정확도에는 더 이상 영향 없음.
- **결정**: 이번 세션 범위 밖. **등재만.** 로그 레벨 튜닝(INFO→파일 분리/회전, heartbeat 로그
  억제, logrotate 도입)은 별도 ops 트랙에서 다룬다. verify는 이미 폭주 무관하게 동작하므로 긴급도 낮음.
- **후속 트리거**: 로그 파일이 디스크 압박(수백 MB↑) 또는 다른 tail-window 도구 오탐 재발 시 착수.
