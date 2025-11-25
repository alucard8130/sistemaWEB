from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render
from principal.models import VisitanteAcceso
from django.shortcuts import redirect, get_object_or_404

@staff_member_required
def lista_usuarios_normales(request):
    usuarios = User.objects.filter(is_superuser=False).order_by('-date_joined')
    return render(request, "adminpanel/lista_usuarios.html", {"usuarios": usuarios})

@staff_member_required
def lista_usuarios_visitantes(request):
    visitantes = VisitanteAcceso.objects.select_related("empresa").all().order_by('-id')
    return render(request, "adminpanel/lista_visitantes.html", {"visitantes": visitantes})

@staff_member_required
def toggle_activo_visitante(request, visitante_id):
    visitante = get_object_or_404(VisitanteAcceso, id=visitante_id)
    visitante.activo = not visitante.activo
    visitante.save()
    return redirect('lista_usuarios_visitantes')

@staff_member_required
def toggle_reporte_visitante(request, visitante_id):
    visitante = get_object_or_404(VisitanteAcceso, id=visitante_id)
    visitante.acceso_api_reporte = not visitante.acceso_api_reporte
    visitante.save()
    return redirect('lista_usuarios_visitantes')