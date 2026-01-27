#!/usr/bin/env python3
"""
OAG KB Search CLI
지식 검색 명령줄 인터페이스

사용법:
    python shared_kb/search.py "검색어"
    python shared_kb/search.py "PER" --type term --domain investment
    python shared_kb/search.py "Django" --limit 5
"""

import argparse
import sys
from typing import Optional
from pathlib import Path

# 직접 실행 시 패키지 경로 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from shared_kb.ontology_kb import OntologyKB
    from shared_kb.schema import KnowledgeType, ConfidenceLevel
else:
    from .ontology_kb import OntologyKB
    from .schema import KnowledgeType, ConfidenceLevel


def main():
    parser = argparse.ArgumentParser(
        description="OAG KB 지식 검색",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    python -m shared_kb.search "PER 지표"
    python -m shared_kb.search "RSI" --type metric
    python -m shared_kb.search "Django" --domain tech --limit 5
        """
    )

    parser.add_argument(
        "query",
        help="검색어"
    )
    parser.add_argument(
        "--type", "-t",
        choices=[t.value for t in KnowledgeType],
        help="지식 유형 필터"
    )
    parser.add_argument(
        "--domain", "-d",
        choices=["investment", "tech", "project", "general"],
        help="도메인 필터"
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="태그 필터 (여러 개 가능)"
    )
    parser.add_argument(
        "--confidence", "-c",
        choices=[c.value for c in ConfidenceLevel],
        help="최소 신뢰도"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="결과 수 제한 (기본: 10)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 출력"
    )

    args = parser.parse_args()

    try:
        kb = OntologyKB()

        # 검색 파라미터 준비
        knowledge_type = KnowledgeType(args.type) if args.type else None
        confidence_min = ConfidenceLevel(args.confidence) if args.confidence else None

        # 검색 실행
        results = kb.search(
            query=args.query,
            knowledge_type=knowledge_type,
            domain=args.domain,
            tags=args.tags,
            confidence_min=confidence_min,
            limit=args.limit,
        )

        # 결과 출력
        if not results:
            print(f"❌ '{args.query}'에 대한 검색 결과가 없습니다.")
            return

        print(f"\n🔍 '{args.query}' 검색 결과 ({len(results)}건)\n")
        print("=" * 60)

        for i, result in enumerate(results, 1):
            item = result.item
            score_bar = "█" * int(result.score * 10) + "░" * (10 - int(result.score * 10))

            print(f"\n[{i}] {item.title}")
            print(f"    유형: {item.knowledge_type.value} | 도메인: {item.domain}")
            print(f"    신뢰도: {item.confidence.value} | 점수: {score_bar} {result.score:.1%}")

            if args.verbose:
                print(f"    태그: {', '.join(item.tags) if item.tags else '-'}")
                print(f"    출처: {item.source or '-'}")
                print(f"    매칭: {', '.join(result.matched_fields)}")
                print(f"\n    {item.content[:200]}..." if len(item.content) > 200 else f"\n    {item.content}")
            else:
                # 간략 출력
                preview = item.content[:100].replace('\n', ' ')
                print(f"    {preview}...")

        print("\n" + "=" * 60)
        print(f"💡 상세 보기: --verbose 옵션 사용")

        kb.close()

    except ValueError as e:
        print(f"⚠️ 설정 오류: {e}")
        print("환경변수 NEO4J_URI, NEO4J_PASSWORD를 확인하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
