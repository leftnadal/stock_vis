# Working Record — Judgment–Outcome–Learning Feedback Loop / Checkpoint 04

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-18  
**Topic:** Judgment–Outcome–Learning Feedback Loop  
**Keywords:** prior-record use, declared use, observable revision, learning effect, retained judgment, non-use rationale, proportional records, 과거 기록 활용, 명시적 사용, 관찰된 변경, 학습 효과, 판단 유지, 비적용 이유  
**Prior Record:** [Checkpoint 03](2026-09-18_judgment-outcome-learning-feedback-loop_03.md)  
**Official Authority:** [`../../research_lab/`](../../research_lab/) on `main`  
**Related Official Documents:** [Operational Record Specification](../../research_lab/01_methodology/operational_record_specification.md), particularly §§3–5; [Evaluation Methodology](../../research_lab/02_evaluation/evaluation_methodology.md), §§13–14; [Research Methodology](../../research_lab/01_methodology/research_methodology.md), §§13–14; [Scientific Philosophy](../../research_lab/00_foundation/scientific_philosophy.md).  
**Record Basis:** 사용자의 이번 ‘다음 논의 하자’ 요청, 이 대화의 공개 합의·제안 이력, 아래 현재 GitHub 문서 확인 및 외부 일차 출처를 바탕으로 작성한 AI의 논의안. 새 실험이나 Work 실행 결과가 아니다.

## Context and Current Position

Research Work에는 Gold v0.2.1 reviewer 패키지 갱신과 한정된 실행안 준비가 승인되어 있다. 실제 reviewer/model 호출은 별도 승인 사항이다. 이번 확인에서 main INDEX도 이 경계를 유지하고 있었으며 새 준비 완료나 독립 검토 결과는 확인하지 않았다. 이번 논의로 Work의 범위를 바꾸지 않는다.

Chat 본류는 판단 당시 근거·실제 결과·사후 학습을 연결하는 시스템이다. Checkpoint 03은 현재 문제에서 검색을 시작하고, 원문 확인 후 현재 사용 목적에 맞는 범위에서 과거 기록을 활용하는 방향을 제안했다. 다음 미결정 사항은 그 활용을 얼마나 가볍게 기록할지였다.

## Main Proposal — Not Yet Agreed

별도 사용 장부나 새 Evaluation family를 만들기보다, 현재 작업의 기존 기록에서 중요한 과거 자료의 참조·명시한 용도·현재 판단·한계를 연결한다. 그 자료 덕분에 판단이 개선됐다는 효과 주장은 별도의 근거가 있을 때만 한다.

이는 프로젝트 전반에 강제할 새 schema나 이미 승인된 운영 정책이 아니다. 사용자가 다음 논의를 요청했다는 사실을 아래 세부안의 승인으로 해석하지 않는다.

## Distinctions That the Record Should Preserve

자료가 검색·전달되었다는 사실, 출력/결정문이 그 자료를 특정 용도로 인용한다는 사실, 실제 선택이나 산출물의 변경, 판단 개선에 대한 인과 주장은 서로 다르다. 이를 단계별 점수나 필수 상태 전이로 만들지 않는다.

- 읽기 도구의 성공이나 입력 포함은 자료 접근/노출을 보여줄 수 있지만 이해·정당한 활용·개선 효과를 입증하지 않는다.
- ‘이 기록을 보고 바꿨다’는 사람/AI의 설명은 명시된 선택 이유로 보존할 수 있다. 그것을 내부 생성 원인에 대한 독립 검증으로 승격하지 않는다.
- 결정문이나 산출물의 전후 차이는 그 차이를 뒷받침한다. 여러 조건이 바뀐 경우 특정 과거 기록만이 개선 원인이었다고 단정하지 않는다.
- 인용이 없거나 최종 선택이 같다는 사실만으로 실제 영향이 없었다고 확정하지 않는다. 확인 가능한 범위와 미확인 부분을 구분한다.

관측되지 않은 내부 사고과정이나 그럴듯한 가상의 초기 판단을 만들어 기록하지 않는다. 사전 판단이 기록되어 있지 않았다면 결손을 남기고 사후 해석의 작성 시점을 밝힌다.

## Minimal Information — Semantic Questions, Not Mandatory Fields

중요한 판단의 이유를 재구성하는 데 필요한 경우 아래 내용을 기존 문단·참조·평가 연결로 알아볼 수 있게 하는 안이다. 이미 기록된 정보는 복제하지 않는다.

1. 지금 어떤 질문이나 선택을 검토하고 있는가?
2. 과거 어느 기록의 어느 버전·관련 부분을 확인했는가? 원문 확인인지 요약/인계만 확인했는지도 중요할 때 구분한다. 과거 당시 버전을 고정해서 참조하되 현재 공식 권위의 유효 상태는 따로 확인한다.
3. 그 내용을 무엇에 쓰거나 적용하지 않기로 했으며, 현재 상황에 맞거나 맞지 않는 이유와 한계는 무엇인가? 탐색 단서·반론·근거·제약은 필요한 의미를 설명하기 위한 예시이지 새로운 고정 role taxonomy가 아니다.
4. 현재 판단 또는 제안은 무엇이며, 확인 가능한 변경/유지와 승인·실행 상태는 무엇인가? 필요하면 이후 확인할 결과나 재검토 조건을 연결한다. 실제 실행·평가가 나오면 그 기록을 후속 연결한다.

공식 규칙의 정당한 적용과 미승인 Working Record의 사용을 같은 권한으로 취급하지 않는다. 사용 기록 작성은 실행 승인, Knowledge/memory admission 또는 공식 규칙 변경이 아니다.

## Where the Information Belongs

Research Case가 이미 존재하면 next action/why it matters/design revision에 짧은 선택 이유와 참조를 연결한다. Case에 detailed evaluation rationale나 Evidence 원문을 모두 복사하지 않는다. 근거 충분성이나 효과에 대한 material 평가가 필요하면 해당 Evaluation Record가 그 평가를 맡고 Case에서는 참조한다.

아직 일반 설계 논의라면 승인된 research_working의 checkpoint로 보존할 수 있다. 기록을 남기기 위해 모든 논의를 정식 Research Case나 별도 Job으로 만들지 않는다. 근거의 원본/버전은 기존 위치에 두고 참조한다. INDEX는 찾는 데 필요한 주제·키워드·링크만 제공하며 실제 현재 정책이나 학습 효과의 권위자가 아니다.

## Materiality and Boundary Cases

- 실제로 선택/가정/대안/검토 순서를 바꾼 이유로 명시한 과거 기록은 연결할 가치가 있다.
- 과거 경고를 검토했지만 현재 조건이 다르거나 다른 근거가 우선하여 적용하지 않은 경우, 중요한 선택이라면 그 이유를 남긴다. 적용을 안 했다는 사실을 기록 검색의 실패로 세지 않는다.
- 판단을 유지하거나 행동을 보류한 경우도 이후 판단 복원에 중요하면 기록한다. 변화 건수를 학습 품질로 대체하지 않는다.
- 검색 결과가 많아도 단순 노출마다 수동 기록이나 별도 파일을 만들지 않는다. 중요한 미적용 이유, 실제 언급된 근거, 중대한 결손을 우선한다. 이는 기술 로그를 일괄 삭제하거나 보존 기간을 변경하는 지시가 아니다.
- 판단 이후 발견한 자료를 당시 근거처럼 소급 연결하지 않는다. 새 자료는 후속 검토의 근거로 연결한다.
- 관련 자료를 찾지 못하거나 원문을 확보하지 못하면 확인 범위를 남긴다. 찾아낸 정보가 없다는 것과 존재하지 않는다는 것은 구분한다.

## Illustrative Example — Not an Executed Case

새로운 평가 작업에서 ‘두 문서가 같은 결론을 적고 있으면 모두 필수 근거인가?’를 검토하는 가상 상황을 생각한다. 과거의 ‘각각 충분한 대안 경로와 함께 필요한 결합을 구분하자’는 Working Record를 읽고, 현재 자료에도 그 구분이 필요한지 점검하는 질문으로 사용할 수 있다. 실제 두 문서를 대조하기 전에는 현재 claim이 단일 경로로 충분하다고 결론 내리지 않는다.

짧은 기록에는 현재 질문, 과거 기록과 버전, 점검 질문으로 사용한다는 용도, 현재 근거 확인/제안 상태, 충분성·개선효과가 아직 미확인이라는 한계만 남길 수 있다. 실행 결과가 나오면 그 결과와 평가를 나중에 연결한다. 이 예시는 Work의 현재 gold/route가 추가 검증됐거나 변경됐다는 뜻이 아니다.

## Why Usage Is Not Yet Learning Effect

일상적인 사용 기록은 실제 개선을 검토할 사례를 찾는 데 도움이 될 수 있지만, 그 자체로 ‘이 기록 때문에 판단이 나아졌다’를 입증하지 않는다. 효과를 강하게 주장하려면 적절한 비교/개입 또는 해당 주장에 충분한 다른 근거가 필요하다. 어떤 설계가 적절한지는 별도 연구 질문이며 모든 사용에 두 번 실행하는 A/B 실험을 요구하지 않는다.

향후 효과 검토에서 잘된 활용 사례만 골라 보면 실제로 도움이 없거나 부담만 늘어난 경우를 놓칠 수 있다. 기록 활용 횟수나 판단 변경 횟수를 주요 성과로 고정하지 않고 중요한 누락·잘못된 적용·비용도 함께 검토할 여지를 둔다. 이번에는 평가 metric이나 비교 실험을 실행하지 않는다.

## Alternatives and Trade-offs

링크만 저장하면 가장 가볍지만 과거 자료가 어떤 판단의 어떤 근거였는지 알기 어렵다. 모든 검색과 중간 설명을 별도 장부에 저장하면 분량·중복·권위 혼동 위험이 커진다. 기존 판단 기록 안에 중요한 사용 이유와 한계를 연결하는 안은 두 극단 사이의 출발점이다.

하지만 이 안도 작성자가 그럴듯한 사용 이유를 사후 만들어내거나 중요한 미활용을 놓칠 수 있다. 따라서 실제 시점·출처·접근 범위·산출물과 연결하고, 자기 설명과 검증된 효과를 구분해야 한다. 선택적 기록이 실제 재구성에 충분한지와 기록 부담이 어느 정도인지는 아직 검증되지 않았다.

## Authority and External Check

이번 시작 시 확인한 main commit은 `78844666434a4c09c3cedf6c135cc7146ab4b995`다. 이 상태에서 INDEX, 본류 Checkpoint 03, ORS §§3–7 도입부, Evaluation Methodology §§13–14, Research Methodology §§13–14, Scientific Philosophy의 Reality 원칙, Working README를 읽었다. ORS blob은 `e10fddb99d0f44eb17d9d343930001cc71426719`, Evaluation은 `a731f70218bfea57f5c33ddfe9b462bc1233bda0`, Research Methodology는 `5abcfc43bc6d775805aaf064a7f6dd05b8b1336a`였다.

W3C PROV-DM §2.1.2는 입력 사용과 결과 생성만으로 특정 derivation이 성립하지는 않는다고 설명한다. https://www.w3.org/TR/prov-dm/

Anthropic의 Measuring faithfulness in Chain-of-Thought reasoning(2023) 초록은 서술된 reasoning에 개입하여 결과 의존성을 살피고, 연구한 모델/과제에서 차이가 있었다고 보고한다. 자기 설명만으로 실제 기여를 입증하지 말아야 한다는 설계 주의의 참고다. 이번 기록에서 Stock_vis 모델에 같은 효과가 관측됐다고 주장하지 않는다. https://www.anthropic.com/research/measuring-faithfulness-in-chain-of-thought-reasoning

외부 문서를 확인한 것은 새 Working Record 의미나 성능이 검증됐다는 뜻이 아니다. 비공개 사고과정 수집을 제안하지 않는다.

## Decision Scope / Next

이번에 제안하는 선택은 별도 장부·상태 분류를 만들기보다 기존 기록의 중요한 판단 이유에 과거 자료의 명시한 용도와 한계를 연결하는 방식으로 설계를 이어가는 것이다. 동의가 있더라도 모든 검색의 의무 기록, 새로운 schema/Methodology, runtime 자동화, 모델 호출, memory admission, reviewer 실행 승인을 뜻하지 않는다.

다음 실제 검토 지점은 이 정도 기록만으로 후속 검토자가 무엇을 읽고 어떤 판단을 했으며 무엇은 미확인인지 재구성할 수 있는지다. 지금은 논의안만 제시한다.

## Actual Change Scope

이번 GitHub 변경은 이 후속 비공식 Working Record와 INDEX의 발견용 참조 갱신에 한정한다. 기존 checkpoint, 공식 research_lab 문서, 프로젝트 지침, Research Work의 gold·validator·prompt·reviewer package·실행안을 변경하지 않는다. 별도 실험이나 reviewer/model 호출을 수행하지 않았다. 다른 Work의 준비 완료나 실행 결과를 추정하지 않는다.
