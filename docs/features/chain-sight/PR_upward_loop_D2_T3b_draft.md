# PR 초안: D2 T-3b — upward 선별 결함 수정 (적용 금지, 주말 일괄 회부용)

- 상태: **초안(DRAFT). 적용 금지.** 2026-07-11(토)~일 관찰 완료 후 일괄 회부에서 적용 판정.
- 근거: D2-a 관찰(07-08 evaluated=270 / 07-09 evaluated=0)이 드러낸 선별 결함 포렌식(2026-07-09).
- flag·§6 동결 무변경 유지. 본 문서는 해석·설계 초안일 뿐 코드 아님.

---

## §1. 원인 판정문 (채택)

evaluated=0(07-09)은 "무 재확인"이 아니라 **선별 결함의 산물**. 포렌식 3중 결함:

- **ⓐ 타이밍**: 재확인 액터 = `sec-seed-relations-to-chainsight`(`0 12 * * * America/New_York` = 12:00 ET = **01:00 KST**, enabled). 270 text pair의 last_observed_at 전부 **16:01 UTC = 01:01 KST 단일 클러스터**. 이 seed가 upward 틱(00:31 KST)보다 **~30분 늦게** 돌아 → upward 실행시 last_observed_at은 항상 전일 seed분(하루 stale).
- **ⓑ auto_now 자가오염**: upward `pair.save()`(update_fields 없음, `relation_tasks.py:519`)가 `last_observed_at`(RC 유일 auto_now)을 실행시각으로 이동 → 재확인 신호 파괴. (aggregate/pair_aggregation은 RC를 `values_list` 읽기만·save 안 함 = 액터 아님 확정.)
- **ⓒ tz 불일치**: `TIME_ZONE=Asia/Seoul`·USE_TZ=True → `__date` 필터는 **Seoul 일자**. 그러나 `period=timezone.now().date()`는 **UTC 일자**(now()=UTC). 날짜 비교 어긋남.

순효과 = evaluated 270/0 진동. **"1일 지연" 가설** — 07-10 틱에서 ~270 재등장으로 검증 예정.

## §2. decay 추가 포렌식 (2026-07-09, 해석용)

- decay(`check_stale_and_decay`) = `queryset.update()` **3건**, `.save()` **0건** → **auto_now 우회 → last_observed_at 불변** → decay는 선별 신호 미오염(경보 시나리오 "decay 오염→날짜 선별→재승급"은 이 경로 미발생).
- 추가: decay 임계 = 90/60/30**일**. 270 SEC 재시드 pair는 매일 신선 → **decay 대상 미도달** → 30 승급분 하향 가능성 낮음(07-11 실측 확인). 단 whipsaw 진짜 벡터 = "decay(임계도달) → SEC 재시드 → 재승급"이나, 재시드가 last_observed 갱신을 유지하는 한 decay 임계 자체에 안 걸림.

## §3. 수정 초안 (개정 3건 반영)

### ① 선별 교체 + ⓐ 콜드스타트 백필
`last_observed_at__date=period`(tz·타이밍·자가오염 취약) 폐기 → **"마지막 처리 이후 재관측"** 신호:
```python
from django.db.models import F, Q
qs = (RelationConfidence.objects.exclude(relation_category="market")
      .filter(Q(last_computed_at__isnull=True) | Q(last_observed_at__gt=F("last_computed_at"))))
```
tz/일자/타이밍 무관. 멱등 자동(처리 후 last_computed_at>last_observed → 다음 seed 전까지 재선별 안 됨).

- **ⓐ 콜드스타트 보완(개정)**: `isnull=True` 분기는 기존 pair 전수(~9k)를 첫 틱에 쓸어버림. **마이그레이션에서 기존 pair의 `last_computed_at`를 `last_observed_at` 값으로 백필** → `isnull`을 **진짜 신규 pair 전용**으로 만든다. 백필 후 첫 틱은 "당일 재관측분(seed로 last_observed>last_computed된 것)"만 평가.
  - 마이그레이션: `RelationConfidence.objects.filter(last_computed_at__isnull=True).update(last_computed_at=F("last_observed_at"))` (data migration, market 포함 무해 — market은 선별서 exclude).
  - 테스트 추가: "백필 후 첫 틱 evaluated = 당일 재관측분만"(전수 아님).

### ② upward save update_fields + ⓑ 전 지점 감사(개정)
```python
pair.save(update_fields=["relation_status","evidence_streak","last_upgraded_at",
                         "fastpath_triggered_at","last_computed_at","neo4j_dirty"])
```
`last_observed_at` 제외 → Django auto_now 미적용 → 재확인 신호 보존(①의 F() 성립 조건).

- **ⓑ 범위 일반화(개정)** — RC를 save/write하는 전 지점 감사:
  | 지점 | 현재 | 조치 |
  |---|---|---|
  | upward `pair.save()` | update_fields 없음 → last_observed 오염 | **update_fields 적용**(위) |
  | decay `.update()` | auto_now 우회(오염 없음) | **현행 유지**(안전) |
  | SEC seed(`sec_pipeline/tasks.py`) | last_observed 갱신 = **정당 재확인 액터** | **현행 유지 명시**(오염 아님 — 이게 신호원) |
  | update_relation_confidence | market만 update_or_create | 선별서 market exclude → 무관 |

### ③ period 인자
선별서 제거(로그 전용). 로깅은 `timezone.localdate()`(Seoul)로 정합. 멱등 date-guard(`exclude(last_computed_at__date=period)`) 삭제 — ①이 대체.

### ④ 잔여 1일 지연 처리 — 선택지 구도(개정, 회부 시 택1)
①②만으로 지연은 "일관된 1일"이라 관찰은 유효하나, 지연 자체 소거 옵션:
- **④-i upward 분리(⑨-C 해체)**: upward를 aggregate 인라인에서 떼어 SEC seed(01:00) *뒤* 별도 트리거로. ⑨-C 결정 되돌림 — 이중경로 재발 위험(드리프트 #7 교훈), DB beat 관리 필요.
- **④-ii seed 전진(SEC 스케줄 변경)**: `sec-seed-relations-to-chainsight`를 upward 틱 *앞*(예: 11:00 ET 전)으로. SEC 파이프라인 스케줄 변경 = 타 도메인 영향, 하류 sync 순서 재검토 필요.
- **④-iii 현상 유지(1일 지연 수용)**: ①②로 신호는 정확, 반영이 1틱 늦을 뿐. 최소 변경·부작용 0. 관찰·학습 목적엔 1일 지연 무해.
- 초안 권고: **④-iii**(최소 변경) 기본, ④-i/ii는 지연이 실사용 문제로 관측될 때.

## §4. 회부 흐름 (판정대로)
- 07-10 틱: evaluated로 "1일 지연(~270 재등장) vs 진동" 확정.
- 07-11(토) decay 후: 30 승급쌍 하향 수 실측(9쌍=30% 브레이크 동일 기준).
- 일요일 틱까지 채집 → **주말 일괄 회부**: 창 판정 + T-3b(①②③) 적용 + ④ 선택지 결정.
