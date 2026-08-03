# 지시서 TH-SESSION-1 — TNV 백필 · stale heat 재산출 · 원장 정정 + SEC β 잔여 정리

**트랙:** TH (기상 실행) + SEC β (사후 정리)
**전제:** TH-RECON-1 정찰 비준 완료. 디렉터 판정 4건 반영 — ① 트리거 문안 정정 승인 ② 백필 범위 = **(A) TNV만 + heat 재산출** (마진 2.25 자동 결정, override 재산출 배제) ③ stale heat 재산출 승인 ④ 단일 커맨드 일괄 승인.
**실행 구조:** CC = 준비·검증(읽기)·문서 커밋. **prod 쓰기 커맨드·main push·브랜치/worktree 삭제 = 병진 수동** (dev=prod 공유 DB · §H).
**worktree:** 신규 생성, 브랜치 `monorepo/sess-th-s1`
**작성일:** 2026-08-03 (디렉터 세션)

---

## §-1. 배달 게이트

1. 이 지시서를 `docs/instructions/TH-SESSION-1.md`로 저장, 단독 커밋. 해시 보고 첫 줄 기록.
2. TH-RECON-1 지시서 커밋(6f8c6c7d, sess-th-recon에 고립)을 본 세션 브랜치로 cherry-pick — 정찰 기록도 main 착지 대상에 포함시킨다 (마감 블록은 하네스가 아니다 — main 착지가 ground truth).

## §I. 불변

- CC의 쓰기 = **문서·하네스 커밋만** (지시서·정정·원장·보고서). 코드 변경 0 · 마이그 0 · **CC의 DB 쓰기 0**.
- LLM 0 · 외부 API 실호출 0 (백필은 순수 DB 집계).
- ThemeTermOverride **215행 ovr_v1 무접촉** — 사전/사후 스냅샷으로 입증 (재적재 금지 조항).
- 브랜치 삭제 `-d`만 · `-D` 금지 · force-push 금지 · `git add -A` 금지.
- 부분 실패·예상 밖 출력 → HALT, 임기응변 금지.

## §0. STEP 0 — 실측 (읽기 전용)

1. `git fetch` → main HEAD·동기 확인. 신규 worktree `monorepo/sess-th-s1`, 셸 위치 원장 대조.
2. 베이스라인 재실측: full suite "N GREEN / M pre-existing" 앵커 (4561/0/53은 이월 금지).
3. **백필 창 재산출** (recon의 07-26→08-03은 참고만 — 날짜가 흘렀을 수 있음):
   - TNV 최신 date = T₀ 실측 → 백필 창 = (T₀+1)→D_end. D_end = corpus(DailyNewsKeyword) 입력이 존재하는 최신일 실측.
   - corpus가 백필 창 전 일자에 존재하는지 (일 1행 불변식) — 결측일 있으면 목록만 기록, 채우지 말 것.
4. 사전 스냅샷 (사후 대조용): TNV 행수(날짜 스코프: 창 내 0행 확인) · heat 07-26→최신 행수·created 분포 · override 215·ovr_v1·최종수정 07-22 · corpus 최신일.
5. **6/11 themes 확인**: ThemeHeatScore 최신일 6 themes vs TNV 11 themes 차이의 사유를 코드에서 규명 (산출 조건 미충족인지 이상인지). 이상이면 HALT.
6. beat 스케줄 시각 확인 (heat-score-daily 11:00 · collect-theme-filings 21:30 · theme-heat-daily 22:00 실측) → §C 실행 권장 시간대 산출 (beat 발화 ±30분 회피).

## §A. Phase A — 원장 정정 (CC 문서 커밋)

1. **TH-TRIGGER-FIRED 문안 정정**: "corpus unfreeze + TNV 백필(07-12→현재, 50일+)" → "TNV 집계 백필 (T₀+1)→D_end (DB 집계·외부 API 0) + stale heat 재산출".
2. **DECISIONS 등재**: 오전이 경위 1건 — "corpus는 동결된 적 없음 · 실동결은 TNV 집계(beat 부재→수동 의존) · '07-12'는 override G2 스코프(≤07-11)의 오전이. 실측으로 정정" (D-TH-TRIGGER-CORRECT).
3. **TASKQUEUE 등재**: `TH-OVR-RECUT` 보류 — "확장 corpus 기반 override 재판정. 트리거: 사전 품질 저하 관측 시. G2 앵커(92/19/0/0) 이관 설계 포함 별도 결정 사이클."
4. TASKQUEUE 갱신: TH-TRIGGER-FIRED 소비 처리. beat 승격 여부(TNV 자동화)는 결정 후보로만 1줄 등재 — 이 세션에서 등록 금지 (#28 beat drift·§H).

## §B. Phase B — 백필 준비 (읽기 전용)

1. 커맨드 정확 문안을 코드에서 역산해 확정: TNV 집계(aggregate_theme_news_volume 계열)·heat 재산출(compute_theme_heat 계열)의 날짜 인자·멱등성(upsert) 코드 근거 인용.
2. dry-run 옵션이 있으면 dry-run 결과 첨부 (없으면 생략 명기 — 창작 금지).
3. **병진 실행용 커맨드 2줄 최종 확정** (worktree 경로 포함 절대경로·foreground):
   - ① TNV 백필: 창 (T₀+1)→D_end
   - ② heat 재산출: 07-26→D_end (**stale 창 시작 07-26 고정** — TNV 결손 성분으로 계산된 전 구간 + 백필 신규 구간을 멱등 덮어쓰기)
4. 여기서 **HALT — 보고 후 병진 실행 대기**. 권장 실행 시간대(§0-6) 명기.

## §C. 병진 수동 실행 (CC는 대기)

- 병진: §B-3 커맨드 ①→② 순서로 foreground 실행, 출력 전문을 CC에 전달.
- 오류·부분 실패 시 재실행 금지, 출력 그대로 CC 보고 → HALT 경로.

## §D. 사후 검증 (CC 읽기 전용)

1. TNV: 창 내 (일수)×(11 themes) 격자 충족 실측 — 결측 셀은 사유(코퍼스 결측일 등)와 함께 목록.
2. heat: 07-26→D_end 재산출 확인 (created 갱신·행수), 최신일 theme 수 (§0-5 사유와 정합).
3. **무접촉 입증**: override 215·ovr_v1·최종수정 07-22 동일 · corpus 무변경 (사전 스냅샷 대조).
4. full suite 재실행 — 시작 앵커와 대조 (문서 커밋뿐이므로 동일 기대, 상이 시 HALT).
5. 종합 결과표 작성 → `docs/features/theme-heat/` 커밋 (TH 기상 완료 선언 초안 포함).

## §E. SEC β 잔여 정리 (검증 CC → 실행 병진)

1. CC 사전 검증 (읽기): 삭제 후보 각각에 대해
   - 브랜치 `monorepo/sess-secb-land`·`sess-secb-g16`·`sess-secb-ge`·`sess-th-recon`(§-1 cherry-pick 후): `git branch --merged origin/main` 포함 여부 + 3-dot diff 공집합 확인 (#78).
   - worktree `sv-secb-land`·`sv-secb-g16`·`sv-secb-ge`·`sv-th-recon`: clean(미커밋 변경 0) 확인.
   - 하나라도 미병합·dirty → 해당 항목 제외하고 사유 보고 (강행 금지).
2. 병진 수동 실행 (검증 통과 항목만):
   - `git worktree remove <경로>` (각각) → `git branch -d <브랜치>` (각각)
   - `-d` 거부 발생 = 안전망 작동 → 뚫지 말고 CC에 출력 전달.
3. CC 사후 확인: `git worktree list`·`git branch -a` 재실측 → 정리 결과표.
4. ⚠️ 본 세션 `sess-th-s1`·`sv-th-s1`은 삭제 대상 아님 (착지 후 차기 정리).

## §F. 랜딩

1. CC: 전 커밋 정리 후 최종 HEAD 보고 → 대기.
2. 병진 수동: `git -C ~/worktrees/sv-th-s1 push origin HEAD:main` (원자·force 금지).
3. CC: push 후 origin/main=HEAD 동기 재확인 → 착지 해시 + 세션 종료 앵커 보고.

## §R. 최종 보고 형식

지시서 커밋 해시 / 백필 창 실측치 (T₀·D_end) / 병진 실행 커맨드 2줄과 출력 요지 / §D 검증표 (격자 충족·무접촉 입증·suite 앵커) / §E 정리 결과표 / 착지 해시 / DECISIONS·TASKQUEUE diff.

## HALT 조건

배달 게이트 실패 / §0-5 이상 판정 / 백필 창 실측이 recon과 정성적으로 다름 (예: TNV가 그새 갱신됨 — 전제 변동) / 커맨드 부분 실패 / 멱등성 코드 근거 확인 불가 / override·corpus 변경 감지 / suite 신규 실패 / `-d` 거부 / CC에 DB 쓰기·삭제·push를 요구하는 모든 상황.
