# Working Record — Record Reconstruction Evaluation Target / Checkpoint 09

**Status:** Working Record — Non-Authoritative  
**Date:** 2026-09-19  
**Topic:** Record Reconstruction Evaluation Target  
**Keywords:** reviewer preparation, 0.2.1r1, coverage, response acceptance, fail closed, schema type error, no-call handoff, 검토 입력, 실패 상태, 응답 수용, 자료형 오류  
**Prior Record:** [Checkpoint 08](2026-09-19_record-reconstruction-evaluation-target_08.md)  
**Official Authority:** `leftnadal/stock_vis`, `main/research_lab/`  
**Record Basis:** 사용자의 Library Work 인계 확인 및 답신 작성 요청, 원 인계·ZIP 열람, Chat의 오프라인 코드·무결성·합성 반례 검사. 독립 의미 감사나 실제 reviewer 실행 결과가 아니다.

## 현재 위치와 인수 자료

기존 no-call 준비 승인 및 Checkpoint 08의 수리 범위에서 후속 준비본 0.2.1r1을 검토했다. Gold v0.2.1의 의미와 40/3/0, frozen output은 이번에 재평가하지 않는다. 별도 ‘다음 연구 행동’ 효용 비교도 진행하지 않는다.

- Source batch: `8737355cc59549c6bee5424cde069d43`; previous: `6f739c4557c84627993657509a9983d0`.
- Library handoff: `Work_Chat_Handoff_ko.md`, file `file_00000000a1c081f9888311e44a8a717c`, version 1.
- Library ZIP: `StockVis_Gold_v021_Reviewer_Preparation_Repair_v021r1.zip`, file `file_000000008ed081f9978a30fac0462801`.
- 직접 계산한 ZIP SHA-256: `64b4f92f3c1f0cae3925ba1944b31180356dd0f8f32f5c1ecbd4e7dca0064338`.

## 확인하여 인수한 수정

등록 파일 해시·크기 23/23 일치, final-input/visible-pack roundtrip 3/3 일치, 62개 고유 검토 항목(20/20/22), 활성 56개·옛 variant 6개·부모 이력 59개·고유 claim 43개를 확인했다. 옛 variant를 하나씩 빼는 6개 반례는 모두 coverage 실패를 검출했다. 원래 지적한 빈 exposure, 허용되지 않은 판정값, 빈 rationale 세 반례도 최종 수용 함수에서 거절됐다. 이 수정은 인수하며 다시 요구하지 않는다.

동봉 정적 검사 함수의 통과와 12개 unittest 본문의 통과를 재현했다. 단, 원 setUpClass는 패키지를 재생성하므로 원본 파일은 변경하지 않고 setup만 메모리에서 frozen 파일 읽기로 대체했다. 원래 build·재생성 경로 전체의 통과를 주장하지 않는다.

부모 준비본의 출력 schema와 source 항목 18개는 동일했다. 기존 item 56개에는 referenceable_source_ids가 추가됐으며 claim/scope/route 등의 다른 변경은 없었다. 검사 전후 모든 패키지 파일 해시가 동일했다. 원 Gold와 전체 upstream 배치 바이트는 이 ZIP에 없으므로 보고된 Gold 해시·전체 source-batch 검사까지 재현했다고 말하지 않는다.

## 잔여 A — 완료 상태를 명시적으로 확인하지 않는 수용 경계

`review_response_acceptance_v021r1.py::accept_response`에 정상 fixture JSON, transport_status=complete, truncated=false를 주고 finish_reason을 refusal, content_filter, incomplete, max_output_tokens, None, unknown으로 바꾸면 accepted_semantic_result가 반환됐다. transport_status 자체를 refused/error 등으로 바꾸면 거절된다.

이는 함수 경계의 합성 반례이며 실제 Responses API가 이런 필드 조합을 보냈다는 관측이 아니다. 실제 provider envelope의 status/error/incomplete_details/typed refusal을 올바르게 변환하는 adapter는 동봉 자료에서 확인하지 못했다. 정상 전송과 정상 의미 완료를 구분하고, 명시된 허용 완료 상태만 수용해야 한다. 이미 다른 adapter가 보장한다면 그 연결과 mock fixture로 대조하면 된다. 본문의 단어 검색으로 refusal을 판정하거나 미확인 상태를 기본 성공으로 채우지 않는다.

## 잔여 B — Schema 오류 뒤의 자료형 예외

`reviews[0].item_id=[]`와 `reviews[0].missing_source_ids=[{}]`는 schema에서 자료형 오류가 발견된 뒤에도 set/dict coverage 검사를 계속해 각각 unhashable list/dict TypeError를 발생시켰다. 구조화된 결과가 반환되지 않았다. 이는 오답의 성공 수용이 아니라 실패 기록을 통제해서 반환하지 못하는 문제다.

Schema 실패 시 안전 반환 또는 자료형 안전성이 있는 후속 검사를 적용하고, 원 응답 해시·구조 오류를 남겨야 한다. 특정 외부 라이브러리 설치나 schema 완화는 요구하지 않는다. 정상 및 기존 반례를 유지하면서 위 잔여 경계만 보완한다.

## 실행안 대조와 한계

현재 final_inputs는 messages/response_format_contract를 가진 입력 snapshot이다. 실제 Responses 요청으로의 변환과 응답 envelope 수용 경로를 오프라인에서 연결하고 정확한 요청의 해시·설정·coverage를 확인해야 한다. 이를 별도 Gold 수정이나 모델 실행으로 확대하지 않는다.

Work의 계획용 입력 181,276 및 최대 출력 24,576 tokens, 기본 input/output 요금 가정에서 $0.657464 산술을 재현했다. 입력 전체에 1.25배 cache-write가 적용되는 민감도 계산은 $0.748102로, 제안 $0.75보다 $0.001898 낮다. 초과했다고 주장하지 않지만 exact count·실제 설정이 없으므로 확정 상한 보장도 아니다. 모델 후보·요금은 공개 공식 문서에서 확인했으며 계정 접근권한과 조직 설정은 확인하지 않았다.

향후 제안된 추론 3회와 pack별 계수 요청 최대 3회는 구분해야 한다. 양쪽 모두 private payload 전송이며 이번에는 어느 쪽도 승인·실행하지 않는다. store=false와 전체 무보관을 같게 보지 않고 실제 endpoint/cache/조직 조건을 후속 CEO 결정안에 명시한다.

## 답신과 다음 범위

답신은 완료된 coverage/기존 schema 반례 수정을 인수하고 위 두 응답 수용 문제와 실제 요청·응답 연결만 기존 준비 범위에서 보완하도록 한다. 새 의미 감사, Gold 재작성·재채점, 대상 prompt 교정은 요구하지 않는다. 실제 reviewer·계수 API·private payload 전송·비용 및 보관 조건은 계속 별도 승인 사항이다. 사용자 요청은 검토·답신 작성이지 실제 호출 승인으로 해석하지 않는다.

전달 파일: `Chat_to_Work_Reviewer_v021r1_Review_2026-09-19.md`; SHA-256 `f5f9d7a93f4256fd5e415fb8c6577879d305428bff3ada327e7eb575b6b41f20`.
재현 ZIP: `StockVis_Reviewer_v021r1_Chat_Review_2026-09-19.zip`; SHA-256 `45871cac27a0458fc7ed7cec64ce0837674635dca7e745667773e80274a81c4a`.
포함: 답신, verify_r1.py, check_results.json, parent_compare_and_cost.json, README, SHA256SUMS. 원 private source payload는 넣지 않았다. 결과 JSON SHA-256은 `abe7a4a854552279f5516660fc1980aa0b6184bccbb79c93eacfbcc2cb1eb602`다. 파일의 장기 원격 가용성을 이 기록만으로 보장하지 않는다.

## Authority / Actual Actions

시작 및 쓰기 전 main은 `0eb66df5c8faa84738dad5f49e57b1038a269d93`였다. 현재 준비 수리 Checkpoint 08, Working README/INDEX, Evaluation Methodology §§3.5–4.1 및 Research Methodology §§14.1–15를 읽었다. 공개 OpenAI 모델·요금·Responses migration·structured outputs·token counting·prompt caching·data controls 문서를 확인했다. 이전에 읽은 상위 의미를 재정의하거나 새 공식 기준을 만들지 않았다.

공식 비교 출처: https://developers.openai.com/api/docs/models/gpt-5.6-terra ; https://developers.openai.com/api/docs/guides/structured-outputs ; https://developers.openai.com/api/docs/guides/migrate-to-responses ; https://developers.openai.com/api/docs/guides/token-counting ; https://developers.openai.com/api/docs/guides/prompt-caching ; https://developers.openai.com/api/docs/guides/your-data .

이번 실행은 읽기·로컬 검사·합성 반례·답신 및 재현 묶음 작성이다. GitHub 변경은 이 비공식 기록과 INDEX 포인터에 한정한다. 원 Work 패키지, Gold, frozen output, 공식 문서, 별도 본류 설계는 수정하지 않는다. 실제 reviewer/모델/계수 API 호출·private payload provider 전송·새 실험·held-out·memory admission·promotion은 없다.
