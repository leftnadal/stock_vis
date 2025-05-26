# PostgreSQL Setup for Stock Javis System

This guide explains how to set up PostgreSQL for your Django Stock Javis System.

## Install PostgreSQL

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

### macOS (using Homebrew)

```bash
brew install postgresql
brew services start postgresql
```

### Windows

Download and install from [PostgreSQL website](https://www.postgresql.org/download/windows/)

## Create Database and User

1. Login to PostgreSQL:

```bash
sudo -u postgres psql
```

2. Create a database:

```sql
CREATE DATABASE stock_javis_db;
```

3. Create a user:

```sql
CREATE USER stock_javis_user WITH PASSWORD 'your_secure_password';
```

4. Grant privileges:

```sql
GRANT ALL PRIVILEGES ON DATABASE stock_javis_db TO stock_javis_user;
ALTER USER stock_javis_user WITH SUPERUSER;
```

5. Exit PostgreSQL:

```sql
\q
```

## Configure Django Settings

1. Install Python PostgreSQL adapter:

```bash
pip install psycopg2-binary
```

2. Add to your `settings.py` file:

```python
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

## Migrate Your Models

Run Django migrations to create tables in PostgreSQL:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Useful PostgreSQL Commands

- Connect to the database:

```bash
psql -U stock_javis_user -d stock_javis_db
```

- List all tables:

```sql
\dt
```

- Describe a table:

```sql
\d+ stocks_stock
```

- Execute SQL query:

```sql
SELECT * FROM stocks_stock LIMIT 5;
```

- Export data:

```bash
pg_dump -U stock_javis_user -d stock_javis_db > backup.sql
```

- Import data:

```bash
psql -U stock_javis_user -d stock_javis_db < backup.sql
```
