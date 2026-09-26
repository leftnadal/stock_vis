# Working Record — Bootstrap Diagnostic Phase A / Checkpoint 02

**Status:** Working Record — Non-Authoritative; operational design and offline reference candidates, not execution authorization  
**Date:** 2026-09-26  
**Topic:** Bootstrap Diagnostic Phase A Input Visibility and Bounded Work Contract  
**Keywords:** bootstrap diagnostic, blind-first, post-reveal audit, selected route validity, batch barrier, frozen claims, exposure, source preservation, work autonomy, 입력 공개, 근거 경로, 사전 봉인, 실행 권한  
**Prior Record:** [Phase A source preflight / Checkpoint 01](2026-09-25_bootstrap-diagnostic-phase-a-preflight_01.md)  
**Related Working Record:** [Chat / Work role boundary](2026-09-20_research-chat-work-role-boundary_01.md)  
**Official Authority:** `leftnadal/stock_vis`, `main/research_lab/`  
**Official snapshot read:** `5aada595ac51f7f4f2d9c87480fd1589af159ee9`  
**Related Official Documents:** [Research Methodology](../../research_lab/01_methodology/research_methodology.md) §§8–9; [Evaluation Methodology](../../research_lab/02_evaluation/evaluation_methodology.md) §§4–6; [Operational Record Specification](../../research_lab/01_methodology/operational_record_specification.md) §3.  
**Record Basis:** 사용자가 직전 사전 점검·교정안 이후 다음 작업 진행을 요청했다. 그 교정 방향을 구체화한 checkpoint다. 아래 새 실행 세부안과 오프라인 후보를 공식 결정이나 새 모델/API 비용 승인으로 확대 해석하지 않는다. 기존 Working Record 체계에 따라 보존한다.

## Context / Current Position

대상은 `8737355cc59549c6bee5424cde069d43`의 개발용 frozen claim inventory 및 당시 basis annotation 출력이다. bundle별 14 / 13 / 16, 총 43개를 유지한다. 세 조건은 기초 실행 자료를 상당 부분 공유하므로 독립 표본 43개가 아니다. 여기서 Primary는 보존된 annotation 출력이며, 최초 자유형 복원 출력이나 새 평가자 호출이 아니다.

이번 작업은 직전 원본 점검을 다시 수행하거나 기존 transfer canary를 실행하는 것이 아니라, 원자료를 보존하면서 입력 공개·관찰·판정의 경계를 실행 가능한 설계 참고 자료로 만드는 것이다.

## Operational Design

### 1. Blind-first and selected-route audit are different observations

사전 단계는 나중 Primary annotation과 Gold를 보지 않고 frozen claim의 근거 경로를 제안하는 source-grounded assessment다. 아직 보지 않은 Primary의 오류를 검출했다고 주장하지 않는다.

공개 후 단계는 실제 Primary가 선택한 basis sets, evidence refs/locators 및 derivation이 claim의 내용·강도·범위를 지지하는지 검사한다. 목표는 `selected_route_validity`이며 가능한 모든 경로 또는 숨은 생성 사고 과정을 복원하는 시험이 아니다.

다른 두 경로가 모두 충분하면 오류가 아니다. 더 좋은 대체 경로를 찾아도 잘못된 원 경로를 사후 valid로 바꾸지 않는다. 원 경로 판정, 대안 경로, 수정 제안을 구분한다.

### 2. All blind responses precede any reveal

세 조건의 입력·prompt·output contract를 고정한 뒤 분리된 context에서 사전 평가한다. 세 사전 응답의 상태·입출력 hash·노출 기록을 모두 봉인한 뒤에만 공개 후 검사를 시작하는 batch barrier를 둔다.

공개 후 입력은 동일 조건의 원자료, 원 Primary annotation, 봉인된 사전 응답이다. 사전 응답은 덮어쓰지 않는다. 공개 후 발견을 사전 blind 발견으로 소급하지 않는다. 같은 reviewer의 공개 후 검사는 독립된 두 번째 검증으로 표현하지 않는다.

사전 응답에 unassessed가 남을 수 있다. 구조적 완료와 실질 평가 완료를 구분하며 미평가를 정상 판정으로 채우지 않는다. batch barrier는 production runtime에서 Work가 실제로 보장해야 한다.

### 3. Visibility boundary

두 단계 모두 frozen claim 문구·scope·원래 기록된 source refs와 record bundle을 유지한다. 근거로 쓰이는 과거 semantic assessment와 participant explanation도 provenance와 함께 유지한다. 원래 결손인 original request를 새로 찾아 채우지 않는다.

나중 Primary annotation은 사전 단계에서 숨기고 공개 후 단계에서만 제공한다. Gold, 사후 점수, 교정 이유, sentinel 정답 및 현재 대상에 대한 후속 판정은 두 reviewer 단계 모두에서 숨긴다. 최종 Work adjudication에서만 필요시 reference로 사용한다.

원래 source refs와 역할 문맥이 남으므로 완전 무유도 또는 pristine held-out이 아니다. 원문·명령·URL·과거 prompt는 evidence이지 실행 지시나 추가 접근 허가가 아니다. reviewer는 다른 bundle, GitHub, 대화 기억, 외부 검색에 접근하지 않는다. 지금 Chat은 과거 결과를 알고 있으므로 독립 reviewer로 간주하지 않는다.

### 4. Complete coverage without forced certainty

43개 전체에 lightweight source-grounded 확인 경로를 둔다. 불일치뿐 아니라 agreement/positive-control 항목도 확인하고 심층 검토는 영향과 불확실성에 비례시킨다.

오류 여부와 materiality는 별도 축이다. 오류가 확인됐어도 중요도는 unresolved일 수 있다. 아직 확정되지 않은 고위험 우려도 unresolved로 보존한다. 어떤 항목을 실제로 평가했는지 확인하지 않고 shared failure를 세지 않는다.

원 evidence를 먼저 대조하고 Gold 충돌은 양쪽 기록과 이유를 보존한다. 자가 검토를 independent semantic audit로 표현하지 않는다. 신규 판정을 이전 Gold나 이전 응답에 덮어쓰지 않는다. 비공개 사고 과정 대신 짧은 근거 연결 이유·필요 계산·한계를 남긴다.

## Bounded Execution Proposal — Not Approved Calls

두 단계를 모두 모델로 수행하는 기준안은 사전 3회와 조건부 공개 후 최대 3회, 총 최대 6회다. Primary 재호출, 자동 retry, 자동 추가 judge는 0회다. 세 사전 응답을 봉인하지 못하면 공개 후 호출은 시작하지 않는다.

provider/model, 설정, final request/schema, 최대 입력·출력, private payload 전송·보관 조건과 비용 상한은 아직 확정하지 않았다. 외부 token-count API도 전송 승인이 필요하면 같은 범위에 포함한다. 문자/byte 수를 exact tokens 또는 실제 과금으로 표현하지 않는다.

Work가 이 자원·전송·비용을 한 실행안으로 묶어 확인해야 한다. 기존 canary 승인을 새 Bootstrap 호출에 전용하지 않는다. 설계 동의나 오프라인 준비가 새 여섯 호출의 승인은 아니다. Phase A의 구조적 완료가 Phase B, permanent architecture, Methodology 변경, Knowledge/memory admission을 자동 승인하지 않는다.

## Concrete Offline Work Completed Here

기존 source ZIP에서 다음을 생성했다.

- 사전 model-visible 입력 후보 3개;
- 운영자 전용 공개 후 기본 자료 3개;
- 두 단계 diagnostic prompt, source/member 및 입력 hash manifest;
- 네트워크·모델 호출 없는 설계 참고 builder와 상태 전이 검사;
- Work 계약서와 미승인 실행 envelope 후보.

builder는 Gold archive를 열지 않는다. 원 frozen claim·scope·original source hints, record bundle, 의도된 결손 및 공개 후 원 Primary annotation은 보존한다.

자체 작성 기계적·합성 검사 36/36 통과. 처음 31개 검사 후 all-blind-first batch barrier의 반례 5개를 추가했다. 별도 출력 폴더에서 다시 빌드한 JSON 8/8은 byte-identical했다. 중간 31-check 개발 빌드는 최종 배포 패키지와 분리했다.

검사 예: 사전 Primary/Gold 주입, evidential prior assessment 삭제, 결손 요청 임의 보충, claim 누락·중복·강도변경, cross-bundle 혼합, Primary 사후 수정, receipt의 잘못된 hash, 미완료/노출된 사전 응답, 다른 조건 봉인 전 공개의 거절.

**한계:** 자체 작성 reference checker의 구조·일관성·상태 연결 시험이다. 새 semantic adjudication, 모델 행동, full production response schema, 실제 provider envelope, runtime/filesystem/context isolation, receipt 진위 또는 의미적 누출 완전 제거를 검증한 것이 아니다. 합성 응답은 모델 결과로 집계하지 않았다.

실제 model/provider 호출 0, 새 독립 reviewer 실행 0, 기존 transfer canary 실행 0이다. 새 static candidate가 있다고 실제 provider request가 동결된 것은 아니다. 공개 후 기본 자료에는 아직 실제 사전 응답이 없으며, Work가 이를 결합하고 최종 요청을 다시 hash해야 한다.

## Source and Deliverables

Source archive: `StockVis_Gold_v021_Route_Sufficiency_Audit_8737355c.zip`  
SHA-256: `507b23a8e389cb90a83a7cc557dafdaab596fa7364b70ead695de5b84863820c`

Input member: `record_reconstruction_development_calibration_v011/inputs/<bundle_id>.json`  
Primary member: `source_batch_8737355c/8737355cc59549c6bee5424cde069d43/<bundle_id>/parsed_final.json`

Conversation deliverable: `StockVis_Bootstrap_PhaseA_Visibility_v01_2026-09-26.zip`  
Detailed contract: `WORK_CONTRACT_ko.md`  
Static manifest SHA-256: `77477ea133f997902c3a472636060b94a0bffe7f64ca502671bbed881c396552`

The ZIP is operator/Work-only as a whole. It includes post-reveal Primary data; do not attach the whole archive to a blind reviewer. Raw source ZIP and protected Gold bytes are not included. The static payloads reuse supplied source content locally; no new provider transmission was performed.

## Existing Work and Next Unit

현재 읽을 수 있는 최신 transfer-canary 자료는 2026-09-22 준비본이다. 검색·최근 파일 metadata에서 그 이후 실제 실행 결과를 확인하지 못했다. 이를 아직 미실행이라고 단정하지 않는다. 해당 Work task를 취소·대체·중복 호출하지 않는다.

Work의 다음 단위는 final provider request/schema, 실행 격리·봉인, full acceptance checks 및 단일 자원/전송/비용 승인안을 묶은 준비다. 승인 범위 내 parser·packaging·serialization·validator 수정은 Work가 자체 해결하고, 연구 의미·권한·비교 유효성을 바꾸어야 할 때만 상신한다. 개별 사실 판정을 CEO에게 넘기지 않는다.

이 기록 저장은 Work 세션을 자동 실행하거나 background 작업을 예약한 것이 아니다.

## Interpretation Limits / Alternatives

한 번의 targeted audit만 하는 대안은 호출을 줄일 수 있지만 사전 독자 판단과 공개 후 변화가 구분되지 않는다. 현재 두 단계안은 이 관찰을 보존하기 위한 development design이며 우월성 입증이 아니다.

세 관련 개발 조건으로 blind-first의 일반적 우월성, 실제 투자·연구 품질 향상, 비용 대비 net benefit 또는 새 사례 일반화를 주장하지 않는다. 비교군을 실행하지 않았으며 43개를 독립 표본으로 취급하지 않는다. 결과는 pre-reveal 우려, post-reveal 발견, source-grounded 최종 판정, 미해결·미평가, 비용으로 나누어 보고한다.
