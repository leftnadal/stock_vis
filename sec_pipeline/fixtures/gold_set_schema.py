"""
Gold Set 스키마 정의.

supply_chain_relations는 primary_type 사용 (relationship_type 아님).
"""

from dataclasses import dataclass, field


@dataclass
class SupplyChainRelation:
    target_ticker: str
    target_name: str
    primary_type: str  # SUPPLIES_TO, CUSTOMER_OF, PARTNER_WITH, DEPENDS_ON, COMPETES_WITH


@dataclass
class GoldSetEntry:
    symbol: str
    section_presence: dict = field(default_factory=dict)
    # {'item_1': True, 'item_1a': True, 'item_7': True}
    supply_chain_relations: list = field(default_factory=list)
    # [SupplyChainRelation, ...]
    business_model: dict = field(default_factory=dict)
    # Phase 2에서 채움
