
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
import openpyxl
#import unidecode
from clientes.models import Cliente
from empresas.models import Empresa
import locales
from .models import LocalComercial
from .forms import LocalCargaMasivaForm, LocalComercialForm
from django.contrib.admin.views.decorators import staff_member_required
from unidecode import unidecode


# Create your views here.

@login_required
def lista_locales(request):
    user = request.user
    if user.is_superuser:
        #locales = LocalComercial.objects.all()
        locales = LocalComercial.objects.filter(activo=True)
    else:
        #empresa = getattr(request.user.perfilusuario, 'empresa', None)
        empresa = user.perfilusuario.empresa
        locales = LocalComercial.objects.filter(empresa=empresa, activo=True)
    return render(request, 'locales/lista_locales.html', {'locales': locales})

@login_required
def crear_local(request):
    user = request.user
    perfil = getattr(user, 'perfilusuario', None)
    
    if request.method == 'POST':
        #form = LocalComercialForm(request.POST, user=user)
        form = LocalComercialForm(request.POST or None, user=request.user)

        if form.is_valid():
            local = form.save(commit=False)
            # Si no es superusuario, asignamos su empresa
            if not user.is_superuser:
                #if perfil and perfil.empresa:
                local.empresa = perfil.empresa
                
            #local.save()
                #else:
                    #return render(request, 'error.html', {'mensaje': 'No tienes empresa asignada.'})
                local.save()
                return redirect('lista_locales')
        
    else:
        
        form = LocalComercialForm(user=user)
        # Si no es superusuario, asignamos la empresa inicial al form
        if not user.is_superuser and perfil and perfil.empresa:
            form.fields['empresa'].initial = perfil.empresa

    return render(request, 'locales/crear_local.html', {'form': form})

@login_required
def editar_local(request, pk):
    user = request.user
    local= get_object_or_404(LocalComercial, pk=pk)
    #perfil = getattr(user, 'perfilusuario', None)
    # Filtrar el local según permisos
    if not user.is_superuser and local.empresa != user.perfilusuario.empresa:
        return redirect('lista_locales')
    #if user.is_superuser:
        #local = get_object_or_404(LocalComercial, pk=pk)
    #else:
     #   local = get_object_or_404(LocalComercial, pk=pk, empresa=perfil.empresa)

    if request.method == 'POST':
        form = LocalComercialForm(request.POST, instance=local, user=user)
        if form.is_valid():
            local = form.save(commit=False)
            form.save()
            #if not user.is_superuser:
             #   local.empresa = perfil.empresa  # reforzar seguridad
            #local.save()
            return redirect('lista_locales')
    else:
        form = LocalComercialForm(instance=local, user=user)

    return render(request, 'locales/editar_local.html', {'form': form, 'local': local})

@login_required
def eliminar_local(request, pk):
    user = request.user
    local= get_object_or_404(LocalComercial, pk=pk)
    if not user.is_superuser and local.empresa != user.perfilusuario.empresa:
        return redirect('lista_locales')
    #perfil = getattr(user, 'perfilusuario', None)

    #if user.is_superuser:
     #   local = get_object_or_404(LocalComercial, pk=pk)
    #else:
     #   local = get_object_or_404(LocalComercial, pk=pk, empresa=perfil.empresa)

    if request.method == 'POST':
        #local.delete()
        local.activo = False
        local.save()
        return redirect('lista_locales')

    return render(request, 'locales/eliminar_local.html', {'local': local})

#@staff_member_required
@user_passes_test(lambda u: u.is_staff)
def locales_inactivos(request):
    locales = LocalComercial.objects.filter(activo=False)
    return render(request, 'locales/locales_inactivos.html', {'locales': locales})

#@staff_member_required
@user_passes_test(lambda u: u.is_staff)
def reactivar_local(request, pk):
    local = get_object_or_404(LocalComercial, pk=pk, activo=False)

    if request.method == 'POST':
        local.activo = True
        local.save()
        return redirect('locales_inactivos')

    return render(request, 'locales/reactivar_confirmacion.html', {'local': local})

@login_required
def incrementar_cuotas_locales(request):
    if request.method == 'POST':
        porcentaje = request.POST.get('porcentaje')
        try:
            porcentaje = Decimal(porcentaje)
            empresa = None
            if not request.user.is_superuser and hasattr(request.user, 'perfilusuario'):
                empresa = request.user.perfilusuario.empresa
                locales = LocalComercial.objects.filter(empresa=empresa, activo=True)
            else:
                locales = LocalComercial.objects.filter(activo=True)

            for local in locales:
                cuota_anterior = local.cuota
                incremento = cuota_anterior * (porcentaje / Decimal('100'))
                local.cuota += incremento
                local.save()

            messages.success(request, f'Se incrementaron las cuotas en un {porcentaje}% para todos los locales activos.')
            return redirect('incrementar_c_locales')
        except:
            messages.error(request, 'Porcentaje inválido.')
    
    return render(request, 'locales/incrementar_c_locales.html')

def buscar_por_id_o_nombre(modelo, valor, campo='nombre'):
    if not valor:
        return None
    val = str(valor).strip().replace(',', '')
    try:
        return modelo.objects.get(pk=int(val))
    except (ValueError, modelo.DoesNotExist):
        todos = modelo.objects.all()
        candidatos = [
            obj for obj in todos
            if unidecode(val).lower() in unidecode(str(getattr(obj, campo))).lower()
        ]
        if len(candidatos) == 1:
            return candidatos[0]
        elif len(candidatos) > 1:
            conflicto = "; ".join([f"ID={obj.pk}, {campo}='{getattr(obj, campo)}'" for obj in candidatos])
            raise Exception(f"Conflicto: '{valor}' coincide con varios registros en {modelo.__name__}: {conflicto}")
        raise Exception(f"No se encontró '{valor}' en {modelo.__name__}")

@staff_member_required
def carga_masiva_locales(request):
    if request.method == 'POST':
        form = LocalCargaMasivaForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            wb = openpyxl.load_workbook(archivo)
            ws = wb.active
            errores = []
            COLUMNAS_ESPERADAS = 9  # Cambia según tus columnas
            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if row is None:
                    continue
                if len(row) != COLUMNAS_ESPERADAS:
                    errores.append(f"Fila {i}: número de columnas incorrecto ({len(row)} en vez de {COLUMNAS_ESPERADAS})")
                    continue
                empresa_val, propietraio_val, cliente_val, numero, ubicacion, superficie_m2, cuota, status, observaciones = row
                try:
                    empresa = buscar_por_id_o_nombre(Empresa, empresa_val)
                    propietario = buscar_por_id_o_nombre(Cliente, propietraio_val) if propietraio_val else None
                    cliente = buscar_por_id_o_nombre(Cliente, cliente_val) if cliente_val else None
                    # Puedes ajustar el campo status si manejas valores específicos en tu modelo
                    LocalComercial.objects.create(
                        empresa=empresa,
                        propietario=propietario.nombre if propietario else "",
                        cliente=cliente.nombre if cliente else "",
                        numero=str(numero),
                        ubicacion=ubicacion or "",
                        superficie_m2=Decimal(superficie_m2) if superficie_m2 else None,
                        cuota=Decimal(cuota),
                        status=status or "ocupado",
                        observaciones=observaciones or ""
                    )
                except Exception as e:
                    errores.append(f"Fila {i}: {e}")

            if errores:
                messages.error(request, "Algunos locales no se cargaron:<br>" + "<br>".join(errores))
            else:
                messages.success(request, "¡Locales cargados exitosamente!")
            return redirect('carga_masiva_locales')
    else:
        form = LocalCargaMasivaForm()
    return render(request, 'locales/carga_masiva_locales.html', {'form': form})

@staff_member_required
def plantilla_locales_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Plantilla Locales"
    ws.append([
        'empresa','propietario', 'cliente', 'numero', 'ubicacion', 'superficie_m2', 'cuota', 'status', 'observaciones'
    ])
    ws.append([
        'Torre Reforma','Tiendas Soriana SA de CV', 'Juan Pérez', '101', 'Planta Baja', '120.5', '3000.00', 'ocupado', 'Local nuevo'
    ])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_locales.xlsx'
    wb.save(response)
    return response
