from django.contrib import messages
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render
from caja_chica.models import FondeoCajaChica, GastoCajaChica, ValeCaja
from principal.models import AuditoriaCambio, Aviso, Evento, SeguimientoTicket, TemaGeneral, TicketMantenimiento, VisitanteAcceso
from django.shortcuts import redirect, get_object_or_404
from django.core.mail import send_mail

@staff_member_required
def lista_usuarios_normales(request):
    usuarios = User.objects.filter(is_superuser=False).order_by('-date_joined')
    return render(request, "adminpanel/lista_usuarios.html", {"usuarios": usuarios})

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
            "Tu cuenta ha sido activada por el sistema GESAC. Ya puedes ingresar: https://adminsoftheron.onrender.com/visitante/login/ \n\n"
            "Atentamente,\n"
            "El equipo de SoftHeron. \n\n" 
            "Gracias por utilizar nuestro sistema. Visita nuestra página web: \n"
            "https://paginaweb-ro9v.onrender.com \n"
            
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

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from empresas.models import Empresa
from locales.models import LocalComercial
from areas.models import AreaComun
from clientes.models import Cliente
from facturacion.models import CobroOtrosIngresos, Factura, FacturaOtrosIngresos, Pago
from gastos.models import Gasto, PagoGasto
from presupuestos.models import Presupuesto, PresupuestoIngreso
from empleados.models import Empleado
from proveedores.models import Proveedor

@user_passes_test(lambda u: u.is_superuser)
def resetear_empresa(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if request.method == "POST":
        # Borra todos los datos relacionados a la empresa
        Factura.objects.filter(empresa=empresa).delete()
        FacturaOtrosIngresos.objects.filter(empresa=empresa).delete()
        Pago.objects.filter(factura__empresa=empresa).delete()
        CobroOtrosIngresos.objects.filter(factura__empresa=empresa).delete()
        FondeoCajaChica.objects.filter(empresa=empresa).delete()
        GastoCajaChica.objects.filter(fondeo__empresa=empresa).delete()
        ValeCaja.objects.filter(fondeo__empresa=empresa).delete()
        LocalComercial.objects.filter(empresa=empresa).delete()
        AreaComun.objects.filter(empresa=empresa).delete()
        Cliente.objects.filter(empresa=empresa).delete()
        Proveedor.objects.filter(empresa=empresa).delete()
        Empleado.objects.filter(empresa=empresa).delete()
        Gasto.objects.filter(empresa=empresa).delete()
        PagoGasto.objects.filter(gasto__empresa=empresa).delete()
        #AuditoriaCambio.objects.filter(usuario__perfilusuario__empresa=empresa).delete()
        Evento.objects.filter(empresa=empresa).delete()
        #TicketMantenimiento.objects.filter(empresa=empresa).delete()
        #SeguimientoTicket.objects.filter(ticket__empresa=empresa).delete()
        TemaGeneral.objects.filter(empresa=empresa).delete()
        Aviso.objects.filter(empresa=empresa).delete()
        Presupuesto.objects.filter(empresa=empresa).delete()
        PresupuestoIngreso.objects.filter(empresa=empresa).delete()
        # Puedes agregar más modelos relacionados aquí

        messages.success(request, f"Todos los datos de la empresa '{empresa.nombre}' han sido eliminados.")
        return redirect('bienvenida')  # O la vista que prefieras

    return render(request, "adminpanel/resetear_empresa_confirm.html", {"empresa": empresa})