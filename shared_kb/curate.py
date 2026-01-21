#!/usr/bin/env python3
"""
OAG KB Curate CLI
큐레이션 명령줄 인터페이스 - 큐 아이템 검토 및 KB 추가

사용법:
    python shared_kb/curate.py
    python shared_kb/curate.py --auto
"""

import argparse
import sys
from pathlib import Path

# 직접 실행 시 패키지 경로 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from shared_kb.ontology_kb import OntologyKB
    from shared_kb.queue import CurationQueue
    from shared_kb.schema import KnowledgeItem, ConfidenceLevel
else:
    from .ontology_kb import OntologyKB
    from .queue import CurationQueue
    from .schema import KnowledgeItem, ConfidenceLevel


def curate_interactive(kb: OntologyKB, queue: CurationQueue):
    """대화형 큐레이션"""
    print("\n🔍 OAG KB 큐레이션 모드\n")
    print("=" * 60)

    while True:
        item = queue.get_next()
        if not item:
            print("\n✅ 모든 큐 항목을 처리했습니다!")
            break

        print(f"\n📝 제목: {item.knowledge_item.title}")
        print(f"   ID: {item.id[:8]}...")
        print(f"   액션: {item.action} | 우선순위: {item.priority}")
        print(f"   유형: {item.knowledge_item.knowledge_type.value}")
        print(f"   도메인: {item.knowledge_item.domain}")
        print(f"   태그: {', '.join(item.knowledge_item.tags) if item.knowledge_item.tags else '-'}")
        print(f"   제안자: {item.suggested_by}")
        if item.reason:
            print(f"   사유: {item.reason}")
        print(f"\n   내용:\n   {item.knowledge_item.content}")
        print("\n" + "-" * 60)

        print("\n선택:")
        print("  [a] 승인 - KB에 추가")
        print("  [e] 수정 후 승인")
        print("  [s] 건너뛰기 (나중에)")
        print("  [r] 거부 - 큐에서 삭제")
        print("  [q] 종료")

        choice = input("\n선택: ").strip().lower()

        if choice == "a":
            # 승인
            try:
                knowledge_id = kb.add_knowledge(item.knowledge_item)
                queue.remove(item.id)
                print(f"✅ KB에 추가되었습니다! (ID: {knowledge_id[:8]}...)")
            except Exception as e:
                print(f"❌ 추가 실패: {e}")

        elif choice == "e":
            # 수정 후 승인
            new_title = input(f"제목 [{item.knowledge_item.title}]: ").strip()
            if new_title:
                item.knowledge_item.title = new_title

            print("내용 수정 (빈 줄로 종료, 엔터만 누르면 기존 유지):")
            new_content_lines = []
            first_line = input()
            if first_line:
                new_content_lines.append(first_line)
                while True:
                    line = input()
                    if line == "":
                        break
                    new_content_lines.append(line)
                item.knowledge_item.content = "\n".join(new_content_lines)

            # 신뢰도 선택
            print("\n신뢰도: [v]erified [h]igh [m]edium [l]ow")
            conf_choice = input("선택 (기본 m): ").strip().lower()
            conf_map = {"v": "verified", "h": "high", "m": "medium", "l": "low"}
            item.knowledge_item.confidence = ConfidenceLevel(conf_map.get(conf_choice, "medium"))

            try:
                knowledge_id = kb.add_knowledge(item.knowledge_item)
                queue.remove(item.id)
                print(f"✅ 수정 후 KB에 추가되었습니다! (ID: {knowledge_id[:8]}...)")
            except Exception as e:
                print(f"❌ 추가 실패: {e}")

        elif choice == "s":
            # 건너뛰기
            print("⏭️ 건너뛰었습니다.")
            # 우선순위 낮추기
            item.priority = max(0, item.priority - 1)
            continue

        elif choice == "r":
            # 거부
            queue.remove(item.id)
            print("🗑️ 큐에서 삭제되었습니다.")

        elif choice == "q":
            print("\n👋 큐레이션 종료")
            break

        else:
            print("⚠️ 잘못된 선택입니다.")
            continue

        remaining = queue.count()
        print(f"\n📊 남은 항목: {remaining}건")


def curate_auto(kb: OntologyKB, queue: CurationQueue, confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM):
    """자동 큐레이션 - 모든 대기 항목을 자동 승인"""
    print("\n🤖 OAG KB 자동 큐레이션\n")
    print("=" * 60)

    items = queue.list_all()
    if not items:
        print("📭 처리할 항목이 없습니다.")
        return

    print(f"총 {len(items)}건을 처리합니다.\n")

    success = 0
    failed = 0

    for item in items:
        item.knowledge_item.confidence = confidence
        try:
            knowledge_id = kb.add_knowledge(item.knowledge_item)
            queue.remove(item.id)
            print(f"✅ {item.knowledge_item.title} (ID: {knowledge_id[:8]}...)")
            success += 1
        except Exception as e:
            print(f"❌ {item.knowledge_item.title}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"결과: 성공 {success}건, 실패 {failed}건")


def main():
    parser = argparse.ArgumentParser(
        description="OAG KB 큐레이션",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    # 대화형 큐레이션
    python -m shared_kb.curate

    # 자동 승인 (모든 대기 항목)
    python -m shared_kb.curate --auto

    # 자동 승인 (verified 신뢰도)
    python -m shared_kb.curate --auto --confidence verified
        """
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="자동 큐레이션 (모든 대기 항목 승인)"
    )
    parser.add_argument(
        "--confidence", "-c",
        choices=[c.value for c in ConfidenceLevel],
        default="medium",
        help="자동 승인 시 신뢰도 (기본: medium)"
    )

    args = parser.parse_args()

    # KB 연결
    try:
        kb = OntologyKB()
    except ValueError as e:
        print(f"❌ KB 연결 실패: {e}")
        print("환경변수를 확인하세요: NEO4J_URI, NEO4J_PASSWORD")
        sys.exit(1)

    queue = CurationQueue()

    try:
        if args.auto:
            curate_auto(kb, queue, ConfidenceLevel(args.confidence))
        else:
            curate_interactive(kb, queue)
    finally:
        kb.close()


if __name__ == "__main__":
    main()
