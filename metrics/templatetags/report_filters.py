"""Django template filters for daily_report.html."""
from django import template

register = template.Library()


@register.filter(name="get_item")
def get_item(d, key):
    """dict[key] — 템플릿에서 dynamic key 접근용."""
    if isinstance(d, dict):
        return d.get(key, "")
    return ""
