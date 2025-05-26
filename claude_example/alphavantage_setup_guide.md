# Setting Up Alpha Vantage Integration with PostgreSQL

This guide walks you through the complete setup process for integrating Alpha Vantage with your Stock Javis Django project and configuring PostgreSQL as your database.

## 1. Install Required Packages

First, add the required packages to your Poetry environment:

```bash
poetry add psycopg2-binary requests
```

Or if you're using pip:

```bash
pip install psycopg2-binary requests
```

## 2. Set Up PostgreSQL

Follow the instructions in `postgresql_setup.md` to:

1. Install PostgreSQL
2. Create a database and user
3. Configure permissions

## 3. Configure Django Settings

Add the Alpha Vantage API key and PostgreSQL database settings to your `settings.py`:

```python
# Alpha Vantage API settings
ALPHA_VANTAGE_API_KEY = 'your_api_key_here'  # Get from https://www.alphavantage.co/support/#api-key

# PostgreSQL Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'stock_javis_db',
        'USER': 'stock_javis_user',
        'PASSWORD': 'your_secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 4. Run Migrations

Apply migrations to create the necessary database tables:

```bash
python manage.py migrate
```

## 5. Test the Integration

Try updating data for a stock to verify everything works:

```bash
# Update a single stock (e.g., Apple)
python manage.py update_stock_data --symbols AAPL
```

If successful, you should see output confirming the data has been updated.

## 6. Populate the Database

Now you can populate your database with more stocks:

```bash
# Update data for major tech companies
python manage.py update_stock_data --symbols AAPL,MSFT,GOOGL,AMZN,META
```

For global market coverage, consider adding more diverse stocks:

```bash
# Add more diverse stocks
python manage.py update_stock_data --symbols TSLA,JPM,V,WMT,JNJ,PG,XOM,BAC,DIS,NFLX
```

## 7. Set Up Scheduled Updates

For production, set up a cron job to regularly update your stock data:

```bash
# Edit crontab
crontab -e

# Add a daily update at 6:00 AM
0 6 * * * cd /path/to/your/project && /path/to/your/venv/bin/python manage.py update_stock_data --all >> /path/to/logs/stock_update.log 2>&1
```

## 8. Troubleshooting

### Rate Limiting

If you encounter rate limit errors, increase the delay between requests:

```bash
python manage.py update_stock_data --symbols AAPL --delay 20
```

### API Key Issues

If you see authentication errors, verify your API key is correct and active.

### Database Connection Issues

If you have trouble connecting to PostgreSQL, check:

- PostgreSQL service is running
- Database name, username, and password are correct
- Host and port settings match your PostgreSQL configuration

### Data Import Errors

If certain stocks fail to update, check:

- The symbol is valid and active on Alpha Vantage
- You have sufficient API calls remaining
- Your models are compatible with the API data structure

## 9. Monitoring

Consider setting up monitoring for your database and API usage:

```python
# In settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/alpha_vantage.log',
        },
    },
    'loggers': {
        'alpha_vantage': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```
