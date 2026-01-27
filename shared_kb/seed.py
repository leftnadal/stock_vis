#!/usr/bin/env python3
"""
OAG KB Seed Data
초기 시드 데이터 - 투자 용어 및 기술 패턴

사용법:
    python shared_kb/seed.py
    python shared_kb/seed.py --dry-run
"""

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path

# 직접 실행 시 패키지 경로 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from shared_kb.ontology_kb import OntologyKB
    from shared_kb.schema import KnowledgeType, ConfidenceLevel, KnowledgeItem
else:
    from .ontology_kb import OntologyKB
    from .schema import KnowledgeType, ConfidenceLevel, KnowledgeItem


# ==================== 투자 용어 시드 데이터 ====================

INVESTMENT_TERMS = [
    {
        "title": "PER (주가수익비율)",
        "content": """PER (Price Earnings Ratio, 주가수익비율)은 주가를 주당순이익(EPS)으로 나눈 값입니다.

**계산 공식**:
PER = 주가 / 주당순이익(EPS)

**해석**:
- PER 10 = 현재 이익 수준으로 투자금 회수에 10년 소요
- 낮을수록 저평가, 높을수록 고평가 가능성
- 동종업계 평균과 비교하여 판단

**주의사항**:
- 적자 기업은 PER 계산 불가 (음수 EPS)
- 성장주는 높은 PER이 정당화될 수 있음
- 업종별 평균 PER이 다름 (IT > 금융 > 유틸리티)""",
        "knowledge_type": KnowledgeType.METRIC,
        "tags": ["가치평가", "지표", "기본분석", "초급"],
        "domain": "investment",
        "confidence": ConfidenceLevel.VERIFIED,
    },
    {
        "title": "PBR (주가순자산비율)",
        "content": """PBR (Price Book-value Ratio, 주가순자산비율)은 주가를 주당순자산으로 나눈 값입니다.

**계산 공식**:
PBR = 주가 / 주당순자산(BPS)

**해석**:
- PBR 1 = 주가가 장부가치와 동일
- PBR < 1 = 청산가치보다 낮은 주가 (저평가 가능성)
- PBR > 1 = 프리미엄이 붙은 상태

**활용**:
- 자산가치 중심 평가에 적합
- 금융업, 제조업 평가에 많이 사용
- 무형자산이 많은 기업은 PBR이 높은 경향""",
        "knowledge_type": KnowledgeType.METRIC,
        "tags": ["가치평가", "지표", "기본분석", "초급"],
        "domain": "investment",
        "confidence": ConfidenceLevel.VERIFIED,
    },
    {
        "title": "RSI (상대강도지수)",
        "content": """RSI (Relative Strength Index, 상대강도지수)는 가격 변동의 강도를 측정하는 모멘텀 지표입니다.

**계산 공식**:
RSI = 100 - (100 / (1 + RS))
RS = 평균 상승폭 / 평균 하락폭 (일반적으로 14일 기준)

**해석**:
- RSI 70 이상: 과매수 구간 (하락 가능성)
- RSI 30 이하: 과매도 구간 (상승 가능성)
- RSI 50: 중립

**매매 신호**:
- 다이버전스: 가격과 RSI의 방향 불일치 시 추세 전환 가능
- 과매수/과매도 탈출 시점이 실제 매매 타이밍""",
        "knowledge_type": KnowledgeType.METRIC,
        "tags": ["기술분석", "지표", "모멘텀", "중급"],
        "domain": "investment",
        "confidence": ConfidenceLevel.VERIFIED,
    },
    {
        "title": "MACD (이동평균수렴확산)",
        "content": """MACD (Moving Average Convergence Divergence)는 두 이동평균선의 차이를 이용한 추세 지표입니다.

**구성요소**:
- MACD선: 12일 EMA - 26일 EMA
- 시그널선: MACD의 9일 EMA
- 히스토그램: MACD선 - 시그널선

**매매 신호**:
- 골든크로스: MACD가 시그널선 상향돌파 → 매수
- 데드크로스: MACD가 시그널선 하향돌파 → 매도
- 제로선 돌파: 추세 전환 확인

**주의사항**:
- 후행성 지표 (늦은 신호)
- 횡보장에서는 잦은 거짓 신호 발생""",
        "knowledge_type": KnowledgeType.METRIC,
        "tags": ["기술분석", "지표", "추세", "중급"],
        "domain": "investment",
        "confidence": ConfidenceLevel.VERIFIED,
    },
    {
        "title": "분산투자 (Diversification)",
        "content": """분산투자는 여러 자산에 투자하여 리스크를 줄이는 전략입니다.

**핵심 원칙**:
- "달걀을 한 바구니에 담지 마라"
- 상관관계가 낮은 자산들로 구성
- 비체계적 리스크 감소 효과

**분산 방법**:
1. 자산군 분산: 주식, 채권, 부동산, 원자재
2. 지역 분산: 국내, 선진국, 신흥국
3. 섹터 분산: IT, 금융, 헬스케어, 에너지
4. 시간 분산: 적립식 투자 (DCA)

**한계**:
- 체계적 리스크(시장 리스크)는 분산으로 제거 불가
- 과도한 분산은 수익률 희석""",
        "knowledge_type": KnowledgeType.STRATEGY,
        "tags": ["포트폴리오", "리스크관리", "전략", "초급"],
        "domain": "investment",
        "confidence": ConfidenceLevel.VERIFIED,
    },
]

# ==================== 기술 패턴 시드 데이터 ====================

TECH_PATTERNS = [
    {
        "title": "Django 3계층 아키텍처",
        "content": """Stock-Vis 프로젝트의 Django 백엔드 3계층 아키텍처:

**구조**:
View → Processor → Service → Model

**1. View (뷰 계층)**:
- HTTP 요청/응답 처리
- 인증/권한 검사
- 입력 유효성 검증
- 적절한 Service 메서드 호출

**2. Processor (처리 계층)**:
- 외부 API 응답 변환
- 데이터 정규화/정제
- 비즈니스 로직 없음 (순수 변환)
- 반드시 return문 포함!

**3. Service (서비스 계층)**:
- 비즈니스 로직 구현
- 트랜잭션 관리
- 여러 모델 조합 작업
- 캐싱 로직

**장점**:
- 관심사 분리로 테스트 용이
- 재사용성 향상
- 유지보수 편의성""",
        "knowledge_type": KnowledgeType.ARCHITECTURE,
        "tags": ["Django", "아키텍처", "백엔드", "패턴"],
        "domain": "tech",
        "confidence": ConfidenceLevel.VERIFIED,
    },
    {
        "title": "Alpha Vantage Rate Limiting",
        "content": """Alpha Vantage API Rate Limiting 처리 패턴:

**제한 사항**:
- 무료 티어: 5 calls/분, 500 calls/일
- 프리미엄: 75 calls/분

**구현 패턴**:
```python
import time

def rate_limited_call(api_func, *args, **kwargs):
    result = api_func(*args, **kwargs)
    time.sleep(12)  # 요청 간 12초 대기
    return result
```

**배치 처리**:
```python
def batch_update(symbols, batch_size=5):
    for batch in chunks(symbols, batch_size):
        for symbol in batch:
            update_stock(symbol)
            time.sleep(12)
```

**에러 응답 처리**:
- `{"Note": "..."}`: Rate limit 초과
- `{"Error Message": "..."}`: API 오류
- `{}`: 데이터 없음""",
        "knowledge_type": KnowledgeType.API,
        "tags": ["API", "Alpha Vantage", "Rate Limiting", "백엔드"],
        "domain": "tech",
        "confidence": ConfidenceLevel.VERIFIED,
    },
    {
        "title": "React Hooks 규칙",
        "content": """React Hooks 사용 시 반드시 지켜야 할 규칙:

**핵심 규칙**:
1. 최상위에서만 Hook 호출
2. React 함수 내에서만 Hook 호출

**잘못된 예시**:
```typescript
// ❌ 조건문 안에서 Hook 호출
if (loading) return <Spinner />;
const data = useMemo(() => process(raw), [raw]);

// ❌ 반복문 안에서 Hook 호출
items.forEach(item => {
  const [state, setState] = useState(item);
});
```

**올바른 예시**:
```typescript
// ✅ 조건문 전에 모든 Hook 호출
const data = useMemo(() => process(raw), [raw]);
if (loading) return <Spinner />;

// ✅ 배열 상태로 관리
const [items, setItems] = useState(initialItems);
```

**이유**:
- React는 Hook 호출 순서로 상태를 추적
- 순서가 바뀌면 상태가 엉킴""",
        "knowledge_type": KnowledgeType.PATTERN,
        "tags": ["React", "Hooks", "프론트엔드", "규칙"],
        "domain": "tech",
        "confidence": ConfidenceLevel.VERIFIED,
    },
]


def create_seed_items():
    """시드 데이터 아이템 생성"""
    items = []

    for data in INVESTMENT_TERMS + TECH_PATTERNS:
        item = KnowledgeItem(
            id=str(uuid.uuid4()),
            title=data["title"],
            content=data["content"],
            knowledge_type=data["knowledge_type"],
            tags=data.get("tags", []),
            source="Stock-Vis Seed Data",
            confidence=data.get("confidence", ConfidenceLevel.VERIFIED),
            domain=data.get("domain", "general"),
            created_by="seed",
        )
        items.append(item)

    return items


def main():
    parser = argparse.ArgumentParser(
        description="OAG KB 시드 데이터 생성",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 저장 없이 미리보기만"
    )

    args = parser.parse_args()

    items = create_seed_items()

    print("\n🌱 OAG KB 시드 데이터\n")
    print("=" * 60)
    print(f"총 {len(items)}개 항목")
    print(f"  - 투자 용어: {len(INVESTMENT_TERMS)}개")
    print(f"  - 기술 패턴: {len(TECH_PATTERNS)}개")
    print("=" * 60)

    if args.dry_run:
        print("\n📋 미리보기 (--dry-run 모드):\n")
        for item in items:
            print(f"  [{item.knowledge_type.value}] {item.title}")
            print(f"      도메인: {item.domain}, 태그: {', '.join(item.tags[:3])}...")
        print("\n💡 실제 저장: --dry-run 옵션 제거")
        return

    try:
        kb = OntologyKB()

        print("\n📥 KB에 저장 중...\n")
        for item in items:
            try:
                knowledge_id = kb.add_knowledge(item)
                print(f"  ✅ {item.title} (ID: {knowledge_id[:8]}...)")
            except Exception as e:
                print(f"  ❌ {item.title}: {e}")

        kb.close()
        print("\n✅ 시드 데이터 저장 완료!")

    except ValueError as e:
        print(f"\n❌ KB 연결 실패: {e}")
        print("환경변수를 확인하세요: NEO4J_URI, NEO4J_PASSWORD")


if __name__ == "__main__":
    main()
