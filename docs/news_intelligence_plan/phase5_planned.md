# Phase 5: ML Production Mode (📋 계획)

## 기간
Week 11-12

## 목표
Shadow Mode 4주 검증 후 ML 가중치를 실제 운영에 적용.

## 구현 항목

### 1. Safety Gate 정식 가동
- 차단 활성화 (Shadow Mode에서 전환)
- Gate 통과 시 ML 가중치 → Engine C 자동 업데이트
- 실패 시 수동 가중치 유지 + 알림

### 2. LLM 정확도 측정
- 예측 방향 vs 실제 주가 변동 비교
- 주간 정확도 리포트 생성

### 3. 관계 품질 검수
- Neo4j 뉴스 이벤트 관계 노이즈 제거
- 비정상 패턴 감지 및 자동 정리

### 4. 성능 최적화
- 부하 테스트 실행
- 쿼리 최적화 (Django + Neo4j)
- 캐시 전략 재검토

## 의존성
- Phase 4 Shadow Mode 4주 완료
- 4주 연속 F1 > 0.55 달성
