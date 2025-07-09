from django import template

register = template.Library()

@register.filter
def div(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return ''
    
@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
    
@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg) if arg else None
    except (ValueError, ZeroDivisionError):
        return None
    
@register.filter    
def minus(value, arg):
    return float(value) - float(arg)    


@register.filter
def index(sequence, position):
    try:
        return sequence[int(position)]
    except (IndexError, ValueError, TypeError):
        return 0