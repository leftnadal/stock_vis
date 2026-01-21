"""
Entity Extractor 사용 예제

사용자 질문에서 종목, 지표, 개념을 추출하고 정규화하는 예제입니다.
"""

import asyncio
import os
import sys

# Django 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from rag_analysis.services.entity_extractor import (
    EntityExtractor,
    EntityNormalizer
)


async def main():
    """Entity Extractor 사용 예제"""

    # 1. 인스턴스 생성
    extractor = EntityExtractor()
    normalizer = EntityNormalizer()

    # 2. 테스트 질문들
    questions = [
        "AAPL과 TSLA의 PER과 매출을 비교해줘",
        "삼성전자의 실적은 어때?",
        "엔비디아와 AMD 중 어느 것이 저평가되어 있나요?",
        "2024년 Q3 실적이 좋은 반도체 종목은?",
    ]

    print("=" * 80)
    print("Entity Extraction 예제")
    print("=" * 80)

    for i, question in enumerate(questions, 1):
        print(f"\n[질문 {i}] {question}")
        print("-" * 80)

        # 3. 엔티티 추출
        entities = await extractor.extract(question)

        print(f"추출된 엔티티:")
        print(f"  - 종목: {entities['stocks']}")
        print(f"  - 지표: {entities['metrics']}")
        print(f"  - 개념: {entities['concepts']}")
        print(f"  - 기간: {entities['timeframe']}")

        # 4. 정규화
        if entities['stocks']:
            normalized_stocks = normalizer.normalize_stocks(entities['stocks'])
            print(f"\n정규화된 종목: {normalized_stocks}")

        if entities['metrics']:
            normalized_metrics = normalizer.normalize_metrics(entities['metrics'])
            print(f"정규화된 지표: {normalized_metrics}")

    print("\n" + "=" * 80)
    print("완료")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
