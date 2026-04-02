# CS-0-3: Neo4j 온톨로지 스키마 초기화

> **작업 번호**: CS-0-3
> **목표**: Neo4j에 constraint/index 생성 + 스키마 초기화 management command 구현
> **예상 소요**: 1~2시간
> **선행 조건**: CS-0-2 완료 (Neo4j 연결 레이어 작동 확인)
> **산출물**: `chainsight/graph/schema.py`, management command, Phase 0 완료

---

## 배경

Neo4j에 데이터를 넣기 전에 constraint와 index를 먼저 설정해야 한다.
이것은 RDBMS에서 `CREATE TABLE` 후 `CREATE INDEX`를 하는 것과 같다.

Phase 1(CS-1-1~CS-1-3)에서 :Stock, :Sector, :Industry 노드를 벌크 로드하기 전에
이 스키마가 준비되어 있어야 중복 방지 + 조회 성능이 보장된다.

---

## 1. 스키마 정의

로드맵 섹션 2.4에 정의된 제약 조건과 인덱스를 그대로 구현한다.

### Constraints (유니크)

| 대상      | 속성   | Cypher                                                                                    |
| --------- | ------ | ----------------------------------------------------------------------------------------- |
| :Stock    | ticker | `CREATE CONSTRAINT stock_ticker IF NOT EXISTS FOR (s:Stock) REQUIRE s.ticker IS UNIQUE`   |
| :Sector   | name   | `CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE`     |
| :Industry | name   | `CREATE CONSTRAINT industry_name IF NOT EXISTS FOR (i:Industry) REQUIRE i.name IS UNIQUE` |
| :Theme    | name   | `CREATE CONSTRAINT theme_name IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE`       |

### Indexes (조회 성능)

| 대상   | 속성         | 용도                | Cypher                                                                         |
| ------ | ------------ | ------------------- | ------------------------------------------------------------------------------ |
| :Stock | sector       | 섹터별 필터링       | `CREATE INDEX stock_sector IF NOT EXISTS FOR (s:Stock) ON (s.sector)`          |
| :Stock | community_id | GDS 커뮤니티별 조회 | `CREATE INDEX stock_community IF NOT EXISTS FOR (s:Stock) ON (s.community_id)` |
| :Stock | market_cap   | 시가총액 정렬       | `CREATE INDEX stock_market_cap IF NOT EXISTS FOR (s:Stock) ON (s.market_cap)`  |
| :Stock | industry     | 산업별 필터링       | `CREATE INDEX stock_industry IF NOT EXISTS FOR (s:Stock) ON (s.industry)`      |

---

## 2. 구현

### 2-1. schema.py

```python
# chainsight/graph/schema.py

"""
Neo4j 온톨로지 스키마 정의.

이 파일이 Chain Sight Neo4j 스키마의 single source of truth이다.
constraint/index 변경이 필요하면 이 파일을 수정하고 management command를 다시 실행한다.
"""

import logging

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 스키마 정의
# ------------------------------------------------------------------

CONSTRAINTS = [
    {
        "name": "stock_ticker",
        "cypher": "CREATE CONSTRAINT stock_ticker IF NOT EXISTS "
                  "FOR (s:Stock) REQUIRE s.ticker IS UNIQUE",
        "description": ":Stock 노드 ticker 유니크",
    },
    {
        "name": "sector_name",
        "cypher": "CREATE CONSTRAINT sector_name IF NOT EXISTS "
                  "FOR (s:Sector) REQUIRE s.name IS UNIQUE",
        "description": ":Sector 노드 name 유니크",
    },
    {
        "name": "industry_name",
        "cypher": "CREATE CONSTRAINT industry_name IF NOT EXISTS "
                  "FOR (i:Industry) REQUIRE i.name IS UNIQUE",
        "description": ":Industry 노드 name 유니크",
    },
    {
        "name": "theme_name",
        "cypher": "CREATE CONSTRAINT theme_name IF NOT EXISTS "
                  "FOR (t:Theme) REQUIRE t.name IS UNIQUE",
        "description": ":Theme 노드 name 유니크 (DC-2 이후 사용)",
    },
]

INDEXES = [
    {
        "name": "stock_sector",
        "cypher": "CREATE INDEX stock_sector IF NOT EXISTS "
                  "FOR (s:Stock) ON (s.sector)",
        "description": ":Stock 섹터별 필터링",
    },
    {
        "name": "stock_community",
        "cypher": "CREATE INDEX stock_community IF NOT EXISTS "
                  "FOR (s:Stock) ON (s.community_id)",
        "description": ":Stock GDS 커뮤니티 조회",
    },
    {
        "name": "stock_market_cap",
        "cypher": "CREATE INDEX stock_market_cap IF NOT EXISTS "
                  "FOR (s:Stock) ON (s.market_cap)",
        "description": ":Stock 시가총액 정렬",
    },
    {
        "name": "stock_industry",
        "cypher": "CREATE INDEX stock_industry IF NOT EXISTS "
                  "FOR (s:Stock) ON (s.industry)",
        "description": ":Stock 산업별 필터링",
    },
]


# ------------------------------------------------------------------
# 스키마 적용 함수
# ------------------------------------------------------------------

def initialize_schema(graph_repo) -> dict:
    """
    Neo4j에 모든 constraint + index를 생성한다.
    IF NOT EXISTS 덕분에 이미 있으면 무시된다 (멱등성).

    Returns:
        {
            "constraints_applied": 4,
            "indexes_applied": 4,
            "errors": []
        }
    """
    result = {
        "constraints_applied": 0,
        "indexes_applied": 0,
        "errors": [],
    }

    for c in CONSTRAINTS:
        try:
            graph_repo.run_query(c["cypher"])
            result["constraints_applied"] += 1
            logger.info(f"Constraint OK: {c['name']} — {c['description']}")
        except Exception as e:
            error_msg = f"Constraint FAIL: {c['name']} — {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)

    for idx in INDEXES:
        try:
            graph_repo.run_query(idx["cypher"])
            result["indexes_applied"] += 1
            logger.info(f"Index OK: {idx['name']} — {idx['description']}")
        except Exception as e:
            error_msg = f"Index FAIL: {idx['name']} — {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)

    return result


def verify_schema(graph_repo) -> dict:
    """
    현재 Neo4j에 존재하는 constraint/index를 조회하여
    기대 스키마와 대조한다.

    Returns:
        {
            "constraints": {"expected": 4, "found": [...], "missing": [...]},
            "indexes": {"expected": 4, "found": [...], "missing": [...]},
        }
    """
    # 현재 constraint 조회
    existing_constraints = graph_repo.run_query("SHOW CONSTRAINTS")
    existing_names = {c.get("name", "") for c in existing_constraints}

    expected_constraint_names = {c["name"] for c in CONSTRAINTS}
    found_constraints = expected_constraint_names & existing_names
    missing_constraints = expected_constraint_names - existing_names

    # 현재 index 조회
    existing_indexes = graph_repo.run_query("SHOW INDEXES")
    existing_idx_names = {idx.get("name", "") for idx in existing_indexes}

    expected_index_names = {idx["name"] for idx in INDEXES}
    found_indexes = expected_index_names & existing_idx_names
    missing_indexes = expected_index_names - existing_idx_names

    return {
        "constraints": {
            "expected": len(CONSTRAINTS),
            "found": sorted(found_constraints),
            "missing": sorted(missing_constraints),
        },
        "indexes": {
            "expected": len(INDEXES),
            "found": sorted(found_indexes),
            "missing": sorted(missing_indexes),
        },
    }
```

### 2-2. Management Command

```bash
mkdir -p chainsight/management/commands
touch chainsight/management/__init__.py
touch chainsight/management/commands/__init__.py
```

```python
# chainsight/management/commands/init_neo4j_schema.py

"""
Neo4j 온톨로지 스키마 초기화 커맨드.

사용법:
  python manage.py init_neo4j_schema           # 스키마 적용
  python manage.py init_neo4j_schema --verify   # 적용 후 검증
  python manage.py init_neo4j_schema --check    # 검증만 (적용 안 함)
  python manage.py init_neo4j_schema --reset    # 전체 삭제 후 재적용 (⚠️ 위험)
"""

from django.core.management.base import BaseCommand

from chainsight.graph import get_graph_repository
from chainsight.graph.schema import initialize_schema, verify_schema


class Command(BaseCommand):
    help = "Neo4j 온톨로지 스키마(constraint + index) 초기화"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verify",
            action="store_true",
            help="스키마 적용 후 검증까지 수행",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="현재 스키마 상태만 확인 (변경 없음)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="⚠️ 기존 constraint/index 삭제 후 재생성",
        )

    def handle(self, *args, **options):
        repo = get_graph_repository()

        # 연결 확인
        if not repo.health_check():
            self.stderr.write(self.style.ERROR("❌ Neo4j 연결 실패. 서버 상태를 확인하세요."))
            return

        self.stdout.write(self.style.SUCCESS("✅ Neo4j 연결 OK"))

        # --check: 검증만
        if options["check"]:
            self._print_verification(repo)
            return

        # --reset: 전체 삭제 후 재적용
        if options["reset"]:
            self.stdout.write(self.style.WARNING("\n⚠️  기존 constraint/index를 삭제합니다..."))
            self._reset_schema(repo)

        # 스키마 적용
        self.stdout.write("\n📋 스키마 적용 시작...")
        result = initialize_schema(repo)

        self.stdout.write(
            f"\n  Constraints: {result['constraints_applied']}/{len(initialize_schema.__code__.co_consts)}"
        )
        # 더 정확한 카운트
        from chainsight.graph.schema import CONSTRAINTS, INDEXES
        self.stdout.write(f"  Constraints 적용: {result['constraints_applied']}/{len(CONSTRAINTS)}")
        self.stdout.write(f"  Indexes 적용: {result['indexes_applied']}/{len(INDEXES)}")

        if result["errors"]:
            for err in result["errors"]:
                self.stderr.write(self.style.ERROR(f"  ❌ {err}"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ 스키마 적용 완료 (오류 없음)"))

        # --verify: 검증까지
        if options["verify"]:
            self._print_verification(repo)

    def _print_verification(self, repo):
        self.stdout.write("\n🔍 스키마 검증...")
        status = verify_schema(repo)

        # Constraints
        c = status["constraints"]
        self.stdout.write(f"\n  Constraints ({len(c['found'])}/{c['expected']}):")
        for name in c["found"]:
            self.stdout.write(self.style.SUCCESS(f"    ✅ {name}"))
        for name in c["missing"]:
            self.stdout.write(self.style.ERROR(f"    ❌ {name} (MISSING)"))

        # Indexes
        i = status["indexes"]
        self.stdout.write(f"\n  Indexes ({len(i['found'])}/{i['expected']}):")
        for name in i["found"]:
            self.stdout.write(self.style.SUCCESS(f"    ✅ {name}"))
        for name in i["missing"]:
            self.stdout.write(self.style.ERROR(f"    ❌ {name} (MISSING)"))

        # 종합
        if not c["missing"] and not i["missing"]:
            self.stdout.write(self.style.SUCCESS("\n✅ 스키마 검증 통과"))
        else:
            self.stderr.write(self.style.ERROR(
                f"\n❌ 누락 항목 있음: constraints {len(c['missing'])}개, indexes {len(i['missing'])}개"
            ))

    def _reset_schema(self, repo):
        """기존 constraint/index 삭제"""
        from chainsight.graph.schema import CONSTRAINTS, INDEXES

        for c in CONSTRAINTS:
            try:
                repo.run_query(f"DROP CONSTRAINT {c['name']} IF EXISTS")
                self.stdout.write(f"  Dropped constraint: {c['name']}")
            except Exception as e:
                self.stderr.write(f"  Drop failed: {c['name']} — {e}")

        for idx in INDEXES:
            try:
                repo.run_query(f"DROP INDEX {idx['name']} IF EXISTS")
                self.stdout.write(f"  Dropped index: {idx['name']}")
            except Exception as e:
                self.stderr.write(f"  Drop failed: {idx['name']} — {e}")
```

---

## 3. 실행 + 검증

### 3-1. 스키마 적용

```bash
python manage.py init_neo4j_schema --verify
```

**기대 출력**:

```
✅ Neo4j 연결 OK

📋 스키마 적용 시작...
  Constraints 적용: 4/4
  Indexes 적용: 4/4

✅ 스키마 적용 완료 (오류 없음)

🔍 스키마 검증...

  Constraints (4/4):
    ✅ stock_ticker
    ✅ sector_name
    ✅ industry_name
    ✅ theme_name

  Indexes (4/4):
    ✅ stock_sector
    ✅ stock_community
    ✅ stock_market_cap
    ✅ stock_industry

✅ 스키마 검증 통과
```

### 3-2. 멱등성 확인 (두 번 실행)

```bash
python manage.py init_neo4j_schema --verify
# → 동일한 성공 결과. IF NOT EXISTS 덕분에 오류 없음.
```

### 3-3. Neo4j Browser에서 직접 확인 (선택)

```
http://localhost:7474
```

```cypher
SHOW CONSTRAINTS;
SHOW INDEXES;
```

### 3-4. 유니크 constraint 동작 확인

```bash
python manage.py shell
```

```python
from chainsight.graph import get_graph_repository

repo = get_graph_repository()

# 같은 ticker로 두 번 MERGE → 노드 1개만 존재해야 함
repo.upsert_node("Stock", "ticker", "CONSTRAINT_TEST", {"name": "Test 1"})
repo.upsert_node("Stock", "ticker", "CONSTRAINT_TEST", {"name": "Test 2"})

count = repo.run_query(
    "MATCH (s:Stock {ticker: 'CONSTRAINT_TEST'}) RETURN count(s) AS cnt"
)
assert count[0]["cnt"] == 1, "유니크 constraint 실패!"
print("유니크 constraint OK")

# 정리
repo.run_query("MATCH (s:Stock {ticker: 'CONSTRAINT_TEST'}) DELETE s")
```

---

## 완료 기준 체크리스트

```
□ chainsight/graph/schema.py 생성
□ chainsight/management/commands/init_neo4j_schema.py 생성
□ python manage.py init_neo4j_schema --verify → 전부 ✅
□ 멱등성 확인 (두 번 실행해도 오류 없음)
□ 유니크 constraint 동작 확인
```

---

## 완료 기록 작성

`docs/chain_sight/task_done/CS-0-3_neo4j_schema.md` 작성:

```markdown
# CS-0-3: Neo4j 온톨로지 스키마 초기화

> **완료일**: 2026-04-XX
> **소요 시간**: XX시간

## 생성된 파일

- chainsight/graph/schema.py
- chainsight/management/**init**.py
- chainsight/management/commands/**init**.py
- chainsight/management/commands/init_neo4j_schema.py

## 스키마 현황

- Constraints: 4개 (stock_ticker, sector_name, industry_name, theme_name)
- Indexes: 4개 (stock_sector, stock_community, stock_market_cap, stock_industry)

## 테스트 결과

- init_neo4j_schema --verify: 전부 통과
- 멱등성: 확인
- 유니크 constraint: 정상 작동

## 발견된 이슈

- (있으면 기록)

## Phase 0 완료 상태

- CS-0-0: ✅ 레거시 정리 + API 테스트
- CS-0-1: ✅ Migrations 검증
- CS-0-2: ✅ Neo4j 연결 레이어
- CS-0-3: ✅ 온톨로지 스키마 ← 이 작업

## 다음 작업 연결

→ Phase 1 (CS-1-1): Stock 노드 벌크 로드

- S&P 500 :Stock 노드 500개를 Neo4j에 적재
- CS-0-2의 bulk_upsert_nodes + CS-0-3의 constraint 활용
```

---

## Phase 0 완료 → 마일스톤 M0 달성

CS-0-3이 완료되면 **M0: "레거시 정리됨, Neo4j 연결됨, 테이블 있음"** 달성이다.

```
M0 체크리스트:
✅ 기존 Chain Sight 코드 제거 (CS-0-0)
✅ API 테스트 결과 decisions/에 기록 (CS-0-0)
✅ RelationConfidence v2.1 마이그레이션 완료 (CS-0-0)
✅ PostgreSQL 12개 테이블 확인 (CS-0-1)
✅ Neo4j 연결 + 읽기/쓰기 작동 (CS-0-2)
✅ Neo4j constraint/index 설정 (CS-0-3)
```

다음 Phase: **CS-1-1 (Stock 노드 벌크 로드)** → S&P 500 :Stock 노드 500개 적재

**END OF DOCUMENT**
