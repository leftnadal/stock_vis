# Replay v0.2A.1 진단 해석 정정 Addendum

상태: Working review evidence. 기존 진단 기록을 수정하거나 삭제하지 않는다.

## 연결된 역사적 기록

- Raw diagnostic commit: `e0749bca62e594f98910e172a561a4a012c99c88`
- Counting repair commit: `4e8920860446ad817b34f6ad671593eb5e3fd58f`
- 기존 outcome label: `B_historical_string_body_not_fully_rendered`

## 확인된 결함

기존 local count `2`는 실제 token sequence 길이가 아니었다. 반환 객체는
`BatchEncoding`이고 최상위 key가 `input_ids`, `attention_mask` 두 개였기 때문에
`len(result)`가 2를 반환했다.

실제 token count는 `input_ids` sequence length로 읽어야 한다.

## 수정 후 관측

동일 historical request, 동일 tokenizer snapshot/revision, 동일 chat-template 호출 조건에서:

| reference | legacy top-level len | actual input_ids | provider reference |
|---|---:|---:|---:|
| short | 2 | 4,903 | 4,903 |
| original | 2 | 14,387 | 14,387 |

Counting-only exact gate는 한 번 실행되어 통과했다. 이 과정에서 tokenizer, template,
historical request 또는 input representation은 변경되지 않았다.

## 철회하는 해석

`2 / 2`를 historical string body가 렌더링되지 않았다는 증거로 사용하는 판단은 철회한다.
기존 B label과 원 artifact는 당시 실행 결과로 보존하지만 현재 해석으로 사용하지 않는다.

## 아직 확정하지 않는 사항

- 마지막 marker exact-substring 불일치의 정확한 원인
- provider 내부 preprocessing 전체
- local/provider count 일치가 provider 내부 normalization 전체의 동일성을 의미하는지

Trailing newline trimming은 가능한 설명일 뿐 확인된 사실로 기록하지 않는다.

## 현재 경계

이 addendum은 counting defect와 historical count reproduction만 정정한다. Evidence access,
context length의 인과효과, Critic topology 또는 permanent runtime architecture를 승인하지 않는다.
