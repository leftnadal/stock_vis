# Alpha Vantage API settings
# Add these to your settings.py file

# Get your API key from https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY = 'your_api_key_here'

# Optional: Configure Alpha Vantage specific logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/alpha_vantage.log',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'alpha_vantage': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'stocks.management.commands.update_stock_data': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Optional: Configure PostgreSQL database settings
"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'stock_javis_db',
        'USER': 'postgres',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
"""