# Fixed Local Observation + Sealed Codex Review v0.1

2026-09-10 CEO 승인에 따른 로컬 candidate 구현이다. 다른 Lab에는 적용하지 않는다.

## 실행 계약

execution_mode=fixed_daily_price_local_then_codex_review_v1이 명시된 OBSERVATION-003만 새 경로를 사용한다. 기존 Job은 기존 runner를 사용한다. 새 경로는 임의 command/test_commands/codex_command를 거부한다.

DailyPrice는 c9bd21effbf0f3b3c728bed97e64f5aca330304c에 고정한다. runtime Python 파일과 authority 참조의 SHA-256을 검증한다. 기존 Poetry Python의 실제 경로와 SHA-256을 기록한다. 새로운 패키지나 credential을 설치하지 않는다.

호스트 probe가 동일 transaction에서 read-only/isolation 확인과 실제 query를 수행한다. 실패 시 접근 실패와 데이터 부재를 구분하고 partial artifact를 보존한다. 생산자는 mac_local_executor/fixed_python_probe다.

JSON·gap·report를 해시로 봉인하고 별도 directory에 검토 사본을 만든다. Codex는 이 사본의 내용을 독립 검토하며 생산자는 codex_reviewer/codex_cli다. DB 환경변수는 Codex에 전달하지 않는다. model-visible shell tool을 끄고 read-only sandbox를 유지한다. 검토 시 빈 임시 `CODEX_HOME`을 사용하고 기존 파일 인증은 symlink로만 참조하며 사용자 config/MCP를 상속하지 않는다. 임시 home은 종료 시 삭제한다. `shell_tool=false`와 활성 MCP 서버 없음이 확인되지 않으면 DB 실행 전에 정지한다. `unified_exec`는 shell tool이 존재할 때 사용하는 실행 backend 선택값이므로 유효 상태를 증거에 기록하되, `shell_tool=false`일 때 별도 host command 권한으로 해석하지 않는다. 사용자 설정 파일을 수정하지 않는다.

CLI 근거: [공식 CLI 문서](https://developers.openai.com/codex/cli/reference/), [공식 설정 문서](https://developers.openai.com/codex/config-reference/). 설치된 CLI의 실제 지원을 사전 확인한다.

검토 누락·실패·blocker·입력 hash 불일치이면 commit을 만들지 않는다. 원 artifact와 사본 해시를 재검증한다. 관측 partial 상태는 미지원 의미론 때문에 가능하지만 database_status=available과 transaction guard 증거가 필요하다. 새 품질 threshold를 만들지 않는다.

오류는 c9bd21ef의 error_redaction boundary를 통과한다. 동일 OS 사용자 권한의 악의적 동시 프로세스에 대한 완전 격리를 주장하지 않는다. Codex에 DB credential이나 source checkout을 검토 입력으로 주지 않는다.

## 계보

OBSERVATION-002 Run 5ace7522-6535-4f16-81b0-bbc63b5daea9와 실패한 003 Run e031a8f8-92af-48aa-b52d-dad085905fad, 8ce6eb9b-d3e0-48b4-8426-9cc6b618631f, 301705d3-a795-4ef1-a6e3-b00e93033505 및 cf8f70a5-3ea9-40e2-8470-a055d5e99b91는 변경하지 않는다. 승인된 수정 후 recovery Run은 같은 Job의 새 UUID·실행별 claim·worktree·append-only ledger·invocation을 가지며 실패 Run을 명시적으로 연결한다. 접근 실패를 commit recovery로 처리하지 않는다.

Runner 변경은 별도 lab-automation branch의 로컬 commit으로 보존한다. 관측 candidate는 c9bd21ef를 parent로 가지며 관측 output directory만 변경한다. push/merge/deploy/main 반영은 하지 않는다.

## Human intervention telemetry

command copy/paste, file/ZIP transport, environment repair, Job state 변경, artifact upload/download, 기타 개입을 구분한다. 관찰할 수 없는 횟수는 null/unknown이며 0으로 바꾸지 않는다. Bootstrap의 사용자 실행 의존성과 요청된 download/command/upload는 별도로 기록한다. 이후 사람이 확인한 개입은 새 확인 event로 추가한다.

## PIC-HUMAN-TRANSPORT-001

상태: 로컬 제안, 미배포. 002의 실제 수동 실행·ZIP 전달과 003 bootstrap의 동일 의존성이 근거다. KPI가 아닌 자동화 공백 진단이다.

| 단계 | 공백 | 다음 version의 제거 방법 |
|---|---|---|
| Job 전달 | 상시 Mac 소비자 없음 | 승인된 Job digest만 가져오는 queue consumer; lease/중복방지 |
| 실행 | 사용자 launcher 실행 | 고정 profile worker; 임의 모델 명령 거부 |
| 결과 전달 | 사용자 ZIP 업로드 | content-addressed 저장소와 GitHub result pointer/receipt |
| Work 회수 | 사용자 대화 입력 | receipt 감지·hash 검증·Lab별 평가 |
| 장애 처리 | 수동 원인 확인 반복 | 실패 분류·제한된 재시도; 경계 변경만 CEO escalation |

result_outbox.json은 전송 준비 상태이며 자동 전송하지 않는다. GitHub watcher, credential provisioning, 상시 서비스 설치·배포는 이번 bootstrap에서 하지 않는다. 필요한 연결·배포·비용 결정은 구체적인 운영안을 만든 뒤 처리한다. routine Job당 human transport dependency ≈ 0은 아직 달성하지 않았다.
