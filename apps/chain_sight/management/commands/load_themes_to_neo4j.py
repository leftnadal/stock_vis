"""
DC-2: ETF Holdings → Neo4j :Theme 노드 + HAS_THEME 관계.

기존 serverless/ETFProfile + ETFHolding + ThemeMatch 데이터를
Neo4j :Theme 노드와 :Stock -[HAS_THEME]-> :Theme 관계로 변환.

Usage:
    python manage.py load_themes_to_neo4j
    python manage.py load_themes_to_neo4j --dry-run
"""

from django.core.management.base import BaseCommand

from apps.chain_sight.graph import get_graph_repository

# ETF → Theme 매핑 (ETF 심볼 → 테마 이름 + 설명)
ETF_THEME_MAP = {
    # Theme ETFs (Tier 2)
    "SOXX": {
        "name": "Semiconductor",
        "description": "반도체 설계/제조/장비",
        "keywords": ["semiconductor", "chip", "foundry", "fab"],
    },
    "BOTZ": {
        "name": "Robotics & AI",
        "description": "로보틱스, 인공지능, 자동화",
        "keywords": ["robotics", "AI", "automation", "machine learning"],
    },
    "ICLN": {
        "name": "Clean Energy",
        "description": "재생에너지, 태양광, 풍력",
        "keywords": ["solar", "wind", "renewable", "clean energy"],
    },
    "LIT": {
        "name": "Lithium & Battery",
        "description": "리튬, 배터리, 전기차 소재",
        "keywords": ["lithium", "battery", "EV", "cathode"],
    },
    "ARKK": {
        "name": "Disruptive Innovation",
        "description": "ARK 파괴적 혁신",
        "keywords": ["innovation", "disruptive", "genomics", "fintech"],
    },
    "ARKG": {
        "name": "Genomic Revolution",
        "description": "유전체, 바이오테크 혁신",
        "keywords": ["genomics", "CRISPR", "gene therapy", "biotech"],
    },
    "HACK": {
        "name": "Cybersecurity",
        "description": "사이버보안",
        "keywords": ["cybersecurity", "firewall", "endpoint", "zero trust"],
    },
    "BETZ": {
        "name": "Sports Betting & Gaming",
        "description": "스포츠 베팅, 온라인 게이밍",
        "keywords": ["betting", "gaming", "casino", "igaming"],
    },
    "KWEB": {
        "name": "China Internet",
        "description": "중국 인터넷 기업",
        "keywords": ["china", "internet", "e-commerce", "alibaba"],
    },
    "TAN": {
        "name": "Solar Energy",
        "description": "태양광 에너지",
        "keywords": ["solar", "photovoltaic", "inverter"],
    },
    # Sector ETFs (Tier 1) → 보조 테마로도 등록
    "XLK": {
        "name": "Technology",
        "description": "정보기술 섹터",
        "keywords": ["technology", "software", "hardware"],
    },
    "XLV": {
        "name": "Healthcare",
        "description": "헬스케어 섹터",
        "keywords": ["healthcare", "pharma", "biotech", "medical"],
    },
    "XLF": {
        "name": "Financials",
        "description": "금융 섹터",
        "keywords": ["banking", "insurance", "fintech"],
    },
    "XLE": {
        "name": "Energy",
        "description": "에너지 섹터",
        "keywords": ["oil", "gas", "energy", "petroleum"],
    },
    "XLI": {
        "name": "Industrials",
        "description": "산업재 섹터",
        "keywords": ["industrial", "manufacturing", "aerospace"],
    },
    "XLY": {
        "name": "Consumer Discretionary",
        "description": "경기소비재",
        "keywords": ["retail", "consumer", "luxury", "auto"],
    },
    "XLP": {
        "name": "Consumer Staples",
        "description": "필수소비재",
        "keywords": ["food", "beverage", "household"],
    },
    "XLU": {
        "name": "Utilities",
        "description": "유틸리티",
        "keywords": ["electric", "water", "gas utility"],
    },
    "XLC": {
        "name": "Communication Services",
        "description": "커뮤니케이션 서비스",
        "keywords": ["media", "telecom", "social media"],
    },
    "XLRE": {
        "name": "Real Estate",
        "description": "부동산",
        "keywords": ["REIT", "real estate", "property"],
    },
    "XLB": {
        "name": "Materials",
        "description": "소재",
        "keywords": ["chemicals", "metals", "mining"],
    },
}


class Command(BaseCommand):
    help = "ETF Holdings → Neo4j :Theme 노드 + HAS_THEME 관계 로드"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--theme-only", action="store_true", help="Theme ETFs만 (Sector ETFs 제외)"
        )

    def handle(self, *args, **options):
        from packages.shared.stocks.models import Stock
        from serverless.models import ETFHolding, ETFProfile

        dry_run = options["dry_run"]
        theme_only = options["theme_only"]

        repo = get_graph_repository()
        stock_set = set(Stock.objects.values_list("symbol", flat=True))

        # ── 1. :Theme 노드 생성 ──
        theme_nodes = []
        for etf_symbol, theme_info in ETF_THEME_MAP.items():
            etf = ETFProfile.objects.filter(symbol=etf_symbol).first()
            if not etf:
                continue
            if theme_only and etf.tier != "theme":
                continue

            theme_nodes.append(
                {
                    "name": theme_info["name"],
                    "description": theme_info["description"],
                    "keywords": theme_info["keywords"],
                    "etf_source": etf_symbol,
                }
            )

        self.stdout.write(f"Theme nodes to create: {len(theme_nodes)}")

        if not dry_run:
            for theme in theme_nodes:
                repo.run_query(
                    """
                    MERGE (t:Theme {name: $name})
                    SET t.description = $description,
                        t.keywords = $keywords,
                        t.etf_source = $etf_source
                """,
                    theme,
                )
            self.stdout.write(
                self.style.SUCCESS(f"  Created {len(theme_nodes)} :Theme nodes")
            )

        # ── 2. HAS_THEME 관계 생성 ──
        # ETF holdings에서 Stock → Theme 매핑
        has_theme_edges = []
        seen = set()

        for etf_symbol, theme_info in ETF_THEME_MAP.items():
            etf = ETFProfile.objects.filter(symbol=etf_symbol).first()
            if not etf:
                continue
            if theme_only and etf.tier != "theme":
                continue

            holdings = ETFHolding.objects.filter(etf=etf)
            for holding in holdings:
                stock_sym = holding.stock_symbol.upper()
                if stock_sym not in stock_set:
                    continue

                edge_key = (stock_sym, theme_info["name"])
                if edge_key in seen:
                    continue
                seen.add(edge_key)

                has_theme_edges.append(
                    {
                        "ticker": stock_sym,
                        "theme_name": theme_info["name"],
                        "weight": float(holding.weight_percent)
                        if holding.weight_percent
                        else 0,
                        "etf_source": etf_symbol,
                    }
                )

        self.stdout.write(f"HAS_THEME edges to create: {len(has_theme_edges)}")

        if not dry_run:
            created = 0
            for edge in has_theme_edges:
                try:
                    repo.run_query(
                        """
                        MATCH (s:Stock {ticker: $ticker})
                        MATCH (t:Theme {name: $theme_name})
                        MERGE (s)-[r:HAS_THEME]->(t)
                        SET r.weight = $weight,
                            r.etf_source = $etf_source,
                            r.source = 'etf_holding'
                    """,
                        edge,
                    )
                    created += 1
                except Exception as e:
                    self.stderr.write(
                        f"  Error: {edge['ticker']}→{edge['theme_name']}: {e}"
                    )

            self.stdout.write(
                self.style.SUCCESS(f"  Created {created} HAS_THEME edges")
            )

        # ── 3. 요약 ──
        if not dry_run:
            result = repo.run_query("MATCH (t:Theme) RETURN count(t) AS cnt")
            theme_count = result[0]["cnt"] if result else 0

            result = repo.run_query("MATCH ()-[r:HAS_THEME]->() RETURN count(r) AS cnt")
            edge_count = result[0]["cnt"] if result else 0

            self.stdout.write(f"\nNeo4j 현황:")
            self.stdout.write(f"  :Theme 노드: {theme_count}")
            self.stdout.write(f"  HAS_THEME 관계: {edge_count}")
        else:
            self.stdout.write("\n[DRY RUN] No changes made.")
