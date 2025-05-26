"""
Management command to update stock data from Alpha Vantage.
"""
import logging
import time
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from stocks.models import Stock
from alpha_vantage.service import AlphaVantageService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates stock data from Alpha Vantage API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            type=str,
            help='Comma-separated list of stock symbols to update (e.g., AAPL,MSFT,GOOGL)'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all stocks in the database'
        )
        
        parser.add_argument(
            '--prices-only',
            action='store_true',
            help='Update only historical price data'
        )
        
        parser.add_argument(
            '--full-history',
            action='store_true',
            help='Fetch full price history (20+ years) instead of the latest 100 days'
        )
        
        parser.add_argument(
            '--delay',
            type=float,
            default=12.0,  # Free tier allows 5 requests per minute (60/5=12)
            help='Delay between API requests in seconds (default: 12.0)'
        )

    def handle(self, *args, **options):
        # Get Alpha Vantage API key from settings
        try:
            api_key = settings.ALPHA_VANTAGE_API_KEY
        except AttributeError:
            raise CommandError(
                "ALPHA_VANTAGE_API_KEY not found in settings. "
                "Add 'ALPHA_VANTAGE_API_KEY = \"your-api-key\"' to your settings.py file."
            )
        
        # Initialize service with custom delay if provided
        delay = options.get('delay', 12.0)
        service = AlphaVantageService(api_key)
        service.client.request_delay = delay
        
        # Determine which stocks to update
        symbols_to_update = []
        
        if options.get('symbols'):
            # Update specified symbols
            symbols_to_update = options['symbols'].split(',')
            self.stdout.write(f"Updating data for {len(symbols_to_update)} stocks: {', '.join(symbols_to_update)}")
        elif options.get('all'):
            # Update all stocks in the database
            stocks = Stock.objects.all()
            if not stocks.exists():
                raise CommandError("No stocks found in the database. Add stocks first or use --symbols option.")
            
            symbols_to_update = list(stocks.values_list('symbol', flat=True))
            self.stdout.write(f"Updating data for all {len(symbols_to_update)} stocks in the database")
        else:
            raise CommandError("Please specify either --symbols or --all")
        
        # Determine update mode
        prices_only = options.get('prices_only', False)
        full_history = options.get('full_history', False)
        history_days = 'full' if full_history else 100
        
        # Update each stock
        successful = 0
        failed = 0
        
        for symbol in symbols_to_update:
            self.stdout.write(f"Processing {symbol}...")
            
            try:
                if prices_only:
                    # Update only price data
                    try:
                        # First ensure stock exists or create it
                        stock, created = Stock.objects.get_or_create(symbol=symbol.upper().strip())
                        if created:
                            self.stdout.write(f"Created new stock entry for {symbol}")
                        
                        # Update price history
                        count = service.update_historical_prices(stock, days=history_days)
                        self.stdout.write(f"✓ Updated {count} price records for {symbol}")
                        successful += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"✗ Error updating prices for {symbol}: {e}"))
                        failed += 1
                else:
                    # Update all stock data
                    results = service.update_all_stock_data(symbol)
                    
                    status_msgs = [
                        "✓ Updated stock information" if results['stock'] else "✗ Failed to update stock information",
                        f"✓ Updated {results['prices']} price records",
                        f"✓ Updated {results['financials']['balance_sheet']} balance sheet records",
                        f"✓ Updated {results['financials']['income_statement']} income statement records",
                        f"✓ Updated {results['financials']['cash_flow']} cash flow records"
                    ]
                    
                    self.stdout.write(f"Results for {symbol}:")
                    for msg in status_msgs:
                        self.stdout.write(f"  {msg}")
                    
                    successful += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error updating {symbol}: {e}"))
                failed += 1
            
            # Add a separator line between stocks
            self.stdout.write("-" * 40)
        
        # Print summary
        self.stdout.write(
            self.style.SUCCESS(f"Update complete: {successful} successful, {failed} failed")
        )