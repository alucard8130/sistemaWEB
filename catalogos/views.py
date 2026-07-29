import openpyxl
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction
from django import forms
from clientes.models import Cliente       # ajusta el import real de tu app de clientes
from empresas.models import Empresa
from proveedores.models import Proveedor  # ajusta el import real de tu app de proveedores


def _empresa_del_usuario(request):
    if request.user.is_superuser:
        empresa_id = request.session.get('empresa_id')
        return Empresa.objects.filter(id=empresa_id).first() if empresa_id else None
    perfil = getattr(request.user, 'perfilusuario', None)
    return perfil.empresa if perfil else None


class CargaMasivaClientesProveedoresForm(forms.Form):
    archivo = forms.FileField(label='Archivo Excel (.xlsx)')

@login_required
def plantilla_clientes_proveedores_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clientes y Proveedores"
    ws.append(['tipo', 'nombre', 'rfc', 'email', 'telefono'])
    ws.append(['cliente', 'Juan Pérez López', 'PELJ800101ABC', 'juan@ejemplo.com', '5512345678'])
    ws.append(['cliente', 'María González', '', '', ''])
    ws.append(['proveedor', 'Suministros del Valle SA de CV', 'SVA050101XYZ', 'contacto@suministros.com', ''])
    ws.append(['proveedor', 'Mantenimientos Integrales', '', '', ''])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_clientes_proveedores.xlsx'
    wb.save(response)
    return response


@login_required
def carga_masiva_clientes_proveedores(request):
    empresa = _empresa_del_usuario(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect('dashboard_inicio')

    if request.method == 'POST':
        form = CargaMasivaClientesProveedoresForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            wb = openpyxl.load_workbook(archivo, data_only=True)
            ws = wb.active

            errores = []
            clientes_creados = 0
            clientes_reutilizados = 0
            proveedores_creados = 0
            proveedores_reutilizados = 0

            with transaction.atomic():
                for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if not row or all((c is None or (isinstance(c, str) and c.strip() == "")) for c in row):
                        continue

                    try:
                        tipo = str(row[0]).strip().lower() if row[0] not in (None, "") else None
                        nombre = str(row[1]).strip() if len(row) > 1 and row[1] not in (None, "") else None
                        rfc = str(row[2]).strip().upper() if len(row) > 2 and row[2] not in (None, "") else None
                        email = str(row[3]).strip() if len(row) > 3 and row[3] not in (None, "") else None
                        telefono = str(row[4]).strip() if len(row) > 4 and row[4] not in (None, "") else None

                        if tipo not in ('cliente', 'proveedor'):
                            raise Exception(f"Tipo '{tipo}' inválido. Usa 'cliente' o 'proveedor'.")
                        if not nombre:
                            raise Exception("Nombre vacío.")

                        if tipo == 'cliente':
                            if rfc:
                                cliente, creado = Cliente.objects.get_or_create(
                                    empresa=empresa, rfc=rfc,
                                    defaults={'nombre': nombre, 'email': email or None}
                                )
                            else:
                                cliente = Cliente.objects.filter(
                                    empresa=empresa, rfc__isnull=True, nombre__iexact=nombre
                                ).first()
                                creado = cliente is None
                                if creado:
                                    cliente = Cliente.objects.create(
                                        empresa=empresa, nombre=nombre, email=email or None
                                    )
                            if creado:
                                clientes_creados += 1
                            else:
                                clientes_reutilizados += 1
                                if telefono and not getattr(cliente, 'telefono', None):
                                    cliente.telefono = telefono
                                    cliente.save(update_fields=['telefono'])

                        else:
                            if rfc:
                                proveedor, creado = Proveedor.objects.get_or_create(
                                    empresa=empresa, rfc=rfc,
                                    defaults={'nombre': nombre, 'email': email or None, 'telefono': telefono or None}
                                )
                            else:
                                proveedor = Proveedor.objects.filter(
                                    empresa=empresa, rfc__isnull=True, nombre__iexact=nombre
                                ).first()
                                creado = proveedor is None
                                if creado:
                                    proveedor = Proveedor.objects.create(
                                        empresa=empresa, nombre=nombre, email=email or None, telefono=telefono or None
                                    )
                            if creado:
                                proveedores_creados += 1
                            else:
                                proveedores_reutilizados += 1

                    except Exception as e:
                        errores.append(f"Fila {i}: {str(e)}")

            resumen = (
                f"✅ Clientes: {clientes_creados} nuevos, {clientes_reutilizados} ya existían. "
                f"Proveedores: {proveedores_creados} nuevos, {proveedores_reutilizados} ya existían."
            )
            messages.success(request, resumen)
            if errores:
                from django.utils.safestring import mark_safe
                msg = "<br>".join(errores[:80])
                if len(errores) > 80:
                    msg += f"<br>...y {len(errores)-80} errores más."
                messages.error(request, mark_safe("Algunas filas tuvieron problemas:<br>" + msg))

            return redirect('carga_masiva_clientes_proveedores')
    else:
        form = CargaMasivaClientesProveedoresForm()

    return render(request, 'catalogos/carga_masiva_clientes_proveedores.html', {'form': form})