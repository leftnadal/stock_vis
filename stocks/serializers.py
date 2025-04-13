from rest_framework import serializers
from .models import Stock, HistoricalPrice, BalanceSheet, IncomeStatement, CashFlowStatement

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['id', 'stock_name', 'symbol', 'exchange', 'sector', 'real_time_price', 
                  'currency', 'overview', 'last_updated']

class StockDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = '__all__'

class HistoricalPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalPrice
        exclude = ['stock']

class BalanceSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceSheet
        exclude = ['stock']

class IncomeStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeStatement
        exclude = ['stock']

class CashFlowStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlowStatement
        exclude = ['stock']