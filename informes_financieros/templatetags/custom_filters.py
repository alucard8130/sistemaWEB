from django import template

register = template.Library()

@register.filter
def get_range(start, end):
    """Devuelve un rango de números desde start hasta end-1 (igual que range en Python)."""
    return range(int(start), int(end))