# Working Record — Judgment–Outcome–Learning Feedback Loop / Checkpoint 03

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-18  
**Topic:** Judgment–Outcome–Learning Feedback Loop  
**Keywords:** prior-learning scan, retrieval cue, relevance screening, use-specific compatibility, positive outcome, authority boundary, historical fidelity, 검색 단서, 적용 가능성, 뜻밖의 성공, 검색과 적용 구분  
**Prior Record:** [Checkpoint 02](2026-09-18_judgment-outcome-learning-feedback-loop_02.md)  
**Official Authority:** [`../../research_lab/`](../../research_lab/) on `main`  
**Record Basis:** 현재 대화의 사용자 요청·공개 제안 이력, 이번에 확인한 GitHub 문서, 아래 외부 출처를 바탕으로 정리한 AI의 후속 제안. 실제 retrieval 성능 실험이나 Research Work calibration 결과가 아니다.

## Context

사용자는 중요한 분류를 제시 전에 여러 관점에서 점검하도록 프로젝트 지침을 변경했다고 알리고 다음 작업을 요청했다. 이는 아래 새 검색 조건이나 compatibility 설계의 최종 승인으로 해석하지 않는다.

Checkpoint 02의 미해결 질문을 이어서, 과거 경험을 찾을 이유와 찾은 기록을 사용할 근거가 혼합되어 있던 제안을 재검토한다. 이번 기록은 이전 문구를 덮어쓰지 않고 수정 이유를 보존한다.

## Authority Check

작업 시작 시 확인한 `main` commit은 `62a40ed5f4abdf1d86e4e4e8159877e4886799b4`이다. 이 상태에서 다음 관련 범위를 읽었다.

- [Scientific Philosophy v1.0](../../research_lab/00_foundation/scientific_philosophy.md): 현실 우선, 관찰과 현실의 구분, 원인과 결론을 조사 전에 확정하지 않음.
- [Terminology Governance v1.0](../../research_lab/01_methodology/terminology_governance.md): 표현보다 개념, 의미 변화의 명시, 미성숙한 class·구조의 성급한 고정 방지.
- [Research Methodology v1.2](../../research_lab/01_methodology/research_methodology.md): 비례적 연구·기록, 재검토와 변경의 구분, 구체적 retrieval·자동화 절차의 Non-Decision 경계.
- [Evaluation Methodology v1.1](../../research_lab/02_evaluation/evaluation_methodology.md), 특히 §§12–18: 목적·대상 상태·조건·기준·근거가 호환될 때 과거 평가 재사용, 구체적 compatibility algorithm은 미정, 평가와 후속 권한의 분리.
- [Operational Record Specification v1.0](../../research_lab/01_methodology/operational_record_specification.md), 특히 §§7–10: 기록과 평가·Evidence 역할의 구분, 맥락에 따른 Evidence–Claim 관계, 이력 보존.
- [Working Record README](../README.md), [INDEX](../INDEX.md), Checkpoint 02.

이하 제안은 기존 authority를 대체하는 분류·규칙·schema가 아니다.

## Current State — Corrections to Earlier Proposals

### 1. 검색 전에 과거 사례의 유사성을 이미 알아야 한다는 조건을 제거한다

`Materially similar judgment or problem structure`는 후보 기록을 읽은 뒤 관련성을 검토하는 질문으로는 유용하지만, 최초 검색을 시작할 필수 조건으로 쓰면 순환이 생긴다. 아직 모르는 과거 경험도 찾을 수 있어야 한다.

따라서 현재 문제, 선택할 행동, 중요한 불확실성, 관찰된 현상 등 현재 작업에서 알 수 있는 정보로 검색을 시작하는 방향을 제안한다. 알려진 과거 사례가 있으면 그것도 검색 단서로 사용할 수 있지만 필수는 아니다.

### 2. 실패 원인이나 실패 여부를 검색 전에 확정하지 않는다

`failure pattern`을 `failure mode`로 바꾼 것만으로 개선이 입증된 것은 아니다. 원인 미확정의 이상 결과, 반복적인 작은 문제, 뜻밖의 성공 또는 유용한 성과도 검색할 이유가 될 수 있다. 결과가 좋다는 이유로 원인이나 재현성을 이미 안다고 가정하지 않는다.

### 3. 다섯 항목은 상호배타적·완결적 taxonomy가 아니라 겹칠 수 있는 검색 단서다

특히 큰 영향을 갖는 결정은 다른 단서에도 동시에 해당할 수 있다. 여러 단서에 해당한다고 가산 점수를 만들거나 자동 변경 권한을 부여하지 않는다. `decision`을 `choice`로 바꾸는 것이 본질적인 해결책이라는 앞선 주장은 유지하지 않는다.

### 4. INDEX 선별과 원문 기반 적용 가능성 확인을 분리한다

INDEX는 관련 기록을 찾는 도구이지, 현재 사례에 대한 적용 가능성을 확정하는 근거가 아니다. `Compatibility Check → 원문 읽기`를 필수 순서로 두지 않는다. 필요한 원문과 근거를 읽은 뒤 의도한 용도에 맞는 적합성을 검토한다.

## Revised Retrieval Cues — AI Proposal, Not Yet Agreed

다음은 prior-learning scan을 고려할 대표적인 상황이다. 목록은 완결적 분류도 의무적 단계도 아니다.

| 단서 | 현재 작업에서 식별할 수 있는 상황 |
|---|---|
| 연구 설계·재개·중요한 다음 행동 선택 | 선행 시도, 대안, 선택 이유 또는 이전 제약을 확인하면 현재 판단에 도움이 될 가능성이 있다. 같은 과거 사례의 존재를 미리 알 필요는 없다. |
| 설명하거나 활용할 가치가 있는 중요한 관찰·성과·문제 | 원인 미확정의 실패·이상뿐 아니라 뜻밖의 성공, 반복되는 작은 이상, 활용할 가치가 있는 성과를 포함한다. |
| 가정·의존성·사용 목적·적용 조건의 중요한 변화 | 과거에 사용했던 판단이나 경험이 지금도 유효한지 확인할 이유가 생긴다. |
| 영향이 크거나 되돌리기 어려운 다음 행동 | 명백한 실패가 없어도 관련 이력과 제약을 더 신중히 확인할 이유가 있다. |
| 중요한 대안·설명·평가 사이의 판단이 갈려 추가 비교 근거가 필요함 | 사람/agent의 의견충돌뿐 아니라 한 연구자 안의 경쟁 설명, 상충하는 평가나 근거도 포함한다. 과거의 다수결로 결론을 정하지 않는다. |

공통 판단은 '과거 경험을 찾는 것이 지금의 중요한 질문, 대안, 가정 또는 다음 행동을 점검하는 데 도움이 될 수 있는가?'이다. 찾을 기록의 존재, 원인 또는 적용 가능성을 미리 증명할 필요는 없다.

작고 가역적인 표현 수정에는 매번 광범위한 검색을 요구하지 않는다. 그러나 사소한 작업이라는 이유로 관련된 기존 승인 경계나 알려진 중대한 제약을 무시하지 않는다.

관련 공식 authority의 선행 확인과 사용자의 명시적인 과거 기록 조회 요청은 위 단서를 충족해야만 수행하는 선택적 검색이 아니다. 사용자 조회 요청은 그 목적에 맞게 수행하고, 현재 공식 상태 판단이 필요하면 authority를 추가 확인한다.

## Candidate Flow

```text
현재 문제·다음 판단·중요한 불확실성을 설명
→ INDEX/metadata 또는 관련 검색으로 후보 탐색
→ 관련 가능성에 따라 필요한 기록·근거 범위를 읽음
→ 현재 사용 목적에 비추어 적용 가능성과 한계를 확인
→ 허용된 역할과 범위 안에서만 현재 판단에 반영
```

중요한 작업의 공식 authority 확인은 위 선택적 과거 경험 검색의 선행 의무로 유지한다. 새 발상을 위해 초기 framing을 먼저 할 수 있지만, 의무적 제약 확인이나 알려진 중대한 위험 정보까지 뒤로 미루는 고정 규칙은 제안하지 않는다.

INDEX에서 못 찾았다는 사실은 관련 기록이 존재하지 않는다는 증거가 아니다. 필요성과 위험에 따라 실제 record 검색이나 연결 이력 확인을 추가할 수 있으며, 그럼에도 없으면 '확인 범위에서 찾지 못함'으로 남긴다. 무제한 검색을 요구하지 않는다.

## Use-Specific Compatibility — Discussion Candidate

적용 가능성의 단위는 기록 하나의 일반적인 'compatible / incompatible' 판정이 아니라 **과거 기록 × 현재 상황 × 의도한 사용 목적**으로 보는 것이 더 적절하다는 제안이다.

새로운 점수표나 공식 profile을 만들지 않고 다음 질문으로 확인한다.

- 현재 무엇을 위해 읽는가: 아이디어 탐색, 위험 점검, 원인 주장에 대한 근거, 절차 선택 등.
- 과거 기록이 실제로 무엇을 뒷받침하는가: 당시 발언/제안, 실행 관찰, 과거 평가, 현재의 새 추론을 혼동하지 않는다. 필요한 원문·근거에 접근할 수 있는지도 확인한다.
- 중요한 적용 조건이 현재에도 맞는가: 대상, task, 입력·정보 접근, 방법·도구 버전, 평가 목적·기준, 가정·의존성의 차이 중 결론을 바꿀 수 있는 것을 검토한다. 모든 조건의 문자적 동일성을 요구하지 않는다.
- 해당 용도에 필요한 근거가 충분한가: 한 사례를 일반 원인으로 확대하지 않는다. 조건 미확인·반증·상충 근거·후속 수정이 있으면 그 한계를 유지한다.

사용할 수 있는 근거라는 판단과 실행/변경 권한은 별개다. 관련성이 높은 Working Record라도 지시 권한을 갖지 않는다. 공식 문서도 단순 경로가 아니라 실제 문서 지위·의미·범위·유효한 승인에 따라 사용한다. 앞서 제시했던 `Govern / Advise / Challenge`는 사용 역할을 설명하는 작업용 표현이지 세 개의 새 권위 등급이나 파일 종류별 고정 routing 규칙이 아니다.

### 설명용 가상 사례

과거 Working Record에 '압축된 자료를 받은 Critic이 새 오류를 냈고, 정보 손실이 원인일 수 있다'고 적혀 있다고 가정한다. 이는 이번 파일럿에서 추가로 확인된 사실이라는 주장이 아니다.

현재 Critic 설계에 이 기록을 사용하는 방식은 달라질 수 있다.

- '현재 입력에서도 중요한 근거가 누락되는가?'라는 점검 질문에는 활용할 수 있다.
- '현재 오류도 정보 손실 때문이다'라는 원인 결론에는, 현재 입력과 다른 설명을 확인하지 않은 상태에서 사용할 수 없다.
- 'Critic을 폐기하라'는 지시 또는 전반적인 architecture 변경 승인으로 사용할 수 없다.

같은 기록이라도 약한 탐색 단서에는 쓸 수 있고, 강한 인과·일반화 주장에는 불충분할 수 있다. 기록 내 제안이 사실 확인을 위한 새로운 조사를 유발하는 것과 그 제안을 공식 지식으로 채택하는 것은 다르다.

## Alternatives / Objections

- 이전 다섯 영어 표현만 다듬는 안: 현재 작업으로부터 관찰 가능한 시작 조건인지, 검색과 적용이 섞이지 않았는지 해결하지 못한다.
- 모든 작업에서 기록 전체를 항상 읽는 안: 누락 가능성을 줄일 수 있으나 불필요한 맥락과 검토 비용을 늘린다. 작은 작업에도 같은 부담을 강제하지 않는다.
- 실패나 이미 알려진 유사 사례가 있을 때만 검색하는 안: 새로운 문제의 선행 시도와 긍정적 경험을 놓칠 수 있다.
- INDEX 요약만으로 적용을 승인하는 안: 요약·색인 결손과 조건 생략에 취약하다.
- 호환성을 기록별 단일 점수로 정하는 안: 위험 점검과 원인 입증처럼 서로 다른 사용에 필요한 근거를 혼동한다.
- 어떤 Working Record도 현재 작업에 영향을 주지 못하게 하는 안: 기록 목적을 무력화한다. 탐색·반론·제한된 사실 확인의 역할은 가능하되, 규범적 권한과 근거 강도를 자동 부여하지 않는 편이 낫다.

## External References and Limits

[NASA Lessons Learned](https://www.nasa.gov/nasa-lessons-learned/) 설명은 검토된 lesson을 색인하고, 원래 사건과 권고를 보존하여 이후 업무 개선에 연결하는 접근을 소개한다. NASA의 reviewed lessons와 Stock_vis의 미승인 Working Record는 같은 지위가 아니다.

[Automatic Recall of Software Lessons Learned for Software Project Managers](https://arxiv.org/abs/2110.05261)의 초록은 현재 project artifact에서 검색 질의를 구성하는 접근을 설명한다. 현재 작업에서 query를 시작한다는 설계 방향의 참고이며, 해당 연구의 수치나 효과를 Stock_vis에 이전하지 않는다. 이번에는 초록과 bibliographic metadata만 확인했다.

외부 사례와 자체 반례 점검은 이 제안의 실제 retrieval 성능이나 다음 판단 개선 효과를 입증하지 않는다.

## Provisional Position

현재 문제에서 검색을 시작하고, 발견한 기록은 원문과 근거를 확인한 뒤 현재 사용 목적에 맞는 범위에서만 활용하자는 AI 제안이다. 사용자 지침 변경 보고는 보존하지만, 이번 수정안에 대한 사용자 동의나 Methodology 반영 승인까지 기록하지 않는다.

## Open Questions / Next

- 위 검색 단서가 실제로 너무 많은 검색 또는 중요한 기록의 누락을 일으키는지 아직 모른다.
- 필요한 원문 읽기 범위, 검색 중단 조건, INDEX 최신성 확인, 이후 수정·철회 기록의 탐색 방식은 실제 사용에 맞춰 검토해야 한다.
- 다음 논의는 현재 판단에 기록이 사용되었을 때 '무엇을 읽고 어떤 역할로 썼으며 무엇을 결론 내리지 않았는가'를 얼마나 가볍게 남길지에 초점을 둘 수 있다. 새로운 schema나 자동화를 지금 고정하지 않는다.

## Change Scope

이번 GitHub 변경은 이 Working Record 추가와 INDEX의 발견용 참조 갱신에 한정한다. 이전 checkpoint 본문, 공식 `research_lab/` 문서, 사용자 프로젝트 지침, Research Work의 baseline/gold annotation/validator/prompt/package는 변경하지 않는다. 별도 모델 실행, held-out 실행, memory admission, permanent architecture 채택은 수행하지 않는다.
