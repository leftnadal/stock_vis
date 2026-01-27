#!/usr/bin/env python3
"""
OAG KB Add CLI
지식 추가 명령줄 인터페이스

사용법:
    python shared_kb/add.py --title "PER" --content "주가수익비율..." --type term
    python shared_kb/add.py --interactive
"""

import argparse
import sys
import uuid
from pathlib import Path

# 직접 실행 시 패키지 경로 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from shared_kb.ontology_kb import OntologyKB
    from shared_kb.queue import CurationQueue
    from shared_kb.schema import KnowledgeType, ConfidenceLevel, KnowledgeItem
else:
    from .ontology_kb import OntologyKB
    from .queue import CurationQueue
    from .schema import KnowledgeType, ConfidenceLevel, KnowledgeItem


def interactive_add(kb: OntologyKB = None, queue: CurationQueue = None, to_queue: bool = False):
    """대화형 지식 추가"""
    print("\n📝 OAG KB 지식 추가 (대화형 모드)\n")
    print("=" * 50)

    # 제목
    title = input("제목: ").strip()
    if not title:
        print("❌ 제목은 필수입니다.")
        return

    # 내용
    print("내용 (여러 줄 입력, 빈 줄로 종료):")
    content_lines = []
    while True:
        line = input()
        if line == "":
            break
        content_lines.append(line)
    content = "\n".join(content_lines)

    if not content:
        print("❌ 내용은 필수입니다.")
        return

    # 지식 유형
    print("\n지식 유형 선택:")
    types = list(KnowledgeType)
    for i, t in enumerate(types, 1):
        print(f"  {i}. {t.value}")
    type_idx = input("번호 선택: ").strip()
    try:
        knowledge_type = types[int(type_idx) - 1]
    except (ValueError, IndexError):
        knowledge_type = KnowledgeType.TERM

    # 도메인
    domains = ["investment", "tech", "project", "general"]
    print("\n도메인 선택:")
    for i, d in enumerate(domains, 1):
        print(f"  {i}. {d}")
    domain_idx = input("번호 선택 (기본: 4): ").strip()
    try:
        domain = domains[int(domain_idx) - 1]
    except (ValueError, IndexError):
        domain = "general"

    # 태그
    tags_input = input("\n태그 (쉼표로 구분): ").strip()
    tags = [t.strip() for t in tags_input.split(",")] if tags_input else []

    # 출처
    source = input("출처 (선택): ").strip() or None

    # 신뢰도
    confidences = list(ConfidenceLevel)
    print("\n신뢰도 선택:")
    for i, c in enumerate(confidences, 1):
        print(f"  {i}. {c.value}")
    conf_idx = input("번호 선택 (기본: 3-medium): ").strip()
    try:
        confidence = confidences[int(conf_idx) - 1]
    except (ValueError, IndexError):
        confidence = ConfidenceLevel.MEDIUM

    # 확인
    print("\n" + "=" * 50)
    print("📋 입력 확인:")
    print(f"  제목: {title}")
    print(f"  유형: {knowledge_type.value}")
    print(f"  도메인: {domain}")
    print(f"  태그: {', '.join(tags) if tags else '-'}")
    print(f"  출처: {source or '-'}")
    print(f"  신뢰도: {confidence.value}")
    print(f"  내용 미리보기: {content[:100]}...")

    confirm = input("\n저장하시겠습니까? (y/n): ").strip().lower()
    if confirm != "y":
        print("❌ 취소되었습니다.")
        return

    # 저장
    item = KnowledgeItem(
        id=str(uuid.uuid4()),
        title=title,
        content=content,
        knowledge_type=knowledge_type,
        tags=tags,
        source=source,
        confidence=confidence,
        domain=domain,
        created_by="user",
    )

    if to_queue:
        # 큐에 추가
        queue = queue or CurationQueue()
        queue_id = queue.add(
            title=title,
            content=content,
            knowledge_type=knowledge_type,
            tags=tags,
            source=source,
            domain=domain,
            suggested_by="user",
            reason="대화형 입력으로 추가",
        )
        print(f"\n✅ 큐에 추가되었습니다! (ID: {queue_id[:8]}...)")
        print("💡 큐레이터가 검토 후 KB에 추가합니다.")
    else:
        # KB에 직접 추가
        if not kb:
            print("❌ KB 연결이 필요합니다.")
            return
        knowledge_id = kb.add_knowledge(item)
        print(f"\n✅ KB에 추가되었습니다! (ID: {knowledge_id[:8]}...)")


def main():
    parser = argparse.ArgumentParser(
        description="OAG KB 지식 추가",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    # 대화형 모드
    python -m shared_kb.add --interactive

    # 직접 입력
    python -m shared_kb.add --title "PER" --content "주가수익비율" --type term

    # 큐에 추가 (검토 필요)
    python -m shared_kb.add --title "RSI" --content "상대강도지수" --type metric --to-queue
        """
    )

    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="대화형 모드"
    )
    parser.add_argument(
        "--title", "-t",
        help="지식 제목"
    )
    parser.add_argument(
        "--content", "-c",
        help="지식 내용"
    )
    parser.add_argument(
        "--type",
        choices=[t.value for t in KnowledgeType],
        default="term",
        help="지식 유형"
    )
    parser.add_argument(
        "--domain", "-d",
        choices=["investment", "tech", "project", "general"],
        default="general",
        help="도메인"
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="태그 (여러 개 가능)"
    )
    parser.add_argument(
        "--source", "-s",
        help="출처"
    )
    parser.add_argument(
        "--confidence",
        choices=[c.value for c in ConfidenceLevel],
        default="medium",
        help="신뢰도"
    )
    parser.add_argument(
        "--to-queue", "-q",
        action="store_true",
        help="KB 대신 큐에 추가 (검토 필요)"
    )

    args = parser.parse_args()

    # 대화형 모드
    if args.interactive:
        try:
            if args.to_queue:
                interactive_add(to_queue=True)
            else:
                kb = OntologyKB()
                interactive_add(kb=kb)
                kb.close()
        except ValueError as e:
            print(f"⚠️ KB 연결 실패: {e}")
            print("큐 모드로 전환합니다...")
            interactive_add(to_queue=True)
        return

    # 직접 입력 모드
    if not args.title or not args.content:
        print("❌ --title과 --content는 필수입니다.")
        print("또는 --interactive 옵션을 사용하세요.")
        sys.exit(1)

    item = KnowledgeItem(
        id=str(uuid.uuid4()),
        title=args.title,
        content=args.content,
        knowledge_type=KnowledgeType(args.type),
        tags=args.tags or [],
        source=args.source,
        confidence=ConfidenceLevel(args.confidence),
        domain=args.domain,
        created_by="cli",
    )

    if args.to_queue:
        queue = CurationQueue()
        queue_id = queue.add(
            title=args.title,
            content=args.content,
            knowledge_type=KnowledgeType(args.type),
            tags=args.tags or [],
            source=args.source,
            domain=args.domain,
            suggested_by="cli",
        )
        print(f"✅ 큐에 추가되었습니다! (ID: {queue_id[:8]}...)")
    else:
        try:
            kb = OntologyKB()
            knowledge_id = kb.add_knowledge(item)
            print(f"✅ KB에 추가되었습니다! (ID: {knowledge_id[:8]}...)")
            kb.close()
        except ValueError as e:
            print(f"⚠️ KB 연결 실패: {e}")
            print("--to-queue 옵션으로 큐에 추가하세요.")
            sys.exit(1)


if __name__ == "__main__":
    main()
