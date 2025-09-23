# apphinc/templatetags/custom_filters.py (new file)
from django import template

register = template.Library()

@register.filter
def currency(value):
    try:
        formatted = '{:,.0f}'.format(float(value)).replace(',', '.')
        return f'${formatted}'
    except (ValueError, TypeError):
        return value