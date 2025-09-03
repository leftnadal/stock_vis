from django.contrib import admin
from .models import Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement

## Stock 모델 관리자 설정
@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """
    ## 주식 모델 관리자 설정
    # - 관리자 페이지에서 주식 데이터를 쉽게 조회하고 관리할 수 있도록 설정
    """
    
    ## 목록 페이지에 표시할 필드들
    # - 주요 정보만 선별하여 한눈에 확인 가능하도록 구성
    list_display = (
        'stock_name',           # 주식명
        'symbol',              # 심볼
        'real_time_price',     # 실시간 가격
        'exchange',            # 거래소
        'sector',              # 섹터 (추가)
        'market_capitalization',  # 시가총액 (추가)
        'last_updated'         # 마지막 업데이트 시간
    )
    
    ## 검색 가능한 필드들
    # - 주식명과 심볼로 빠른 검색 가능
    search_fields = ('stock_name', 'symbol')
    
    ## 필터링 옵션들 (추가)
    # - 사이드바에서 빠른 필터링 가능
    list_filter = (
        'sector',              # 섹터별 필터링
        'exchange',            # 거래소별 필터링
        'currency',            # 통화별 필터링
        'last_updated'         # 업데이트 날짜별 필터링
    )
    
    ## 페이지당 표시할 항목 수
    list_per_page = 50
    
    ## 정렬 기본값 (시가총액 내림차순)
    ordering = ('-market_capitalization',)


## DailyPrice 모델 관리자 설정
@admin.register(DailyPrice)
class DailyPriceAdmin(admin.ModelAdmin):
    """
    ## 일일 가격 데이터 관리자 설정
    # - 일일 가격 데이터를 관리자 페이지에서 조회 및 관리
    """
    
    list_display = (
        'stock',               # 주식 (외래키)
        'date',                # 날짜
        'open_price',          # 시가
        'high_price',          # 고가
        'low_price',           # 저가
        'close_price',         # 종가
        'volume',              # 거래량
    )
    
    list_filter = (
        'date',                # 날짜별 필터링
        'stock__sector',       # 섹터별 필터링 (역참조)
    )
    
    search_fields = ('stock__symbol', 'stock__stock_name')  # 주식 심볼/명으로 검색
    ordering = ('-date', 'stock')  # 날짜 내림차순, 주식별 정렬
    list_per_page = 100


## WeeklyPrice 모델 관리자 설정
@admin.register(WeeklyPrice)
class WeeklyPriceAdmin(admin.ModelAdmin):
    """
    ## 주간 가격 데이터 관리자 설정
    """
    
    list_display = (
        'stock',
        'date',
        'open_price',
        'high_price', 
        'low_price',
        'close_price',
        'volume',
        'week_start_date',     # 주간 시작일
        'week_end_date',       # 주간 종료일
    )
    
    list_filter = ('date', 'stock__sector')
    search_fields = ('stock__symbol', 'stock__stock_name')
    ordering = ('-date', 'stock')
    list_per_page = 100


## BalanceSheet 모델 관리자 설정
@admin.register(BalanceSheet)
class BalanceSheetAdmin(admin.ModelAdmin):
    """
    ## 대차대조표 관리자 설정
    """
    
    list_display = (
        'stock',
        'period_type',         # 기간 타입 (연간/분기)
        'fiscal_year',         # 회계연도
        'fiscal_quarter',      # 회계분기
        'reported_date',       # 공시일
        'total_assets',        # 총자산
        'total_liabilities',   # 총부채
        'total_shareholder_equity',  # 총자본
    )
    
    list_filter = (
        'period_type',
        'fiscal_year',
        'stock__sector',
    )
    
    search_fields = ('stock__symbol', 'stock__stock_name')
    ordering = ('-fiscal_year', '-fiscal_quarter', 'stock')
    list_per_page = 50


## IncomeStatement 모델 관리자 설정
@admin.register(IncomeStatement)
class IncomeStatementAdmin(admin.ModelAdmin):
    """
    ## 손익계산서 관리자 설정
    """
    
    list_display = (
        'stock',
        'period_type',
        'fiscal_year',
        'fiscal_quarter',
        'reported_date',
        'total_revenue',       # 총매출
        'gross_profit',        # 매출총이익
        'operating_income',    # 영업이익
        'net_income',          # 순이익
    )
    
    list_filter = (
        'period_type',
        'fiscal_year',
        'stock__sector',
    )
    
    search_fields = ('stock__symbol', 'stock__stock_name')
    ordering = ('-fiscal_year', '-fiscal_quarter', 'stock')
    list_per_page = 50


## CashFlowStatement 모델 관리자 설정
@admin.register(CashFlowStatement)
class CashFlowStatementAdmin(admin.ModelAdmin):
    """
    ## 현금흐름표 관리자 설정
    """
    
    list_display = (
        'stock',
        'period_type',
        'fiscal_year',
        'fiscal_quarter',
        'reported_date',
        'operating_cashflow',        # 영업현금흐름
        'cashflow_from_investment',  # 투자현금흐름
        'cashflow_from_financing',   # 재무현금흐름
    )
    
    list_filter = (
        'period_type',
        'fiscal_year',
        'stock__sector',
    )
    
    search_fields = ('stock__symbol', 'stock__stock_name')
    ordering = ('-fiscal_year', '-fiscal_quarter', 'stock')
    list_per_page = 50