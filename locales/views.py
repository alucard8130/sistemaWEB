
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
import openpyxl
from clientes.models import Cliente
from empresas.models import Empresa
import locales
from principal.models import AuditoriaCambio
from .models import LocalComercial
from .forms import LocalCargaMasivaForm, LocalComercialForm
from django.contrib.admin.views.decorators import staff_member_required
from unidecode import unidecode
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Sum, Avg


@login_required
def lista_locales(request):
    user = request.user
    query = request.GET.get("q", "")
    if user.is_superuser:
        empresa_id = request.session.get("empresa_id")
        if empresa_id:
            locales = LocalComercial.objects.filter(activo=True, empresa_id=empresa_id).select_related('cliente', 'empresa').order_by('numero')
        else:
            locales = LocalComercial.objects.filter(activo=True).select_related('cliente', 'empresa').order_by('numero')
    else:
        empresa = user.perfilusuario.empresa
        locales = LocalComercial.objects.filter(empresa=empresa, activo=True).select_related('cliente', 'empresa').order_by('numero')

    if query:
        locales = locales.filter(
            Q(numero__icontains=query) | Q(cliente__nombre__icontains=query) | Q(cliente__rfc__icontains=query)
        )

    locales = locales.order_by('numero')
    locales_totales_activos =locales.count()  
    total_superficie = locales.aggregate(Sum('superficie_m2'))['superficie_m2__sum'] or 0
    superficie_ocupada = locales.filter(status='ocupado').aggregate(Sum('superficie_m2'))['superficie_m2__sum'] or 0
    superficie_disponible = total_superficie - superficie_ocupada   
    total_cuotas = locales.aggregate(Sum('cuota'))['cuota__sum'] or 0
    promedio_cuotas = locales.aggregate(Avg('cuota'))['cuota__avg'] or 0
    promedio_precio_m2 = total_superficie > 0 and (total_cuotas / total_superficie) or 0
    porcentaje_ocupacion = (superficie_ocupada / total_superficie * 100) if total_superficie > 0 else 0
    
    # Paginación
    paginator = Paginator(locales, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'locales/lista_locales.html', {'locales': page_obj, 'q': query, 
                                                          'locales_totales_activos': locales_totales_activos,
                                                          'total_superficie': total_superficie,
                                                          'superficie_ocupada': superficie_ocupada,
                                                          'superficie_disponible': superficie_disponible,
                                                          'total_cuotas': total_cuotas,
                                                          'promedio_cuotas': promedio_cuotas,
                                                          'promedio_precio_m2': promedio_precio_m2,
                                                          'porcentaje_ocupacion': porcentaje_ocupacion,
                                                          })

@login_required
def crear_local(request):
    user = request.user
    perfil = getattr(user, 'perfilusuario', None)
    
    if request.method == 'POST':
        form = LocalComercialForm(request.POST, user=user)
        if form.is_valid():
            local = form.save(commit=False)
            # Si no es superusuario, asignamos su empresa
            if not user.is_superuser and perfil and perfil.empresa:
                local.empresa = perfil.empresa
            local.save()
            messages.success(request, "Local creado correctamente.")
            return redirect('lista_locales')
        else:
            messages.error(request, "No se pudo crear el local. Revisa los datos ingresados.")
    else:
        form = LocalComercialForm(user=user)
        # Si no es superusuario, asignamos la empresa inicial al form
        if not user.is_superuser and perfil and perfil.empresa:
            form.fields['empresa'].initial = perfil.empresa

    return render(request, 'locales/crear_local.html', {'form': form})

@login_required
def editar_local(request, pk):
    user = request.user
    local= get_object_or_404(LocalComercial, pk=pk)
 
    if not user.is_superuser and local.empresa != user.perfilusuario.empresa:
        return redirect('lista_locales')

    if request.method == 'POST':
        form = LocalComercialForm(request.POST, instance=local, user=user)
        if form.is_valid():
            local_original = LocalComercial.objects.get(pk=pk)
            local_modificado = form.save(commit=False)
            for field in form.changed_data:
                valor_anterior = getattr(local_original, field)
                valor_nuevo = getattr(local_modificado, field)
                AuditoriaCambio.objects.create(
                    modelo='local',
                    objeto_id=local.pk,
                    campo=field,
                    valor_anterior=valor_anterior,
                    valor_nuevo=valor_nuevo,
                    usuario=request.user,
                )
            form.save()
            messages.success(request, "Local actualizado correctamente.")
            return redirect('lista_locales')
    else:
        form = LocalComercialForm(instance=local, user=user)

    return render(request, 'locales/editar_local.html', {'form': form, 'local': local})

@login_required
def eliminar_local(request, pk):
    user = request.user
    local= get_object_or_404(LocalComercial, pk=pk)
    if not user.is_superuser and local.empresa != user.perfilusuario.empresa:
        return redirect('lista_locales')

    if request.method == 'POST':
        local.activo = False
        local.save()
        return redirect('lista_locales')

    return render(request, 'locales/eliminar_local.html', {'local': local})


@login_required
def locales_inactivos(request):
    user = request.user
    if user.is_superuser:
        empresa_id = request.session.get("empresa_id")
        if empresa_id:
            locales = LocalComercial.objects.filter(empresa_id=empresa_id, activo=False)
        else:
            locales = LocalComercial.objects.filter(activo=False)
    else:
        empresa = user.perfilusuario.empresa
        locales = LocalComercial.objects.filter(empresa=empresa, activo=False)
    return render(request, 'locales/locales_inactivos.html', {'locales': locales})


def reactivar_local(request, pk):
    local = get_object_or_404(LocalComercial, pk=pk, activo=False)

    if request.method == 'POST':
        local.activo = True
        local.save()
        return redirect('locales_inactivos')

    return render(request, 'locales/reactivar_confirmacion.html', {'local': local})

@login_required
def incrementar_cuotas_locales(request):
    if request.method == 'POST':
        porcentaje = request.POST.get('porcentaje')
        try:
            porcentaje = Decimal(porcentaje)
            empresa = None
            if not request.user.is_superuser and hasattr(request.user, 'perfilusuario'):
                empresa = request.user.perfilusuario.empresa
                locales = LocalComercial.objects.filter(empresa=empresa, activo=True)
            else:
                locales = LocalComercial.objects.filter(activo=True)

            for local in locales:
                cuota_anterior = local.cuota
                incremento = cuota_anterior * (porcentaje / Decimal('100'))
                local.cuota += incremento
                local.save()

            messages.success(request, f'Se incrementaron las cuotas en un {porcentaje}% para todos los locales activos.')
            return redirect('incrementar_c_locales')
        except:
            messages.error(request, 'Porcentaje inválido.')
    
    return render(request, 'locales/incrementar_c_locales.html')

def buscar_por_id_o_nombre(modelo, valor, campo='nombre'):
    if not valor:
        return None
    val = str(valor).strip().replace(',', '')
    try:
        return modelo.objects.get(pk=int(val))
    except (ValueError, modelo.DoesNotExist):
        todos = modelo.objects.all()
        candidatos = [
            obj for obj in todos
            if unidecode(val).lower() in unidecode(str(getattr(obj, campo))).lower()
        ]
        if len(candidatos) == 1:
            return candidatos[0]
        elif len(candidatos) > 1:
            conflicto = "; ".join([f"ID={obj.pk}, {campo}='{getattr(obj, campo)}'" for obj in candidatos])
            raise Exception(f"Conflicto: '{valor}' coincide con varios registros en {modelo.__name__}: {conflicto}")
        raise Exception(f"No se encontró '{valor}' en {modelo.__name__}")

@login_required
def carga_masiva_locales(request):
    if request.method == 'POST':
        form = LocalCargaMasivaForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            wb = openpyxl.load_workbook(archivo, data_only=True)
            ws = wb.active
            errores = []
            exitos = 0

            # detectar encabezado y mapear columnas (si existe)
            header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
            headers_map = {}
            if header:
                hdrs = [str(h).strip().lower() if h is not None else "" for h in header]
                for idx, h in enumerate(hdrs):
                    if h in ('condominio', 'empresa'):
                        headers_map['empresa'] = idx
                    if h in ('propietario',):
                        headers_map['propietario'] = idx
                    if h in ('cliente', 'cliente nombre', 'nombre'):
                        headers_map['cliente'] = idx
                    if h in ('rfc', 'rfc cliente', 'cliente rfc'):
                        headers_map['rfc'] = idx
                    if h in ('email', 'correo', 'correo electronico'):
                        headers_map['email'] = idx
                    if h in ('numero', 'num', 'número'):
                        headers_map['numero'] = idx
                    if h in ('cuota', 'monto', 'importe'):
                        headers_map['cuota'] = idx
                    if h in ('ubicacion',):
                        headers_map['ubicacion'] = idx
                    if h in ('superficie', 'superficie_m2', 'm2'):
                        headers_map['superficie_m2'] = idx
                    if h in ('giro',):
                        headers_map['giro'] = idx
                    if h in ('status', 'estatus'):
                        headers_map['status'] = idx
                    if h in ('observaciones', 'obs', 'comentarios'):
                        headers_map['observaciones'] = idx

            def cell(row, key, pos):
                if key in headers_map:
                    i = headers_map[key]
                    return row[i] if i < len(row) else None
                return row[pos] if pos < len(row) else None

            # iterar filas
            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                # saltar filas totalmente vacías
                if not row or all((c is None or (isinstance(c, str) and c.strip() == "")) for c in row):
                    continue

                try:
                    # leer valores (fallback posicional si no hay headers)
                    empresa_val = cell(row, 'empresa', 0)
                    propietario_val = cell(row, 'propietario', 1)
                    nombre_cliente = cell(row, 'cliente', 2)
                    rfc_cliente = cell(row, 'rfc', 3)
                    email_cliente = cell(row, 'email', 4)
                    numero = cell(row, 'numero', 5)
                    cuota = cell(row, 'cuota', 6)
                    ubicacion = cell(row, 'ubicacion', 7)
                    superficie_m2 = cell(row, 'superficie_m2', 8)
                    giro = cell(row, 'giro', 9)
                    status = cell(row, 'status', 10)
                    observaciones = cell(row, 'observaciones', 11)

                    # determinar empresa (superuser puede especificar, sino usar perfil)
                    if request.user.is_superuser:
                        empresa = buscar_por_id_o_nombre(Empresa, empresa_val) if empresa_val else None
                        if not empresa:
                            raise Exception(f"Fila {i}: No se encontró la empresa '{empresa_val}'")
                    else:
                        perfil = getattr(request.user, 'perfilusuario', None)
                        if not perfil or not getattr(perfil, 'empresa', None):
                            raise Exception("No se pudo determinar la empresa del usuario")
                        empresa = perfil.empresa

                    # número requerido
                    if not numero:
                        raise Exception("Número vacío")

                    # validar unicidad del número por empresa
                    if LocalComercial.objects.filter(empresa=empresa, numero=str(numero)).exists():
                        raise Exception(f"El número de local '{numero}' ya existe para la empresa '{empresa.nombre}'.")

                    # validar cuota
                    try:
                        cuota_decimal = Decimal(str(cuota)) if cuota not in (None, "") else Decimal('0.00')
                    except (InvalidOperation, TypeError, ValueError):
                        raise Exception(f"El valor de cuota '{cuota}' no es válido.")

                    # normalizar rfc y nombre
                    rfc_norm = str(rfc_cliente).strip().upper() if rfc_cliente not in (None, "") else None
                    nombre_norm = str(nombre_cliente).strip() if nombre_cliente not in (None, "") else ""

                    # BUSCAR/CREAR CLIENTE priorizando RFC
                    cliente = None
                    if rfc_norm:
                        cliente = Cliente.objects.filter(empresa=empresa, rfc__iexact=rfc_norm).first()
                        if cliente:
                            # actualizar datos faltantes
                            updated = False
                            if nombre_norm and (not getattr(cliente, 'nombre', None) or cliente.nombre.strip() == ""):
                                cliente.nombre = nombre_norm; updated = True
                            if email_cliente and (not getattr(cliente, 'email', None) or cliente.email.strip() == ""):
                                cliente.email = email_cliente; updated = True
                            if updated:
                                cliente.save()
                        else:
                            # crear con RFC
                            cliente = Cliente.objects.create(
                                empresa=empresa,
                                nombre=nombre_norm or f"Cliente {rfc_norm}",
                                rfc=rfc_norm,
                                email=email_cliente or None,
                                activo=True,
                            )
                    else:
                        # sin RFC: buscar por nombre (preferir registro con RFC)
                        if not nombre_norm:
                            raise Exception("Nombre de cliente vacío y no se proporcionó RFC")
                        qs = Cliente.objects.filter(empresa=empresa, nombre__iexact=nombre_norm)
                        if qs.exists():
                            cliente = qs.filter(rfc__isnull=False).exclude(rfc='').first() or qs.first()
                        else:
                            cliente = Cliente.objects.create(
                                empresa=empresa,
                                nombre=nombre_norm,
                                email=email_cliente or None,
                                activo=True,
                            )

                    # crear local dentro de transacción para cada fila
                    from django.db import transaction
                    with transaction.atomic():
                        LocalComercial.objects.create(
                            empresa=empresa,
                            propietario=propietario_val or "",
                            cliente=cliente,
                            numero=str(numero),
                            cuota=cuota_decimal,
                            ubicacion=ubicacion or "",
                            superficie_m2=Decimal(superficie_m2) if superficie_m2 not in (None, "") else None,
                            giro=giro or "",
                            status=status or "ocupado",
                            observaciones=observaciones or ""
                        )

                    exitos += 1

                except Exception as e:
                    import traceback
                    errores.append(f"Fila {i}: {str(e) or repr(e)}<br>{traceback.format_exc()}")

            # mensajes
            if exitos:
                messages.success(request, f"¡{exitos} locales cargados exitosamente!")
            if errores:
                from django.utils.safestring import mark_safe
                msg = "<br>".join(errores[:80])
                if len(errores) > 80:
                    msg += f"<br>...y {len(errores)-80} errores más."
                messages.error(request, mark_safe("Algunos locales no se cargaron:<br>" + msg))

            return redirect('carga_masiva_locales')
    else:
        form = LocalCargaMasivaForm()
    return render(request, 'locales/carga_masiva_locales.html', {'form': form})

@login_required
def plantilla_locales_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Plantilla Locales"
    ws.append([
        'condominio','propietario', 'cliente', 'rfc','email','numero',  'cuota','ubicacion', 'superficie_m2','giro', 'status', 'observaciones'
    ])
    ws.append([
        'plaza en condominio AC','Tiendas Soriana SA de CV','Juan Pérez','XXX-XXX-XXX','email@ejemplo.com', '101', '120.3', 'planta baja', '30.5','venta ropa', 'ocupado', 'carga inicial'
    ])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_locales.xlsx'
    wb.save(response)
    return response
