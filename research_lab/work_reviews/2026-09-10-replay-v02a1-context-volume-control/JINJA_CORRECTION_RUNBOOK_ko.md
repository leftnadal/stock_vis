# Replay v0.2A.1 Jinja correction 실행 경계

상태: CEO-approved limited correction execution. Working review evidence이며
Methodology, runtime, topology 또는 promotion 승인이 아니다.

## 고정 dependency

- 기존: `transformers==5.16.1`, `tokenizers==0.23.2`
- correction: `Jinja2==3.1.6`, `MarkupSafe==3.0.2`
- correction source: official PyPI only
- correction acquisition: exact wheel 2개를 받는 1회 명령

기존 `official-pinned-001` 환경, wheel, tokenizer snapshot과 Git evidence는 수정하지
않는다. 기존 wheel 27개와 tokenizer asset 5개를 hash로 재검증하고 새 격리 환경에
재사용한다.

## 단계적 중단 조건

1. 준비 checksum 또는 회귀 테스트 실패: acquisition/model call 전에 중단
2. 기존 artifact identity/hash 불일치: acquisition/model call 전에 중단
3. correction wheel 획득·offline install·exact freeze 실패: model call 0회로 기록
4. historical provider count `4,903`과 `14,387` 중 하나라도 불일치: model call 0회
5. gate 성공 시에만 S-short와 S-long-control을 각각 1회, 총 최대 2회 실행
6. retry와 selective rerun은 하지 않음

Gate evidence를 먼저 별도 commit/push하고, execution evidence는 추가 파일로만 두 번째
commit/push한다. 기존 gate checksum과 historical artifact는 덮어쓰지 않는다.

## 비승인 범위

- 다른 Jinja/tokenizer/Transformers 조합 탐색
- 문자·byte 근사
- model weight 다운로드
- v0.2B 또는 held-out 실행
- main merge, deploy, Approved/Effective promotion
- Methodology, permanent runtime, role, memory architecture 채택

