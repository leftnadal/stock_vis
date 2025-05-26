# Alpha Vantage Integration for Stock Javis System

This module integrates Alpha Vantage's financial API with the Stock Javis Django backend, allowing you to fetch and store stock data in your PostgreSQL database.

## Getting Started

### Prerequisites

1. Get a free API key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
2. Add the API key to your Django settings:

```python
# In settings.py
ALPHA_VANTAGE_API_KEY = 'your_api_key_here'
```

### Directory Structure

```
alpha_vantage/
  ├── __init__.py
  ├── client.py        # API client for Alpha Vantage
  ├── processor.py     # Process and transform API data
  ├── service.py       # Database operations service
  └── README.md        # This file
```

## Usage

### From Command Line

Use the Django management command to update stock data:

```bash
# Update all data for specific stocks
python manage.py update_stock_data --symbols AAPL,MSFT,GOOGL

# Update all stocks in database
python manage.py update_stock_data --all

# Update only price data
python manage.py update_stock_data --symbols AAPL --prices-only

# Fetch full price history (20+ years)
python manage.py update_stock_data --symbols AAPL --full-history

# Custom delay between requests (in seconds)
python manage.py update_stock_data --symbols AAPL --delay 15
```

### From Admin UI

Use the provided API endpoint to update stock data from the admin interface:

```
POST /api/v1/stocks/api/update-data/
```

Request body parameters:

- `symbol`: Stock symbol to update (required)
- `update_type`: Type of update ('all', 'prices', 'overview', 'financials')
- `full_history`: Whether to fetch full price history (boolean)

### From Python Code

```python
from django.conf import settings
from alpha_vantage.service import AlphaVantageService

# Initialize the service with your API key
service = AlphaVantageService(settings.ALPHA_VANTAGE_API_KEY)

# Update all data for a stock
results = service.update_all_stock_data('AAPL')

# Update stock overview
stock = service.update_stock_data('MSFT')

# Update historical prices
count = service.update_historical_prices('GOOGL', days=100)

# Update financial statements
financials = service.update_financial_statements('TSLA')
print(f"Updated {financials['balance_sheet']} balance sheets")
print(f"Updated {financials['income_statement']} income statements")
print(f"Updated {financials['cash_flow']} cash flow statements")
```

## Rate Limits

Alpha Vantage has different rate limits depending on your subscription:

- Free tier: 5 API calls per minute, 500 API calls per day
- Premium plans: Higher limits

The service includes built-in rate limiting to respect these constraints. By default, it adds a 12-second delay between requests (5 calls per minute). You can adjust this with the `request_delay` parameter:

```python
service = AlphaVantageService(api_key)
service.client.request_delay = 15  # 15 seconds between requests
```

## Error Handling

The service includes comprehensive error handling:

- API errors (invalid symbols, rate limiting, etc.)
- Connection issues
- Data parsing errors
- Database errors

Errors are logged and propagated appropriately.

## Data Processing

The service automatically processes Alpha Vantage data to match your Django models:

- Standardizes field names
- Converts data types (e.g., strings to Decimal)
- Maps API fields to model fields
- Handles date parsing

## Scheduled Updates

For production, consider setting up scheduled updates using Django's management commands with a cron job:

```bash
# Example crontab entry to update major stocks daily at 6:00 AM
0 6 * * * cd /path/to/your/project && /path/to/your/venv/bin/python manage.py update_stock_data --symbols AAPL,MSFT,GOOGL,AMZN,TSLA >> /path/to/logs/stock_update.log 2>&1
```

Or use Celery for more complex scheduling:

```python
# In your Celery tasks file
@shared_task
def update_stock_task(symbol):
    from django.conf import settings
    from alpha_vantage.service import AlphaVantageService

    service = AlphaVantageService(settings.ALPHA_VANTAGE_API_KEY)
    return service.update_all_stock_data(symbol)
```
