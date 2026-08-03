# SECB-GE-R1R5-SPEC — v2 프롬프트 델타 사양서 + 잔여 재정 2건

**소속:** SECB-GE-EXEC-1 · Phase B 프리플라이트 해소분
**성격:** 디렉터 사양서 (측정 대상 원문 — 창작·의역·보완 금지, 원문 그대로 커밋·삽입)
**커밋 위치:** `docs/features/chain-sight/SECB-GE-R1R5-SPEC.md` 원문 그대로 단독 커밋 → 실행순서 ①(정의서 개정)에서 이 파일을 참조(내용 복제 금지 — 단일 출처).

---

## §1. R1~R5 — v2 프롬프트 삽입 문구 (영문 원문 = 삽입 대상)

v1 프롬프트 구조는 그대로 보존하고, evidence 추출 지시 블록에 아래 5개 절을 **영문 원문 그대로** 삽입한다. `{MAX_EVIDENCE_CHARS}`는 CC가 evidence 필드 최대 길이에서 역산해 정수로 치환하고, 치환값을 최종 보고서에 명기한다. 이 외 어떤 문구 수정도 금지.

**R1 — Verbatim copy**
> The evidence_text field MUST be an exact, contiguous substring copied character-for-character from the filing text, preserving original punctuation, capitalization, numbers, symbols, and whitespace exactly as they appear in the source.

**R2 — Sentence-boundary extension (절단 교정 핵심)**
> Always extend evidence_text to complete sentence boundaries. Never cut a sentence in the middle: begin at the first character of the first sentence containing the supporting claim, and end at the terminal punctuation of the last sentence. If a sentence contains a list, include the entire list through the end of that sentence.

**R3 — Multi-sentence span**
> If the supporting claim spans multiple sentences, include the full contiguous span of complete sentences, up to a maximum of {MAX_EVIDENCE_CHARS} characters. If the span would exceed this limit, keep the sentence containing the core claim complete and drop whole sentences from the edges — never truncate mid-sentence.

**R4 — No paraphrase / no ellipsis**
> Do not paraphrase, normalize, abbreviate, translate, re-punctuate, or summarize. Do not insert ellipses ("...") and do not join non-adjacent fragments of text.

**R5 — Pre-output self-verification**
> Before returning your output, verify that every evidence_text value appears verbatim as a contiguous substring of the filing text. If any value fails this check, re-copy it directly from the source. Never output evidence_text that fails this verification.

## §2. 재정 — 동률 tiebreak (CC 상신 건 승인 + 보강)

- 선정 정렬 키를 3단으로 확정: **① tail desc → ② cites desc → ③ accession asc** (③은 완전 결정론 보장용 최종 키).
- CC가 적용한 `-tail, -cites`는 승인. 3단 키 재적용 시 선정 5건(AKAM·COR·CAT·ISRG·FIX)의 **구성이 바뀌지 않으면 재보고 불요**, 바뀌면 HALT 후 상신.
- 6위 이하 tail=15 후보의 존재는 문제 아님 — 결정론 키가 유일해를 보장하는 것으로 충분.

## §3. 재정 — 판정식 명확화 (paired 기준선)

- **1차(성공 판정) 기준선 = 표본 내 paired 비교**: 동일 5 filings에 대해
  - v1 tail율 = 86 / 121 = **71.07%** (사전 산출 완료분)
  - v2 tail율 = (v2 partial_match + not_found) / (v2 총 인용 수) — v2 자신의 분모 사용
  - v2 재추출은 인용 집합 자체가 달라질 수 있으므로 비교 단위는 **filing 수준 비율**이며, v2 총 인용 수·filing별 분포를 결과표에 병기한다.
- **전역 24.96%는 맥락 참고치일 뿐 판정 기준 아님** (tail 편중 표본이므로 직접 비교 무효).
- G-e는 **측정 세션**이다: 개선 폭을 정직하게 보고하는 것이 목적. v2 전면 배포 여부는 이 수치를 근거로 한 **별도 결정 사이클** — 이 세션에서 pass/fail 낙인이나 배포 착수를 하지 않는다.

## §4. 재개 승인

위 §1~§3 반영으로 프리플라이트 단일 차단 해소. 실행순서 완주 승인:
① 이 사양서 단독 커밋 → 정의서 개정(N=5·선정 5건·물리격리(b)·`var/secb_ge_v2_sample/`·본 사양서 참조) 단독 커밋
② PROMPT_V2 구현(R1~R5 원문 삽입·{MAX_EVIDENCE_CHARS} 치환) + 표본 커맨드(prod 읽기전용·파일 출력) + 채점 러너(g16 재사용)
③ 프리플라이트 재확인 — 토큰 비용 산정 ≤$5 포함
④ 실행 (gemini-2.5-flash · filing당 1콜 · 총 5콜 · 재시도는 5xx만 filing당 ≤1 · 절대 상한 10콜)
⑤ 집계(§3 판정식) + prod 사전/사후 스냅샷 동일 입증
⑥ Phase C — 추가 등록 2건: TASKQUEUE "v1 1768 vs marker 1751 — 17행 관찰" / 배달사고 원장 **#8: 비준문이 참조한 R1~R5 사양이 chat에만 존재, repo 미커밋** (귀책: 디렉터 — 비준문 복사 블록 밖에 사양 배치).

불변 유지: prod/dev DB 쓰기 0 · 표본 5 고정 · main 랜딩은 최종 보고 후 디렉터 확인 하에.
