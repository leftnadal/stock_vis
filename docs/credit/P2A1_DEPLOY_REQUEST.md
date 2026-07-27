# CS-CREDIT-P2A-1 배포 요청서 (집행 아님 — 승인 대기)

> 이 문서는 **요청서**다. 배포·push 어느 것도 집행하지 않는다.
> 집행 = 이 요청서 승인 + **사용자 명시 승인 인용** + 본 프로젝트(Stock-Vis) 조율 후에만.
> 작성: 2026-07-21. 발효 규칙(배포·재배포·beat·prod 쓰기 = 승인 인용 없이 STOP) 유지.

## 0. 대상 상태
- 브랜치: `monorepo/sess-credit-p2a-1`, 커밋 **`7f3ad05`** (로컬, **미푸시**)
- 분기 base = origin/main **`1cd9460`** (작성 시각 기준 현재 HEAD와 동일)
- Gate 2 GREEN: pytest **48**(14 신규+34 회귀), strip API **diff 0** 실측
- 변경: `credit_signals`(models·constants·signal_service·etf_nav_service·0002·ingest_etf_nav 커맨드)
  + `packages/shared/.../fmp/client.py`(`get_etf_info` additive) + `tests/credit_signals/test_etf_nav.py`.
  프론트 0, grade_from_z·미러 상수 0.

## a. Push 대상 (명령만 기재 — push 자체도 대기)
```bash
# push 직전 재확인 (해시 고정 금지)
git fetch origin && git log -1 --oneline origin/main
# 브랜치 push (main 반영 방식은 c-1 참조)
git push origin monorepo/sess-credit-p2a-1
```

## b. 선행 체크리스트 (배포 착수 전 read-only 확인)
0. **prod DB 접속성 확인 (`SELECT 1`) — 실패 시 STOP.** 이 세션에서 psql 직접 접속 자체가 타임아웃했으므로, 배포 창에서 **접속성부터** 분리 확인한다(접속 불가면 배포 중단·상신).
1. **origin/main 현재 HEAD 재확인** — 작성 시 `1cd9460`. 배포 시 반드시 재 `git fetch` (main 계속 이동, 해시 고정 금지).
2. **chain_sight 멀티헤드 상태 확인 (TH C8 실행 결과 반영):**
   - 07-16 통지 기준 prod chainsight = **3중 멀티헤드**(0016/0017/0018 각 2계보: 메인라인 vs TH계보).
   - 절차: `showmigrations chainsight`로 양 계보 확인 → `makemigrations --merge`(양측 기적용 시 **no-op**) → merge 마이그레이션 생성 후 main 접촉.
   - ⚠️ **본 세션에서 라이브 확인 실패**(showmigrations·psql 반복 타임아웃). **원인 미확정**(그래프 오버헤드 또는 접속 경로 — psql은 migration 그래프 미로드이므로 접속 경로 가능성) → **배포 창에서 분리 확인**(b-0 접속성 선행). merge가 no-op 아니면 STOP + 에스컬레이션.
   - ★ **credit_signals 0002는 chainsight와 독립 앱** — 멀티헤드와 무관. 단 배포가 `migrate`(전체 앱)를 돌리면 chainsight 멀티헤드 **선해소 필요**(app-scoped `migrate credit_signals`면 회피).
3. **no-op merge migration 필요 여부 판정:**
   - `credit_signals`: 0002가 유일 신규, 선형(0001→0002) → **merge 불필요**.
   - `chainsight`: 별도 사안(C8), credit 배포와 독립. 전체 migrate 경로 선택 시에만 makemigrations --merge 선행.

## c. 배포 페이로드
1. **코드 머지**: `monorepo/sess-credit-p2a-1`(`7f3ad05`) → origin/main.
   - 충돌 예상 **0**(credit_signals 격리 + FMP client `get_etf_info` additive). repo 관례 = `--no-ff` merge commit.
2. **migrate**: `python manage.py migrate credit_signals` → `0002_etf_nav_history`.
   - ⚠️ **로컬 dev stock_vis엔 이미 적용됨**(0002). 배포 런타임 트리/prod가 동일 stock_vis면 **이미 적용 상태 = no-op**; 별도 prod DB면 신규 적용.
   - 전체 `migrate` 사용 시 chainsight 멀티헤드 선해소(b-2) 확인.
3. **worker/beat 재기동**: 코드 반영 위해 `bash scripts/worker_sync.sh` 배포 + `launchctl kickstart -k` (worker/web/api 3트리 동기화).
4. **검증**: `python manage.py ingest_etf_nav` 1회 실행 → EtfNavHistory 1행 upsert + 디스카운트 신호(HYG/LQD_NAV_DISCOUNT) 생성 확인. 재실행 시 `skipped`(멱등) 확인.
5. **beat 등록 = 별도 슬라이스** (본 배포 범위 아님). 등록 시 폴링 타이밍 = nav 갱신(~11:16 KST) **이후**, 07:30 아님.

## d. 신호값 저장 단위 (P2a-2 카피 도출용)
- **value = (nav − price)/nav × 100 = 퍼센트(%) 단위** (비율 아님).
- 부호: **양수 = 디스카운트**(price < nav, 스트레스), 음수 = 프리미엄. 예: HYG value=`−0.0502` → NAV 대비 0.0502% **프리미엄**.
- z-score는 단위 무관(robust z 스케일 불변). grade 부호 규약 B: 디스카운트(양수 value)가 양의 z로 상향, 프리미엄은 gray.

## 승인 요건 (재확인)
- push조차 대기 (요청서 단계). 배포 집행 = **요청서 승인 + 사용자 명시 승인 인용 + 본 프로젝트 조율** 3건 충족 후.
- UI(P2a-2)·beat 등록은 파킹 유지.
