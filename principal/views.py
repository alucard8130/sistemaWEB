
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
import openpyxl
from empleados.models import Empleado
from empresas.models import Empresa
from clientes.models import Cliente
from gastos.models import Gasto
from locales.models import LocalComercial
from areas.models import AreaComun
from facturacion.models import Factura, Pago
from presupuestos.models import Presupuesto
from principal.models import AuditoriaCambio
from proveedores.models import Proveedor
# Create your views here.

@login_required
def bienvenida(request):
    empresa = None
    if not request.user.is_superuser:
        empresa = request.user.perfilusuario.empresa
    return render(request, 'bienvenida.html', {
        'empresa': empresa,
    })

@staff_member_required
@login_required
def reiniciar_sistema(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Orden: pagos > facturas > locales/areas > clientes > empresas etc...
                Pago.objects.all().delete()
                Factura.objects.all().delete()
                LocalComercial.objects.all().delete()
                AreaComun.objects.all().delete()
                Cliente.objects.all().delete()
                #Empresa.objects.all().delete()
                Proveedor.objects.all().delete() 
                Empleado.objects.all().delete()  
                Gasto.objects.all().delete()  
                Presupuesto.objects.all().delete()
                

            messages.success(request, '¡El sistema fue reiniciado exitosamente!')
        except Exception as e:
            messages.error(request, f'Error al reiniciar: {e}')
        return redirect('bienvenida')
    return render(request, 'reiniciar_sistema.html')

@staff_member_required
def respaldo_empresa_excel(request):
    from django.shortcuts import render
    # Si no hay empresa seleccionada, muestra el formulario
    if request.method == 'GET' and 'empresa_id' not in request.GET:
        empresas = Empresa.objects.all()
        return render(request, 'respaldo_empresas.html', {'empresas': empresas})

    empresa_id = request.GET.get('empresa_id')
    empresa = Empresa.objects.get(pk=empresa_id)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Borra hoja por defecto

    # CLIENTES
    ws = wb.create_sheet("Clientes")
    ws.append(['id', 'nombre', 'rfc', 'telefono', 'email', 'activo'])
    for c in Cliente.objects.filter(empresa=empresa):
        ws.append([c.id, c.nombre, c.rfc, c.telefono, c.email, c.activo])

    # LOCALES
    ws = wb.create_sheet("Locales")
    ws.append(['id', 'numero', 'cliente', 'ubicacion', 'superficie_m2', 'cuota', 'status', 'activo', 'observaciones'])
    for l in LocalComercial.objects.filter(empresa=empresa):
        ws.append([l.id, l.numero, l.cliente.nombre if l.cliente else "", l.ubicacion, l.superficie_m2, l.cuota, l.status, l.activo, l.observaciones])

    # ÁREAS COMUNES
    ws = wb.create_sheet("Áreas Comunes")
    ws.append([ 'cliente', 'numero', 'cuota', 'ubicacion', 'superficie_m2', 'status', 'fecha_inicial', 'fecha_fin', 'activo', 'observaciones'])
    for a in AreaComun.objects.filter(empresa=empresa):
        ws.append([
             a.cliente.nombre if a.cliente else '', a.numero, a.cuota, a.ubicacion, a.superficie_m2,
            a.status, str(a.fecha_inicial) if a.fecha_inicial else '', str(a.fecha_fin) if a.fecha_fin else '', a.activo, a.observaciones
        ])

    # FACTURAS
    ws = wb.create_sheet("Facturas")
    ws.append(['folio', 'cliente', 'local', 'area_comun', 'monto', 'fecha_emision', 'fecha_vencimiento', 'estatus'])
    for f in Factura.objects.filter(empresa=empresa):
        ws.append([
            f.folio, f.cliente.nombre if f.cliente else '', 
            f.local.numero if f.local else '', f.area_comun.numero if f.area_comun else '',
            f.monto, str(f.fecha_emision), str(f.fecha_vencimiento), f.estatus
        ])

    # PAGOS
    ws = wb.create_sheet("Pagos")
    ws.append(['id', 'factura', 'fecha_pago', 'monto', 'registrado_por'])
    for p in Pago.objects.filter(factura__empresa=empresa):
        ws.append([
            p.id, p.factura.folio if p.factura else '', str(p.fecha_pago), p.monto, 
            p.registrado_por.get_full_name() if p.registrado_por else ''
        ])
    # GASTOS
    ws = wb.create_sheet("Gastos")  
    ws.append(['id', 'proveedor', 'empleado','descripcion', 'monto','tipo_gasto', 'fecha'])
    for g in Gasto.objects.filter(empresa=empresa):
        ws.append([g.id,str(g.proveedor),str(g.empleado), g.descripcion, g.monto, str(g.tipo_gasto), str(g.fecha)])  

    #pago gastos
    ws = wb.create_sheet("Pagos Gastos")
    ws.append(['id', 'referencia', 'fecha_pago', 'monto', 'registrado_por'])
    for g in Gasto.objects.filter(empresa=empresa):
        for pago in g.pagos.all():
            ws.append([
                pago.id, pago.referencia, str(pago.fecha_pago), pago.monto, 
                pago.registrado_por.get_full_name() if pago.registrado_por else ''
            ])

    # PRESUPUESTOS
    ws = wb.create_sheet("Presupuestos")
    ws.append(['id', 'empresa', 'grupo', 'subgrupo', 'tipo_gasto', 'anio', 'mes', 'monto'])
    for p in Presupuesto.objects.filter(empresa=empresa):
        ws.append([
            p.id, p.empresa.nombre if p.empresa else '', str(p.grupo), str(p.subgrupo), 
            str(p.tipo_gasto), p.anio, p.mes, p.monto
        ])  
    # EMPLEADOS
    ws = wb.create_sheet("Empleados")
    ws.append(['id', 'nombre', 'email', 'telefono', 'puesto', 'activo'])
    for e in Empleado.objects.filter(empresa=empresa):
        ws.append([e.id, e.nombre, e.email, e.telefono, e.puesto, e.activo])
    # PROVEEDORES
    ws = wb.create_sheet("Proveedores")
    ws.append(['id', 'nombre', 'rfc', 'telefono', 'email', 'activo'])
    for p in Proveedor.objects.filter(empresa=empresa):
        ws.append([p.id, str(p.nombre), p.rfc, p.telefono, p.email, p.activo])
    # 


    # Responde el archivo Excel
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=respaldo_empresa_{empresa.nombre}.xlsx'
    wb.save(response)
    return response

@staff_member_required  # Solo para admin/superusuario, opcional
def reporte_auditoria(request):
    modelo = request.GET.get('modelo')
    queryset = AuditoriaCambio.objects.all().order_by('-fecha_cambio')
    if modelo in ['local', 'area', 'factura']:
        queryset = queryset.filter(modelo=modelo)
    return render(request, 'auditoria/reporte.html', {'auditorias': queryset, 'modelo': modelo})