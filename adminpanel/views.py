
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from areas.models import AreaComun
from caja_chica.models import FondeoCajaChica, GastoCajaChica, ValeCaja
from clientes.models import Cliente
from conciliaciones.models import (
    ConciliacionBancaria,
    EstadoCuentaBancario,
    MovimientoSistema,
    SaldoCuentaPeriodo,
)
from empleados.models import Empleado
from empresas.models import Empresa
from escuelas.models import (
    Alumno,
    CarteraVencida,
    IngresoEscuela,
    LoteImportacionIngresos,
    PresupuestoIngresoEscuela,
    SolicitudAdmision,
)
from facturacion.models import (
    CobroOtrosIngresos,
    Factura,
    FacturaOtrosIngresos,
    GrupoFacturacion,
    Pago,
    PoolVacancia,
    SaldoAFavor,
    TipoCuotaHomologacion,
    TipoOtroIngreso,
)
from gastos.models import (
    CuentaContable,
    Gasto,
    GrupoGasto,
    PagoGasto,
    SubgrupoGasto,
    TipoGasto,
)
from locales.models import LocalComercial
from presupuestos.models import Presupuesto, PresupuestoIngreso
from principal.models import Aviso, Evento, PerfilUsuario, TemaGeneral, VisitanteAcceso
from proveedores.models import Proveedor
from sanitarios.models import BoletoFisico, CasetaOperador, CorteSanitario, UsoSanitario
from traspasos.models import TraspasoBancario

logger = logging.getLogger(__name__)


#usuarios GESAC
@staff_member_required
def lista_usuarios_normales(request):
    usuarios = User.objects.filter(is_superuser=False).order_by('-date_joined')
    return render(request, "adminpanel/lista_usuarios.html", {"usuarios": usuarios})

#usuarios condomninos
@staff_member_required
def lista_usuarios_visitantes(request):
    visitantes = VisitanteAcceso.objects.all().order_by('-id')
    return render(request, "adminpanel/lista_visitantes.html", {"visitantes": visitantes})

@staff_member_required
def toggle_activo_visitante(request, visitante_id):
    visitante = get_object_or_404(VisitanteAcceso, id=visitante_id)
    visitante.activo = not visitante.activo
    visitante.save()
    estado = "activado" if visitante.activo else "desactivado"
    messages.success(request, f"El visitante {visitante.username} ha sido {estado}.")

    # Enviar correo solo si se activó
    if visitante.activo:
        mensaje = (
            f"Hola {visitante.nombre},\n\n"
            "Tu cuenta ha sido activada por el sistema GESAC. Ya puedes ingresar: https://www.gesac.com.mx/visitante/login/ \n\n"
            "Atentamente,\n"
            "El equipo de SoftHeron. \n\n" 
            "Gracias por utilizar nuestro sistema. Visita nuestra página web: \n"
            "https://www.devsoftheron.com.mx \n"
            
        )
        send_mail(
            'Tu cuenta ha sido activada',
            mensaje,
            settings.EMAIL_HOST_USER, 
            [visitante.email],
            fail_silently=True,
        )
    return redirect('lista_usuarios_visitantes')

@staff_member_required
def toggle_reporte_visitante(request, visitante_id):
    visitante = get_object_or_404(VisitanteAcceso, id=visitante_id)
    visitante.acceso_api_reporte = not visitante.acceso_api_reporte
    visitante.save()
    return redirect('lista_usuarios_visitantes')



MODOS_RESET = {
    'movimientos': 'Solo movimientos (deja catálogos, presupuestos, usuarios y cuentas bancarias)',
    'todo': 'Todo (movimientos + catálogos, presupuestos y datos maestros)',
}


def _plan_reset(empresa, modo):
    """Lista ordenada [(grupo, etiqueta, queryset)] de lo que se borra. Es la
    MISMA lista que muestra la vista previa y la que se ejecuta, para que lo que
    ves sea exactamente lo que se elimina."""
    todo = modo == 'todo'
    plan = []

    def add(grupo, etiqueta, qs):
        plan.append((grupo, etiqueta, qs))

    # --- Facturación y cobranza ---
    add('Facturación y cobranza', 'Saldos a favor de clientes', SaldoAFavor.objects.filter(empresa=empresa))
    add('Facturación y cobranza', 'Pagos (incluye depósitos no identificados)',
        Pago.objects.filter(Q(factura__empresa=empresa) | Q(empresa=empresa)))
    add('Facturación y cobranza', 'Cobros de otros ingresos', CobroOtrosIngresos.objects.filter(factura__empresa=empresa))
    add('Facturación y cobranza', 'Facturas de otros ingresos', FacturaOtrosIngresos.objects.filter(empresa=empresa))
    add('Facturación y cobranza', 'Facturas', Factura.objects.filter(empresa=empresa))
    if todo:
        add('Facturación y cobranza', 'Grupos de facturación', GrupoFacturacion.objects.filter(empresa=empresa))
        add('Facturación y cobranza', 'Pools de vacancia', PoolVacancia.objects.filter(empresa=empresa))

    # --- Caja chica ---
    add('Caja chica', 'Gastos de caja chica', GastoCajaChica.objects.filter(fondeo__empresa=empresa))
    add('Caja chica', 'Vales de caja', ValeCaja.objects.filter(fondeo__empresa=empresa))
    add('Caja chica', 'Fondeos (cheque / transferencia / cobros en efectivo)', FondeoCajaChica.objects.filter(empresa=empresa))

    # --- Gastos ---
    add('Gastos', 'Pagos de gastos', PagoGasto.objects.filter(gasto__empresa=empresa))
    add('Gastos', 'Gastos', Gasto.objects.filter(empresa=empresa))

    # --- Bancos ---
    add('Bancos', 'Traspasos bancarios', TraspasoBancario.objects.filter(empresa=empresa))
    add('Bancos', 'Conciliaciones', ConciliacionBancaria.objects.filter(empresa=empresa))
    add('Bancos', 'Estados de cuenta cargados', EstadoCuentaBancario.objects.filter(empresa=empresa))
    add('Bancos', 'Movimientos de sistema (conciliación)', MovimientoSistema.objects.filter(empresa=empresa))
    add('Bancos', 'Saldos por período', SaldoCuentaPeriodo.objects.filter(empresa=empresa))

    # --- Escuela (solo si la empresa es del segmento escuela) ---
    if empresa.segmento == 'escuela':
        add('Escuela', 'Ingresos importados (Detalle de Pagos / cobranza)', IngresoEscuela.objects.filter(empresa=empresa))
        add('Escuela', 'Lotes de importación de ingresos', LoteImportacionIngresos.objects.filter(empresa=empresa))
        add('Escuela', 'Cartera vencida (todos los cortes)', CarteraVencida.objects.filter(empresa=empresa))
        add('Escuela', 'Alumnos (roster)', Alumno.objects.filter(empresa=empresa))
        if todo:
            add('Escuela', 'Presupuesto de ingresos', PresupuestoIngresoEscuela.objects.filter(empresa=empresa))
            add('Escuela', 'Solicitudes de admisión (HubSpot)', SolicitudAdmision.objects.filter(empresa=empresa))

    # --- Control de sanitarios ---
    add('Sanitarios', 'Usos de sanitario', UsoSanitario.objects.filter(empresa=empresa))
    add('Sanitarios', 'Boletos físicos', BoletoFisico.objects.filter(empresa=empresa))
    add('Sanitarios', 'Cortes sanitarios', CorteSanitario.objects.filter(empresa=empresa))

    if todo:
        # --- Propiedades y catálogos ---
        add('Catálogos y datos maestros', 'Locales', LocalComercial.objects.filter(empresa=empresa))
        add('Catálogos y datos maestros', 'Áreas comunes', AreaComun.objects.filter(empresa=empresa))
        add('Catálogos y datos maestros', 'Clientes', Cliente.objects.filter(empresa=empresa))
        add('Catálogos y datos maestros', 'Proveedores', Proveedor.objects.filter(empresa=empresa))
        add('Catálogos y datos maestros', 'Empleados', Empleado.objects.filter(empresa=empresa))
        add('Catálogos y datos maestros', 'Tipos de gasto', TipoGasto.objects.filter(empresa=empresa))
        add('Catálogos y datos maestros', 'Tipos de cuota (homologación)', TipoCuotaHomologacion.objects.filter(empresa=empresa))
        add('Catálogos y datos maestros', 'Tipos de otro ingreso', TipoOtroIngreso.objects.filter(empresa=empresa))
        add('Catálogos y datos maestros', 'Cuentas contables', CuentaContable.objects.filter(empresa=empresa))
        add('Catálogos y datos maestros', 'Casetas de operador', CasetaOperador.objects.filter(empresa=empresa))
        # --- Comunicación ---
        add('Comunicación', 'Eventos', Evento.objects.filter(empresa=empresa))
        add('Comunicación', 'Temas generales', TemaGeneral.objects.filter(empresa=empresa))
        add('Comunicación', 'Avisos', Aviso.objects.filter(empresa=empresa))
        # --- Presupuestos ---
        add('Presupuestos', 'Presupuestos de gasto', Presupuesto.objects.filter(empresa=empresa))
        add('Presupuestos', 'Presupuestos de ingreso', PresupuestoIngreso.objects.filter(empresa=empresa))
    return plan


@user_passes_test(lambda u: u.is_superuser)
def resetear_empresa(request, empresa_id):
    """Pone una empresa en ceros. Solo superusuario. Dos modos:
    - 'movimientos': borra lo transaccional (ingresos, gastos, caja chica, bancos,
      alumnos, cartera...) y deja catálogos, presupuestos, usuarios y cuentas bancarias.
    - 'todo': además borra catálogos y datos maestros (comportamiento anterior).
    Pide escribir el nombre exacto de la empresa para confirmar."""
    empresa = get_object_or_404(Empresa, id=empresa_id)
    modo_default = 'movimientos' if empresa.segmento == 'escuela' else 'todo'

    if request.method == "POST":
        modo = request.POST.get('modo', modo_default)
        if modo not in MODOS_RESET:
            modo = modo_default
        if request.POST.get('confirmacion', '').strip().casefold() != empresa.nombre.strip().casefold():
            messages.error(request, "El nombre escrito no coincide con el de la empresa; no se borró nada.")
            return redirect(f"{request.path}?modo={modo}")

        resumen = {}
        with transaction.atomic():
            for _grupo, etiqueta, qs in _plan_reset(empresa, modo):
                total = qs.count()
                if total:
                    qs.delete()
                    resumen[etiqueta] = total

            if modo == 'todo':
                # --- Contadores -- solo se les quita el acceso a ESTA empresa, nunca se borra su cuenta ---
                for perfil in PerfilUsuario.objects.filter(empresas_contador=empresa):
                    perfil.empresas_contador.remove(empresa)
                    if perfil.empresa_id == empresa.id:
                        nueva_empresa = perfil.empresas_contador.first()
                        perfil.empresa = nueva_empresa
                        perfil.save(update_fields=["empresa"])

        logger.warning(
            "RESET EMPRESA id=%s nombre=%r modo=%s por usuario=%s -- registros borrados: %s",
            empresa.id, empresa.nombre, modo, request.user.username, resumen,
        )
        messages.success(
            request,
            f"La empresa '{empresa.nombre}' quedó en ceros ({MODOS_RESET[modo].split(' (')[0].lower()}): "
            f"{sum(resumen.values())} registro(s) eliminado(s).",
        )
        return redirect('dashboard_inicio')

    modo = request.GET.get('modo', modo_default)
    if modo not in MODOS_RESET:
        modo = modo_default
    grupos = {}
    total_registros = 0
    for grupo, etiqueta, qs in _plan_reset(empresa, modo):
        n = qs.count()
        total_registros += n
        grupos.setdefault(grupo, []).append({'etiqueta': etiqueta, 'n': n})
    return render(request, "adminpanel/resetear_empresa_confirm.html", {
        "empresa": empresa,
        "modo": modo,
        "modos": MODOS_RESET,
        "grupos": grupos,
        "total_registros": total_registros,
    })