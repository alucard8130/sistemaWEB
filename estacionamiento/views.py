from django.db import models
# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from .models import CorteEstacionamiento, TicketEstacionamiento
from .forms import CorteEstacionamientoForm, ImportarTicketsForm
#from empresas.models import CuentaBancaria
import csv
import io
from facturacion.models import CobroOtrosIngresos, FacturaOtrosIngresos, TipoOtroIngreso
from clientes.models import Cliente
import datetime
from django.db import transaction, IntegrityError
import re



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

    return render(request, 'estacionamiento/lista_cortes.html', {
        'cortes': cortes,
        'totales': totales,
        'periodo_filtro': periodo,
    })


@login_required
def crear_corte(request):
    perfil = getattr(request.user, 'perfilusuario', None)
    empresa = perfil.empresa if perfil and not request.user.is_superuser else None

    if request.method == 'POST':
        form = CorteEstacionamientoForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            corte = form.save(commit=False)
            if empresa:
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

    clientes = Cliente.objects.filter(empresa=empresa, activo=True)
    tipos_ingreso = "Estacionamiento"  # Tipo de ingreso fijo para cortes de estacionamiento

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        #tipo_ingreso_id = request.POST.get('tipo_ingreso_id')
        fecha_vencimiento = request.POST.get('fecha_vencimiento')
        observaciones = request.POST.get('observaciones', '').strip()

        if not cliente_id  or not fecha_vencimiento:
            messages.error(request, "Todos los campos marcados con * son obligatorios.")
            return render(request, 'estacionamiento/generar_factura_corte.html', {
                'corte': corte,
                'clientes': clientes,
                'tipos_ingreso': tipos_ingreso,
                'fecha_vencimiento_default': corte.fecha_fin.strftime('%Y-%m-%d'),
            })

        cliente = get_object_or_404(Cliente, pk=cliente_id, empresa=empresa)
        # Obtener o crear tipo de ingreso Estacionamiento automáticamente
        tipo_ingreso, _ = TipoOtroIngreso.objects.get_or_create(
            empresa=empresa,
            nombre="Estacionamiento"
        )

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
                        observaciones=observaciones or f"Ingresos por estacionamiento — {corte.label_periodo}",
                        estatus='pendiente',
                    )
                    # Registrar el cobro automáticamente — el corte ya fue depositado
                    CobroOtrosIngresos.objects.create(
                        factura=factura,
                        fecha_cobro=corte.fecha_deposito,
                        monto=corte.ingreso_neto_plaza,
                        forma_cobro='deposito',
                        cuenta_bancaria=corte.cuenta_bancaria,
                        registrado_por=request.user,
                        observaciones=f"Cobro automático — {corte.label_periodo}",
                    )
                    # Actualizar estatus de la factura a cobrada
                    factura.actualizar_estatus()

                    corte.factura = factura
                    corte.save()
                    guardado = True
                    break
            except IntegrityError:
                continue

        if guardado:
            messages.success(request, f"Factura {factura.folio} generada correctamente por ${corte.ingreso_neto_plaza:,.2f}.")
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
    corte = get_object_or_404(CorteEstacionamiento, pk=pk)
    tickets = corte.tickets.all()

    # Subtotales por forma de pago
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
    corte = get_object_or_404(CorteEstacionamiento, pk=pk)
    perfil = getattr(request.user, 'perfilusuario', None)
    empresa = perfil.empresa if perfil and not request.user.is_superuser else None

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
    corte = get_object_or_404(CorteEstacionamiento, pk=pk)
    if request.method == 'POST':
        corte.delete()
        messages.success(request, "Corte eliminado correctamente.")
        return redirect('lista_cortes_estacionamiento')
    return render(request, 'estacionamiento/eliminar_corte.html', {'corte': corte})


@login_required
def importar_tickets(request, corte_pk):
    corte = get_object_or_404(CorteEstacionamiento, pk=corte_pk)

    if request.method == 'POST':
        form = ImportarTicketsForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            decoded = archivo.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

            tickets_creados = 0
            errores = []

            for i, row in enumerate(reader, start=2):
                try:
                    TicketEstacionamiento.objects.create(
                        corte=corte,
                        numero_ticket=row.get('numero_ticket', '').strip(),
                        fecha=row.get('fecha', '').strip(),
                        hora_entrada=row.get('hora_entrada', '').strip(),
                        hora_salida=row.get('hora_salida', '').strip(),
                        minutos=int(row.get('minutos', 0) or 0),
                        monto=float(row.get('monto', 0) or 0),
                        forma_pago=row.get('forma_pago', 'efectivo').strip().lower(),
                    )
                    tickets_creados += 1
                except Exception as e:
                    errores.append(f"Fila {i}: {str(e)}")

            # Recalcular totales del corte desde los tickets
            totales = corte.tickets.aggregate(
                efectivo=Sum('monto', filter=models.Q(forma_pago='efectivo')),
                tarjeta=Sum('monto', filter=models.Q(forma_pago='tarjeta')),
                boletos=Count('id'),
            )
            corte.total_efectivo = totales['efectivo'] or 0
            corte.total_tarjeta = totales['tarjeta'] or 0
            corte.total_boletos = totales['boletos'] or 0
            corte.save()

            if errores:
                messages.warning(request, f"Se importaron {tickets_creados} tickets con {len(errores)} errores: {', '.join(errores[:3])}")
            else:
                messages.success(request, f"Se importaron {tickets_creados} tickets correctamente.")

            return redirect('detalle_corte_estacionamiento', pk=corte_pk)
    else:
        form = ImportarTicketsForm()

    return render(request, 'estacionamiento/importar_tickets.html', {
        'form': form,
        'corte': corte,
    })

