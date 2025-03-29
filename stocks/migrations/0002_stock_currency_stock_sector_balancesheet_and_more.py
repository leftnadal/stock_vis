# Generated by Django 5.1.7 on 2025-03-25 09:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='stock',
            name='currency',
            field=models.CharField(choices=[('usd', 'USD'), ('won', 'WON')], default='USD', max_length=10),
        ),
        migrations.AddField(
            model_name='stock',
            name='sector',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.CreateModel(
            name='BalanceSheet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reported_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('currency', models.CharField(choices=[('usd', 'USD'), ('won', 'WON')], default='USD', max_length=10)),
                ('fidcal_date_ending', models.DateField(blank=True, null=True)),
                ('period_type', models.CharField(choices=[('annual', 'Annual'), ('quarter', 'Quarterly')], max_length=10)),
                ('fiscal_year', models.IntegerField(blank=True, null=True)),
                ('fiscal_quarter', models.IntegerField(blank=True, null=True)),
                ('current_year', models.IntegerField(blank=True, null=True)),
                ('prior_year', models.IntegerField(blank=True, null=True)),
                ('total_assets', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('total_current_assets', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('cash_and_cash_equivalents_at_carrying_value', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('cash_and_short_term_investments', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('inventory', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('current_net_receivables', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('total_non_current_assets', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('property_plant_equipment', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('accumulated_depreciation_amortization_ppe', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('intangible_assets', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('intangible_assets_excluding_goodwill', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('goodwill', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('investments', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('long_term_investments', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('short_term_investments', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('other_non_current_assets', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stocks.stock')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CashFlowStatement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reported_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('currency', models.CharField(choices=[('usd', 'USD'), ('won', 'WON')], default='USD', max_length=10)),
                ('fidcal_date_ending', models.DateField(blank=True, null=True)),
                ('period_type', models.CharField(choices=[('annual', 'Annual'), ('quarter', 'Quarterly')], max_length=10)),
                ('fiscal_year', models.IntegerField(blank=True, null=True)),
                ('fiscal_quarter', models.IntegerField(blank=True, null=True)),
                ('current_year', models.IntegerField(blank=True, null=True)),
                ('prior_year', models.IntegerField(blank=True, null=True)),
                ('operating_cashflow', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('payments_for_operating_activities', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('proceeds_from_operating_activities', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('change_in_operating_liabilities', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('change_in_operating_assets', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('depreciation_depletion_and_amortization', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('capital_expenditures', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('change_in_receivables', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('change_in_inventory', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('profit_loss', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('cashflow_from_investment', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('cashflow_from_financing', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('proceeds_from_repayments_of_short_term_debt', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('payments_for_repurchase_of_common_stock', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('payments_for_repurchase_of_equity', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('payments_for_repurchase_of_preferred_stock', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('dividend_payout', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('dividend_payout_common_stock', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('dividend_payout_preferred_stock', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('proceeds_from_issuance_of_common_stock', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('proceeds_from_issuance_of_long_term_debt_and_capital_securities_net', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('proceeds_from_issuance_of_preferred_stock', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('proceeds_from_repurchase_of_equity', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('proceeds_from_sale_of_treasury_stock', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('change_in_cash_and_cash_equivalents', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('change_in_exchange_rate', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('net_income', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stocks.stock')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IncomeStatement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reported_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('currency', models.CharField(choices=[('usd', 'USD'), ('won', 'WON')], default='USD', max_length=10)),
                ('fidcal_date_ending', models.DateField(blank=True, null=True)),
                ('period_type', models.CharField(choices=[('annual', 'Annual'), ('quarter', 'Quarterly')], max_length=10)),
                ('fiscal_year', models.IntegerField(blank=True, null=True)),
                ('fiscal_quarter', models.IntegerField(blank=True, null=True)),
                ('current_year', models.IntegerField(blank=True, null=True)),
                ('prior_year', models.IntegerField(blank=True, null=True)),
                ('total_revenue', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('gross_profit', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('cost_of_revenue', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('cost_of_goods_and_services_sold', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('selling_General_And_Administrative', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('operating_expenses', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('research_and_development', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('depreciation_and_amortization', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('other_nonOperating_income', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('interest_expense', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('operating_income', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('net_income', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('ebitda', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stocks.stock')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='HistoricalPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency', models.CharField(choices=[('usd', 'USD'), ('won', 'WON')], default='USD', max_length=10)),
                ('date', models.DateField()),
                ('open_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('high_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('low_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('close_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('volume', models.BigIntegerField()),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_history', to='stocks.stock')),
            ],
            options={
                'unique_together': {('stock', 'date')},
            },
        ),
    ]
