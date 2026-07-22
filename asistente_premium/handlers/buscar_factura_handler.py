"""Handler para buscar el estatus de una factura"""
import re
from datetime import date
from typing import Dict, List, Any, Optional, Tuple
from django.db.models import Q
from .base_handler import BaseHandler
from facturacion.models import Factura

MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12,
}


class BuscarFacturaHandler(BaseHandler):
    """
    Handler de CONSULTA (no de alta): busca una factura por local, área común
    o cliente, opcionalmente filtrando por mes, y reporta su estatus. Si está
    pendiente, ofrece un botón para asignar un pago; si ya está cobrada, no
    hace nada más.
    """

    intencion_principal = 'buscar_factura'
    intencion_aliases = [
        'buscar_factura', 'consultar_factura', 'estatus_factura', 'checar_factura',
        'ver_factura', 'factura_pendiente','abrir_factura','busca_factura','consulta_factura',
    ]
    descripcion = "Buscar factura cuotas y asignar cobro"
    emoji = "🔎"

    campos_requeridos = ['criterio']
    campos_opcionales = ['mes']

    def obtener_campos(self) -> List[Dict]:
        return [
            {
                'nombre': 'criterio',
                'label': (
                    '¿De qué local, área común o cliente buscas la factura? '
                    '(ej. "local 12", "área común AC-21", "cliente Juan Pérez")'
                ),
                'tipo': 'text',
                'requerido': True,
            },
            {
                'nombre': 'mes',
                'label': '¿De qué mes? (ej. "julio" o "julio 2026", opcional — si no me dices, reviso la más reciente)',
                'tipo': 'text',
                'requerido': False,
            },
        ]

    def validar(self) -> bool:
        self.limpiar_errores()

        if not self.datos.get('criterio'):
            self.agregar_error('criterio', 'Necesito saber de qué local, área común o cliente es la factura')
            return False

        # El mes es opcional, pero si viene debe poder interpretarse
        if self.datos.get('mes'):
            anio, mes = self._parsear_mes(self.datos['mes'])
            if mes is None:
                self.agregar_error('mes', 'No entendí el mes, intenta con algo como "julio" o "julio 2026"')
                return False

        return True

    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        self.establecer_datos(datos)

        if not self.validar():
            return {
                'exito': False,
                'errores': self.errores,
                'mensaje': '❌ ' + ' / '.join(self.errores.values())
            }

        tipo, valor = self._interpretar_criterio(self.datos['criterio'])

        qs = Factura.objects.filter(empresa=self.empresa, activo=True)

        if tipo == 'local':
            qs = qs.filter(local__numero__icontains=valor)
        elif tipo == 'area':
            qs = qs.filter(area_comun__numero__icontains=valor)
        elif tipo == 'cliente':
            qs = qs.filter(cliente__nombre__icontains=valor)
        else:
            qs = qs.filter(
                Q(local__numero__icontains=valor) |
                Q(area_comun__numero__icontains=valor) |
                Q(cliente__nombre__icontains=valor)
            )

        if self.datos.get('mes'):
            anio, mes = self._parsear_mes(self.datos['mes'])
            qs = qs.filter(fecha_emision__year=anio, fecha_emision__month=mes)

        qs = qs.order_by('-fecha_emision')
        total_encontradas = qs.count()

        if total_encontradas == 0:
            return {
                'exito': True,
                'mensaje': f"🔎 No encontré ninguna factura que coincida con \"{self.datos['criterio']}\""
                           + (f" en {self.datos['mes']}" if self.datos.get('mes') else "") + ".",
            }

        factura = qs.first()
        aviso_varias = (
            f" (encontré {total_encontradas} facturas que coinciden, te muestro la más reciente)"
            if total_encontradas > 1 else ""
        )

        referencia = factura.local or factura.area_comun or factura.cliente
        estatus_emoji = {'pendiente': '🟡', 'cobrada': '🟢', 'cancelada': '⚪'}.get(factura.estatus, '')

        mensaje = (
            f"{estatus_emoji} Factura **{factura.folio}** — {referencia} ({factura.cliente.nombre})\n"
            f"Tipo: {factura.get_tipo_cuota_display()}\n"
            f"Monto: ${factura.monto:,.2f} | Vence: {factura.fecha_vencimiento.strftime('%d/%m/%Y')}\n"
            f"Estatus: **{factura.get_estatus_display()}**"
            + (f" (saldo pendiente: ${factura.saldo_pendiente:,.2f})" if factura.estatus == 'pendiente' else "")
            + aviso_varias
        )

        resultado = {
            'exito': True,
            'mensaje': mensaje,
            'objeto_id': factura.id,
            'objeto_nombre': factura.folio,
        }

        # Solo si está pendiente se ofrece la acción de asignar cobro
        if factura.estatus == 'pendiente':
            resultado['opciones'] = [
                {
                    'texto': '💰 Registrar Cobro',
                    'valor': f"Quiero registrar un cobro a la factura {factura.folio}",
                    'intencion': 'registrar_cobro'
                }
            ]

        return resultado

    @staticmethod
    def _interpretar_criterio(texto: str) -> Tuple[str, str]:
        """
        Interpreta el texto libre del usuario para saber si busca por local,
        área común o cliente. Si no hay prefijo reconocible, se busca en los
        tres campos a la vez ('auto').
        """
        limpio = texto.strip().lower()

        if limpio.startswith('local'):
            return 'local', re.sub(r'^local\s*', '', limpio).strip()

        if re.match(r'^(area|área)', limpio):
            valor = re.sub(r'^(area|área)\s*(com[uú]n)?\s*', '', limpio).strip()
            return 'area', valor

        if limpio.startswith('cliente'):
            return 'cliente', re.sub(r'^cliente\s*', '', limpio).strip()

        return 'auto', limpio

    @staticmethod
    def _parsear_mes(texto: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Interpreta el mes en distintos formatos: 'julio', 'julio 2026',
        'AAAA-MM', 'MM/AAAA'. Devuelve (año, mes) o (None, None) si no se
        pudo interpretar. Si no se especifica año, se asume el actual.
        """
        limpio = texto.strip().lower()

        m = re.match(r'^(\d{4})-(\d{1,2})$', limpio)
        if m:
            return int(m.group(1)), int(m.group(2))

        m = re.match(r'^(\d{1,2})/(\d{4})$', limpio)
        if m:
            return int(m.group(2)), int(m.group(1))

        for nombre, numero in MESES.items():
            if nombre in limpio:
                m2 = re.search(r'(\d{4})', limpio)
                anio = int(m2.group(1)) if m2 else date.today().year
                return anio, numero

        return None, None