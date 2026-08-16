#from empresas.models import CuentaBancaria
import csv
import datetime
import io
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, models, transaction
from django.db.models import Count, Sum

# Create your views here.
from django.shortcuts import get_object_or_404, redirect, render

from clientes.models import Cliente
from conciliaciones.utils import validar_periodo_abierto
from facturacion.models import FacturaOtrosIngresos, TipoOtroIngreso

from .forms import CorteEstacionamientoForm, ImportarTicketsForm
from .models import CorteEstacionamiento, TicketEstacionamiento


@login_required
def lista_cortes(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    if request.user.is_superuser:
        empresa_id = request.GET.get('empresa')
        cortes = CorteEstacionamiento.objects.all()
        if empresa_id:
            cortes = cortes.filter(empresa_id=empresa_id)
    else:
        empresa = perfil.empresa if perfil else None
        cortes = CorteEstacionamiento.objects.filter(empresa=empresa)

    # Filtros opcionales
    periodo = request.GET.get('periodo')
    if periodo:
        cortes = cortes.filter(periodo=periodo)

    # Totales
    totales = cortes.aggregate(
        total_efectivo=Sum('total_efectivo'),
        total_tarjeta=Sum('total_tarjeta'),
        total_boletos=Sum('total_boletos'),
    )

    # NUEVO -- neto real para la plaza (considera renta fija cuando hay operador externo)
    totales['total_neto_plaza'] = sum(c.ingreso_neto_plaza for c in cortes)

    return render(request, 'estacionamiento/lista_cortes.html', {
        'cortes': cortes,
        'totales': totales,
        'periodo_filtro': periodo,
    })


@login_required
def crear_corte(request):
    perfil = getattr(request.user, 'perfilusuario', None)

    if request.user.is_superuser or not perfil or not perfil.empresa:
        messages.error(request, "Esta pantalla es exclusiva de administradores de una empresa.")
        return redirect('lista_cortes_estacionamiento')

    empresa = perfil.empresa

    if request.method == 'POST':
        form = CorteEstacionamientoForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            corte = form.save(commit=False)
            corte.empresa = empresa
            corte.registrado_por = request.user
            corte.save()
            messages.success(request, f"Corte registrado correctamente: {corte.label_periodo}")
            return redirect('lista_cortes_estacionamiento')
    else:
        form = CorteEstacionamientoForm(empresa=empresa)

    return render(request, 'estacionamiento/crear_corte.html', {'form': form})


@login_required
def generar_factura_corte(request, pk):
    corte = get_object_or_404(CorteEstacionamiento, pk=pk)
    empresa = corte.empresa

    if corte.factura:
        messages.info(request, "Este corte ya tiene una factura generada.")
        return redirect('detalle_corte_estacionamiento', pk=pk)

    if corte.ingreso_neto_plaza <= 0:
        messages.error(request, "El ingreso neto de este corte es $0 o negativo, revisa los datos capturados.")
        return redirect('detalle_corte_estacionamiento', pk=pk)

    clientes = Cliente.objects.filter(empresa=empresa, activo=True)
    tipos_ingreso = "Estacionamiento"

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        fecha_vencimiento = request.POST.get('fecha_vencimiento')
        observaciones = request.POST.get('observaciones', '').strip()

        if not cliente_id or not fecha_vencimiento:
            messages.error(request, "Todos los campos marcados con * son obligatorios.")
            return render(request, 'estacionamiento/generar_factura_corte.html', {
                'corte': corte,
                'clientes': clientes,
                'tipos_ingreso': tipos_ingreso,
                'fecha_vencimiento_default': corte.fecha_fin.strftime('%Y-%m-%d'),
            })

        try:
            fecha_venc = datetime.date.fromisoformat(fecha_vencimiento)
        except ValueError:
            messages.error(request, "Fecha de vencimiento inválida.")
            return render(request, 'estacionamiento/generar_factura_corte.html', {
                'corte': corte,
                'clientes': clientes,
                'fecha_vencimiento_default': corte.fecha_fin.strftime('%Y-%m-%d'),
            })

        periodo_valido, error_periodo = validar_periodo_abierto(None, fecha_venc, user=request.user)
        if not periodo_valido:
            messages.error(request, error_periodo)
            return render(request, 'estacionamiento/generar_factura_corte.html', {
                'corte': corte,
                'clientes': clientes,
                'fecha_vencimiento_default': corte.fecha_fin.strftime('%Y-%m-%d'),
            })

        cliente = get_object_or_404(Cliente, pk=cliente_id, empresa=empresa)
        tipo_ingreso, _ = TipoOtroIngreso.objects.get_or_create(empresa=empresa, nombre="Estacionamiento")

        prefix = "EST-F"
        guardado = False
        factura = None

        for intento in range(5):
            try:
                with transaction.atomic():
                    last_folio = (
                        FacturaOtrosIngresos.objects
                        .select_for_update()
                        .filter(empresa=empresa, folio__startswith=prefix)
                        .order_by('-folio')
                        .values_list('folio', flat=True)
                        .first()
                    )
                    if last_folio and re.match(r'^EST-F\d{5}$', last_folio):
                        last_num = int(last_folio.replace(prefix, ""))
                    else:
                        last_num = 0

                    folio = f"{prefix}{last_num + 1:05d}"

                    factura = FacturaOtrosIngresos.objects.create(
                        empresa=empresa,
                        cliente=cliente,
                        tipo_ingreso=tipo_ingreso,
                        folio=folio,
                        fecha_vencimiento=fecha_vencimiento,
                        monto=corte.ingreso_neto_plaza,
                        observaciones=observaciones if observaciones else f"Ingresos por estacionamiento — {corte.label_periodo}",
                        estatus='pendiente',
                    )
                    corte.factura = factura
                    corte.save(update_fields=['factura'])
                    guardado = True
                    break
            except IntegrityError:
                continue

        if guardado:
            messages.success(request, f"Factura {factura.folio} generada por ${corte.ingreso_neto_plaza:,.2f} — regístrala como cobrada desde la lista de Otros Ingresos cuando se deposite.")
            return redirect('lista_cortes_estacionamiento')
        else:
            messages.error(request, "No se pudo generar un folio único. Intenta de nuevo.")

    return render(request, 'estacionamiento/generar_factura_corte.html', {
        'corte': corte,
        'clientes': clientes,
        'fecha_vencimiento_default': corte.fecha_fin.strftime('%Y-%m-%d'),
    })


@login_required
def detalle_corte(request, pk):
    perfil = getattr(request.user, 'perfilusuario', None)

    if request.user.is_superuser:
        corte = get_object_or_404(CorteEstacionamiento, pk=pk)
    else:
        if not perfil or not perfil.empresa:
            messages.error(request, "No se pudo determinar tu empresa.")
            return redirect('lista_cortes_estacionamiento')
        corte = get_object_or_404(CorteEstacionamiento, pk=pk, empresa=perfil.empresa)

    tickets = corte.tickets.all()

    subtotales = tickets.values('forma_pago').annotate(
        total=Sum('monto'),
        cantidad=Count('id')
    )

    return render(request, 'estacionamiento/detalle_corte.html', {
        'corte': corte,
        'tickets': tickets,
        'subtotales': subtotales,
    })


@login_required
def editar_corte(request, pk):
    perfil = getattr(request.user, 'perfilusuario', None)

    if request.user.is_superuser:
        corte = get_object_or_404(CorteEstacionamiento, pk=pk)
        empresa = None
    else:
        if not perfil or not perfil.empresa:
            messages.error(request, "No se pudo determinar tu empresa.")
            return redirect('lista_cortes_estacionamiento')
        corte = get_object_or_404(CorteEstacionamiento, pk=pk, empresa=perfil.empresa)
        empresa = perfil.empresa

    if corte.factura:
        messages.error(request, "Este corte ya tiene una factura generada y no puede editarse.")
        return redirect('detalle_corte_estacionamiento', pk=pk)

    if request.method == 'POST':
        form = CorteEstacionamientoForm(request.POST, request.FILES, instance=corte, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, "Corte actualizado correctamente.")
            return redirect('lista_cortes_estacionamiento')
    else:
        form = CorteEstacionamientoForm(instance=corte, empresa=empresa)

    return render(request, 'estacionamiento/crear_corte.html', {
        'form': form,
        'corte': corte,
        'editando': True,
    })


@login_required
def eliminar_corte(request, pk):
    perfil = getattr(request.user, 'perfilusuario', None)

    if request.user.is_superuser:
        corte = get_object_or_404(CorteEstacionamiento, pk=pk)
    else:
        if not perfil or not perfil.empresa:
            messages.error(request, "No se pudo determinar tu empresa.")
            return redirect('lista_cortes_estacionamiento')
        corte = get_object_or_404(CorteEstacionamiento, pk=pk, empresa=perfil.empresa)

    if corte.factura:
        messages.error(request, "Este corte ya tiene una factura generada y no puede eliminarse.")
        return redirect('detalle_corte_estacionamiento', pk=pk)

    if request.method == 'POST':
        corte.delete()
        messages.success(request, "Corte eliminado correctamente.")
        return redirect('lista_cortes_estacionamiento')

    return render(request, 'estacionamiento/eliminar_corte.html', {'corte': corte})


@login_required
def importar_tickets(request, corte_pk):
    perfil = getattr(request.user, 'perfilusuario', None)

    if request.user.is_superuser:
        corte = get_object_or_404(CorteEstacionamiento, pk=corte_pk)
    else:
        if not perfil or not perfil.empresa:
            messages.error(request, "No se pudo determinar tu empresa.")
            return redirect('lista_cortes_estacionamiento')
        corte = get_object_or_404(CorteEstacionamiento, pk=corte_pk, empresa=perfil.empresa)

    if request.method == 'POST':
        form = ImportarTicketsForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            decoded = archivo.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

            # NUEVO -- evita duplicados si el mismo archivo se importa 2 veces
            numeros_existentes = set(
                corte.tickets.values_list('numero_ticket', flat=True)
            )

            tickets_creados = 0
            tickets_duplicados = 0
            errores = []

            for i, row in enumerate(reader, start=2):
                numero = row.get('numero_ticket', '').strip()

                if numero in numeros_existentes:
                    tickets_duplicados += 1
                    continue

                try:
                    def parse_fecha_flexible(valor):
                        valor = valor.strip()
                        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
                            try:
                                return datetime.strptime(valor, fmt).date()
                            except ValueError:
                                continue
                        raise ValueError(f"formato de fecha no reconocido: '{valor}'")

                    def parse_hora_flexible(valor):
                        valor = valor.strip()
                        for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M:%S %p'):
                            try:
                                return datetime.strptime(valor, fmt).time()
                            except ValueError:
                                continue
                        raise ValueError(f"formato de hora no reconocido: '{valor}'")

                    fecha = parse_fecha_flexible(row.get('fecha', ''))
                    hora_entrada = parse_hora_flexible(row.get('hora_entrada', ''))
                    hora_salida = parse_hora_flexible(row.get('hora_salida', ''))

                    TicketEstacionamiento.objects.create(
                        corte=corte,
                        numero_ticket=numero,
                        fecha=fecha,
                        hora_entrada=hora_entrada,
                        hora_salida=hora_salida,
                        minutos=int(row.get('minutos', 0) or 0),
                        monto=float(row.get('monto', 0) or 0),
                        forma_pago=row.get('forma_pago', 'efectivo').strip().lower(),
                    )
                    numeros_existentes.add(numero)
                    tickets_creados += 1
                except ValueError as e:
                    errores.append(f"Fila {i}: formato de fecha/hora inválido ({str(e)})")
                except Exception as e:
                    errores.append(f"Fila {i}: {str(e)}")

            totales = corte.tickets.aggregate(
                efectivo=Sum('monto', filter=models.Q(forma_pago='efectivo')),
                tarjeta=Sum('monto', filter=models.Q(forma_pago='tarjeta')),
                boletos=Count('id'),
            )
            corte.total_efectivo = totales['efectivo'] or 0
            corte.total_tarjeta = totales['tarjeta'] or 0
            corte.total_boletos = totales['boletos'] or 0
            corte.save(update_fields=['total_efectivo', 'total_tarjeta', 'total_boletos'])

            resumen = f"✅ {tickets_creados} tickets importados."
            if tickets_duplicados:
                resumen += f" {tickets_duplicados} ya existían (omitidos, sin duplicar)."
            if errores:
                messages.warning(request, f"{resumen} {len(errores)} error(es): {', '.join(errores[:3])}")
            else:
                messages.success(request, resumen)

            return redirect('detalle_corte_estacionamiento', pk=corte_pk)
    else:
        form = ImportarTicketsForm()

    return render(request, 'estacionamiento/importar_tickets.html', {
        'form': form,
        'corte': corte,
    })

