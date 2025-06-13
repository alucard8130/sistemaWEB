
# Create your views here.
from pyexpat.errors import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from gastos.models import Gasto, GrupoGasto, TipoGasto
from .models import Presupuesto
from .forms import PresupuestoForm
from django.utils.timezone import now
from django.db.models import Sum
from empresas.models import Empresa
from calendar import month_name
from collections import defaultdict
from decimal import Decimal



@login_required
def presupuesto_lista(request):
    if request.user.is_superuser:
        presupuestos = Presupuesto.objects.all()
    else:
        empresa = request.user.perfilusuario.empresa
        presupuestos = Presupuesto.objects.filter(empresa=empresa)
    return render(request, 'presupuestos/lista.html', {'presupuestos': presupuestos})

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
    if request.user.is_superuser:
        empresas = Empresa.objects.all()
        empresa_id = request.GET.get('empresa')
        empresa = Empresa.objects.get(pk=empresa_id) if empresa_id else empresas.first()
    else:
        empresa = request.user.perfilusuario.empresa
        empresas = None

    meses = list(range(1, 13))
    meses_nombres = [month_name[m].capitalize() for m in meses]

    # Prepara jerarquía y rowspans
    tipos = TipoGasto.objects.select_related('subgrupo', 'subgrupo__grupo').order_by(
        'subgrupo__grupo__nombre', 'subgrupo__nombre', 'nombre')
    print("TIPOS TOTAL:", tipos.count())
    if tipos.count() == 0:
        print("¡No hay tipos de gasto en la BD!")       
    


   

    presupuestos = Presupuesto.objects.filter(empresa=empresa, anio=anio)
    presup_dict = {(p.tipo_gasto_id, p.mes): p for p in presupuestos}

    # -------------- JERARQUÍA -------------
    jerarquia = defaultdict(lambda: defaultdict(list))
    subgrupo_rowspan = defaultdict(int)
    grupo_rowspan = defaultdict(int)

    print(f"Total tipos: {tipos.count()}")
    for tipo in tipos:
        print("Tipo:", tipo.nombre, "| Subgrupo:", tipo.subgrupo, "| Grupo:", tipo.subgrupo.grupo)


    for tipo in tipos:
        grupo = tipo.subgrupo.grupo
        subgrupo = tipo.subgrupo
        jerarquia[grupo][subgrupo].append(tipo)
        subgrupo_rowspan[subgrupo] += 1
        grupo_rowspan[grupo] += 1
    
    # Al final, conviértelo:
    jerarquia = dict(jerarquia)
    for grupo, subgrupos in jerarquia.items():
        jerarquia[grupo] = dict(subgrupos)


    print('Grupos:', len(jerarquia))
    for grupo, subgrupos in jerarquia.items():
        print('  Subgrupos:', len(subgrupos))
    for subgrupo, tipos in subgrupos.items():
        print('    Tipos:', len(tipos))
    

    # -------- SUBTOTALES POR SUBGRUPO Y GRUPO ----------
    #subgrupo_subtotales = defaultdict(lambda: defaultdict(float))
    #grupo_subtotales = defaultdict(lambda: defaultdict(float))
    subgrupo_subtotales = defaultdict(lambda: defaultdict(lambda: Decimal('0')))
    grupo_subtotales = defaultdict(lambda: defaultdict(lambda: Decimal('0')))
    for grupo, subgrupos in jerarquia.items():
        for subgrupo, tiposg in subgrupos.items():
            for mes in meses:
                subtotal = sum(
                    presup_dict.get((tipo.id, mes), None).monto 
                    if presup_dict.get((tipo.id, mes), None) else Decimal('0') 
                    for tipo in tiposg
                )
                subgrupo_subtotales[subgrupo][mes] = subtotal
                grupo_subtotales[grupo][mes] += subtotal

    # ------------ GUARDADO DE PRESUPUESTO ---------------
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
                        empresa=empresa,
                        tipo_gasto=tipo,
                        anio=anio,
                        mes=mes,
                        defaults={
                            "monto": monto,
                            "grupo": grupo,
                            "subgrupo": subgrupo,
                        }
                    )
                    # Actualiza si ya existe y cambia el monto
                    if not created and (obj.monto != monto or obj.grupo != grupo or obj.subgrupo != subgrupo):
                        obj.monto = monto
                        obj.grupo = grupo
                        obj.subgrupo = subgrupo
                        obj.save()
        messages.success(request, "Presupuestos actualizados")
        return redirect(request.path + f"?anio={anio}" + (f"&empresa={empresa.id}" if empresa else ""))
        
    print('jerarquia:', jerarquia)
    print('presup_dict:', presup_dict)
    return render(request, "presupuestos/matriz.html", {
        "tipos": tipos,
        "meses": meses,
        "meses_nombres": meses_nombres,
        "jerarquia": jerarquia,
        "grupo_rowspan": grupo_rowspan,
        "subgrupo_rowspan": subgrupo_rowspan,
        "subgrupo_subtotales": subgrupo_subtotales,
        "grupo_subtotales": grupo_subtotales,
        "presup_dict": presup_dict,
        "anio": anio,
        "empresas": empresas,
        "empresa": empresa,
        "is_super": request.user.is_superuser,
        
    })
