from datetime import datetime
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from empresas.models import Empresa, CuentaBancaria
from facturacion.models import TipoOtroIngreso, FacturaOtrosIngresos, CobroOtrosIngresos
from .models import BoletoFisico, UsoSanitario, CorteSanitario
from django.shortcuts import get_object_or_404
from .models import CasetaOperador  


def _empresa_actual(request):
    if request.user.is_superuser:
        empresa_id = request.session.get("empresa_id")
        return Empresa.objects.filter(id=empresa_id).first()
    return request.user.perfilusuario.empresa


@login_required
def sanitarios_operador(request):
    empresa = _empresa_actual(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    if not empresa.precio_sanitario:
        messages.error(request, "Este condominio no tiene configurado el precio de uso de sanitarios.")
        return redirect("dashboard_inicio")

    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "generar":
            if empresa.usa_boletos_fisicos_sanitario:
                boleto = BoletoFisico.objects.filter(
                    empresa=empresa, estado="disponible"
                ).order_by("codigo").first()

                if not boleto:
                    messages.error(request, "❌ No quedan boletos físicos disponibles. Carga más folios.")
                    return redirect("sanitarios_operador")

                uso = UsoSanitario.objects.create(empresa=empresa, codigo=boleto.codigo, generado_por=request.user)
                boleto.estado = "usado"
                boleto.uso = uso
                boleto.save()

                messages.success(request, f"✅ Entrega el boleto físico número: {boleto.codigo}")
            else:
                codigo = UsoSanitario.generar_codigo_unico(empresa)
                UsoSanitario.objects.create(empresa=empresa, codigo=codigo, generado_por=request.user)
                messages.success(request, f"✅ Código generado: {codigo}")

        elif accion == "cobrar":
            codigo_ingresado = request.POST.get("codigo", "").strip().upper()
            uso = UsoSanitario.objects.filter(
                empresa=empresa, codigo=codigo_ingresado, estado="pendiente"
            ).order_by("fecha_generado").first()

            if not uso:
                messages.error(request, f"❌ No hay ningún uso PENDIENTE con el código '{codigo_ingresado}'.")
            else:
                uso.estado = "cobrado"
                uso.monto = empresa.precio_sanitario
                uso.fecha_cobro = timezone.now()
                uso.cobrado_por = request.user
                uso.save()
                messages.success(request, f"✅ Cobrado ${uso.monto} — código {uso.codigo}")

        return redirect("sanitarios_operador")

    hoy = timezone.localtime(timezone.now()).date()
    usos_hoy = UsoSanitario.objects.filter(empresa=empresa, fecha_generado__date=hoy)
    pendientes_hoy = usos_hoy.filter(estado="pendiente")
    cobrados_hoy = usos_hoy.filter(estado="cobrado")
    total_cobrado_hoy = cobrados_hoy.aggregate(t=Sum("monto"))["t"] or 0

    boletos_disponibles = None
    if empresa.usa_boletos_fisicos_sanitario:
        boletos_disponibles = BoletoFisico.objects.filter(empresa=empresa, estado="disponible").count()

    return render(request, "sanitarios/sanitarios_operador.html", {
        "empresa": empresa,
        "usos_hoy": usos_hoy,
        "pendientes_hoy": pendientes_hoy,
        "cobrados_count": cobrados_hoy.count(),
        "total_cobrado_hoy": total_cobrado_hoy,
        "boletos_disponibles": boletos_disponibles,
    })



@login_required
def sanitarios_corte_diario(request):
    empresa = _empresa_actual(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    fecha_str = request.GET.get("fecha") or request.POST.get("fecha")
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else timezone.localtime(timezone.now()).date()

    usos_dia = UsoSanitario.objects.filter(empresa=empresa, fecha_generado__date=fecha)
    generados = usos_dia.count()
    cobrados = usos_dia.filter(estado="cobrado")
    total_cobrado = cobrados.aggregate(t=Sum("monto"))["t"] or Decimal("0")
    pendientes = usos_dia.filter(estado="pendiente").count()

    corte_existente = CorteSanitario.objects.filter(empresa=empresa, fecha=fecha).first()

    if request.method == "POST" and request.POST.get("accion") == "cerrar_corte":
        if corte_existente:
            messages.error(request, f"El corte del {fecha.strftime('%d/%m/%Y')} ya fue cerrado anteriormente.")
            return redirect(f"{request.path}?fecha={fecha}")

        if total_cobrado <= 0:
            messages.error(request, "No hay nada cobrado ese día para generar el ingreso.")
            return redirect(f"{request.path}?fecha={fecha}")

        cuenta_bancaria_id = request.POST.get("cuenta_bancaria")
        cuenta_bancaria = CuentaBancaria.objects.filter(id=cuenta_bancaria_id, empresa=empresa).first() if cuenta_bancaria_id else None

        if not cuenta_bancaria:
            messages.error(request, "Debes seleccionar la cuenta bancaria donde se depositará el efectivo.")
            return redirect(f"{request.path}?fecha={fecha}")

        fecha_deposito_str = request.POST.get("fecha_deposito", "").strip()
        try:
            fecha_deposito = datetime.strptime(fecha_deposito_str, "%Y-%m-%d").date() if fecha_deposito_str else fecha
        except Exception:
            fecha_deposito = fecha

        if fecha_deposito < fecha:
            messages.error(request, "La fecha de depósito no puede ser anterior a la fecha del corte.")
            return redirect(f"{request.path}?fecha={fecha}")

        tipo_ingreso, _ = TipoOtroIngreso.objects.get_or_create(empresa=empresa, nombre="Uso de Sanitarios")

        with transaction.atomic():
            prefix = "SAN-"
            last_folio = FacturaOtrosIngresos.objects.filter(empresa=empresa, folio__startswith=prefix).order_by("-folio").values_list("folio", flat=True).first()
            last_num = int(last_folio.replace(prefix, "")) if last_folio else 0
            folio = f"{prefix}{last_num + 1:05d}"

            factura = FacturaOtrosIngresos.objects.create(
                empresa=empresa, tipo_ingreso=tipo_ingreso, folio=folio,
                fecha_vencimiento=fecha, monto=total_cobrado,
                observaciones=f"Corte de sanitarios del {fecha.strftime('%d/%m/%Y')} — {cobrados.count()} usos cobrados",
                estatus="pendiente", cliente=None,
            )
            CobroOtrosIngresos.objects.create(
                factura=factura, fecha_cobro=fecha_deposito, monto=total_cobrado,
                forma_cobro="efectivo", cuenta_bancaria=cuenta_bancaria,
                registrado_por=request.user,
                observaciones=f"Generado desde Corte de Sanitarios del {fecha.strftime('%d/%m/%Y')}",
            )
            factura.actualizar_estatus()

            CorteSanitario.objects.create(
                empresa=empresa, fecha=fecha, total_cobrado=total_cobrado,
                factura=factura, cerrado_por=request.user,
            )

        messages.success(request, f"✅ Ingreso registrado: {folio} por ${total_cobrado}")
        return redirect(f"{request.path}?fecha={fecha}")

    cuentas = CuentaBancaria.objects.filter(empresa=empresa, activa=True)

    return render(request, "sanitarios/sanitarios_corte_diario.html", {
        "empresa": empresa,
        "fecha": fecha,
        "fecha_formateada": fecha.strftime("%d/%m/%Y"),
        "generados": generados,
        "cobrados_count": cobrados.count(),
        "pendientes": pendientes,
        "total_cobrado": total_cobrado,
        "cuentas": cuentas,
        "corte_existente": corte_existente,
    })


@login_required
def cortes_sanitario_pendientes(request):
    empresa = _empresa_actual(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    # Días con al menos un cobro, agrupados
    fechas_con_cobro = (
        UsoSanitario.objects.filter(empresa=empresa, estado="cobrado")
        .annotate(dia=TruncDate("fecha_cobro"))
        .values("dia")
        .annotate(total=Sum("monto"), cantidad=Count("id"))
        .order_by("-dia")
    )

    dias_cerrados = set(
        CorteSanitario.objects.filter(empresa=empresa).values_list("fecha", flat=True)
    )

    pendientes = [
        f for f in fechas_con_cobro if f["dia"] not in dias_cerrados
    ]

    return render(request, "sanitarios/cortes_pendientes.html", {
        "empresa": empresa,
        "pendientes": pendientes,
        "total_pendiente": sum(p["total"] for p in pendientes),
    })


@login_required
def configurar_precio_sanitario(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect("dashboard_inicio")

    if request.method == "POST":
        for empresa in Empresa.objects.all():
            precio = request.POST.get(f"precio_{empresa.id}", "").strip()
            try:
                empresa.precio_sanitario = Decimal(precio) if precio else None
                empresa.usa_boletos_fisicos_sanitario = f"boletos_{empresa.id}" in request.POST  # NUEVO
                empresa.save(update_fields=["precio_sanitario", "usa_boletos_fisicos_sanitario"])
            except Exception:
                pass
        messages.success(request, "✅ Precios actualizados correctamente.")
        return redirect("configurar_precio_sanitario")

    empresas = Empresa.objects.all().order_by("nombre")
    return render(request, "sanitarios/configurar_precio.html", {"empresas": empresas})



def sanitarios_operador_caseta(request, token):
    caseta = get_object_or_404(CasetaOperador, token=token, activo=True)
    empresa = caseta.empresa

    if not empresa.precio_sanitario:
        return render(request, "sanitarios/caseta_no_configurada.html", {"empresa": empresa})

    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "generar":
            if empresa.usa_boletos_fisicos_sanitario:
                boleto = BoletoFisico.objects.filter(
                    empresa=empresa, estado="disponible"
                ).order_by("codigo").first()

                if not boleto:
                    messages.error(request, "❌ No quedan boletos físicos disponibles. Contacta al administrador.")
                    return redirect("sanitarios_operador_caseta", token=token)

                uso = UsoSanitario.objects.create(empresa=empresa, codigo=boleto.codigo, caseta=caseta)
                boleto.estado = "usado"
                boleto.uso = uso
                boleto.save()

                messages.success(request, f"✅ Entrega el boleto físico número: {boleto.codigo}")
            else:
                codigo = UsoSanitario.generar_codigo_unico(empresa)
                UsoSanitario.objects.create(empresa=empresa, codigo=codigo, caseta=caseta)
                messages.success(request, f"✅ Código generado: {codigo}")

        elif accion == "cobrar":
            codigo_ingresado = request.POST.get("codigo", "").strip().upper()
            uso = UsoSanitario.objects.filter(
                empresa=empresa, codigo=codigo_ingresado, estado="pendiente"
            ).order_by("fecha_generado").first()

            if not uso:
                messages.error(request, f"❌ No hay ningún uso PENDIENTE con el código '{codigo_ingresado}'.")
            else:
                uso.estado = "cobrado"
                uso.monto = empresa.precio_sanitario
                uso.fecha_cobro = timezone.now()
                uso.caseta = caseta
                uso.save()
                messages.success(request, f"✅ Cobrado ${uso.monto} — código {uso.codigo}")

        return redirect("sanitarios_operador_caseta", token=token)

    hoy = timezone.localtime(timezone.now()).date()
    usos_hoy = UsoSanitario.objects.filter(empresa=empresa, fecha_generado__date=hoy)
    pendientes_hoy = usos_hoy.filter(estado="pendiente")
    cobrados_hoy = usos_hoy.filter(estado="cobrado")
    total_cobrado_hoy = cobrados_hoy.aggregate(t=Sum("monto"))["t"] or 0

    boletos_disponibles = None
    if empresa.usa_boletos_fisicos_sanitario:
        boletos_disponibles = BoletoFisico.objects.filter(empresa=empresa, estado="disponible").count()

    return render(request, "sanitarios/sanitarios_operador.html", {
        "empresa": empresa,
        "caseta": caseta,
        "usos_hoy": usos_hoy,
        "pendientes_hoy": pendientes_hoy,
        "cobrados_count": cobrados_hoy.count(),
        "total_cobrado_hoy": total_cobrado_hoy,
        "es_caseta_publica": True,
        "boletos_disponibles": boletos_disponibles,
    })


@login_required
def lista_casetas_sanitario(request):
    if request.user.is_superuser:
        empresas = Empresa.objects.all().order_by("nombre")
        empresa_id = request.GET.get("empresa")
        empresa = Empresa.objects.filter(id=empresa_id).first() if empresa_id else empresas.first()
    else:
        empresas = None
        empresa = request.user.perfilusuario.empresa

    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if nombre:
            CasetaOperador.objects.create(empresa=empresa, nombre=nombre)
            messages.success(request, f"✅ Caseta '{nombre}' creada.")
        if request.user.is_superuser:
            return redirect(f"{request.path}?empresa={empresa.id}")
        return redirect("lista_casetas_sanitario")

    casetas = CasetaOperador.objects.filter(empresa=empresa).order_by("nombre")
    return render(request, "sanitarios/lista_casetas.html", {
        "casetas": casetas,
        "empresa": empresa,
        "empresas": empresas,
    })


#solo super user puede cargar boletos fisicos
@login_required
def cargar_boletos_fisicos(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect("dashboard_inicio")

    empresas = Empresa.objects.filter(usa_boletos_fisicos_sanitario=True).order_by("nombre")
    empresa_id = request.GET.get("empresa") or request.POST.get("empresa")
    empresa = empresas.filter(id=empresa_id).first() if empresa_id else empresas.first()

    if not empresa:
        messages.error(request, "No hay ninguna empresa configurada con boletos físicos.")
        return redirect("configurar_precio_sanitario")

    if request.method == "POST":
        prefijo = request.POST.get("prefijo", "").strip().upper()
        inicio = request.POST.get("inicio", "").strip()
        fin = request.POST.get("fin", "").strip()
        digitos = request.POST.get("digitos", "4").strip()

        try:
            inicio_n = int(inicio)
            fin_n = int(fin)
            digitos_n = int(digitos)
            if fin_n < inicio_n:
                raise ValueError("rango invertido")
            if fin_n - inicio_n > 10000:
                messages.error(request, "No puedes cargar más de 10,000 boletos de una sola vez.")
                return redirect(f"{request.path}?empresa={empresa.id}")
        except ValueError:
            messages.error(request, "Revisa que el rango de números sea válido.")
            return redirect(f"{request.path}?empresa={empresa.id}")

        # Verifica cuáles códigos ya existen, en 1 sola consulta
        codigos_generados = []
        for n in range(inicio_n, fin_n + 1):
            numero = str(n).zfill(digitos_n)
            codigo = f"{prefijo}-{numero}" if prefijo else numero
            codigos_generados.append(codigo)

        existentes = set(
            BoletoFisico.objects.filter(empresa=empresa, codigo__in=codigos_generados)
            .values_list("codigo", flat=True)
        )

        nuevos = [
            BoletoFisico(empresa=empresa, codigo=c, cargado_por=request.user)
            for c in codigos_generados if c not in existentes
        ]

        with transaction.atomic():
            BoletoFisico.objects.bulk_create(nuevos, batch_size=1000)

        creados = len(nuevos)
        ya_existian = len(codigos_generados) - creados

        messages.success(request, f"✅ {creados} boleto(s) nuevo(s) cargado(s). {ya_existian} ya existían (sin duplicar).")
        return redirect(f"{request.path}?empresa={empresa.id}")

    disponibles = BoletoFisico.objects.filter(empresa=empresa, estado="disponible").count()
    usados = BoletoFisico.objects.filter(empresa=empresa, estado="usado").count()

    return render(request, "sanitarios/cargar_boletos.html", {
        "empresas": empresas,
        "empresa": empresa,
        "disponibles": disponibles,
        "usados": usados,
    })