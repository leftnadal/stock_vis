#!/usr/bin/env python3
"""
OAG KB Queue Status CLI
큐레이션 큐 상태 확인 명령줄 인터페이스

사용법:
    python shared_kb/queue_status.py
    python shared_kb/queue_status.py --action add
    python shared_kb/queue_status.py --suggested-by investment-advisor
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 직접 실행 시 패키지 경로 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from shared_kb.queue import CurationQueue
else:
    from .queue import CurationQueue


def main():
    parser = argparse.ArgumentParser(
        description="OAG KB 큐레이션 큐 상태 확인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    python -m shared_kb.queue_status
    python -m shared_kb.queue_status --action add
    python -m shared_kb.queue_status --suggested-by backend --limit 5
        """
    )

    parser.add_argument(
        "--action", "-a",
        choices=["add", "update", "review", "merge"],
        help="액션 필터"
    )
    parser.add_argument(
        "--suggested-by", "-s",
        help="제안자 필터"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=20,
        help="결과 수 제한 (기본: 20)"
    )

    args = parser.parse_args()

    queue = CurationQueue()

    # 통계 출력
    stats = queue.get_stats()
    print("\n📋 큐레이션 큐 상태\n")
    print("=" * 60)
    print(f"총 대기 항목: {stats['total']}건")

    if stats['by_action']:
        actions_str = ", ".join([f"{a}: {c}" for a, c in stats['by_action'].items()])
        print(f"액션별: {actions_str}")

    if stats['by_suggested_by']:
        suggested_str = ", ".join([f"{s}: {c}" for s, c in stats['by_suggested_by'].items()])
        print(f"제안자별: {suggested_str}")

    print("=" * 60)

    # 목록 출력
    items = queue.list_all(
        action=args.action,
        suggested_by=args.suggested_by,
        limit=args.limit,
    )

    if not items:
        print("\n📭 대기 중인 항목이 없습니다.")
        return

    print(f"\n📝 대기 목록 ({len(items)}건)\n")

    for i, item in enumerate(items, 1):
        created_ago = datetime.now() - item.created_at
        if created_ago.days > 0:
            time_str = f"{created_ago.days}일 전"
        elif created_ago.seconds > 3600:
            time_str = f"{created_ago.seconds // 3600}시간 전"
        else:
            time_str = f"{created_ago.seconds // 60}분 전"

        priority_icon = "🔥" if item.priority >= 10 else "📌" if item.priority >= 5 else "📄"

        print(f"{priority_icon} [{i}] {item.knowledge_item.title}")
        print(f"      ID: {item.id[:8]}... | 액션: {item.action} | 우선순위: {item.priority}")
        print(f"      유형: {item.knowledge_item.knowledge_type.value} | 도메인: {item.knowledge_item.domain}")
        print(f"      제안자: {item.suggested_by} | {time_str}")
        if item.reason:
            print(f"      사유: {item.reason}")
        print()

    print("=" * 60)
    print("💡 큐레이션: python -m shared_kb.curate")


if __name__ == "__main__":
    main()
