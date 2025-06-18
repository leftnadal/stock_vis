import json

from django.shortcuts import render, get_object_or_404


from .models import Stock, DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement



def dashboard(request):
    """
    대시보드 ( 주요 섹터, 관심 주식 가격 등)
    """
    top_stocks = Stock.objects.filter(market_capitalization__isnull=False).order_by('-market_capitalization')[:10]

    context = {
        'top_stocks' : top_stocks,
    }

    return render(request, 'stocks/dashboard.html', context)
