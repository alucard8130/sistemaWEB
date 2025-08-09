from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import FondeoCajaChica, GastoCajaChica, ValeCaja
from .forms import FondeoCajaChicaForm, GastoCajaChicaForm, ValeCajaForm


def imprimir_vale_caja(request, vale_id):
    vale = get_object_or_404(ValeCaja, id=vale_id)
    return render(request, "caja_chica/imprimir_vale_caja.html", {"vale": vale})


def detalle_fondeo(request, fondeo_id):
    fondeo = get_object_or_404(FondeoCajaChica, id=fondeo_id)
    gastos = fondeo.gastocajachica_set.all()
    vales = fondeo.valecaja_set.all()
    return render(
        request,
        "caja_chica/detalle_fondeo.html",
        {"fondeo": fondeo, "gastos": gastos, "vales": vales},
    )

@login_required
def fondeo_caja_chica(request):
    empresa = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil:
            empresa = getattr(perfil, "empresa", None)
    if request.method == "POST":
        form = FondeoCajaChicaForm(request.POST)
        if empresa:
            form.fields["empleado_asignado"].queryset = form.fields["empleado_asignado"].queryset.filter(empresa=empresa)
        if form.is_valid():
            fondeo = form.save(commit=False)
            fondeo.saldo = fondeo.importe_cheque
            fondeo.empresa = empresa
            fondeo.save()
            messages.success(request, "Fondeo registrado exitosamente.")
            return redirect("lista_fondeos")
    else:
        form = FondeoCajaChicaForm()
        if empresa:
            form.fields["empleado_asignado"].queryset = form.fields["empleado_asignado"].queryset.filter(empresa=empresa)
    return render(request, "caja_chica/fondeo_caja_chica.html", {"form": form})

@login_required
def registrar_gasto_caja_chica(request):
    empresa = None
    perfil = getattr(request.user, "perfilusuario", None)
    if perfil:
        empresa = getattr(perfil, "empresa", None)
    fondeo_id = request.GET.get("fondeo_id")
    fondeo_instance = None
    if fondeo_id:
        try:
            fondeo_instance = FondeoCajaChica.objects.get(id=fondeo_id)
        except FondeoCajaChica.DoesNotExist:
            fondeo_instance = None
    if request.method == "POST":
        form = GastoCajaChicaForm(request.POST)
        if empresa:
            form.fields["proveedor"].queryset = form.fields["proveedor"].queryset.filter(empresa=empresa)
            form.fields["tipo_gasto"].queryset = form.fields["tipo_gasto"].queryset.filter(empresa=empresa)
        if form.is_valid():
            gasto = form.save(commit=False)
            fondeo = gasto.fondeo
            fondeo.saldo -= gasto.importe
            fondeo.save()
            gasto.save()
            messages.success(request, "Gasto registrado exitosamente.")
            return redirect("lista_gastos_caja_chica")
    else:
        initial = {}
        if fondeo_instance:
            initial["fondeo"] = fondeo_instance
        form = GastoCajaChicaForm(initial=initial)
        if empresa:
            form.fields["proveedor"].queryset = form.fields["proveedor"].queryset.filter(empresa=empresa)
            form.fields["tipo_gasto"].queryset = form.fields["tipo_gasto"].queryset.filter(empresa=empresa)
        if fondeo_instance:
            form.fields["fondeo"].queryset = FondeoCajaChica.objects.filter(id=fondeo_instance.id)
    return render(request, "caja_chica/registrar_gasto_caja_chica.html", {"form": form})

@login_required
def generar_vale_caja(request):
    from gastos.models import TipoGasto

    empresa = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil:
            empresa = getattr(perfil, "empresa", None)
    if request.method == "POST":
        form = ValeCajaForm(request.POST)
        if empresa:
            form.fields["tipo_gasto"].queryset = TipoGasto.objects.filter(
                empresa=empresa
            )
        if form.is_valid():
            vale = form.save(commit=False)
            fondeo = vale.fondeo
            fondeo.saldo -= vale.importe
            fondeo.save()
            vale.save()
            messages.success(request, "Vale generado exitosamente.")
            return redirect("lista_vales_caja_chica")
    else:
        form = ValeCajaForm()
        if empresa:
            form.fields["tipo_gasto"].queryset = TipoGasto.objects.filter(
                empresa=empresa
            )
    return render(request, "caja_chica/generar_vale_caja.html", {"form": form})

@login_required
def lista_fondeos(request):
    empresa = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil:
            empresa = getattr(perfil, "empresa", None)
    if empresa:
        fondeos = FondeoCajaChica.objects.filter(empresa=empresa)
    else:
        fondeos = FondeoCajaChica.objects.all()
    return render(request, "caja_chica/lista_fondeos.html", {"fondeos": fondeos})


@login_required
def lista_gastos_caja_chica(request):
    empresa = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil:
            empresa = getattr(perfil, "empresa", None)
    if empresa:
        gastos = GastoCajaChica.objects.select_related("fondeo").filter(
            fondeo__empresa=empresa
        )
    else:
        gastos = GastoCajaChica.objects.select_related("fondeo").all()
    return render(
        request, "caja_chica/lista_gastos_caja_chica.html", {"gastos": gastos}
    )


@login_required
def lista_vales_caja_chica(request):
    empresa = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil:
            empresa = getattr(perfil, "empresa", None)
    if empresa:
        vales = ValeCaja.objects.select_related("fondeo").filter(
            fondeo__empresa=empresa
        )
    else:
        vales = ValeCaja.objects.select_related("fondeo").all()
    return render(request, "caja_chica/lista_vales_caja_chica.html", {"vales": vales})
