from django import template
register = template.Library()

@register.simple_tag
def get_presupuesto(presup_dict, tipo_id, mes):
    return presup_dict.get((tipo_id, mes))

@register.filter
def get_item(dictionary, key):
    """Returns the value for a given key in a dictionary."""
    return dictionary.get(key)