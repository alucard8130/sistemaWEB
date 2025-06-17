from django import template

register = template.Library()

@register.filter
def porcentaje(var, presup):
    try:
        presup = float(presup)
        if presup == 0:
            return ''
        return '{:.0f}%'.format((float(var) / presup) * 100)
    except (ValueError, ZeroDivisionError, TypeError):
        return ''
