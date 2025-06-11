# tu_app/templatetags/range_filters.py
from django import template
register = template.Library()

@register.filter
def get_range(start, end):
    """
    Retorna un rango de números: {% for y in 2022|get_range:2030 %}
    """
    return range(int(start), int(end) + 1)
