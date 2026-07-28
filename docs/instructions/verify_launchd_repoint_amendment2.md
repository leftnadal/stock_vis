# 개정문 2: verify launchd repoint — 전파/plist를 야간 창 번들로 이행 + §3-2 시점 개정

- 발행: 감독 세션, 2026-07-24
- 선행: [개정문1](verify_launchd_repoint_amendment1.md)(self-locate 래퍼 + α 승인·집행 STEP 0~3 완료), 원 지시서(2026-07-21) 미수정.
- 개정 사유: Step 4(worker_sync 전파)의 blast radius가 celery-worker + celery-beat + **daphne(WS 연결 끊김)** 3종 재기동으로 확인됨. 정기 타이머 없음(재기동은 서비스 startup 시점 = 불확정). 라이브 disruption 타이밍을 CC 즉시 발화로 두지 않고 병진 야간 창 단일 이벤트로 묶는다. 또한 §3-2(인위 stale 마커 발화)를 봉인 관찰 오염 방지를 위해 익일 회수 세션으로 이연.

## 승인 결정

- **Step 4+5 야간 번들**: worker_sync 전파(Step 4)와 plist repoint(Step 5)를 병진 야간 창 한 이벤트로 실행. 라이브 3종 재기동을 1회로 수렴.
- **CC 이번 세션 산출물 = 병진 야간 창 명령서 1부** (`verify_launchd_repoint_night_window_commands.md`). 명령서 필수 포함 항목:
  - 사전 점검: 발화 직전 in-flight Celery task 유무 + nightly 자동화 창(23:00, ~4h) 비중첩 + verify 02:30 비근접 확인. 겹치면 대기.
  - ① worker_sync 발화 → 같은 shell 재조회로 sv-worker-runtime 래퍼 self-locate 반영 확증(파일 grep). GREEN이어야 ②로.
  - ② plist: 백업 사본 → 후보 plist 교체 → bootout → bootstrap → launchctl print 실효 경로 재실측(§2-3).
  - ③ 수동 verify 1회 발화 → 출력 로그 저장. 육안 1차 2줄: PRE/A/B/C 존재 + section D 3항목 출력 존재. (정밀 IDENTICAL 비교는 익일 회수 세션이 이 로그로 수행.)
  - 각 단계 실패 시 즉시 중단 지점 + 원복 명령(plist 백업 복원 → bootout/bootstrap 원상) 명기.
- **§3-2 개정**: 인위 stale 마커 발화 테스트는 야간 창에서 **실행 금지**. 익일 02:30 봉인 관찰(첫 라이브 section D 3항목 발화 1회) 후 회수 세션에서 실행. 봉인 관찰 오염 방지.

## 세션 종료 조건

- 개정문2 + 명령서 커밋·경로 보고 후 이 세션 종료.
- Phase 3 봉인은 여전히 익일 라이브 02:30 관찰로만 선언(불변).

## 집행 현황(개정문2 시점)

- origin/main = `b9ddf41a`(내 2커밋 착지: 개정문1 `410307b6`→rebase 후 해시 이동, self-locate `403a8f4a`→이동). self-locate 래퍼가 origin/main에 존재.
- sv-worker-runtime = `970d9e29`(내 push 이전 상태, self-locate 미반영) → 야간 `sv sync`로 최신화 예정.
