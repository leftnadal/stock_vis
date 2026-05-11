# contracts/ — 에이전트 간 인터페이스 계약

> **스펙이 진실의 소스(Single Source of Truth)**
> 스펙과 구현이 불일치하면 구현 쪽을 수정한다.

## 파일 구조

| 파일 | 역할 | 소유 에이전트 |
|------|------|-------------|
| `chainsight-api.yaml` | Chain Sight API 스펙 (마켓 뷰 + Deep Dive) | @backend |
| `validation-api.yaml` | 1차 검증 API 스펙 | @backend |
| `sec-pipeline-api.yaml` | SEC Pipeline API 스펙 | @backend |
| `shared-types.ts` | 프론트엔드 공유 타입 | @frontend |

## 작성 규칙

1. **@backend가 API 변경 시**: 해당 `.yaml` 먼저 업데이트 → 코드 구현
2. **@frontend는 `.yaml` 기준으로**: 타입/API 호출 코드 작성
3. **@qa는 계약 정합성 검증**: `.yaml` vs 실제 응답 비교
4. **Breaking change**: TASKQUEUE.md에 의존 에이전트 알림 태스크 생성

## OpenAPI 스펙 형식

- OpenAPI 3.0.3
- 경로는 `/api/v1/` prefix 포함
- 응답 예시(`example`) 필수
- 에러 응답(400, 404) 포함
