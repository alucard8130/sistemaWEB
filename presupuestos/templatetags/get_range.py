# templatetags/presupuesto_tags.py
from django import template
register = template.Library()

@register.filter
def get_range(start, end):
    """Genera una lista de años de start a end (incluyendo ambos)."""
    #return range(start, end+1)
    return range(int(start), int(end))
