#!/usr/bin/env python3
"""
OAG KB Stats CLI
지식 베이스 통계 명령줄 인터페이스

사용법:
    python shared_kb/stats.py
    python shared_kb/stats.py --detailed
"""

import argparse
import sys
from pathlib import Path

# 직접 실행 시 패키지 경로 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from shared_kb.ontology_kb import OntologyKB
    from shared_kb.queue import CurationQueue
else:
    from .ontology_kb import OntologyKB
    from .queue import CurationQueue


def main():
    parser = argparse.ArgumentParser(
        description="OAG KB 통계 조회",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="상세 통계 출력"
    )
    parser.add_argument(
        "--queue-only", "-q",
        action="store_true",
        help="큐 통계만 출력"
    )

    args = parser.parse_args()

    print("\n📊 OAG KB 통계\n")
    print("=" * 50)

    # 큐 통계 (항상 표시)
    try:
        queue = CurationQueue()
        queue_stats = queue.get_stats()

        print("\n📋 큐레이션 큐")
        print(f"   총 대기: {queue_stats['total']}건")

        if queue_stats['by_action']:
            print("   액션별:")
            for action, count in queue_stats['by_action'].items():
                print(f"     - {action}: {count}건")

        if queue_stats['by_suggested_by']:
            print("   제안자별:")
            for suggested_by, count in queue_stats['by_suggested_by'].items():
                print(f"     - {suggested_by}: {count}건")

    except Exception as e:
        print(f"   ⚠️ 큐 통계 조회 실패: {e}")

    if args.queue_only:
        print("\n" + "=" * 50)
        return

    # KB 통계
    try:
        kb = OntologyKB()
        stats = kb.get_stats()

        print("\n📚 Knowledge Base")
        print(f"   총 지식: {stats['total_knowledge']}건")
        print(f"   관계 수: {stats['total_relationships']}개")

        if stats['by_type']:
            print("\n   유형별:")
            for ktype, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
                bar = "█" * min(count, 20)
                print(f"     {ktype:15} {bar} {count}")

        if stats['by_domain']:
            print("\n   도메인별:")
            for domain, count in sorted(stats['by_domain'].items(), key=lambda x: -x[1]):
                bar = "█" * min(count, 20)
                print(f"     {domain:15} {bar} {count}")

        if args.detailed and stats['by_confidence']:
            print("\n   신뢰도별:")
            confidence_order = ["verified", "high", "medium", "low", "deprecated"]
            for conf in confidence_order:
                count = stats['by_confidence'].get(conf, 0)
                if count > 0:
                    bar = "█" * min(count, 20)
                    print(f"     {conf:15} {bar} {count}")

        kb.close()

    except ValueError as e:
        print(f"\n⚠️ KB 연결 실패: {e}")
        print("   환경변수를 확인하세요: NEO4J_URI, NEO4J_PASSWORD")

    except Exception as e:
        print(f"\n❌ KB 통계 조회 실패: {e}")

    print("\n" + "=" * 50)
    print("💡 상세 통계: --detailed 옵션 사용")


if __name__ == "__main__":
    main()
