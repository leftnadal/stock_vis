# Working Record — Record Reconstruction Evaluation Target / Checkpoint 07

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-19  
**Topic:** Record Reconstruction Evaluation Target  
**Keywords:** reviewer preparation, coverage gap, excluded routes, schema validation, synthetic counterexamples, readiness, no inference calls, 검토 준비, 제외 경로, 출력 검사기, 실행 준비  
**Prior Record:** [Checkpoint 06](2026-09-18_record-reconstruction-evaluation-target_06.md)  
**Official Authority:** [`../../research_lab/`](../../research_lab/) on `main`  
**Record Basis:** 사용자의 Library Work 인계서 확인 요청, 인계서와 ZIP 원본 직접 열람, Chat의 로컬 무결성 검사와 합성 validator 반례 실행, 최신 GitHub 및 공식 provider 문서 확인. 독립 의미 감사 또는 reviewer 실행 결과가 아니다.

## Source and Current Position

Library에서 확인한 최신 관련 파일은 `Work_Chat_Handoff_ko(1).md`와 `StockVis_Gold_v021_Reviewer_Package_Preparation.zip`이다. 둘 다 2026-09-18 등록 자료다.

- Handoff file ID: `file_00000000024c82119b1c8dbe90ce48d3`.
- ZIP file ID: `file_0000000093a8821186b73be131ffe084`.
- 직접 계산한 ZIP SHA-256: `d7cd2b682480b6371bec452d47580b88d0e81310af9d8f5b115dd16ebf53d715`.
- Package root: `record_route_independent_review_prep_v021/`.
- Source batch: `8737355cc59549c6bee5424cde069d43`.

Work는 56개 활성 경로를 19/20/17로 나눈 reviewer 입력과 실행안의 준비 완료, 실제 reviewer/model 호출 0회를 보고했다. 이번 Chat은 준비물의 존재와 일부 검사를 직접 확인했지만, 아래 두 결함 때문에 승인 범위 전체를 충족한 실행 준비본으로 받아들이지는 않을 것을 권고한다. Gold v0.2.1과 40/3/0 판정은 이번에 재평가하지 않았다.

## Direct Checks Performed

- ARTIFACT_MANIFEST.json에 등록된 19개 파일의 hash 및 byte size: 19/19 일치.
- 세 final input과 visible pack의 JSON roundtrip, instruction 및 output schema 내용: 3/3 일치.
- Visible review items: 56개, 연결된 고유 frozen claim: 43개.
- Parent route disposition: 59개.
- Source payload canonical hash: 18/18 일치. 동일 source의 여러 bundle 내 사본을 독립 Evidence로 세지 않는다.
- 제공된 read-only `static_validate_v021.py` 실행: pass 재현.
- 아래 반례 실행 후 원본 ZIP 및 19개 등록 파일의 hash 동일성 확인.
- Chat의 reviewer/model/provider inference 호출: 0. Web/GitHub 조회와 로컬 코드 검사는 수행했다.

이 검사는 패키지 내부 무결성·구조 확인이다. 전체 upstream source archive와의 대조, 59개 경로의 독립 의미 감사, Gold 정확성 입증이 아니다. 제공된 전체 unittest suite는 setUpClass에서 부모 자료를 읽고 패키지를 다시 생성하므로 실행하지 않았다. 대신 보존된 바이트를 대상으로 별도의 읽기 전용 검사와 합성 반례를 실행했다.

## Finding 1 — Parent Mapping Is Not Reviewer Coverage

`build_review_package_v021.py`는 활성 Gold의 `sufficient_routes`만 visible item으로 구성한다. Protected mapping의 제외 3개, 교체 1개, 단순화 2개에 해당하는 옛 route signature 6개는 실제 visible 검토 항목에 없다.

- 제외: `2f9c8a41e6d54703-q1-c3 / manifest`, `a4d71e0b93c6425f-q1-c1 / manifest`, `a4d71e0b93c6425f-q1-c4 / plan`.
- 교체 전: `a4d71e0b93c6425f-q4-c4 / raw-plus-inference`.
- 단순화 전: `a4d71e0b93c6425f-q3-c1 / plan-plus-outcome`, `a4d71e0b93c6425f-q3-c3 / raw-plus-prior-limit`.

Checkpoint 06은 제외·단순화·교체된 판단도 대조할 수 있게 요구했다. 현재 59/59 mapping은 역사적 계보를 보존하지만, 별도 reviewer가 그 정정에 동의하는지 판단할 입력 coverage를 제공하지는 않는다. 56개만을 검토하는 데에도 제한된 가치는 있지만 원래 합의한 검토 범위와 같다고 보고해서는 안 된다.

보완 권고: 활성 후보와 정정 대조 항목을 구분해 추적하되, 최초 reviewer 입력에는 옛/새 판정이나 정정 이유를 노출하지 않는다. 실제 검토 항목 수와 Gold 활성 경로 수를 구분하고 묶음·토큰·비용을 다시 계산한다. 20/20/19 또는 19/20/17을 고정할 필요는 없다. 이 보완은 Gold 의미를 수정하거나 원 출력에 다른 유효 경로를 사후 대신 선택하는 작업이 아니다.

## Finding 2 — Output Validator Does Not Enforce Its Declared Schema

`validate_review_output_v021.py`의 `validate(result, pack)`에는 전체 JSON Schema 검사가 연결되어 있지 않다. 정상 synthetic fixture는 통과했지만 다음 각각의 잘못된 입력도 `errors=[]`로 통과했다.

| 합성 반례 | 제공 함수 | 동봉 schema에 대한 Draft202012 검증 |
|---|---|---|
| `exposure_declaration={}` | 오류 없음 | 필수항목 누락 5개 |
| `route_sufficiency=not_an_allowed_verdict` | 오류 없음 | enum 위반 1개 |
| 빈 `rationale` | 오류 없음 | minLength 위반 1개 |

이는 실제 모델 응답이 아니라 로컬 구조 반례다. 실제 provider가 이런 응답을 낸다는 주장이 아니며, 최종 runner에 별도 schema 검사가 결합됐다는 근거는 이 준비 패키지에서 확인하지 못했다.

보완 권고: 동봉 schema 전체 검증과 item/source coverage 검증을 최종 실행 경로에서 명시적으로 결합하고, 이 반례들을 negative fixture로 보존한다. Provider structured outputs 지원이 로컬 산출물 검증의 대체물은 아니다. 거절·중단·truncation도 별도 상태로 남긴다. 의미 평가를 결정론적 구조 검사로 대체하지 않는다.

## Execution Plan and External Verification

Work 제안은 `gpt-5.6-terra`, 3회/재시도 0, tools/retrieval 없음, reasoning medium, output 상한 8,192/pack, 예상 최대비용 $0.50 이내다. 사용자 실행 승인은 아니다.

2026-09-19 OpenAI 공식 모델 문서에서 모델 존재, medium 지원, 기본 input $2/output $12 per 1M 표시는 재확인했다. 문서는 272K를 넘는 context 요금 및 cache-write 1.25배 요금도 설명한다. 따라서 실제 endpoint/service/cache 설정과 수정 후 전체 request를 기준으로 최대비용을 계산해야 한다. 계정별 모델 접근권한, exact input tokens, 최종 요청 형식/설정은 미확인이다.

공식 데이터 문서는 기본 abuse monitoring logs와 endpoint별 application state, prompt caching 보관을 구분한다. 학습 미사용 또는 store=false만으로 모든 데이터 무보관을 뜻하지 않는다. 실제 계정·endpoint·cache 설정과 보관 조건, 외부 전달 범위를 실행 승인안에 명시해야 한다. 이번에는 private payload를 provider에 보내거나 token-count API를 호출하지 않았다.

- https://developers.openai.com/api/docs/models/gpt-5.6-terra
- https://developers.openai.com/api/docs/guides/your-data
- https://openai.com/api/

Approval record의 hash가 local evidence set에 없다는 보고도 있었다. 이번에 GitHub main의 Checkpoint 06 본문과 blob `cd5a6db0e301c5242d20d69d6d213acc6ff1cb39`를 확인했다. 실행안에 해당 승인 snapshot을 연결할 수 있으며, Git blob SHA와 파일 SHA-256을 혼동해서는 안 된다.

## Disposition and Scope

추천 상태는 ‘준비물 인수 및 일부 검사 재현 완료 / 두 준비 결함 보완 필요 / reviewer 호출 미승인’이다. 같은 준비 승인을 CEO에게 다시 요구하기보다 기존 Checkpoint 06의 패키지 결함 보완 범위에서 수정·검사하고, 최종 비용·데이터 조건을 담은 실행안을 반환하는 것이 맞다. 구체적인 reviewer 실행은 이후 별도 승인한다.

이번 요청은 인계서 확인이다. 새 reviewer/model 호출, Gold 의미 변경·재채점, 대상 prompt 튜닝, held-out, Methodology/Terminology 변경, memory admission, Work artifact promotion을 승인하거나 수행하지 않는다. 새로 합의한 ‘다음 연구 행동 제안’ 비교 방향도 별도 설계 논의이며 이번 검토의 실행 범위를 확장하지 않는다.

## Authority and Reproducibility

확인 시작 시 main은 `1e882bb54974df0397699b8e31abb81aacb6f7bd`다. 현재 승인 기록, Evaluation Methodology §§3.5–4.1, INDEX를 읽고, 앞선 상위/ORS/Working README 확인 ref `898c70ca4e3a66e6ad318b2784b7e33dfa15b445`와 비교해 변경이 Working INDEX 및 본류 Checkpoints 08–09뿐임을 확인했다. 공식 문서는 그 이후 변경되지 않았다.

로컬 재현 묶음은 `StockVis_Reviewer_Preparation_Chat_Checks_2026-09-19.zip`으로 생성했다. 검토 메모, `check_preparation.py`, `package_check_results.json`, `validator_counterexamples.json`을 포함한다. 검사 결과 JSON의 SHA-256은 `83d771d88789a28afb510b35a5dad416d9a51b7dfeedb923b1506b8f4cfb709c`이다. 이 기록은 재현용 묶음의 장기 원격 보관을 보장하지 않으며, 원 Library 패키지로 위 반례를 다시 구성할 수 있다.

이번 GitHub 변경은 비공식 작업 기록과 INDEX의 참조에 한정한다. 원 패키지·Gold·frozen output·승인 이력·공식 문서는 변경하지 않는다.
