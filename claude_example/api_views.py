"""
API views for Alpha Vantage stock data updates.
"""
import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import ParseError, NotFound

from .models import Stock
from alpha_vantage.service import AlphaVantageService

logger = logging.getLogger(__name__)

class StockDataUpdateView(APIView):
    """
    API endpoint for updating stock data from Alpha Vantage.
    Only accessible to admin users.
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """
        Trigger stock data update for specified symbol.
        
        POST parameters:
        - symbol: Stock symbol to update
        - update_type: 'all' for all data, 'prices' for only price history,
                       'overview' for basic stock info, 'financials' for financial statements
        - full_history: true/false - whether to fetch full price history
        """
        try:
            # Get Alpha Vantage API key from settings
            try:
                api_key = settings.ALPHA_VANTAGE_API_KEY
            except AttributeError:
                return Response(
                    {"error": "Alpha Vantage API key not configured"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Get request parameters
            symbol = request.data.get('symbol')
            if not symbol:
                raise ParseError("Stock symbol is required")
            
            update_type = request.data.get('update_type', 'all')
            full_history = request.data.get('full_history', False)
            history_days = 'full' if full_history else 100
            
            # Standardize symbol
            symbol = symbol.upper().strip()
            
            # Initialize service
            service = AlphaVantageService(api_key)
            
            # Perform update based on requested type
            if update_type == 'all':
                results = service.update_all_stock_data(symbol)
                return Response({
                    "message": f"Stock data update completed for {symbol}",
                    "results": results
                })
            
            elif update_type == 'prices':
                # First ensure stock exists
                try:
                    stock = Stock.objects.get(symbol=symbol)
                except Stock.DoesNotExist:
                    # Try to create stock with basic info first
                    stock = service.update_stock_data(symbol)
                    
                count = service.update_historical_prices(stock, days=history_days)
                return Response({
                    "message": f"Price data update completed for {symbol}",
                    "count": count
                })
            
            elif update_type == 'overview':
                stock = service.update_stock_data(symbol)
                return Response({
                    "message": f"Stock overview updated for {symbol}",
                    "stock_id": stock.id
                })
            
            elif update_type == 'financials':
                # First ensure stock exists
                try:
                    stock = Stock.objects.get(symbol=symbol)
                except Stock.DoesNotExist:
                    # Try to create stock with basic info first
                    stock = service.update_stock_data(symbol)
                
                financials = service.update_financial_statements(stock)
                return Response({
                    "message": f"Financial statements updated for {symbol}",
                    "results": financials
                })
            
            else:
                raise ParseError(f"Invalid update_type: {update_type}")
                
        except NotFound as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ParseError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating stock data: {e}")
            return Response(
                {"error": f"Failed to update stock data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )