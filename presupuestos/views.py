
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from gastos.models import Gasto
from .models import Presupuesto
from .forms import PresupuestoForm
from django.utils.timezone import now
from django.db.models import Sum
from empresas.models import Empresa


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
        form = PresupuestoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('presupuesto_lista')
    else:
        form = PresupuestoForm()
    return render(request, 'presupuestos/form.html', {'form': form})

@login_required
def presupuesto_editar(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    if request.method == 'POST':
        form = PresupuestoForm(request.POST, instance=presupuesto)
        if form.is_valid():
            form.save()
            return redirect('presupuesto_lista')
    else:
        form = PresupuestoForm(instance=presupuesto)
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