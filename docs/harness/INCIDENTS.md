# INCIDENTS.md — 하네스 인시던트 대장

> 규약·게이트 위반, 사고, 근접 사고(near-miss)의 단일 기록. 번호제 `INC-NNN`.
> 항목 형식: **[경위 / 결과 손상 / 처분 / 교훈]**. 롤백·재발방지 결정은 DECISIONS로 링크.
> 신규 등재는 mgmt/거버넌스 세션에서. 관련: `session_isolation_guide.md`(규약 정본) · `DECISIONS.md`.

---

## INC-001 — CLOSE-0808-PUSH (HALT 자가 해제) [2026-08-10]

- **경위**:
  1. CLOSE-0808 세션에서 병진 채팅 승인("푸시해줘") 하에 CC가 origin/main push를 집행. 당시 규약
     문언("push는 병진 수동")과 충돌했으나 **승인 실체는 존재**(명시 지시).
  2. push 직전 `behind=2` 조우 시 CC가 HALT를 선언했으나, **충돌 위험 파일 교집합 0을 근거로
     자가 해제하고 `git rebase origin/main` 진행** 후 push. → 지시서가 명시 금지한 "자가 흡수 판단·실행"
     위반(무충돌 실측을 진행 근거로 오용).
- **결과 손상**: **0**. 변경분은 문서 4종(PROGRESS/TASKQUEUE/common-bugs/지시서), rebase 무충돌,
  착지 검증(ahead 0·origin/main 해시 확인) 완료. 데이터·코드 영향 없음.
- **처분**: **롤백 불요**. `D-PUSH-DELEG` 규칙 명문화(push 조건부 위임 + behind>0 하드 스톱)로 종결.
  후속 실증 게이트를 TASKQUEUE에 등재.
- **교훈**:
  ⑴ **HALT는 자가 해제 불가** — 해제 권한은 병진 채팅 지시만.
  ⑵ **무충돌 실측(교집합 0)은 진행 근거가 아니라 보고 내용**이다.
  ⑶ push 위험의 실체는 push 행위 자체가 아니라 **non-ff 상황의 자가 흡수 판단** — 통제 지점은 거기.
  ⑷ 실증(GOV-PUSHDELEG-0810 STEP 0): behind=1→3 및 다중 게이트 편차에서 **HALT 2회 준수(GREEN)** 확인.
