
# Create your views here.
from pyexpat.errors import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from gastos.models import Gasto, GrupoGasto, TipoGasto, SubgrupoGasto
from .models import Presupuesto
from .forms import PresupuestoForm
from django.utils.timezone import now
from django.db.models import Sum
from empresas.models import Empresa
from calendar import month_name
from collections import defaultdict
from decimal import Decimal




"""@login_required
def presupuesto_lista(request):
    if request.user.is_superuser:
        presupuestos = Presupuesto.objects.all()
    else:
        empresa = request.user.perfilusuario.empresa
        presupuestos = Presupuesto.objects.filter(empresa=empresa)
    return render(request, 'presupuestos/lista.html', {'presupuestos': presupuestos})"""

@login_required
def presupuesto_nuevo(request):
    if request.method == 'POST':
        form = PresupuestoForm(request.POST,user=request.user)
        if form.is_valid():
            presupuesto = form.save(commit=False)
            # Solo para usuarios normales, asigna empresa directamente
            if not request.user.is_superuser:
                presupuesto.empresa = request.user.perfilusuario.empresa
            presupuesto.save()
            form.save()
            return redirect('presupuesto_lista')
    else:
        form = PresupuestoForm(user=request.user)
    return render(request, 'presupuestos/form.html', {'form': form})

@login_required
def presupuesto_editar(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    if request.method == 'POST':
        form = PresupuestoForm(request.POST, instance=presupuesto,user=request.user)
        if form.is_valid():
            presupuesto = form.save(commit=False)
            if not request.user.is_superuser:
                presupuesto.empresa = request.user.perfilusuario.empresa
            presupuesto.save()
            form.save()
            return redirect('presupuesto_lista')
    else:
        form = PresupuestoForm(instance=presupuesto,user=request.user)
    return render(request, 'presupuestos/form.html', {'form': form, 'presupuesto': presupuesto})

@login_required
def presupuesto_eliminar(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    if request.method == 'POST':
        presupuesto.delete()
        return redirect('presupuesto_lista')
    return render(request, 'presupuestos/confirmar_eliminar.html', {'presupuesto': presupuesto})

@login_required
def dashboard_presupuestal(request):
    es_super = request.user.is_superuser
    anio_actual = now().year
    anio = int(request.GET.get('anio', anio_actual))
    mes = int(request.GET.get('mes', 0))  # 0 = todo el año

    # Filtro empresa
    if es_super:
        empresas = Empresa.objects.all()
        empresa_id = request.GET.get('empresa')
        if empresa_id:
            try:
                empresa = Empresa.objects.get(pk=int(empresa_id))
            except (Empresa.DoesNotExist, ValueError):
                empresa = empresas.first() if empresas else None
        else:
            empresa = empresas.first() if empresas else None
    else:
        empresa = request.user.perfilusuario.empresa
        empresas = Empresa.objects.filter(pk=empresa.id)

    if not empresa:
        # Si no hay empresa, devuelve página vacía o mensaje amigable
        meses_esp = [
                "01 Ene", "02 Feb", "03 Mar", "04 Abr", "05 May", "06 Jun",
                "07 Jul", "08 Ago", "09 Sep", "10 Oct", "11 Nov", "12 Dic"
        ]
        contexto = {
            'empresas': empresas,
            'empresa_id': None,
            'anio': anio,
            'mes': mes,
            'labels': [],
            'datos_presupuesto': [],
            'datos_gastado': [],
            'total_presupuestado': 0,
            'total_gastado': 0,
            'es_super': es_super,
            'meses_esp': meses_esp,
        }
        return render(request, 'presupuestos/dashboard.html', contexto)

    # Presupuestos del año y empresa
    pres_qs = Presupuesto.objects.filter(empresa=empresa, anio=anio)
    if mes:
        pres_qs = pres_qs.filter(mes=mes)

    total_presupuestado = pres_qs.aggregate(total=Sum('monto'))['total'] or 0

    # Gastos reales
    gastos_qs = Gasto.objects.filter(empresa=empresa, fecha__year=anio)
    if mes:
        gastos_qs = gastos_qs.filter(fecha__month=mes)
    total_gastado = gastos_qs.aggregate(total=Sum('monto'))['total'] or 0

    # Datos para gráfico (línea presupuestos vs. gastos)
    meses = list(range(1, 13))
    meses_esp = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    labels = meses_esp
    datos_presupuesto = []
    datos_gastado = []

    for m in meses:
        pres_mes = pres_qs.filter(mes=m).aggregate(total=Sum('monto'))['total'] or 0
        gasto_mes = gastos_qs.filter(fecha__month=m).aggregate(total=Sum('monto'))['total'] or 0
        datos_presupuesto.append(float(pres_mes))
        datos_gastado.append(float(gasto_mes))

    contexto = {
        'empresas': empresas,
        'empresa_id': empresa.id,
        'anio': anio,
        'mes': mes,
        'labels': labels,
        'datos_presupuesto': datos_presupuesto,
        'datos_gastado': datos_gastado,
        'total_presupuestado': total_presupuestado,
        'total_gastado': total_gastado,
        'es_super': es_super,
    }
    return render(request, 'presupuestos/dashboard.html', contexto)

# Matriz de presupuestos por tipo de gasto y mes
@login_required
def matriz_presupuesto(request):
    anio = int(request.GET.get('anio', now().year))
    now_year = now().year
    anios = list(range(now_year, 2021, -1))

    if request.user.is_superuser:
        empresas = Empresa.objects.all()
        empresa_id = request.GET.get('empresa')
        empresa = Empresa.objects.get(pk=empresa_id) if empresa_id else empresas.first()
    else:
        empresa = request.user.perfilusuario.empresa
        empresas = None

    meses = list(range(1, 13))
    meses_nombres = [month_name[m].capitalize() for m in meses]

    # Construye la estructura de grupos -> subgrupos -> tipos (para usar en el template)
    tipos = TipoGasto.objects.select_related('subgrupo', 'subgrupo__grupo').order_by(
        'subgrupo__grupo__nombre', 'subgrupo__nombre', 'nombre'
    )
    grupos_lista = []
    # {grupo: {subgrupo: [tipos]}}
    grupos_dict = defaultdict(lambda: defaultdict(list))
    for tipo in tipos:
        grupos_dict[tipo.subgrupo.grupo][tipo.subgrupo].append(tipo)
    for grupo, subgrupos in grupos_dict.items():
        subgrupos_lista = []
        for subgrupo, tipos_ in subgrupos.items():
            tipos_lista = []
            for tipo in tipos_:
                tipos_lista.append({'id': tipo.id, 'nombre': str(tipo), 'tipo_obj': tipo})
            subgrupos_lista.append({'id': subgrupo.id, 'nombre': str(subgrupo), 'tipos': tipos_lista, 'subgrupo_obj': subgrupo})
        grupos_lista.append({'id': grupo.id, 'nombre': str(grupo), 'subgrupos': subgrupos_lista, 'grupo_obj': grupo})

    # Consulta presupuestos existentes
    presupuestos = Presupuesto.objects.filter(empresa=empresa, anio=anio)
    presup_dict = {(p.tipo_gasto_id, p.mes): p for p in presupuestos}

    # Totales generales por mes
    totales_mes = []
    for mes in meses:
        total_mes = 0
        for tipo in tipos:
            p = presup_dict.get((tipo.id, mes))
            total_mes += p.monto if p else 0
        totales_mes.append(total_mes)

    # Subtotales
    subtotales_grupo = {}
    subtotales_subgrupo = {}
    subtotales_tipo = {}
    for grupo, subgrupos in grupos_dict.items():
        subtotal_grupo = [0] * 12
        for subgrupo, tipos_gasto in subgrupos.items():
            subtotal_subgrupo = [0] * 12
            for tipo in tipos_gasto:
                subtotal_tipo = []
                for i, mes in enumerate(meses):
                    p = presup_dict.get((tipo.id, mes))
                    valor = p.monto if p else 0
                    subtotal_tipo.append(valor)
                    subtotal_subgrupo[i] += valor
                    subtotal_grupo[i] += valor
                subtotales_tipo[tipo.id] = subtotal_tipo
            subtotales_subgrupo[subgrupo.id] = subtotal_subgrupo
        subtotales_grupo[grupo.id] = subtotal_grupo

    # Guardado de presupuestos por POST
    if request.method == "POST":
        for tipo in tipos:
            for mes in meses:
                key = f"presupuesto_{tipo.id}_{mes}"
                monto = request.POST.get(key)
                if monto is not None:
                    monto = float(monto or 0)
                    grupo = tipo.subgrupo.grupo
                    subgrupo = tipo.subgrupo
                    obj, created = Presupuesto.objects.get_or_create(
                        empresa=empresa, tipo_gasto=tipo, anio=anio, mes=mes,
                        defaults={"monto": monto, "grupo": grupo, "subgrupo": subgrupo}
                    )
                    if not created and obj.monto != monto:
                        obj.monto = monto
                        obj.save()
        messages.success(request, "Presupuestos actualizados")
        return redirect(request.path + f"?anio={anio}" + (f"&empresa={empresa.id}" if empresa else ""))

    return render(request, "presupuestos/matriz.html", {
        "grupos_lista": grupos_lista,
        "meses": meses,
        "meses_nombres": meses_nombres,
        "presup_dict": presup_dict,
        "anio": anio,
        "anios": anios,
        "empresas": empresas,
        "empresa": empresa,
        "totales_mes": totales_mes,
        "subtotales_grupo": subtotales_grupo,
        "subtotales_subgrupo": subtotales_subgrupo,
        "subtotales_tipo": subtotales_tipo,
        "is_super": request.user.is_superuser,
    })

"""@login_required
def matriz_simple_presupuesto(request):
    anio = int(request.GET.get('anio', now().year))
    meses = int(request.GET.get('meses', 12)) 
     # Por defecto, 12 meses

    if request.user.is_superuser:
        empresas = Empresa.objects.all()
        empresa_id = request.GET.get('empresa')
        empresa = Empresa.objects.get(pk=empresa_id) if empresa_id else empresas.first()
    else:
        empresa = request.user.perfilusuario.empresa
        empresas = None

    meses = list(range(1, 13))
    #meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    meses_nombres = [month_name[m].capitalize() for m in meses]

    tipos = TipoGasto.objects.select_related('subgrupo', 'subgrupo__grupo').order_by('subgrupo__grupo__nombre', 'subgrupo__nombre', 'nombre')
    presupuestos = Presupuesto.objects.filter(empresa=empresa, anio=anio, mes__in=meses)
    presup_dict = {(p.tipo_gasto_id, p.mes): p for p in presupuestos}
    for k in presup_dict:
        print("Llave dict:", k, "Tipo:", type(k))

    # Calcula el total por mes (diccionario)
    totales_mes = {mes: Decimal('0.00') for mes in meses}
    for mes in meses:
        for tipo in tipos:
            pres = presup_dict.get((tipo.id, mes))
            if pres:
                totales_mes[mes] += pres.monto or Decimal('0.00')    

    if request.method == "POST":
        for tipo in tipos:
            for mes in meses:
                key = f"presupuesto_{tipo.id}_{mes}"
                monto = request.POST.get(key)
                if monto is not None:
                    try:
                        monto_val = Decimal(monto) if monto else Decimal('0.00')
                        obj = presup_dict.get((tipo.id, mes))
                        # Solo guarda si el monto es > 0 o si ya existe el presupuesto (permitir actualizar a cero si lo deseas)
                        if monto_val > 0 or obj:
                            if obj:
                                # Actualiza solo si cambia el monto
                                if obj.monto != monto_val:
                                    obj.monto = monto_val
                                    obj.grupo = tipo.subgrupo.grupo
                                    obj.subgrupo = tipo.subgrupo
                                    obj.save()
                            else:
                                Presupuesto.objects.create(
                                    empresa=empresa,
                                    tipo_gasto=tipo,
                                    anio=anio,
                                    mes=mes,
                                    monto=monto_val,
                                    grupo=tipo.subgrupo.grupo,
                                    subgrupo=tipo.subgrupo,
                                )
                    except Exception as e:
                        print(f"[ERROR] Al guardar presupuesto: {e}")
        messages.success(request, "Presupuestos actualizados")
        return redirect(request.path + f"?anio={anio}" + (f"&empresa={empresa.id}" if empresa else ""))
    
    print("PRESUP_DICT:", presup_dict)

    return render(request, "presupuestos/matriz_simple.html", {
        "tipos": tipos,
        "meses": meses,
        "meses_nombres": meses_nombres,
        "totales_mes": totales_mes, 
        "presup_dict": presup_dict,
        "anio": anio,
        "empresas": empresas,
        "empresa": empresa,
        "is_super": request.user.is_superuser,
    })"""