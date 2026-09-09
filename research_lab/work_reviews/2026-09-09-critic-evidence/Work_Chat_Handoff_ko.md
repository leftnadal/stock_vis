# StockVis Work → Chat Handoff

## Executive Summary

Mac Studio Ultra 256GB·내부 SSD 2TB·추가 저장장치 가능이라는 승인된 전제 아래, 기존 서브에이전트 실험을 read-only로 재검토했다. 원 manifest 28개와 모델 실행 출력 38개를 확보하고, 명시적 case hash가 있는 8개 manifest를 복원된 입력과 대조해 모두 일치함을 확인했다. 한 Critic 출력에서는 원 답변의 분모 오류를 고치는 동시에 조건부 산술을 상한으로 바꾸는 새로운 오류가 확인됐다. 압축 사례에서는 설치 시점과 매출 인식 시점의 차이를 설명하는 원자료가 있어도 결론에서 그 조건이 사라질 수 있었다. 이는 기존 Evaluation/Operational Record Specification이 이미 요구하는 범위·조건·근거 연결을 실제 전달 과정에서 검증할 필요를 보여준다. 모델 우열이나 Mac 실행 가능성은 이 자료로 확정하지 않는다. 후속 제안은 요약 전달 방식의 제한적 비교이며, 새로운 공통 운영 규칙으로의 채택은 Chat 판단으로 남긴다.

## Current Task

- Lab: Research Lab
- 작업: 기존 Critic·근거 보존 실험의 회고적 증거 audit 및 후속 검증안
- 작업 식별자: RESEARCH-CRITIC-EVIDENCE-AUDIT-20260909 (이 문서의 로컬 추적용 명칭; 공식 Job ID 아님)
- 상태: offline audit 완료 / 후속 비교 설계 제안 / promotion 없음
- Branch / candidate SHA: 없음. 기존 git worktree 및 branch를 변경하지 않은 독립 검토 패키지
- 실행 환경: ChatGPT Work Linux. Mac 측 실행·메모리·저장장치 측정 없음
- 승인 근거: 사용자의 2026-09-09 “맞아. 진행하자” — 서브에이전트 운영·Critic 검증·근거 보존 후속 작업

## Original Objective

기존 실험을 활용해 Critic의 도움과 부작용, 압축 중 손실되는 material evidence, 다음 평가자가 실제로 받을 정보의 적절성을 검증한다. 장비 기준 변경은 모델 상주 수나 실행 속도에 대한 검증 결과가 아니다. 저장공간 부족을 이유로 material input·결과·수정 이력을 버리는 구조를 전제하지 않는다.

## What Was Done

1. 최신 GitHub main의 Research Methodology, Evaluation Methodology, Operational Record Specification, Scientific Philosophy, DR-0008을 읽고 조회된 본문을 `authority_sources.json`에 보존했다.
2. 기존 업로드의 manifest 28개, Critic/primary 출력 38개, serverless starter v0.8.1의 case와 관련 실행 코드를 확보했다. 원 파일은 덮어쓰지 않았다.
3. `audit.py`로 JSON 파싱, byte hash, 출력 상태, case hash 대조를 수행했다. 외부 API·DB 접근 기능은 없는 별도 스크립트다.
4. hard-003 및 hard-006의 특정 출력 내용을 해당 synthetic evidence와 비교했다. 38개 출력 전체에 대한 의미 평가·점수 산정은 하지 않았다.
5. 동일 evidence에서 상한 결론이 도출되지 않음을 설명하는 조건부 산술 반례를 계산했다. 실제 기업에 대한 전망이나 신규 모델 실험이 아니다.

## Verified Facts

| 확인 항목 | 결과 | 해석 경계 |
|---|---|---|
| manifest | 28개: compare 8, topology 6, review 13, family 1 | 28개의 독립 연구 사례 또는 28개의 성공 run이라는 뜻 아님 |
| 명시된 case hash | 8/8이 v0.8.1에서 추출한 해당 case와 일치 | 다른 prompt·모델·실행 순서까지 검증한 것은 아님 |
| 원 실행 출력 | 38개: complete 37, needs_inspection 1 | 원 파일이 기록한 상태이며 semantic pass 수가 아님 |
| 길이 제한 출력 | `122-397-critic_critic(1).json`: finish_reason=length | 실패를 삭제하거나 재실행하지 않음 |
| 실험 성격 | 원 manifest에 synthetic / hosted proxy / precision·serving confound 명시 | Mac runtime benchmark 및 confirmatory evidence로 해석 불가 |
| Critic 입력 구조 | 보존된 코드의 `critic_messages`가 case 전체와 candidate_answer를 전달 | 새 호출이어도 후보 framing에 노출됨; memory-blind 독립 사고와 다름 |
| 비교 평가 구조 | 코드에 package-only와 source-enabled 경로가 구분됨 | 실제 각 평가의 가림 유지 여부는 manifest 선언만으로 입증되지 않음 |

`audit_results.json`은 38개 출력별 파일·모델·response ID·상태·answer hash와 원 JSON의 byte hash를 포함한다. 최초 raw provider 응답이나 실제 네트워크 요청을 새로 복원했다고 주장하지 않는다.

## New Finding / Problem

### F1. 오류를 고친 Critic이 새로운 오류를 더할 수 있음

대상: `122-122-critic_primary(2).json` 및 `122-122-critic_critic(2).json`, case `hard-003`.

- 원자료 E5의 분모는 **통신사업자용 기존 제품 매출**이다. primary는 근거 목록에서는 이를 유지했지만 하방 리스크 설명에서는 **전체 매출의 40%**로 바꿨다.
- Critic은 이 분모 오류를 명시적으로 바로잡았다. 따라서 해당 수정에는 식별 가능한 실익이 있다.
- 그러나 같은 Critic은 24% × 42% = 10.08%p를 회사 전체 성장에 대한 AI 기여도의 **최대치**로 쓰고, 비AI 약 19.7% 성장이 **필수**라고 표현했다. E1은 시장 전망이며 회사 점유율 변화는 가정하지 않는다. 회사 AI 매출이 시장과 동일하게 성장한다는 조건은 입증되지 않았다.
- 산술 자체와 산술에 부여한 의미를 구분해야 한다. 예를 들어 AI가 100%, 비AI가 2% 성장한다는 가상 조건에서는 0.24×1.00 + 0.76×0.02 = **25.52%**다. 이 수치는 실제 가능성 추정이 아니라 10.08%p가 주어진 자료만으로 일반 상한이 아님을 보이는 예다. 최근 분기 비중을 12개월 기초 비중으로 적용하는 조건도 별도로 필요하다.
- Critic의 마지막 문장은 Unsupported에서 “달성 가능성이 낮음”으로 강해진다. 현재 증거의 불충분함은 낮은 발생확률의 근거와 동일하지 않다.

두 파일의 이름·내용·역할은 해당 전후 비교와 부합하지만, byte hash로 연결된 원 invocation parent record는 미확인이다. 따라서 엄격한 paired causal effect나 모델 전체의 오류율을 주장하지 않는다.

### F2. 설치 병목을 매출 전체의 지연으로 옮기는 조건 손실

대상: `397b-critic(2).json`의 `hard-006/397b-critic` 출력과 case `hard-006`.

- E9/E10: 동일 캠퍼스의 AI 수주잔고 31%, 전력 인가 후 설치 일정 확정, 인가 예상 15~21개월.
- E11/E12/E13: 일부 표준 장비는 인가 전 출하 가능, 출하·검수 후 매출 인식 가능, 표준/맞춤형 금액 비중 미공개.
- 출력은 전량 지연으로 단정하면 안 된다는 점과 미공개 비중을 인식한다. 그런데 최종 결론에서는 12개월 내 28% 성장의 가능성이 낮다고 진전시킨다.
- 원자료가 존재한다는 것, 답변 어딘가에 조건이 등장한다는 것, 그 조건이 최종 추론을 실제 제한한다는 것은 서로 다른 검증 대상이다.

이 사례의 기존 질문은 근거 ID를 최대 5개로 제한한다. 이 인위적 압축 조건은 실험 변수이며 Research Lab 공통 보존 규칙이 아니다. 현재 검토로는 오류가 압축 때문에 발생했는지, 추론 오류인지, 후보에 대한 anchoring인지 분리할 수 없다. 다른 방식의 전달과 비교하기 전까지 압축의 인과적 피해 크기를 산정하지 않는다.

### F3. 실행 완료와 검증 가능한 입력 계보 사이의 간격

13개 review manifest에는 prompt hash가 있지만 이 패키지에서 해당 실제 prompt 본문과 평가 결과 전체를 복원·매칭하지 않았다. 38개 출력에는 자체 response ID가 있으나 모든 부모 입력·코드 버전·최종 평가를 immutable ref로 연결한 증거는 미확인이다. 업로드 suffix와 가까운 시간만으로 이 공백을 메우지 않는다. 기존 파일을 새 manifest로 덮어쓰지 않고 이 audit을 별도 증거로 남긴다.

## Why This Requires Chat

오류의 확인과 입력 inventory는 승인된 Work 범위에서 완료했다. 그러나 요약에 담을 내용, 평가자가 원문을 다시 열 수 있는 권한, Critic과 Evaluator의 분리 수준을 Research Lab 전체에 적용하는 것은 장기 운영 구조에 영향을 준다. 사용자 Work → Chat Directive의 방법론/평가·아키텍처·해석 항목에 따라 아래 대안을 제안으로만 남긴다. 기존 방법론과의 충돌을 발견한 것은 아니며, 새 역할이나 규범을 만들어 해결해야 한다는 근거도 아직 없다.

## Options

| 선택지 | 내용 | 장점 | 단점 / 위험 |
|---|---|---|---|
| A | 짧은 요약만 전달하는 기존 조건을 비교군으로 유지 | 전달 비용이 작고 현재 실패 재현에 유리 | 누락된 조건을 다음 평가자가 확인하기 어려움 |
| B | 같은 짧은 요약에 정확한 근거 fragment·버전 참조·명시적 한계를 연결하고 필요할 때 조회 | 핵심 조건을 재검토할 수 있고 요약 길이와 보존 범위를 분리 가능 | 잘못된 참조, 조회 실패, 선택적 조회에 의한 누락 가능 |
| C | 평가자에게 전체 evidence와 변경 전후 답변 제공 | 원문 접근의 상한 비교군으로 유용 | context·지연 부담과 정보 과다; 전체 입력도 올바른 해석을 보장하지 않음 |

## Proposed Next Validation

**제안용 명칭:** Research Evidence Handoff Replay v0.1. 공식 Job 등록·실행 승인 또는 공통 contract 채택을 뜻하지 않는다.

같은 synthetic case와 동결한 candidate 출력에 대해 A/B/C 전달 조건을 비교한다. 모델·추론 설정·출력 예산·평가 목적을 고정하고, 전달 조건과 실제 접근한 source ID만 다르게 기록한다. 초기에는 Critic topology와 memory 재사용을 동시에 바꾸지 않는다. 그렇지 않으면 무엇이 차이를 만들었는지 분리하기 어렵다.

첫 비교의 대상은 hard-003의 분모·상한 오류와 hard-006의 설치/매출 인식 조건이다. 이미 본 사례이므로 **개발용 calibration**으로만 사용한다. 일반화 검증용 held-out은 별도 설계·보존이 필요하다. 점수나 통과율 threshold를 이번에 만들지 않는다.

이 비교에서 관찰할 것은 다음이다.

- 원 답변의 오류를 실제로 고쳤는가.
- 수정 답변에 새 unsupported assertion이나 더 강한 결론을 넣었는가.
- 중요한 조건이 최종 결론의 범위를 제한했는가.
- 필요한 source fragment를 정확히 찾았는가; 찾지 못하면 unassessed로 남겼는가.
- 같은 결론을 반복했는지와 근거가 개선됐는지를 구분했는가.
- 호출 실패·잘림·입력 누락을 의미 평가와 분리했는가.

위 항목은 현행 평가의 범위·증거 정합성·추론 타당성·재구성 가능성을 이 사례에 적용한 관찰 항목이다. 새 admission 기준이나 Lab 공통 benchmark가 아니다. 의미 판정은 근거를 대조한 평가로 남기고 모델 평가자 한 명의 결과를 정답으로 자동 채택하지 않는다.

제안된 B의 최소 전달 내용: 대상 내용과 정확한 버전, 원 질문·범위, 잠정 결론, 중요한 근거의 ID/fragment/hash, 그 근거가 지지·제한하는 부분, 가정·미해결 조건, 변경 전후 차이, 다음 검증, 실제 수신자가 본 입력 목록. 이를 새 canonical record 종류로 추가하지 않고 ORS의 기존 대상·평가·Evidence Reference를 참조하는 실험용 view로 구성한다.

## Mac Studio / Storage Working Constraints

- 기준 장비는 사용자가 지정한 Ultra 256GB / 내부 2TB / 외부 저장 확장 가능이다. 현재 현물 사양이나 성능을 측정했다는 뜻은 아니다.
- 모델 상주 수, 양자화, context 길이, 동시성은 미결정. 기존 hosted fp4/fp8 결과를 로컬 값으로 환산하지 않는다.
- 후속 로컬 시험에서 exact model artifact/quantization·runtime version·context·동시성·메모리 압박·swap·cold/warm load·지연·실패를 함께 기록하는 안을 제안한다. 현재 구매 제품 추천이나 다운로드는 하지 않았다.
- 요약은 context 전달을 위한 view로 취급하고, 원 material evidence와 run history는 별도 보존한다. 저장 위치를 옮겨도 내용 identity와 참조가 유지되는지 실제 복원으로 검증해야 한다.
- 추가 공간이 있어도 held-out 접근 격리, 비밀정보 처리, 회복 가능성을 별도로 확인해야 한다. 무제한 raw trace 보존이나 private chain-of-thought 수집을 요구하지 않는다.
- 최종 보존 기간·외장/NAS 구성·공통 Artifact Store 변경은 이 문서에서 확정하지 않는다. 기존 Lab Automation과 충돌하는 수정이 필요하면 담당 Work/Chat으로 인계한다.

## Consistency / Impact

| Authority / 영역 | 이번 검토와의 관계 |
|---|---|
| Scientific Philosophy | Critic의 수정안도 근거에 의해 반박·수정 가능해야 한다는 원칙을 적용 |
| Research Methodology v1.2 / DR-0008 | 기존 coverage부터 확인. 실행 결함을 새 규칙 필요로 자동 승격하지 않음 |
| Evaluation Methodology v1.1 §8,10,11,13,14,16 | scope propagation, 과정/결과 구분, output별 평가, version-bound warrant, meta-evaluation을 적용 |
| ORS v1.0 §6–10 | 단축 표현이 canonical 내용을 대체하지 않음; exact state·metric meaning·qualified relation을 참조 |
| Model / Runtime | hosted 합성 결과에서 local 성능·역할 배치 결론으로 넘어가지 않음 |
| Other Labs | Math DailyPrice 및 Design 작업과 분리; 기존 산출물·코드 변경 없음 |
| Automation | 공통 runner/ledger 변경 없음. 검토 패키지만 생성 |
| Long-term scalability | context를 줄여도 근거가 복원되는지, 조회 부담이 이익보다 큰지 비교 후 판단 |

## Work Recommendation

**추천:** B를 후속 실험의 주된 후보로 두되 A/C를 비교군으로 유지한다. 첫 단계는 기존 오류와 조건 손실에 대한 좁은 replay이며 모델 우열·영구 역할·memory 학습으로 범위를 넓히지 않는다.

**추천 강도: Moderate.** 원문 조건 손실과 수정 중 새 오류가 실제 출력에서 확인됐고 기존 ORS로 설명 가능하다. 그러나 B의 효과·조회 비용은 아직 측정되지 않았다.

**추천이 틀릴 수 있는 조건:** 요약만으로도 동일한 중요한 오류를 일관되게 검출하고 적절히 보류하는 경우, B의 참조/조회 실패가 오류를 늘리는 경우, 작은 전체 입력을 전달하는 C가 더 단순하고 비용 차이도 무시할 수준인 경우, 효과가 전달 방식보다 모델·prompt 변화에 의해 설명되는 경우.

## Decision Needed From Chat / CEO

1. 다음 검증을 A/B/C의 근거 전달 비교로 제한하고, B를 실험 후보로 진행할 것인가?
2. 이 비교의 결과가 나오기 전까지 모델 상주 배치·영구 agent 역할·memory 학습의 채택 결정을 미룰 것인가?

추가 비용이 드는 호출이나 Mac 실행을 위한 구체 설정·예산·권한은 현재 패키지에 없다. 후속 실행 handoff에는 동결 input, 승인된 runtime, validation 범위, 비용 한도, stop condition을 명시해야 한다. CEO에게 개별 합성 기업 주장의 금융 사실 판정을 요청하지 않는다.

## References / Reproduction

- `inputs/`: 원 업로드 JSON 66개 (manifest 28 + output 38)
- `sources/calibration.json`: 기존 v0.8.1 case 원문; 본 검토에서 생성한 자료 아님
- `sources/run.py`, `topology_benchmark.py`, `overnight_family_benchmark.py`: 기존 동작 해석용 원 코드, 수정 없음. 이 코드를 실행할 필요 없음
- `authority_sources.json`: GitHub main에서 조회한 5개 상위 문서 본문. 특정 git commit을 검증한 snapshot이 아니며 내용 hash는 checksum 목록으로 고정
- `audit.py`: 이 패키지에서 새로 만든 offline inventory 도구
- `audit_results.json`: 실제 이번 audit 결과; 원 run manifest 대체 아님
- 재현: 패키지 디렉터리에서 `python3 audit.py` (기본 Python만 필요; network/model/DB 호출 없음)
- `SHA256SUMS`: 이 파일 자체를 제외한 모든 package 파일의 SHA-256
- 독립 재검토자는 F1/F2 의미 판단을 원문과 다시 대조할 수 있다. 이 보고서 자체도 공식 지식·정답표가 아니다.

상위 문서 위치: https://github.com/leftnadal/stock_vis/tree/main/research_lab

## Current Safety State

- push_performed: false
- merge_performed: false
- deploy_performed: false
- main_modified: false
- original_candidate_modified: false
- db_execution_performed: false
- paid_model_invocation_performed: false
- local_mac_benchmark_performed: false
- approval_required: 후속 비교 설계의 선택 및 구체 실행 범위; 공식 운영 구조 채택 및 promotion은 별도 승인
- 계속 가능한 Work: 기존 입력·평가 artifact 연결 보완, 승인된 방법론에 따른 read-only 검토
- 결정 전 보류: 전달 방식의 공통 규칙화, 영구 agent/model topology, 새로운 유료 실행, 학습·배포
