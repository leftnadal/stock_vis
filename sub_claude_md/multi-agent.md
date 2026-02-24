# 멀티에이전트 시스템

## 에이전트 담당 영역

| 에이전트 | 담당 영역 |
|---------|----------|
| @backend | stocks/, users/, analysis/, API_request/, serverless/, news/, macro/ |
| @frontend | frontend/ 전체 |
| @rag-llm | rag_analysis/ 전체 |
| @infra | */tasks.py, */consumers.py, config/, docker/ |
| @qa | tests/, docs/ |
| @investment-advisor | 투자 도메인 콘텐츠 |

**참고**: serverless/ 앱은 백엔드 에이전트가 담당

## 워크플로우

1. Orchestrator가 작업 분배 미리보기 제공
2. 사용자 확인 후 에이전트 순차 호출
3. 에이전트 완료/도움 요청 시 사용자가 조율
