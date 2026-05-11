class GraphConnectionError(Exception):
    """Neo4j 연결 실패"""
    pass

class GraphQueryError(Exception):
    """Cypher 쿼리 실행 실패"""
    pass
