from django import template

register = template.Library()

@register.filter
def get_empresa_nombre(empresas, empresa_id):
    for emp in empresas:
        if str(emp.id) == str(empresa_id):
            return emp.nombre
    return "Desconocida"

@register.filter
def get_cliente_nombre(clientes, cliente_id):
    for cli in clientes:
        if str(cli.id) == str(cliente_id):
            return cli.nombre
    return "Desconocido"

@register.filter
def nombre_mes(numero):
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    try:
        return meses[int(numero)-1]
    except:
        return ""


@register.filter
def sin_page(querydict):
    """Query string actual sin el parámetro 'page'.

    Se usa en los enlaces de paginación: '?page=N&{{ request.GET|sin_page }}'.
    Con request.GET.urlencode el 'page' viejo viajaba duplicado y Django
    tomaba el último, por lo que 'Anterior'/'Siguiente' no avanzaban.
    """
    params = querydict.copy()
    params.pop("page", None)
    return params.urlencode()
