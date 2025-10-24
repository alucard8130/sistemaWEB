from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from num2words import num2words
from .models import FondeoCajaChica, GastoCajaChica, ValeCaja
from .forms import FondeoCajaChicaForm, GastoCajaChicaForm, ValeCajaForm
from gastos.models import TipoGasto
from django.db import transaction
from decimal import Decimal, InvalidOperation

def imprimir_vale_caja(request, vale_id):
    vale = get_object_or_404(ValeCaja, id=vale_id)
    monto_letra = num2words(vale.importe, lang='es', to='currency', currency='MXN').capitalize()
    empresa = request.user.perfilusuario.empresa
    return render(request, "caja_chica/imprimir_vale_caja.html", {"vale": vale, "monto_letra": monto_letra, "empresa": empresa})


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
    """
    Alta de fondeo: valida que numero_cheque no se repita dentro de la misma empresa
    del usuario logeado. Si existe, marca error en el form.
    """
    empresa = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil:
            empresa = getattr(perfil, "empresa", None)

    if request.method == "POST":
        form = FondeoCajaChicaForm(request.POST)
        # filtrar campos relacionados por empresa si aplica
        try:
            if empresa:
                if "empleado_asignado" in form.fields:
                    form.fields["empleado_asignado"].queryset = form.fields["empleado_asignado"].queryset.filter(empresa=empresa)
        except Exception:
            pass

        if form.is_valid():
            cheque_val = form.cleaned_data.get("numero_cheque", None)
            if cheque_val:
                cheque_norm = str(cheque_val).strip()
                qs = FondeoCajaChica.objects.filter(numero_cheque__iexact=cheque_norm)
                if empresa:
                    qs = qs.filter(empresa=empresa)
                if qs.exists():
                    form.add_error("numero_cheque", "El número de cheque ya existe para esta empresa.")
                    messages.error(request, "El número de cheque ya existe para esta empresa.")
                    return render(request, "caja_chica/fondeo_caja_chica.html", {"form": form})

            fondeo = form.save(commit=False)
            # asegurar empresa asociada al fondeo (usar empresa del perfil)
            if empresa:
                fondeo.empresa = empresa
            # inicializar saldo con importe_cheque si no se proporcionó saldo
            if (fondeo.saldo is None or fondeo.saldo == 0) and getattr(fondeo, "importe_cheque", None) not in (None, ""):
                try:
                    fondeo.saldo = fondeo.importe_cheque
                except Exception:
                    pass
            fondeo.save()
            messages.success(request, "Fondeo registrado exitosamente.")
            return redirect("lista_fondeos")
    else:
        form = FondeoCajaChicaForm()
        if empresa:
            try:
                if "empleado_asignado" in form.fields:
                    form.fields["empleado_asignado"].queryset = form.fields["empleado_asignado"].queryset.filter(empresa=empresa)
            except Exception:
                pass

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
            form.fields["fondeo"].queryset = FondeoCajaChica.objects.filter(empresa=empresa)
        if form.is_valid():
            gasto = form.save(commit=False)
            fondeo = gasto.fondeo
            if gasto.importe > fondeo.saldo:
                form.add_error("importe", f"El importe excede el saldo disponible (${fondeo.saldo}) en el fondeo.")
                messages.error(request, f"El importe excede el saldo disponible ${fondeo.saldo} en el fondeo.")
            else:
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
            form.fields["fondeo"].queryset = FondeoCajaChica.objects.filter(empresa=empresa)
        if fondeo_instance:
            form.fields["fondeo"].queryset = FondeoCajaChica.objects.filter(id=fondeo_instance.id)
    return render(request, "caja_chica/registrar_gasto_caja_chica.html", {"form": form})

@login_required
def generar_vale_caja(request):
    empresa = None
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil:
            empresa = getattr(perfil, "empresa", None)
    if request.method == "POST":
        form = ValeCajaForm(request.POST)
        if empresa:
            form.fields["tipo_gasto"].queryset = TipoGasto.objects.filter(empresa=empresa)
            form.fields["fondeo"].queryset = FondeoCajaChica.objects.filter(empresa=empresa)
        if form.is_valid():
            vale = form.save(commit=False)
            fondeo = vale.fondeo
            if vale.importe > fondeo.saldo:
                form.add_error("importe", f"El importe excede el saldo disponible (${fondeo.saldo}) en el fondeo.")
                messages.error(request, f"El importe excede el saldo disponible ${fondeo.saldo} en el fondeo.")
            else:
                fondeo.saldo -= vale.importe
                fondeo.save()
                vale.save()
                messages.success(request, "Vale generado exitosamente.")
                return redirect("lista_vales_caja_chica")
    else:
        form = ValeCajaForm()
        if empresa:
            form.fields["tipo_gasto"].queryset = TipoGasto.objects.filter(empresa=empresa)
            form.fields["fondeo"].queryset = FondeoCajaChica.objects.filter(empresa=empresa)
    return render(request, "caja_chica/generar_vale_caja.html", {"form": form})

@login_required
def lista_fondeos(request):
    empresa_id = request.session.get("empresa_id")
    if request.user.is_superuser and empresa_id:
        fondeos = FondeoCajaChica.objects.filter(empresa_id=empresa_id)
    elif request.user.is_superuser:
        fondeos = FondeoCajaChica.objects.all()
    else:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil and perfil.empresa:
            fondeos = FondeoCajaChica.objects.filter(empresa=perfil.empresa)
        else:
            fondeos = FondeoCajaChica.objects.none()
    return render(request, "caja_chica/lista_fondeos.html", {"fondeos": fondeos})


@login_required
def lista_gastos_caja_chica(request):
    empresa_id = request.session.get("empresa_id")
    if request.user.is_superuser and empresa_id:
        gastos = GastoCajaChica.objects.select_related("fondeo").filter(
            fondeo__empresa_id=empresa_id
        )
    elif request.user.is_superuser:
        gastos = GastoCajaChica.objects.select_related("fondeo").all()
    else:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil and perfil.empresa:
            gastos = GastoCajaChica.objects.select_related("fondeo").filter(
                fondeo__empresa=perfil.empresa
            )
        else:
            gastos = GastoCajaChica.objects.select_related("fondeo").none()
    return render(
        request, "caja_chica/lista_gastos_caja_chica.html", {"gastos": gastos}
    )


@login_required
def lista_vales_caja_chica(request):
    empresa_id = request.session.get("empresa_id")
    if request.user.is_superuser and empresa_id:
        vales = ValeCaja.objects.select_related("fondeo").filter(
            fondeo__empresa_id=empresa_id
        )
    elif request.user.is_superuser:
        vales = ValeCaja.objects.select_related("fondeo").all()
    else:
        perfil = getattr(request.user, "perfilusuario", None)
        if perfil and perfil.empresa:
            vales = ValeCaja.objects.select_related("fondeo").filter(
                fondeo__empresa=perfil.empresa
            )
        else:
            vales = ValeCaja.objects.select_related("fondeo").none()
    return render(request, "caja_chica/lista_vales_caja_chica.html", {"vales": vales})

@login_required
def recibo_fondeo_caja(request, fondeo_id):
    fondeo = get_object_or_404(FondeoCajaChica, pk=fondeo_id)
    empresa = request.user.perfilusuario.empresa
    monto_letra = num2words(fondeo.importe_cheque, lang='es', to='currency', currency='MXN').capitalize()
    return render(request, 'caja_chica/recibo_fondeo.html', {'fondeo': fondeo, 'monto_letra': monto_letra, 'empresa': empresa })



@login_required
def eliminar_vale_caja(request, vale_id):
    """
    Confirmar (GET) y eliminar (POST) un ValeCaja.
    - Superuser: si hay empresa seleccionada en session ('empresa_id'), sólo puede eliminar vales de esa empresa.
    - Usuario normal: sólo puede eliminar vales pertenecientes a su empresa en perfil.
    Al eliminar, devuelve el importe al fondeo asociado.
    """
    vale = get_object_or_404(ValeCaja, pk=vale_id)
    fondeo = getattr(vale, "fondeo", None)
    vale_empresa_id = None
    if fondeo and getattr(fondeo, "empresa", None):
        vale_empresa_id = fondeo.empresa.id

    # permiso multiempresa
    if request.user.is_superuser:
        sess_empresa_id = request.session.get("empresa_id")
        if sess_empresa_id and vale_empresa_id and int(sess_empresa_id) != int(vale_empresa_id):
            messages.error(request, "No tienes permiso para eliminar este vale bajo la empresa seleccionada.")
            return redirect("lista_vales_caja_chica")
    else:
        perfil = getattr(request.user, "perfilusuario", None)
        if not perfil or not getattr(perfil, "empresa", None) or perfil.empresa.id != vale_empresa_id:
            messages.error(request, "No tienes permiso para eliminar este vale.")
            return redirect("lista_vales_caja_chica")

    if request.method == "POST":
        with transaction.atomic():
            # devolver importe al fondeo si aplica
            if fondeo:
                fondeo.saldo = (fondeo.saldo or 0) + (vale.importe or 0)
                fondeo.save()
            vale.delete()
        messages.success(request, "Vale eliminado correctamente.")
        return redirect("lista_vales_caja_chica")

    return render(request, "caja_chica/confirm_eliminar_vale.html", {"vale": vale})

@login_required
def eliminar_gasto_caja(request, gasto_id):
    """
    Confirmar (GET) y eliminar (POST) un GastoCaja.
    - Superuser: si hay empresa seleccionada en session ('empresa_id'), sólo puede eliminar gastos de esa empresa.
    - Usuario normal: sólo puede eliminar gastos pertenecientes a su empresa en perfil.
    Al eliminar, devuelve el importe al fondeo asociado si aplica.
    """
    gasto = get_object_or_404(GastoCajaChica, pk=gasto_id)
    fondeo = getattr(gasto, "fondeo", None)
    gasto_empresa_id = None
    if fondeo and getattr(fondeo, "empresa", None):
        gasto_empresa_id = fondeo.empresa.id
    else:
        # intentar obtener empresa desde el gasto o su vale relacionado
        gasto_empresa_id = getattr(gasto, 'empresa_id', None) or getattr(getattr(gasto, 'vale', None), 'empresa_id', None)

    # permisos multiempresa
    if request.user.is_superuser:
        sess_empresa_id = request.session.get("empresa_id")
        if sess_empresa_id and gasto_empresa_id and int(sess_empresa_id) != int(gasto_empresa_id):
            messages.error(request, "No tienes permiso para eliminar este gasto bajo la empresa seleccionada.")
            return redirect("lista_gastos_caja_chica")
    else:
        perfil = getattr(request.user, "perfilusuario", None)
        if not perfil or not getattr(perfil, "empresa", None) or perfil.empresa.id != gasto_empresa_id:
            messages.error(request, "No tienes permiso para eliminar este gasto.")
            return redirect("lista_gastos_caja_chica")

    if request.method == "POST":
        with transaction.atomic():
            if fondeo:
                fondeo.saldo = (fondeo.saldo or 0) + (gasto.importe or 0)
                fondeo.save()
            gasto.delete()
        messages.success(request, "Gasto eliminado correctamente.")
        return redirect("lista_gastos_caja_chica")

    return render(request, "caja_chica/confirm_eliminar_gasto.html", {"gasto": gasto})


@login_required
def eliminar_fondeo(request, fondeo_id):
    """
    Elimina un FondeoCajaChica solo si saldo == importe_cheque.
    Respeta permisos multiempresa (session empresa para superuser, perfil para usuario normal).
    """
    fondeo = get_object_or_404(FondeoCajaChica, pk=fondeo_id)
    fondeo_empresa_id = getattr(getattr(fondeo, "empresa", None), "id", None)

    # permisos multiempresa
    if request.user.is_superuser:
        sess_empresa_id = request.session.get("empresa_id")
        if sess_empresa_id and fondeo_empresa_id and int(sess_empresa_id) != int(fondeo_empresa_id):
            messages.error(request, "No tienes permiso para eliminar este fondeo bajo la empresa seleccionada.")
            return redirect("lista_fondeos")
    else:
        perfil = getattr(request.user, "perfilusuario", None)
        if not perfil or not getattr(perfil, "empresa", None) or perfil.empresa.id != fondeo_empresa_id:
            messages.error(request, "No tienes permiso para eliminar este fondeo.")
            return redirect("lista_fondeos")

    # obtener importe_cheque y saldo como Decimal
    try:
        importe = Decimal(str(fondeo.importe_cheque or 0))
    except (InvalidOperation, TypeError, ValueError):
        importe = Decimal("0")
    try:
        saldo = Decimal(str(fondeo.saldo or 0))
    except (InvalidOperation, TypeError, ValueError):
        saldo = Decimal("0")

    # GET -> mostrar confirmación
    if request.method == "GET":
        return render(request, "caja_chica/confirm_eliminar_fondeo.html", {"fondeo": fondeo, "importe": importe, "saldo": saldo})

    # POST -> eliminar sólo si saldo == importe_cheque
    if request.method == "POST":
        if saldo != importe:
            messages.error(request, "No se puede eliminar el fondeo: tiene gastos asociados.")
            return redirect("lista_fondeos")
        with transaction.atomic():
            fondeo.delete()
        messages.success(request, "Fondeo eliminado correctamente.")
        return redirect("lista_fondeos")