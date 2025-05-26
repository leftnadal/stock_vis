#!/usr/bin/env python
"""
Script to add multiple stock symbols to the database.
Run with: python scripts/add_stock_symbols.py
"""
import os
import sys
import django
import time
import logging
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from stocks.models import Stock
from alpha_vantage.service import AlphaVantageService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/add_stocks.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# List of stock symbols to add - Edit this list as needed
STOCK_SYMBOLS = [
    # US Major Indices
    'SPY',      # S&P 500 ETF
    'QQQ',      # NASDAQ 100 ETF
    'DIA',      # Dow Jones Industrial Average ETF
    
    # US Tech
    'AAPL',     # Apple
    'MSFT',     # Microsoft
    'GOOGL',    # Alphabet (Google)
    'AMZN',     # Amazon
    'META',     # Meta (Facebook)
    'TSLA',     # Tesla
    'NVDA',     # NVIDIA
    
    # US Finance
    'JPM',      # JPMorgan Chase
    'BAC',      # Bank of America
    'GS',       # Goldman Sachs
    'V',        # Visa
    'MA',       # Mastercard
    
    # US Healthcare
    'JNJ',      # Johnson & Johnson
    'PFE',      # Pfizer
    'UNH',      # UnitedHealth Group
    'ABBV',     # AbbVie
    
    # US Consumer
    'WMT',      # Walmart
    'PG',       # Procter & Gamble
    'KO',       # Coca-Cola
    'PEP',      # PepsiCo
    'DIS',      # Walt Disney
    'NFLX',     # Netflix
    
    # US Energy/Industrial
    'XOM',      # ExxonMobil
    'CVX',      # Chevron
    'CAT',      # Caterpillar
    
    # Korean Stocks
    '005930.KS',    # Samsung Electronics
    '000660.KS',    # SK Hynix
    '035420.KS',    # NAVER
    '035720.KS',    # Kakao
    '051910.KS',    # LG Chem
    '068270.KS',    # Celltrion
    
    # Japanese Stocks
    '7203.T',       # Toyota
    '6758.T',       # Sony
    '9984.T',       # SoftBank Group
    
    # Chinese Stocks
    'BABA',         # Alibaba
    'TCEHY',        # Tencent
    'PDD',          # PDD Holdings (Pinduoduo)
    'BIDU',         # Baidu
]

def main():
    try:
        # Get Alpha Vantage API key from settings
        try:
            api_key = settings.ALPHA_VANTAGE_API_KEY
        except AttributeError:
            logger.error("ALPHA_VANTAGE_API_KEY not found in settings")
            sys.exit(1)
            
        # Initialize service
        service = AlphaVantageService(api_key)
        service.client.request_delay = 15  # Adjust for rate limiting if needed
        
        logger.info(f"Starting to add {len(STOCK_SYMBOLS)} stock symbols")
        
        # Track progress
        successful = 0
        failed = 0
        
        # Process each symbol
        for i, symbol in enumerate(STOCK_SYMBOLS, 1):
            logger.info(f"Processing {i}/{len(STOCK_SYMBOLS)}: {symbol}")
            
            try:
                # First try to add basic stock info
                stock = service.update_stock_data(symbol)
                logger.info(f"Added stock: {stock.symbol} - {stock.stock_name}")
                successful += 1
                
            except Exception as e:
                logger.error(f"Failed to add stock {symbol}: {str(e)}")
                failed += 1
            
            # Progress update
            logger.info(f"Progress: {i}/{len(STOCK_SYMBOLS)} - Success: {successful}, Failed: {failed}")
            
        # Final summary
        logger.info(f"Completed adding stocks. Success: {successful}, Failed: {failed}")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"Script started at {start_time}")
    
    main()
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Script completed at {end_time}")
    logger.info(f"Total duration: {duration}")