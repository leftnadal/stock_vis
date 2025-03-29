from django.contrib import admin
from .models import EconomicIndicator

# Register your models here.
@admin.register(EconomicIndicator)
class EconomicIndicatorAdmin(admin.ModelAdmin):
    list_display = ('indicator_name', 'value', 'unit')
    search_fields = ('indicator_name', 'value')
