# 지시서 TH-TNV-CHAIN-1 — TNV 집계를 heat 태스크에 체이닝 (재동결 방지) + 갭 백필 + 잔여 정리

**트랙:** TH (자동화 완결)
**전제:** 결정 확정 — **(B) 체이닝** (가중합 4.15, 마진 1.30 자동 결정, D-TH-TNV-CHAIN으로 등재할 것). 신규 beat 등록 금지 (#28 회피가 B 선택의 근거 그 자체).
**실행 구조:** CC = 코드·문서·검증. **prod 쓰기 커맨드(갭 백필)·main push·워커 재기동·원격 삭제 = 병진 수동** (§H).
**worktree:** 신규 생성, 브랜치 `monorepo/sess-th-chain`
**작성일:** 2026-08-04 (디렉터 세션)

---

## §-1. 배달 게이트

이 지시서를 `docs/instructions/TH-TNV-CHAIN-1.md`로 저장, 단독 커밋. 해시 보고 첫 줄 기록. **세션 말미 병진 push로 반드시 착지** (cherry-pick 잔존 패턴 재발 방지 — TH-SESSION-1 교훈).

## §I. 불변

- CC의 DB 쓰기 0 · beat 스케줄(PeriodicTask) 등록·수정·활성화 0 · launchctl·워커 조작 0.
- 신규 beat 태스크 등록 절대 금지 — 체이닝은 **기존 theme-heat-daily 태스크 코드 내부** 수정만.
- heat 산식·판정 로직 무변경 (행위보존 정의는 §V 참조).
- force-push 금지 · `git add -A` 금지 · CC의 `-D`는 병진 건별 명시 지시 + 손실 0 사전 입증 시에만 (§A-2 규칙).
- 부분 실패 → HALT.

## §0. STEP 0 — 실측

1. `git fetch` → main HEAD·동기. 신규 worktree `monorepo/sess-th-chain`. 베이스라인 full suite 재실측·앵커 — **suite는 동시 1개만, 실행 전 `ps`+`pg_stat_activity`로 잔여 프로세스·연결 0 확인** (신규 common-bugs 항목 — §A-1에서 등재).
2. **재동결 폭 실측**: TNV 최신 date(T₀′)·corpus 최신(D_end′) → 갭 창 = (T₀′+1)→D_end′. keywords=[] 일자는 분리 표기 (일·월 공백 패턴 — 채우려 하지 말 것, CORPUS-SUNMON-EMPTYKW 별건).
3. theme-heat-daily 태스크의 정확한 코드 위치·현재 구조(진입점→compute_theme_heat 호출 경로)·beat 발화 시각 재확인.
4. **워커 런타임 트리 실측**: sv-worker-runtime(또는 실제 런타임 트리) 경로·추적 브랜치·현재 HEAD가 origin/main 대비 몇 커밋 뒤인지 (§D 배포 절차의 입력).
5. 메인 트리 HEAD 확인 (구 브랜치 체크아웃 위생 — §E-3 보고 입력).

## §A. Phase A — 원장·하네스 선행 커밋

1. **common-bugs 등재 2건**: ⓐ 동시 pytest 금지 — 단일 공유 test DB에 suite 겹침 실행 시 reuse=DuplicateColumn·create-db=DB-in-use 가짜 에러(8초대 조기 종료), 앵커 suite는 단독 1개·사전 프로세스/연결 0 확인 (TH-SESSION-1 실측, CC 메모리 lesson의 repo 정본화) ⓑ CC `-D` 경계 — 병진 건별 명시 지시 + 손실 0 사전 입증(내용의 main 존재 확인) 동시 충족 시에만, 일괄·재량 -D 불허 (sess-th-recon 선례).
2. **DECISIONS**: D-TH-TNV-CHAIN — 선택지 A/B/C·가중합·마진 1.30·B 확정 근거(#28 회피·순서 구조 보장) 기록.
3. **TASKQUEUE**: TH-RESUME-CORPUS-UNFREEZE ✅완료 처리 / TH-TNV-BEAT-SPLIT 보류 신설(트리거: TNV·heat 주기 분화 필요 시 — A안의 미래 재개점).

## §B. Phase B — 체이닝 구현

1. theme-heat-daily 태스크 선두에 `aggregate_theme_news_volume(당일 date)` 호출 삽입:
   - 당일 1일 스코프 (범위 인자 아님 — 갭 메움은 §C 수동, 태스크는 전진만)
   - 결과 로그 필수: `TNV_CHAIN date=… written=N zeroed=M` 형식 (관측성 확보 — B안 단점 보완)
   - **TNV 실패 시 heat 진행 정책 = 실패 전파(태스크 실패)로 구현**: 빈 재료로 조용히 계산하는 것이 이번 사태의 본질이므로, 소리 내고 멈추는 쪽이 옳다. 단 keywords=[] 정상 공백(written=0)은 실패 아님 — 예외와 0건을 구분할 것.
2. 단위 테스트 추가: 체인 순서(TNV→heat)·실패 전파·written=0 통과의 3케이스 최소.
3. 코드 변경 반경 보고: 변경 파일·라인 수 (최소 침습 확인).

## §V. 행위보존 검증 (정의 명확화)

- **보존 대상**: heat 산식·등급 판정·기존 테스트 전부 GREEN. suite 앵커 대조 (시작 대비 신규 실패 0, 신규 테스트 +3 예상).
- **의도된 변화 (보존 위반 아님)**: 배포 후 heat가 *채워진 TNV*로 계산되어 값이 달라지는 것 — 이것이 이 세션의 목적이다. 혼동 방지를 위해 §R에 명시 기재.

## §C. 갭 백필 (병진 수동 — TH-SESSION-1 §C와 동일 패턴)

1. CC: §0-2 실측 창으로 검증된 커맨드 2줄(TNV 범위 백필 + heat 재산출 루프) 확정 — TH-SESSION-1에서 실증된 함수 경로 재사용, 창만 치환. beat 회피 시간대 명기. → **HALT, 병진 실행 대기.**
2. 병진 foreground 실행 → 출력 전문 전달 → CC 사후 검증 (격자·무접촉: override 215·corpus 불변).
3. 갭이 0일이면(§0-2 실측 결과) 본 절 생략 명기.

## §F. 랜딩 + 배포 (순서 엄수 — 활성화≠배포)

1. CC: 최종 HEAD 보고 → **병진 push** `origin HEAD:main` (원자·force 금지) → CC 동기 재확인.
2. **병진 수동 배포 2단**: ⓐ 워커 런타임 트리를 origin/main 신규 HEAD로 전진 (§0-4 실측 경로 기준, CC가 정확한 명령 1줄 제시) ⓑ 워커 재기동. **push만 하고 ⓐⓑ를 생략하면 코드는 배포되지 않은 것** (3회 재발 함정 — 이 줄을 §R에 재인용할 것).
3. CC: 재기동 후 워커가 신규 HEAD 코드를 로드했는지 가능한 범위에서 확인 (로그·프로세스 시작 시각).

## §G. 프로덕션 게이트 (익일 — 세션 분리)

- **G-fire**: 배포 익일 18:00 ET(≈KST 익일 07:00) beat 자연 발화 후, 병진이 "게이트 확인해줘" 한 마디로 짧은 검증 실행:
  ① 태스크 로그에 `TNV_CHAIN` 라인 존재 ② 당일 TNV 행 실측 (keywords=[] 요일이면 written=0 정상 판정) ③ 동일 실행에서 heat 저장 확인 ④ 오류 0.
- G-fire 통과 시 CC가 TASKQUEUE에 TH-TNV-CHAIN ✅완료 커밋 → 병진 push → **트랙 종결**. 미통과 시 HALT·롤백 후보 보고 (revert 커밋 준비만, 실행은 판정 후).

## §E. 잔여 정리 동승

1. **잔존 secb 4건 검증** (읽기): sess-secb-kickoff(+worktree sv-secb)·gate2-amend·progress 각각 merged/미착지 내용 실측(#78 — 2-dot 뒤처짐 아티팩트 구분), 원격 origin/sess-secb-g16 삭제 명령 확정 → 검증 통과분의 삭제 명령 목록 보고 (**실행 전부 병진 수동** — 원격은 `git push origin --delete`).
2. 미착지 내용 보유 브랜치 발견 시 삭제 후보에서 제외·내용 요지 보고 (회수 여부 디렉터 판단).
3. **메인 트리 위생 보고**: 메인 트리 HEAD가 구 브랜치면, main 복귀 명령 1줄 + 영향(스크립트 오판 방지) 보고 — 실행은 병진 선택.

## §R. 최종 보고 형식

지시서·D-TH-TNV-CHAIN 커밋 해시 / 갭 창 실측·백필 출력 / 코드 변경 반경 / suite 앵커(시작·종료, §V 의도된 변화 명시 포함) / 착지 해시·런타임 트리 전진·재기동 확인 / §E 검증표·병진 명령 목록 / G-fire는 익일 별도 보고.

## HALT 조건

배달 게이트 실패 / beat 등록·스케줄 변경이 필요해지는 모든 상황(설계 전제 붕괴 = B 재검토 회부) / 체인 구현이 heat 산식 변경을 요구 / suite 신규 실패 / 갭 백필 부분 실패 / 런타임 트리 구조가 §0-4 실측과 불일치 / CC에 워커 조작·prod 쓰기·원격 삭제를 요구하는 모든 상황.
