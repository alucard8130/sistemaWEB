import base64
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from areas.models import AreaComun
from clientes.models import Cliente
from empleados.models import Empleado
from empresas.models import CuentaBancaria, Empresa
from facturacion.models import CobroOtrosIngresos, FacturaOtrosIngresos, TipoOtroIngreso
from locales.models import LocalComercial

from .models import (
    BoletoFisico,
    CasetaOperador,
    CorteSanitario,
    GafeteAcceso,
    LoteToallas,
    UsoSanitario,
)


def _empresa_actual(request):
    if request.user.is_superuser:
        empresa_id = request.session.get("empresa_id")
        return Empresa.objects.filter(id=empresa_id).first()
    return request.user.perfilusuario.empresa


def _cerrar_corte_sanitarios(empresa, caseta, usuario=None, empleado=None):
    """Cierra el corte de una caseta (o del flujo sin caseta si caseta=None),
    capturando todo lo cobrado desde el último corte cerrado hasta ahora."""

    ultimo_corte = CorteSanitario.objects.filter(empresa=empresa, caseta=caseta).order_by("-fecha_hora_fin").first()
    if ultimo_corte:
        inicio = ultimo_corte.fecha_hora_fin
    else:
        primer_uso = UsoSanitario.objects.filter(empresa=empresa, caseta=caseta).order_by("fecha_generado").first()
        inicio = primer_uso.fecha_generado if primer_uso else timezone.now()

    fin = timezone.now()

    cobrados_ventana = UsoSanitario.objects.filter(
        empresa=empresa, caseta=caseta, estado="cobrado",
        fecha_cobro__gte=inicio, fecha_cobro__lt=fin,
    )
    total = cobrados_ventana.aggregate(t=Sum("monto"))["t"] or Decimal("0")

    if total <= 0:
        return None, "No hay nada cobrado desde el último corte cerrado."

    tipo_ingreso, _ = TipoOtroIngreso.objects.get_or_create(empresa=empresa, nombre="Ingresos de Sanitarios (General)")
    cliente_generico = Cliente.objects.filter(empresa=empresa, nombre__iexact="Público en General").first()
    if not cliente_generico:
        cliente_generico = Cliente.objects.create(empresa=empresa, nombre="Público en General", activo=True)

    TIPOS = [("sanitario", "Sanitario"), ("papel", "Papel"), ("toalla", "Toallas")]
    partes = []
    for tipo_key, tipo_label in TIPOS:
        sub = cobrados_ventana.filter(tipo=tipo_key)
        sub_total = sub.aggregate(t=Sum("monto"))["t"] or Decimal("0")
        if sub_total > 0:
            partes.append(f"{tipo_label}: {sub.count()} x ${sub_total}")
    detalle_texto = " | ".join(partes)

    with transaction.atomic():
        prefix = "SAN-"
        last_folio = FacturaOtrosIngresos.objects.filter(empresa=empresa, folio__startswith=prefix).order_by("-folio").values_list("folio", flat=True).first()
        last_num = int(last_folio.replace(prefix, "")) if last_folio else 0
        folio = f"{prefix}{last_num + 1:05d}"

        caseta_nombre = caseta.nombre if caseta else "Sin caseta"
        factura = FacturaOtrosIngresos.objects.create(
            empresa=empresa, tipo_ingreso=tipo_ingreso, folio=folio,
            fecha_vencimiento=fin.date(), monto=total,
            observaciones=f"Corte de sanitarios — {caseta_nombre} — {inicio.strftime('%d/%m %H:%M')} a {fin.strftime('%d/%m %H:%M')} — {detalle_texto}",
            estatus="pendiente", cliente=cliente_generico,
        )

        corte = CorteSanitario.objects.create(
            empresa=empresa, caseta=caseta,
            fecha_hora_inicio=inicio, fecha_hora_fin=fin,
            total_cobrado=total, factura=factura,
            cerrado_por=usuario, cerrado_por_empleado=empleado,
        )

    return corte, None


#no se usa, solo para supervision del ususrio GESAC, esta vista no se usa por ningun empleado
@login_required
def sanitarios_operador(request):
    empresa = _empresa_actual(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    if not empresa.precio_sanitario and not empresa.precio_papel:
        messages.error(request, "Este condominio no tiene configurado ningún concepto de sanitarios.")
        return redirect("dashboard_inicio")

    if request.method == "POST":
        tipo = request.POST.get("tipo", "sanitario")
        accion = request.POST.get("accion")
        precio = empresa.precio_sanitario if tipo == 'sanitario' else empresa.precio_papel
        usa_boletos = empresa.usa_boletos_fisicos_sanitario if tipo == 'sanitario' else empresa.usa_boletos_fisicos_papel
        nombre_concepto = "Sanitario" if tipo == 'sanitario' else "Papel"

        if accion == "gafete":
            numero_gafete = request.POST.get("numero_gafete", "").strip().upper()
            if not numero_gafete:
                messages.error(request, "Captura el número de gafete.")
                return redirect(f"{reverse('sanitarios_operador')}?tab={tipo}")

            gafete = GafeteAcceso.objects.filter(empresa=empresa, numero=numero_gafete, activo=True).first()
            if not gafete:
                messages.error(request, f"❌ El gafete '{numero_gafete}' no está registrado o está inactivo.")
                return redirect(f"{reverse('sanitarios_operador')}?tab={tipo}")

            codigo_gratis = UsoSanitario.generar_codigo_unico(empresa, tipo=tipo)
            UsoSanitario.objects.create(
                empresa=empresa, tipo=tipo, codigo=codigo_gratis, generado_por=request.user,
                estado="gratis", monto=Decimal("0"), fecha_cobro=timezone.now(),
                gafete=gafete,
            )
            titular = gafete.nombre_titular or gafete.numero
            messages.success(request, f"✅ {nombre_concepto} gratuito registrado — Gafete {gafete.numero} ({titular})")

        elif accion == "generar":
            if usa_boletos:
                boleto = BoletoFisico.objects.filter(empresa=empresa, tipo=tipo, estado="disponible").order_by("codigo").first()
                if not boleto:
                    messages.error(request, f"❌ No quedan boletos físicos de {nombre_concepto} disponibles.")
                else:
                    uso = UsoSanitario.objects.create(empresa=empresa, tipo=tipo, codigo=boleto.codigo, generado_por=request.user)
                    boleto.estado = "usado"
                    boleto.uso = uso
                    boleto.save()
                    messages.success(request, f"✅ Entrega el boleto físico número: {boleto.codigo}")
            else:
                codigo = UsoSanitario.generar_codigo_unico(empresa, tipo=tipo)
                UsoSanitario.objects.create(empresa=empresa, tipo=tipo, codigo=codigo, generado_por=request.user)
                messages.success(request, f"✅ Código generado: {codigo}")

        elif accion == "cobrar":
            codigo_ingresado = request.POST.get("codigo", "").strip().upper()
            uso = UsoSanitario.objects.filter(empresa=empresa, tipo=tipo, codigo=codigo_ingresado, estado="pendiente").order_by("fecha_generado").first()
            if not uso:
                messages.error(request, f"❌ No hay ningún uso PENDIENTE con el código '{codigo_ingresado}'.")
            else:
                uso.estado = "cobrado"
                uso.monto = precio
                uso.fecha_cobro = timezone.now()
                uso.cobrado_por = request.user
                uso.save()
                messages.success(request, f"✅ Cobrado ${uso.monto} — código {uso.codigo}")

        elif accion == "vender_toalla":
            lote = LoteToallas.objects.filter(empresa=empresa, cantidad_disponible__gt=0).order_by("fecha_recepcion").first()
            if not lote:
                messages.error(request, "❌ No hay inventario de toallas disponible. Registra un lote nuevo.")
            else:
                with transaction.atomic():
                    lote.cantidad_disponible -= 1
                    lote.save(update_fields=["cantidad_disponible"])

                    codigo = UsoSanitario.generar_codigo_unico(empresa, tipo="toalla")
                    UsoSanitario.objects.create(
                        empresa=empresa, tipo="toalla", codigo=codigo,
                        estado="cobrado", monto=empresa.precio_toalla,
                        fecha_cobro=timezone.now(), cobrado_por=request.user,
                        lote_toallas=lote,
                    )
                messages.success(request, f"✅ Toalla vendida — ${empresa.precio_toalla}. Quedan {lote.cantidad_disponible} en el lote.")        

        return redirect(f"{reverse('sanitarios_operador')}?tab={tipo}")

    # GET -- carga los datos de AMBOS conceptos a la vez
    hoy = timezone.localtime(timezone.now()).date()

    def _datos_tipo(tipo):
        usos_hoy = UsoSanitario.objects.filter(empresa=empresa, tipo=tipo, fecha_generado__date=hoy)
        cobrados_hoy = usos_hoy.filter(estado="cobrado")
        usa_boletos = empresa.usa_boletos_fisicos_sanitario if tipo == 'sanitario' else empresa.usa_boletos_fisicos_papel

        # NUEVO -- todos los pendientes históricos, no solo los de hoy, para poder cobrar atrasados
        pendientes_todos = UsoSanitario.objects.filter(
            empresa=empresa, tipo=tipo, estado="pendiente"
        ).order_by("fecha_generado")

        return {
            "tipo": tipo,
            "activo": bool(empresa.precio_sanitario if tipo == 'sanitario' else empresa.precio_papel),
            "usa_boletos_fisicos": usa_boletos,
            "boletos_disponibles": BoletoFisico.objects.filter(empresa=empresa, tipo=tipo, estado="disponible").count() if usa_boletos else None,
            "usos_hoy": usos_hoy,
            "pendientes_hoy": usos_hoy.filter(estado="pendiente"),
            "pendientes_todos": pendientes_todos,  # NUEVO
            "cobrados_count": cobrados_hoy.count(),
            "gratis_count": usos_hoy.filter(estado="gratis").count(),
            "total_cobrado_hoy": cobrados_hoy.aggregate(t=Sum("monto"))["t"] or 0,
        }
    inventario_toallas = LoteToallas.objects.filter(empresa=empresa, cantidad_disponible__gt=0).aggregate(t=Sum("cantidad_disponible"))["t"] or 0

    return render(request, "sanitarios/sanitarios_operador.html", {
        "empresa": empresa,
        "datos_sanitario": _datos_tipo("sanitario"),
        "datos_papel": _datos_tipo("papel"),
        "datos_toalla": _datos_tipo("toalla"),  # reutiliza la misma función helper
        "inventario_toallas": inventario_toallas,
        "hoy": hoy,
    })


def sanitarios_operador_caseta(request, token):
    caseta = get_object_or_404(CasetaOperador, token=token, activo=True)
    empresa = caseta.empresa

    if not empresa.precio_sanitario and not empresa.precio_papel:
        return render(request, "sanitarios/caseta_no_configurada.html", {"empresa": empresa})

    if request.method == "POST":
        tipo = request.POST.get("tipo", "sanitario")
        accion = request.POST.get("accion")
        precio = empresa.precio_sanitario if tipo == 'sanitario' else empresa.precio_papel
        usa_boletos = empresa.usa_boletos_fisicos_sanitario if tipo == 'sanitario' else empresa.usa_boletos_fisicos_papel
        nombre_concepto = "Sanitario" if tipo == 'sanitario' else "Papel"
        url_base = reverse("sanitarios_operador_caseta", kwargs={"token": token})

        if accion == "gafete":
            numero_gafete = request.POST.get("numero_gafete", "").strip().upper()
            if not numero_gafete:
                messages.error(request, "Captura el número de gafete.")
                return redirect(f"{url_base}?tab={tipo}")

            gafete = GafeteAcceso.objects.filter(empresa=empresa, numero=numero_gafete, activo=True).first()
            if not gafete:
                messages.error(request, f"❌ El gafete '{numero_gafete}' no está registrado o está inactivo.")
                return redirect(f"{url_base}?tab={tipo}")

            codigo_gratis = UsoSanitario.generar_codigo_unico(empresa, tipo=tipo)
            UsoSanitario.objects.create(
                empresa=empresa, tipo=tipo, codigo=codigo_gratis, caseta=caseta,
                estado="gratis", monto=Decimal("0"), fecha_cobro=timezone.now(),
                gafete=gafete,
            )
            titular = gafete.nombre_titular or gafete.numero
            messages.success(request, f"✅ {nombre_concepto} gratuito registrado — Gafete {gafete.numero} ({titular})")

        elif accion == "generar":
            es_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

            if usa_boletos:
                boleto = BoletoFisico.objects.filter(empresa=empresa, tipo=tipo, estado="disponible").order_by("codigo").first()
                if not boleto:
                    msg = f"❌ No quedan boletos físicos de {nombre_concepto} disponibles."
                    if es_ajax:
                        return JsonResponse({"ok": False, "error": msg})
                    messages.error(request, msg)
                    return redirect(f"{url_base}?tab={tipo}")

                uso = UsoSanitario.objects.create(empresa=empresa, tipo=tipo, codigo=boleto.codigo, caseta=caseta)
                boleto.estado = "usado"
                boleto.uso = uso
                boleto.save()

                if es_ajax:
                    restantes = BoletoFisico.objects.filter(empresa=empresa, tipo=tipo, estado="disponible").count()
                    return JsonResponse({"ok": True, "codigo": boleto.codigo, "boletos_disponibles": restantes})

                messages.success(request, f"✅ Entrega el boleto físico número: {boleto.codigo}")
            else:
                codigo = UsoSanitario.generar_codigo_unico(empresa, tipo=tipo)
                UsoSanitario.objects.create(empresa=empresa, tipo=tipo, codigo=codigo, caseta=caseta)

                if es_ajax:
                    return JsonResponse({"ok": True, "codigo": codigo, "boletos_disponibles": None})

                messages.success(request, f"✅ Código generado: {codigo}")

        elif accion == "cobrar":
            codigo_ingresado = request.POST.get("codigo", "").strip().upper()
            uso = UsoSanitario.objects.filter(empresa=empresa, tipo=tipo, codigo=codigo_ingresado, estado="pendiente").order_by("fecha_generado").first()
            if not uso:
                messages.error(request, f"❌ No hay ningún uso PENDIENTE con el código '{codigo_ingresado}'.")
            else:
                uso.estado = "cobrado"
                uso.monto = precio
                uso.fecha_cobro = timezone.now()
                uso.caseta = caseta
                uso.save()
                messages.success(request, f"✅ Cobrado ${uso.monto} — código {uso.codigo}")

        elif accion == "vender_toalla":
            lote = LoteToallas.objects.filter(empresa=empresa, cantidad_disponible__gt=0).order_by("fecha_recepcion").first()
            if not lote:
                messages.error(request, "❌ No hay inventario de toallas disponible.")
            else:
                with transaction.atomic():
                    lote.cantidad_disponible -= 1
                    lote.save(update_fields=["cantidad_disponible"])

                    codigo = UsoSanitario.generar_codigo_unico(empresa, tipo="toalla")
                    UsoSanitario.objects.create(
                        empresa=empresa, tipo="toalla", codigo=codigo,
                        estado="cobrado", monto=empresa.precio_toalla,
                        fecha_cobro=timezone.now(), caseta=caseta,
                        lote_toallas=lote,
                    )
                messages.success(request, f"✅ Toalla vendida — ${empresa.precio_toalla}. Quedan {lote.cantidad_disponible} en el lote.")        

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # Ya se respondió con JsonResponse dentro del bloque "generar" (AJAX).
            # Si llegamos aquí es porque fue otra acción (gafete, cobrar, vender_toalla) vía AJAX sin manejarla — por seguridad, respondemos OK genérico.
            return JsonResponse({"ok": True})
        return redirect(f"{url_base}?tab={tipo}")

    hoy = timezone.localtime(timezone.now()).date()

    def _datos_tipo(tipo):
        usos_hoy = UsoSanitario.objects.filter(empresa=empresa, tipo=tipo, fecha_generado__date=hoy)
        cobrados_hoy = usos_hoy.filter(estado="cobrado")
        usa_boletos = empresa.usa_boletos_fisicos_sanitario if tipo == 'sanitario' else empresa.usa_boletos_fisicos_papel

        # NUEVO -- todos los pendientes históricos, no solo los de hoy, para poder cobrar atrasados
        pendientes_todos = UsoSanitario.objects.filter(
            empresa=empresa, tipo=tipo, estado="pendiente"
        ).order_by("fecha_generado")

        return {
            "tipo": tipo,
            "activo": bool(empresa.precio_sanitario if tipo == 'sanitario' else empresa.precio_papel),
            "usa_boletos_fisicos": usa_boletos,
            "boletos_disponibles": BoletoFisico.objects.filter(empresa=empresa, tipo=tipo, estado="disponible").count() if usa_boletos else None,
            "usos_hoy": usos_hoy,
            "pendientes_hoy": usos_hoy.filter(estado="pendiente"),
            "pendientes_todos": pendientes_todos,  # NUEVO
            "cobrados_count": cobrados_hoy.count(),
            "gratis_count": usos_hoy.filter(estado="gratis").count(),
            "total_cobrado_hoy": cobrados_hoy.aggregate(t=Sum("monto"))["t"] or 0,
        }
    inventario_toallas = LoteToallas.objects.filter(empresa=empresa, cantidad_disponible__gt=0).aggregate(t=Sum("cantidad_disponible"))["t"] or 0
    empleados_empresa = Empleado.objects.filter(empresa=empresa).order_by("nombre")

    return render(request, "sanitarios/sanitarios_operador.html", {
        "empresa": empresa,
        "caseta": caseta,
        "datos_sanitario": _datos_tipo("sanitario"),
        "datos_papel": _datos_tipo("papel"),
        "es_caseta_publica": True,
        "datos_toalla": _datos_tipo("toalla"),  # reutiliza la misma función helper
        "inventario_toallas": inventario_toallas,
        "hoy": hoy,
        "empleados_empresa": empleados_empresa,
    })


def cerrar_corte_caseta(request, token):
    caseta = get_object_or_404(CasetaOperador, token=token, activo=True)

    if request.method == "POST":
        empleado_id = request.POST.get("empleado_id")
        empleado = Empleado.objects.filter(id=empleado_id, empresa=caseta.empresa).first()
        if not empleado:
            messages.error(request, "Selecciona tu nombre de la lista antes de cerrar el corte.")
            return redirect("sanitarios_operador_caseta", token=token)

        corte, error = _cerrar_corte_sanitarios(caseta.empresa, caseta, empleado=empleado)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, f"✅ Corte cerrado por {empleado.nombre} — ${corte.total_cobrado}. Entrega el efectivo al administrador.")

    return redirect("sanitarios_operador_caseta", token=token)



@login_required
def sanitarios_corte_diario(request):
    empresa = _empresa_actual(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    caseta_id = request.GET.get("caseta")
    empleado_id = request.GET.get("empleado")
    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")

    cortes = CorteSanitario.objects.filter(empresa=empresa).select_related(
        "caseta", "cerrado_por", "cerrado_por_empleado", "factura"
    )

    if caseta_id:
        if caseta_id == "sin_caseta":
            cortes = cortes.filter(caseta__isnull=True)
        else:
            cortes = cortes.filter(caseta_id=caseta_id)

    if empleado_id:
        cortes = cortes.filter(cerrado_por_empleado_id=empleado_id)

    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            cortes = cortes.filter(fecha_hora_fin__date__gte=fecha_inicio)
        except ValueError:
            pass

    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
            cortes = cortes.filter(fecha_hora_fin__date__lte=fecha_fin)
        except ValueError:
            pass

    cortes = cortes.order_by("-fecha_hora_fin")[:200]

    casetas = CasetaOperador.objects.filter(empresa=empresa, activo=True).order_by("nombre")
    empleados = Empleado.objects.filter(
        id__in=CorteSanitario.objects.filter(empresa=empresa).exclude(cerrado_por_empleado__isnull=True).values_list("cerrado_por_empleado_id", flat=True)
    ).order_by("nombre")

    total_pendiente_deposito = sum(
        c.total_cobrado for c in cortes if c.factura and c.factura.estatus == "pendiente"
    )

    return render(request, "sanitarios/sanitarios_corte_diario.html", {
        "empresa": empresa,
        "cortes": cortes,
        "casetas": casetas,
        "empleados": empleados,
        "caseta_id": caseta_id,
        "empleado_id": empleado_id,
        "fecha_inicio": fecha_inicio_str,
        "fecha_fin": fecha_fin_str,
        "total_pendiente_deposito": total_pendiente_deposito,
    })



@login_required
def registrar_deposito_sanitarios(request):
    empresa = _empresa_actual(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    prefijos = ("SAN-", "PAP-", "TOA-")  # noqa: F841
    facturas_pendientes = FacturaOtrosIngresos.objects.filter(
        empresa=empresa, estatus="pendiente", folio__startswith="SAN-",
    ).order_by("fecha_vencimiento")

    if request.method == "POST":
        factura_id = request.POST.get("factura_id")
        cuenta_bancaria_id = request.POST.get("cuenta_bancaria")
        fecha_deposito_str = request.POST.get("fecha_deposito", "").strip()

        factura = FacturaOtrosIngresos.objects.filter(id=factura_id, empresa=empresa, estatus="pendiente").first()
        cuenta_bancaria = CuentaBancaria.objects.filter(id=cuenta_bancaria_id, empresa=empresa).first()

        if not factura or not cuenta_bancaria:
            messages.error(request, "Selecciona el ingreso y la cuenta bancaria correctamente.")
            return redirect("registrar_deposito_sanitarios")

        try:
            fecha_deposito = datetime.strptime(fecha_deposito_str, "%Y-%m-%d").date() if fecha_deposito_str else date.today()  # noqa: DTZ007, DTZ011
        except Exception:  # noqa: BLE001
            fecha_deposito = date.today()  # noqa: DTZ011

        if fecha_deposito < factura.fecha_vencimiento:
            messages.error(request, "La fecha de depósito no puede ser anterior a la fecha del corte.")
            return redirect("registrar_deposito_sanitarios")

        CobroOtrosIngresos.objects.create(
            factura=factura, fecha_cobro=fecha_deposito, monto=factura.monto,
            forma_cobro="efectivo", cuenta_bancaria=cuenta_bancaria,
            registrado_por=request.user,
            observaciones=f"Depósito registrado — {factura.observaciones}",
        )
        factura.actualizar_estatus()

        messages.success(request, f"✅ Depósito registrado para {factura.folio} — ${factura.monto}")
        return redirect("registrar_deposito_sanitarios")

    cuentas = CuentaBancaria.objects.filter(empresa=empresa, activa=True)

    return render(request, "sanitarios/registrar_deposito.html", {
        "empresa": empresa,
        "facturas_pendientes": facturas_pendientes,
        "cuentas": cuentas,
    })



##solo super user puede configurar precios de sanitarios y papel
@login_required
def configurar_precio_sanitario(request):
    if request.user.is_superuser:
        empresas = Empresa.objects.all().order_by("nombre")
    else:
        if not hasattr(request.user, "perfilusuario") or not request.user.perfilusuario.empresa:
            messages.error(request, "No tienes permiso para acceder a esta sección.")
            return redirect("dashboard_inicio")
        empresas = Empresa.objects.filter(id=request.user.perfilusuario.empresa_id)

    if request.method == "POST":
        for empresa in empresas:
            precio = request.POST.get(f"precio_{empresa.id}", "").strip()
            precio_papel = request.POST.get(f"precio_papel_{empresa.id}", "").strip()
            precio_toalla = request.POST.get(f"precio_toalla_{empresa.id}", "").strip()
            try:
                empresa.precio_sanitario = Decimal(precio) if precio else None
                empresa.precio_papel = Decimal(precio_papel) if precio_papel else None
                empresa.precio_toalla = Decimal(precio_toalla) if precio_toalla else None
                empresa.usa_boletos_fisicos_sanitario = f"boletos_{empresa.id}" in request.POST
                empresa.usa_boletos_fisicos_papel = f"boletos_papel_{empresa.id}" in request.POST
                empresa.save(update_fields=[
                    "precio_sanitario", "precio_papel", "precio_toalla",
                    "usa_boletos_fisicos_sanitario", "usa_boletos_fisicos_papel",
                ])
            except Exception:
                pass
        messages.success(request, "✅ Precios actualizados correctamente.")
        return redirect("configurar_precio_sanitario")

    return render(request, "sanitarios/configurar_precio.html", {"empresas": empresas})



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



@login_required
def imprimir_corte_sanitario(request, corte_id):
    corte = get_object_or_404(CorteSanitario, id=corte_id)

    usos_ventana = UsoSanitario.objects.filter(
        empresa=corte.empresa, caseta=corte.caseta,
        fecha_generado__gte=corte.fecha_hora_inicio, fecha_generado__lt=corte.fecha_hora_fin,
    )
    cobrados_ventana = UsoSanitario.objects.filter(
        empresa=corte.empresa, caseta=corte.caseta, estado="cobrado",
        fecha_cobro__gte=corte.fecha_hora_inicio, fecha_cobro__lt=corte.fecha_hora_fin,
    )

    generados = usos_ventana.count()
    gratuitos = usos_ventana.filter(estado="gratis").count()
    pendientes = usos_ventana.filter(estado="pendiente").count()
    total_real = cobrados_ventana.aggregate(t=Sum("monto"))["t"] or Decimal("0")

    TIPOS = [("sanitario", "🚻 Sanitario"), ("papel", "🧻 Papel"), ("toalla", "🩸 Toallas")]
    desglose = []
    for tipo_key, tipo_label in TIPOS:
        cobrados_tipo = cobrados_ventana.filter(tipo=tipo_key).order_by("codigo")
        if not cobrados_tipo.exists():
            continue

        total_tipo = cobrados_tipo.aggregate(t=Sum("monto"))["t"] or Decimal("0")
        cantidad = cobrados_tipo.count()

        if tipo_key == "toalla":
            rango = None
        else:
            usa_boletos = corte.empresa.usa_boletos_fisicos_sanitario if tipo_key == "sanitario" else corte.empresa.usa_boletos_fisicos_papel
            if usa_boletos:
                codigos = list(cobrados_tipo.values_list("codigo", flat=True))
                rango = f"{codigos[0]} a {codigos[-1]}" if codigos else None
            else:
                rango = "Códigos virtuales"

        desglose.append({"label": tipo_label, "cantidad": cantidad, "total": total_tipo, "rango": rango})

    cobro_deposito = None
    if corte.factura and corte.factura.estatus == "cobrada":
        cobro_deposito = corte.factura.cobros.order_by("-fecha_cobro").first()

    return render(request, "sanitarios/imprimir_corte.html", {
        "corte": corte,
        "total_real": total_real,
        "generados": generados,
        "gratuitos": gratuitos,
        "pendientes": pendientes,
        "desglose": desglose,
        "cobro_deposito": cobro_deposito,
    })


#solo super user puede cargar boletos fisicos
@login_required
def cargar_boletos_fisicos(request):
    tipo = request.GET.get("tipo") or request.POST.get("tipo") or "sanitario"
    nombre_concepto = "Sanitario" if tipo == 'sanitario' else "Papel"

    if tipo == 'sanitario':
        empresas_qs = Empresa.objects.filter(usa_boletos_fisicos_sanitario=True)
    else:
        empresas_qs = Empresa.objects.filter(usa_boletos_fisicos_papel=True)

    if not request.user.is_superuser:
        if not hasattr(request.user, "perfilusuario") or not request.user.perfilusuario.empresa:
            messages.error(request, "No tienes permiso para acceder a esta sección.")
            return redirect("dashboard_inicio")
        empresas_qs = empresas_qs.filter(id=request.user.perfilusuario.empresa_id)

    empresas = empresas_qs.order_by("nombre")

    empresa_id = request.GET.get("empresa") or request.POST.get("empresa")
    empresa = empresas.filter(id=empresa_id).first() if empresa_id else empresas.first()

    if not empresa:
        messages.error(request, f"No hay ninguna empresa configurada con boletos físicos de {nombre_concepto}.")
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
                return redirect(f"{request.path}?empresa={empresa.id}&tipo={tipo}")
        except ValueError:
            messages.error(request, "Revisa que el rango de números sea válido.")
            return redirect(f"{request.path}?empresa={empresa.id}&tipo={tipo}")

        codigos_generados = []
        for n in range(inicio_n, fin_n + 1):
            numero = str(n).zfill(digitos_n)
            codigo = f"{prefijo}-{numero}" if prefijo else numero
            codigos_generados.append(codigo)

        existentes = set(
            BoletoFisico.objects.filter(empresa=empresa, tipo=tipo, codigo__in=codigos_generados)
            .values_list("codigo", flat=True)
        )

        nuevos = [
            BoletoFisico(empresa=empresa, tipo=tipo, codigo=c, cargado_por=request.user)
            for c in codigos_generados if c not in existentes
        ]

        with transaction.atomic():
            BoletoFisico.objects.bulk_create(nuevos, batch_size=1000)

        creados = len(nuevos)
        ya_existian = len(codigos_generados) - creados

        messages.success(request, f"✅ {creados} boleto(s) de {nombre_concepto} cargado(s). {ya_existian} ya existían.")
        return redirect(f"{request.path}?empresa={empresa.id}&tipo={tipo}")

    disponibles = BoletoFisico.objects.filter(empresa=empresa, tipo=tipo, estado="disponible").count()
    usados = BoletoFisico.objects.filter(empresa=empresa, tipo=tipo, estado="usado").count()

    return render(request, "sanitarios/cargar_boletos.html", {
        "empresas": empresas,
        "empresa": empresa,
        "tipo": tipo,
        "nombre_concepto": nombre_concepto,
        "disponibles": disponibles,
        "usados": usados,
    })


#########modulo de venta de toallas para sanitarios########################

@login_required
def registrar_lote_toallas(request):
    empresa = _empresa_actual(request)
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    if request.method == "POST":
        codigo_barras = request.POST.get("codigo_barras", "").strip()
        cantidad = request.POST.get("cantidad", "").strip()

        if not codigo_barras or not cantidad.isdigit() or int(cantidad) <= 0:
            messages.error(request, "Captura el código de barras y una cantidad válida.")
            return redirect("registrar_lote_toallas")

        LoteToallas.objects.create(
            empresa=empresa, codigo_barras=codigo_barras,
            cantidad_inicial=int(cantidad), cantidad_disponible=int(cantidad),
            recibido_por=request.user,
        )
        messages.success(request, f"✅ Lote registrado: {cantidad} toallas.")
        return redirect("registrar_lote_toallas")

    lotes = LoteToallas.objects.filter(empresa=empresa).order_by("-fecha_recepcion")
    inventario_total = sum(l.cantidad_disponible for l in lotes)

    return render(request, "sanitarios/registrar_lote_toallas.html", {
        "empresa": empresa, "lotes": lotes, "inventario_total": inventario_total,
    })


@login_required
def imprimir_entrega_lote(request, lote_id):
    lote = get_object_or_404(LoteToallas, id=lote_id)
    return render(request, "sanitarios/entrega_lote.html", {"lote": lote})


########LISTA DE GAFETES DE ACCESO GRATUITO PARA SANITARIOS#####################
@login_required
def lista_gafetes_acceso(request):
    empresa = request.user.perfilusuario.empresa if not request.user.is_superuser else Empresa.objects.filter(id=request.session.get("empresa_id")).first()
    if not empresa:
        messages.error(request, "No se pudo determinar tu empresa.")
        return redirect("dashboard_inicio")

    if request.method == "POST":
        nombre_titular = request.POST.get("nombre_titular", "").strip()
        origen_tipo = request.POST.get("origen_tipo")
        local_id = request.POST.get("local")
        area_id = request.POST.get("area")

        local = LocalComercial.objects.filter(id=local_id, empresa=empresa).first() if origen_tipo == "local" and local_id else None
        area = AreaComun.objects.filter(id=area_id, empresa=empresa).first() if origen_tipo == "area" and area_id else None

        if not nombre_titular:
            messages.error(request, "Captura el nombre del titular.")
            return redirect("lista_gafetes_acceso")

        if not local and not area:
            messages.error(request, "Selecciona el local o el área común al que pertenece este gafete.")
            return redirect("lista_gafetes_acceso")

        gafete = GafeteAcceso.objects.create(
            empresa=empresa, nombre_titular=nombre_titular, local=local, area_comun=area,
        )
        messages.success(request, f"✅ Gafete '{gafete.numero}' registrado para {nombre_titular}.")
        return redirect("lista_gafetes_acceso")

    gafetes = GafeteAcceso.objects.filter(empresa=empresa).select_related("local", "area_comun").order_by("numero")
    locales = LocalComercial.objects.filter(empresa=empresa, activo=True).order_by("numero")
    areas = AreaComun.objects.filter(empresa=empresa, activo=True).order_by("numero")

    return render(request, "sanitarios/lista_gafetes.html", {
        "empresa": empresa, "gafetes": gafetes, "locales": locales, "areas": areas,
    })


@login_required
def toggle_gafete_acceso(request, gafete_id):
    gafete = get_object_or_404(GafeteAcceso, id=gafete_id)
    gafete.activo = not gafete.activo
    gafete.save(update_fields=["activo"])
    estado = "activado" if gafete.activo else "desactivado"
    messages.success(request, f"Gafete '{gafete.numero}' {estado}.")
    return redirect("lista_gafetes_acceso")



@login_required
def imprimir_gafete(request, gafete_id):
    gafete = get_object_or_404(GafeteAcceso, id=gafete_id)

    # Genera el QR con el número del gafete
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(gafete.numero)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "sanitarios/imprimir_gafete.html", {
        "gafete": gafete,
        "qr_base64": qr_base64,
    })