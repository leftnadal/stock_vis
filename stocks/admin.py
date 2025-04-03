from django.contrib import admin
from .models import Stock

# Register your models here.

@admin.register(Stock)
class Stockadmin(admin.ModelAdmin):
    list_display = ('stock_name', 'symbol', 'real_time_price', 'exchange','overview','last_updated')
    search_fields = ('stock_name', 'symbol')