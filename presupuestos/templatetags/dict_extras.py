from django import template
register = template.Library()

#@register.simple_tag
#def get_presupuesto(presup_dict, tipo_id, mes):
 #   return presup_dict.get((tipo_id, mes))

@register.filter
def get_item(dictionary, key):
    if dictionary:
        return dictionary.get(key, 0)
    return 0