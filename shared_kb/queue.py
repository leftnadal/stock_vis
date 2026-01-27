"""
OAG KB Curation Queue
지식 큐레이션을 위한 큐 관리 시스템
"""

import os
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from .schema import KnowledgeItem, QueueItem, KnowledgeType, ConfidenceLevel


class CurationQueue:
    """
    큐레이션 큐 관리

    지식 추가/검토 요청을 큐에 저장하고 관리합니다.
    로컬 JSON 파일 기반 (Neo4j 없이도 동작)
    """

    def __init__(self, queue_file: str = None):
        """
        Args:
            queue_file: 큐 저장 파일 경로 (기본: shared_kb/queue_data.json)
        """
        if queue_file:
            self.queue_file = Path(queue_file)
        else:
            self.queue_file = Path(__file__).parent / "queue_data.json"

        self._load_queue()

    def _load_queue(self):
        """큐 파일 로드"""
        if self.queue_file.exists():
            with open(self.queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.items = [self._dict_to_queue_item(item) for item in data]
        else:
            self.items = []

    def _save_queue(self):
        """큐 파일 저장"""
        with open(self.queue_file, "w", encoding="utf-8") as f:
            data = [self._queue_item_to_dict(item) for item in self.items]
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _dict_to_queue_item(self, data: Dict[str, Any]) -> QueueItem:
        """딕셔너리를 QueueItem으로 변환"""
        knowledge_data = data["knowledge_item"]
        knowledge_item = KnowledgeItem(
            id=knowledge_data["id"],
            title=knowledge_data["title"],
            content=knowledge_data["content"],
            knowledge_type=KnowledgeType(knowledge_data["knowledge_type"]),
            tags=knowledge_data.get("tags", []),
            source=knowledge_data.get("source"),
            confidence=ConfidenceLevel(knowledge_data.get("confidence", "medium")),
            domain=knowledge_data.get("domain", "general"),
            created_by=knowledge_data.get("created_by", "system"),
        )

        return QueueItem(
            id=data["id"],
            knowledge_item=knowledge_item,
            action=data["action"],
            priority=data.get("priority", 0),
            reason=data.get("reason"),
            suggested_by=data.get("suggested_by", "system"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )

    def _queue_item_to_dict(self, item: QueueItem) -> Dict[str, Any]:
        """QueueItem을 딕셔너리로 변환"""
        return {
            "id": item.id,
            "knowledge_item": item.knowledge_item.to_dict(),
            "action": item.action,
            "priority": item.priority,
            "reason": item.reason,
            "suggested_by": item.suggested_by,
            "created_at": item.created_at.isoformat(),
        }

    # ==================== Queue Operations ====================

    def add(
        self,
        title: str,
        content: str,
        knowledge_type: KnowledgeType,
        action: str = "add",
        tags: List[str] = None,
        source: str = None,
        domain: str = "general",
        priority: int = 0,
        reason: str = None,
        suggested_by: str = "system",
    ) -> str:
        """
        큐에 새 아이템 추가

        Args:
            title: 지식 제목
            content: 지식 내용
            knowledge_type: 지식 유형
            action: 액션 (add, update, review, merge)
            tags: 태그 리스트
            source: 출처
            domain: 도메인
            priority: 우선순위 (높을수록 먼저)
            reason: 큐 추가 이유
            suggested_by: 제안자

        Returns:
            생성된 큐 아이템 ID
        """
        queue_id = str(uuid.uuid4())
        knowledge_id = str(uuid.uuid4())

        knowledge_item = KnowledgeItem(
            id=knowledge_id,
            title=title,
            content=content,
            knowledge_type=knowledge_type,
            tags=tags or [],
            source=source,
            domain=domain,
            created_by=suggested_by,
        )

        queue_item = QueueItem(
            id=queue_id,
            knowledge_item=knowledge_item,
            action=action,
            priority=priority,
            reason=reason,
            suggested_by=suggested_by,
        )

        self.items.append(queue_item)
        self._save_queue()

        return queue_id

    def add_item(self, queue_item: QueueItem) -> str:
        """QueueItem 객체 직접 추가"""
        if not queue_item.id:
            queue_item.id = str(uuid.uuid4())
        self.items.append(queue_item)
        self._save_queue()
        return queue_item.id

    def get(self, queue_id: str) -> Optional[QueueItem]:
        """ID로 큐 아이템 조회"""
        for item in self.items:
            if item.id == queue_id:
                return item
        return None

    def remove(self, queue_id: str) -> bool:
        """큐에서 아이템 제거"""
        for i, item in enumerate(self.items):
            if item.id == queue_id:
                self.items.pop(i)
                self._save_queue()
                return True
        return False

    def list_all(
        self,
        action: str = None,
        suggested_by: str = None,
        limit: int = 50,
    ) -> List[QueueItem]:
        """
        큐 아이템 목록 조회

        Args:
            action: 액션 필터
            suggested_by: 제안자 필터
            limit: 결과 수 제한

        Returns:
            우선순위순 정렬된 QueueItem 리스트
        """
        result = self.items.copy()

        if action:
            result = [item for item in result if item.action == action]

        if suggested_by:
            result = [item for item in result if item.suggested_by == suggested_by]

        # 우선순위 높은 순, 생성일 오래된 순
        result.sort(key=lambda x: (-x.priority, x.created_at))

        return result[:limit]

    def get_next(self) -> Optional[QueueItem]:
        """다음 처리할 아이템 조회 (제거하지 않음)"""
        sorted_items = sorted(
            self.items,
            key=lambda x: (-x.priority, x.created_at)
        )
        return sorted_items[0] if sorted_items else None

    def pop_next(self) -> Optional[QueueItem]:
        """다음 처리할 아이템 조회 및 제거"""
        item = self.get_next()
        if item:
            self.remove(item.id)
        return item

    def count(self, action: str = None) -> int:
        """큐 아이템 수"""
        if action:
            return len([item for item in self.items if item.action == action])
        return len(self.items)

    def clear(self):
        """큐 비우기"""
        self.items = []
        self._save_queue()

    def get_stats(self) -> Dict[str, Any]:
        """큐 통계"""
        by_action = {}
        by_suggested = {}
        by_domain = {}

        for item in self.items:
            # 액션별
            by_action[item.action] = by_action.get(item.action, 0) + 1

            # 제안자별
            by_suggested[item.suggested_by] = by_suggested.get(item.suggested_by, 0) + 1

            # 도메인별
            domain = item.knowledge_item.domain
            by_domain[domain] = by_domain.get(domain, 0) + 1

        return {
            "total": len(self.items),
            "by_action": by_action,
            "by_suggested_by": by_suggested,
            "by_domain": by_domain,
        }
