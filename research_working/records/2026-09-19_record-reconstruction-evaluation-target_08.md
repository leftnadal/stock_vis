# Working Record — Record Reconstruction Evaluation Target / Checkpoint 08

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-19  
**Topic:** Record Reconstruction Evaluation Target  
**Keywords:** reviewer preparation repair, coverage, parent variants, schema validation, negative fixtures, no-call handoff, 검토 입력 보완, 출력 검증, 호출 미승인  
**Prior Record:** [Checkpoint 07](2026-09-19_record-reconstruction-evaluation-target_07.md)  
**Official Authority:** `leftnadal/stock_vis`, `main/research_lab/`  
**Record Basis:** 두 준비 결함 보완을 권고한 직전 Chat 답변에 대한 사용자 응답 “좋아 다음 작업하자”. 기존 준비 승인 안에서 Research Work에 보완 범위를 인계하는 기록이며 수정 완료나 reviewer 실행 결과가 아니다.

## 현재 위치와 실행 경계

담당은 기존 `research_work_01`이다. 새 Job이나 Crosslab 이관 없이 기존 계보를 유지한다. [준비 승인 Checkpoint 06](2026-09-18_record-reconstruction-evaluation-target_06.md)의 패키지 결함 보완 범위에서 진행한다. 준비를 반복 승인받을 필요는 없으며 실제 reviewer 호출은 여전히 별도 승인 사항이다.

- Source batch: `8737355cc59549c6bee5424cde069d43`
- Previous batch: `6f739c4557c84627993657509a9983d0`
- 검토 대상 원 ZIP: `StockVis_Gold_v021_Reviewer_Package_Preparation.zip`
- 원 ZIP SHA-256: `d7cd2b682480b6371bec452d47580b88d0e81310af9d8f5b115dd16ebf53d715` — Checkpoint 07 및 재현 결과의 값. 이번에는 원 ZIP을 다시 해시하지 않았다.
- 재현 묶음: `StockVis_Reviewer_Preparation_Chat_Checks_2026-09-19.zip`
- 재현 묶음 SHA-256: `a6f5d78f22ed2d7eede1d31fdf4f1cbedce17ef0717e14e66c9f80bcaf8bd62f` — 이번 Chat에서 실제 파일로 계산했다.

Gold v0.2.1의 의미, Option B 평가 목표, 43개 frozen claim과 출력, 기존 40/3/0 결과는 변경하지 않는다. 보완은 reviewer 입력과 출력 검증 구현에 한정한다. 이미 후속 수정본이 있으면 원본·차이를 확인하고 충족된 작업은 재사용한다.

## Work 보완 1 — 정정 대상이 실제 입력에 포함되는지 검증

활성 경로 56개뿐 아니라 아래 옛 형태 6개도 reviewer가 그 충분성·필수 결합을 판단할 수 있게 제시한다. 보호된 이력 매핑만 존재하는 상태를 검토 완료로 세지 않는다.

| Claim | 옛 route ID | 이력상 관계 — 첫 판정 입력에는 비노출 |
|---|---|---|
| `2f9c8a41e6d54703-q1-c3` | `manifest` | 제외 |
| `a4d71e0b93c6425f-q1-c1` | `manifest` | 제외 |
| `a4d71e0b93c6425f-q1-c4` | `plan` | 제외 |
| `a4d71e0b93c6425f-q4-c4` | `raw-plus-inference` | 교체 전 |
| `a4d71e0b93c6425f-q3-c1` | `plan-plus-outcome` | 단순화 전 |
| `a4d71e0b93c6425f-q3-c3` | `raw-plus-prior-limit` | 단순화 전 |

이 표와 Chat 검토 메모는 Work용 대조 자료다. Reviewer의 첫 입력에는 기존 점수, Gold verdict, 제외·교체·단순화라는 정답 표지, 정정 이유, 작성자의 충분성 결론을 넣지 않는다. 원 claim, 당시 계약, source payload와 provenance, 판단에 필요한 prior assessment 본문은 유지한다. 후보 basis·경로는 검토 대상으로 제시하며 정답으로 지시하지 않는다.

활성 Gold 경로 수, 부모 이력 수, 실제 검토할 고유 variant 수와 묶음 수를 분리한다. 56+6이라는 구성에서 시작하되 같은 claim·근거 범위·필수 연산의 중복 여부를 확인해 실제 분모와 대응표를 제시한다. 이 비교 항목 추가가 Gold sufficient set의 확장은 아니다. 같은 source를 공유한다는 이유로 서로 다른 claim/경로를 합치지 않는다.

최종 직렬화된 reviewer 입력에서 각 variant를 역추적하고 근거 완전성과 결론 누출을 검사한다. 필수 옛 variant 하나를 시험 복사본에서 제거했을 때 coverage 검사가 실패하는 negative fixture를 포함한다. 기존 19/20/17 분할이나 3-call 제안을 유지하려고 필요한 문맥을 자르지 않는다.

## Work 보완 2 — 실제 응답 수용 경로에 전체 schema 검사를 연결

`validate_review_output_v021.py`와 최종 응답 수용 경로에서 동봉 schema 전체 검사와 item/source coverage 검사를 함께 수행한다. 별도 schema 함수가 있어도 실제 수용 경로가 우회하면 보완 완료가 아니다. 테스트를 통과시키기 위해 기존 필수 필드나 enum을 느슨하게 바꾸지 않는다.

재현 묶음의 다음 합성 반례는 정상 성공 결과로 수용되지 않아야 한다.

- `exposure_declaration={}`
- `route_sufficiency=not_an_allowed_verdict`
- 빈 `rationale`

정상 fixture는 통과시킨다. 중복·누락 item ID, 알 수 없거나 해당 항목에서 허용되지 않은 source ID도 기존 계약에 따라 검출한다. 거절·API 오류·중단·잘린 응답·잘못된 JSON은 성공한 의미 판정과 구분하고 원 응답 및 오류를 보존한다. 자동 보정·자동 재시도로 정상 결과처럼 덮지 않는다.

위 테스트는 네트워크 없이 합성 응답을 실제 검증/수용 함수에 전달하는 방식으로 확인한다. 현재 reviewer 실행 코드가 없다면 네트워크 없는 수용 경로를 준비·검사하거나 미구현 상태를 명시한다. 구조 검사를 Gold의 의미적 정확성 또는 독립 감사의 증명으로 사용하지 않는다.

## 원본 보존과 실행안 갱신

원 패키지와 반례를 보존하고 별도 준비 revision에서 수정한다. 패키지 revision과 Gold v0.2.1 버전을 구분한다. 재생성 테스트는 원본이 아닌 격리된 작업 복사본에서 실행한다. 재현 스크립트의 과거 절대 경로는 실제 원본 위치에 맞게 매개변수화하되 미확인 로컬 경로를 만들지 않는다.

수정 후 package/manifest/final input의 실제 해시·크기·매핑, 원 Gold·출력·자료 보존을 확인한다. 최신 공개 공식 자료에 근거해 모델 ID·지원 설정·요금·보관 조건을 확인하고, 계정별 접근은 공개 정보와 구분한다. 이전 모델명·요금·3회/재시도 0/$0.50 제안은 이번 실행 승인이 아니다.

수정된 전체 요청의 토큰 산정 방법, 출력·reasoning 및 실제 청구 항목을 반영한 최대비용, 호출·재시도 상한, endpoint/service/cache 설정, 외부 전달 범위와 보관 조건을 포함해 실행안을 반환한다. 공개 자료 조회와 허용된 로컬 측정은 가능하지만, token-count 용도라도 private payload의 provider 전송이나 reviewer/model API 호출은 하지 않는다. 정확한 사전 계산이 불가능하면 미확인·보수적 추정·필요한 별도 권한을 구분한다. 모델이나 예산이 달라져도 조용히 대체하거나 승인된 것으로 처리하지 않는다.

## 반환물·완료 기준

실제 접근 가능한 수정 패키지와 SHA-256, 원본 대비 변경표, 최종 입력에서 확인한 variant coverage, 정상/음성 fixture 결과, 실제 수용 경로의 schema 검사 연결, 원본 보존 결과와 수정된 실행안을 반환한다. 결함을 검사하는 데 충분한 근거를 제공하되 전체 의미 감사를 다시 시작하지 않는다.

현재 완료 목표는 **“준비 결함 보완·로컬 검사 완료, 실제 reviewer 호출 승인 대기”**다. 검사 실패나 원자료 결손은 가능한 보완과 분리해 보고한다. 준비 검사가 통과해도 reviewer 의미 검토·historical fact 재현·held-out 성능이 검증된 것은 아니다.

비범위: 실제 reviewer/모델 호출, 유료 작업·외부 payload 업로드, Gold 의미 수정·추가 재채점, 대상 prompt calibration, 과거 실험 재실행, held-out, 공식 Methodology/Terminology 변경, permanent architecture, Knowledge/memory admission, Work 산출물 push/merge/deploy/promotion. 별도 ‘다음 연구 행동 제안 비교’ 설계의 실험도 이번에 시작하지 않는다.

## 이번 Chat의 실제 작업과 확인 범위

시작 시 main은 `6898a27e509c3238ad14e665060b493fa3865629`였다. 최신 INDEX·Working README·준비 승인 06·결함 검토 07·Evaluation Methodology §§3.5–4.1을 읽었다. 직전 확인 `1096254b10fdfefb186e756096e4d56e386efbce`부터의 변경을 비교해 관련 research_lab 및 research_working 문서는 그대로임을 확인했다. 다른 제품 파일·TASKQUEUE·DECISIONS 변경은 이번 작업 대상이 아니다.

현재 컨테이너에서 재현 ZIP을 열어 검토 메모·결과 JSON을 확인하고 ZIP 해시를 계산했다. 이번에 원 패키지 테스트나 reviewer 호출을 재실행하지 않았다. 실제 작성 범위는 이 인계용 Working Record, INDEX의 포인터, 동일 내용의 전달용 Markdown 파일이다. Work 코드 수정·수정 패키지 완료·다른 세션 자동 전달을 수행했다고 주장하지 않는다.
