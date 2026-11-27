"""GESAC Campus -- Otros ingresos: ingresos que no vienen de Academic+ y se
registran a mano (donativos, renta de espacios, intereses, eventos...). Siempre
son cobros al momento: el efectivo suma al fondo de caja chica y lo depositado
va a su cuenta bancaria. Alimentan el estado de resultados y la conciliacion."""

import datetime
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from conciliaciones.utils import validar_periodo_abierto
from empresas.models import CuentaBancaria
from facturacion.models import TipoOtroIngreso

from . import ingresos_utils as iu
from .decoradores import requiere_membresia_activa_escuela
from .models import IngresoEscuela
from .views_ingresos import _empresa_escuela

AREAS = [('liceo', 'Liceo'), ('ipc', 'IPC'), ('cafeteria', 'Cafetería')]
AREA_A_FUENTE = {'liceo': 'colegiaturas', 'ipc': 'ipc', 'cafeteria': 'cafeteria'}
FUENTE_A_AREA = {v: k for k, v in AREA_A_FUENTE.items()}
NOMBRE_AREA = dict(AREAS)
FORMAS = [(f, f) for f in ('Efectivo', 'Transferencia', 'Cheque', 'Depósito', 'Tarjeta')]


class OtroIngresoForm(forms.Form):
    fecha = forms.DateField(label='Fecha del cobro', widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    tipo = forms.ModelChoiceField(queryset=TipoOtroIngreso.objects.none(), label='Tipo de ingreso',
                                  widget=forms.Select(attrs={'class': 'form-select'}))
    area = forms.ChoiceField(choices=AREAS, label='Área', widget=forms.Select(attrs={'class': 'form-select'}))
    monto = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'), label='Monto',
                               widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}))
    forma_pago = forms.ChoiceField(choices=FORMAS, label='Forma de pago', widget=forms.Select(attrs={'class': 'form-select'}))
    cuenta_bancaria = forms.ModelChoiceField(queryset=CuentaBancaria.objects.none(), required=False, label='Cuenta bancaria',
                                             widget=forms.Select(attrs={'class': 'form-select'}))
    pagador = forms.CharField(max_length=255, required=False, label='Quién pagó (opcional)',
                              widget=forms.TextInput(attrs={'class': 'form-control'}))
    comentario = forms.CharField(max_length=255, required=False, label='Comentario (opcional)',
                                 widget=forms.TextInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, empresa, fecha_original=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fecha_original = fecha_original  # al editar, no se revalida una fecha que no cambio
        self.fields['tipo'].queryset = TipoOtroIngreso.objects.filter(empresa=empresa).order_by('nombre')
        self.fields['cuenta_bancaria'].queryset = CuentaBancaria.objects.filter(empresa=empresa)
        self.fields['cuenta_bancaria'].empty_label = '— Selecciona —'

    def clean(self):
        datos = super().clean()
        if datos.get('forma_pago') and datos['forma_pago'] != 'Efectivo' and not datos.get('cuenta_bancaria'):
            self.add_error('cuenta_bancaria', 'Elige la cuenta donde se depositó.')
        # Candado de fechas del sistema: no anios anteriores al actual, no fechas futuras,
        # no periodos cerrados (misma regla que condominios y caja chica).
        fecha = datos.get('fecha')
        if fecha and fecha != self.fecha_original:
            ok, error = validar_periodo_abierto(datos.get('cuenta_bancaria'), fecha)
            if not ok:
                self.add_error('fecha', error)
        return datos


def _numero_fondo(empresa_fuente, fecha, tipo_nombre):
    categoria = iu.categoria_fondo(tipo_nombre) if empresa_fuente == 'ipc' else None
    return iu.numero_fondeo_efectivo(empresa_fuente, fecha.year, fecha.month, categoria), categoria


def _guardar(empresa, usuario, datos, ingreso=None):
    """Crea o actualiza el ingreso y mantiene el fondo de caja chica al dia.
    Debe llamarse dentro de transaction.atomic(). ValueError si la caja ya gasto."""
    tipo = datos['tipo']
    fuente = AREA_A_FUENTE[datos['area']]
    efectivo = iu.es_efectivo(datos['forma_pago'])
    monto = datos['monto']
    fecha = datos['fecha']

    numero_nuevo = categoria = None
    if efectivo:
        numero_nuevo, categoria = _numero_fondo(fuente, fecha, tipo.nombre)

    fondeo = None
    if ingreso is not None:
        numero_viejo = ingreso.fondeo.numero_cheque if (ingreso.es_efectivo and ingreso.fondeo_id) else None
        mismo_fondo = efectivo and ingreso.es_efectivo and ingreso.fondeo_id and numero_viejo == numero_nuevo
        if mismo_fondo:
            # Mismo fondo: solo se ajusta la diferencia (no se borra ni se recrea).
            fondeo = ingreso.fondeo
            diferencia = monto - ingreso.monto
            if diferencia > 0:
                iu.sumar_a_fondeo(fondeo, diferencia, fecha)
            elif diferencia < 0:
                iu.restar_de_fondeo(fondeo, -diferencia)
        elif ingreso.es_efectivo and ingreso.fondeo_id:
            iu.restar_de_fondeo(ingreso.fondeo, ingreso.monto)  # cambia de fondo o deja de ser efectivo
    else:
        ingreso = IngresoEscuela(empresa=empresa, origen='manual', importado_por=usuario, categoria='otro')

    if efectivo and fondeo is None:
        fondeo = iu.fondeo_efectivo_para(empresa, fuente, fecha, categoria)
        iu.sumar_a_fondeo(fondeo, monto, fecha)

    ingreso.fecha = fecha
    ingreso.tipo_otro_ingreso = tipo
    ingreso.rubro = tipo.nombre[:60]
    ingreso.concepto = (datos.get('comentario') or tipo.nombre)[:255]
    ingreso.pagador = datos.get('pagador') or ''
    ingreso.monto = monto
    ingreso.forma_pago = iu.etiqueta_forma_pago(datos['forma_pago'])
    ingreso.fuente = fuente
    ingreso.es_efectivo = efectivo
    ingreso.cuenta_bancaria = None if efectivo else datos['cuenta_bancaria']
    ingreso.fondeo = fondeo
    ingreso.save()
    return ingreso


@login_required
@requiere_membresia_activa_escuela
def otros_ingresos_lista(request):
    empresa = _empresa_escuela(request)
    if not empresa:
        return redirect('dashboard_inicio')

    hoy = datetime.date.today()  # noqa: DTZ011
    try:
        desde = datetime.date.fromisoformat(request.GET.get('desde', ''))
    except ValueError:
        desde = hoy.replace(day=1)
    try:
        hasta = datetime.date.fromisoformat(request.GET.get('hasta', ''))
    except ValueError:
        hasta = hoy
    tipo_id = request.GET.get('tipo', '')
    area = request.GET.get('area', '')

    qs = (
        IngresoEscuela.objects.filter(empresa=empresa, origen='manual', fecha__gte=desde, fecha__lte=hasta)
        .select_related('tipo_otro_ingreso', 'cuenta_bancaria', 'fondeo')
        .order_by('-fecha', '-id')
    )
    if tipo_id.isdigit():
        qs = qs.filter(tipo_otro_ingreso_id=int(tipo_id))
    if area in AREA_A_FUENTE:
        qs = qs.filter(fuente=AREA_A_FUENTE[area])
    filas = list(qs)
    for f in filas:
        f.area_nombre = NOMBRE_AREA.get(FUENTE_A_AREA.get(f.fuente, ''), '')
    return render(request, 'escuelas/otros_ingresos_lista.html', {
        'filas': filas,
        'total': qs.aggregate(t=Sum('monto'))['t'] or Decimal('0'),
        'desde': desde.isoformat(), 'hasta': hasta.isoformat(),
        'tipo_sel': tipo_id, 'area_sel': area, 'areas': AREAS,
        'tipos': TipoOtroIngreso.objects.filter(empresa=empresa).order_by('nombre'),
    })


@login_required
@requiere_membresia_activa_escuela
def otro_ingreso_form(request, pk=None):
    empresa = _empresa_escuela(request)
    if not empresa:
        return redirect('dashboard_inicio')
    ingreso = get_object_or_404(IngresoEscuela, pk=pk, empresa=empresa, origen='manual') if pk else None

    if request.method == 'POST':
        form = OtroIngresoForm(request.POST, empresa=empresa, fecha_original=ingreso.fecha if ingreso else None)
        if form.is_valid():
            try:
                with transaction.atomic():
                    _guardar(empresa, request.user, form.cleaned_data, ingreso)
            except ValueError as e:
                form.add_error(None, str(e))
            else:
                messages.success(request, 'Ingreso actualizado.' if ingreso else 'Ingreso registrado.')
                return redirect('escuela_otros_ingresos_lista')
    elif ingreso:
        form = OtroIngresoForm(empresa=empresa, initial={
            'fecha': ingreso.fecha, 'tipo': ingreso.tipo_otro_ingreso_id,
            'area': FUENTE_A_AREA.get(ingreso.fuente, 'ipc'), 'monto': ingreso.monto,
            'forma_pago': 'Efectivo' if ingreso.es_efectivo else (
                ingreso.forma_pago if ingreso.forma_pago in dict(FORMAS) else 'Transferencia'),
            'cuenta_bancaria': ingreso.cuenta_bancaria_id, 'pagador': ingreso.pagador,
            'comentario': '' if ingreso.concepto == ingreso.rubro else ingreso.concepto,
        })
    else:
        form = OtroIngresoForm(empresa=empresa, initial={'fecha': datetime.date.today()})  # noqa: DTZ011
    return render(request, 'escuelas/otros_ingresos_form.html', {'form': form, 'ingreso': ingreso})


@login_required
@requiere_membresia_activa_escuela
@require_POST
def otro_ingreso_eliminar(request, pk):
    empresa = _empresa_escuela(request)
    if not empresa:
        return redirect('dashboard_inicio')
    ingreso = get_object_or_404(IngresoEscuela, pk=pk, empresa=empresa, origen='manual')
    try:
        with transaction.atomic():
            if ingreso.es_efectivo and ingreso.fondeo_id:
                iu.restar_de_fondeo(ingreso.fondeo, ingreso.monto)
            ingreso.delete()
        messages.success(request, 'Ingreso eliminado.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('escuela_otros_ingresos_lista')


@login_required
@requiere_membresia_activa_escuela
@require_POST
def tipo_otro_ingreso_crear(request):
    """Crea un tipo de ingreso (JSON) desde la pantalla de captura."""
    empresa = _empresa_escuela(request)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'Sin empresa de escuela.'}, status=400)
    nombre = ' '.join((request.POST.get('nombre') or '').split())
    if not nombre or len(nombre) > 100:
        return JsonResponse({'success': False, 'error': 'Escribe un nombre (máximo 100 caracteres).'}, status=400)
    existente = TipoOtroIngreso.objects.filter(empresa=empresa, nombre__iexact=nombre).first()
    if existente:
        return JsonResponse({'success': True, 'id': existente.id, 'nombre': existente.nombre, 'existia': True})
    tipo = TipoOtroIngreso.objects.create(empresa=empresa, nombre=nombre)
    return JsonResponse({'success': True, 'id': tipo.id, 'nombre': tipo.nombre})
