"""
RAG Analysis 상수 정의
"""

# 데이터 타입별 용량 (units)
DATA_UNITS = {
    'overview': 5,        # 기본 정보
    'price': 5,           # 현재 주가
    'financial_summary': 15,  # 재무제표 요약
    'financial_full': 45,     # 재무제표 전체
    'indicator': 5,       # 기술적 지표
    'news': 3,            # 뉴스 (건당)
    'macro': 10,          # 거시경제 지표
}

# 바구니 최대 용량
MAX_BASKET_UNITS = 100

# 기본 데이터 용량 (명시되지 않은 타입)
DEFAULT_DATA_UNITS = 5
