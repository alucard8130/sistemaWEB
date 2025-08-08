from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import FondeoCajaChica, GastoCajaChica, ValeCaja
from .forms import FondeoCajaChicaForm, GastoCajaChicaForm, ValeCajaForm

def imprimir_vale_caja(request, vale_id):
    vale = get_object_or_404(ValeCaja, id=vale_id)
    return render(request, "caja_chica/imprimir_vale_caja.html", {"vale": vale})


from django.shortcuts import get_object_or_404


def detalle_fondeo(request, fondeo_id):
    fondeo = get_object_or_404(FondeoCajaChica, id=fondeo_id)
    gastos = fondeo.gastocajachica_set.all()
    vales = fondeo.valecaja_set.all()
    return render(
        request,
        "caja_chica/detalle_fondeo.html",
        {"fondeo": fondeo, "gastos": gastos, "vales": vales},
    )


def fondeo_caja_chica(request):
    empresa = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil:
            empresa = getattr(perfil, "empresa", None)
    if request.method == "POST":
        form = FondeoCajaChicaForm(request.POST)
        if form.is_valid():
            fondeo = form.save(commit=False)
            fondeo.saldo = fondeo.importe_cheque
            fondeo.empresa = empresa
            fondeo.save()
            messages.success(request, "Fondeo registrado exitosamente.")
            return redirect("lista_fondeos")
    else:
        form = FondeoCajaChicaForm()
    return render(request, "caja_chica/fondeo_caja_chica.html", {"form": form})


def registrar_gasto_caja_chica(request):
    empresa = getattr(request.user, "empresa", None)
    fondeo_id = request.GET.get("fondeo_id")
    fondeo_instance = None
    if fondeo_id:
        try:
            fondeo_instance = FondeoCajaChica.objects.get(id=fondeo_id)
        except FondeoCajaChica.DoesNotExist:
            fondeo_instance = None
    if request.method == "POST":
        form = GastoCajaChicaForm(request.POST)
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
            form.fields["proveedor"].queryset = form.fields[
                "proveedor"
            ].queryset.filter(empresa=empresa)
            form.fields["tipo_gasto"].queryset = form.fields[
                "tipo_gasto"
            ].queryset.filter(empresa=empresa)
        if fondeo_instance:
            form.fields["fondeo"].queryset = FondeoCajaChica.objects.filter(
                id=fondeo_instance.id
            )
    return render(request, "caja_chica/registrar_gasto_caja_chica.html", {"form": form})


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


def lista_fondeos(request):
    empresa = getattr(request.user, "empresa", None)
    if empresa:
        fondeos = FondeoCajaChica.objects.filter(empresa=empresa)
    else:
        fondeos = FondeoCajaChica.objects.all()
    return render(request, "caja_chica/lista_fondeos.html", {"fondeos": fondeos})


def lista_gastos_caja_chica(request):
    gastos = GastoCajaChica.objects.select_related("fondeo").all()
    return render(
        request, "caja_chica/lista_gastos_caja_chica.html", {"gastos": gastos}
    )


def lista_vales_caja_chica(request):
    vales = ValeCaja.objects.select_related("fondeo").all()
    return render(request, "caja_chica/lista_vales_caja_chica.html", {"vales": vales})
