"""Handler para asignar un pago a una factura"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional
from .base_handler import BaseHandler
from facturacion.models import Factura, Pago
from empresas.models import CuentaBancaria


class AsignarPagoHandler(BaseHandler):
    """Handler para registrar un cobro sobre una factura existente"""

    intencion_principal = 'asignar_cobro'
    intencion_aliases = [
        'registrar_cobro', 'agregar_cobro', 'nuevo_cobro', 'cobrar_factura', 'abonar_factura','asignar_pago','asignar_cobro', 'registrar_pago', 'agregar_pago', 'nuevo_pago', 'pagar_factura', 'abonar_factura'
    ]
    descripcion = "Asignar un cobro a una factura"
    emoji = "💰"

    campos_requeridos = ['folio', 'monto', 'forma_pago']
    campos_opcionales = ['fecha_pago', 'cuenta_bancaria', 'observaciones']

    def obtener_campos(self) -> List[Dict]:
        cuentas = CuentaBancaria.objects.filter(empresa=self.empresa, activa=True)
        opciones_cuenta = [(str(c.id), str(c)) for c in cuentas]

        return [
            {
                'nombre': 'folio',
                'label': '¿Cuál es el folio de la factura a cobrar?',
                'tipo': 'text',
                'requerido': True,
            },
            {
                'nombre': 'monto',
                'label': '¿Cuál es el monto del cobro?',
                'tipo': 'text',
                'requerido': True,
            },
            {
                'nombre': 'forma_pago',
                'label': '¿Cuál fue la forma de cobro?',
                'tipo': 'select',
                'requerido': True,
                'opciones': Pago.FORMAS_PAGO,
            },
            {
                'nombre': 'fecha_pago',
                'label': '¿Qué fecha tuvo el cobro? (opcional, formato DD/MM/AAAA; si no me dices, uso hoy)',
                'tipo': 'text',
                'requerido': False,
            },
            {
                'nombre': 'cuenta_bancaria',
                'label': '¿A qué cuenta bancaria entró el cobro? (opcional)',
                'tipo': 'select',
                'requerido': False,
                'opciones': opciones_cuenta,
            },
            {
                'nombre': 'observaciones',
                'label': '¿Alguna observación? (opcional)',
                'tipo': 'textarea',
                'requerido': False,
            },
        ]

    def validar(self) -> bool:
        self.limpiar_errores()

        # Folio: requerido, la factura debe existir en esta empresa
        if not self.datos.get('folio'):
            self.agregar_error('folio', 'El folio de la factura es requerido')
            return False

        factura = self._obtener_factura(self.datos['folio'])
        if factura is None:
            self.agregar_error('folio', 'No encontré ninguna factura con ese folio en tu empresa')
            return False

        if factura.estatus == 'cancelada':
            self.agregar_error('folio', 'Esa factura está cancelada, no se le puede asignar un cobro')
            return False

        if factura.estatus == 'cobrada':
            self.agregar_error('folio', 'Esa factura ya está cobrada por completo')
            return False

        # Monto: requerido, debe ser un número válido mayor a cero
        if not self.datos.get('monto'):
            self.agregar_error('monto', 'El monto es requerido')
            return False
 
        monto = self._parsear_decimal(self.datos['monto'])
        if monto is None or monto <= 0:
            self.agregar_error('monto', 'El monto debe ser un número válido mayor a cero, ej. 1500.00')
            return False
 
        saldo_pendiente = Decimal(str(factura.saldo_pendiente))
        if monto > saldo_pendiente:
            self.agregar_error(
                'monto',
                f'El monto (${monto:,.2f}) no puede ser mayor al saldo pendiente de la factura (${saldo_pendiente:,.2f})'
            )
            return False
 
        self.datos['monto'] = monto

        # Forma de pago: requerida, debe ser una opción válida
        formas_validas = dict(Pago.FORMAS_PAGO)
        if not self.datos.get('forma_pago'):
            self.agregar_error('forma_pago', 'La forma de cobro es requerida')
            return False
        if self.datos['forma_pago'] not in formas_validas:
            self.agregar_error('forma_pago', 'Forma de cobro no válida')
            return False

        # Fecha de cobro: opcional, si viene debe tener formato válido
        if self.datos.get('fecha_pago'):
            fecha_normalizada = self._normalizar_fecha(self.datos['fecha_pago'])
            if fecha_normalizada is None:
                self.agregar_error('fecha_pago', 'Fecha inválida, usa el formato DD/MM/AAAA')
                return False
            self.datos['fecha_pago'] = fecha_normalizada

        # Cuenta bancaria: opcional, si viene debe existir
        if self.datos.get('cuenta_bancaria'):
            cuenta = self._obtener_cuenta(self.datos['cuenta_bancaria'])
            if cuenta is None:
                self.agregar_error('cuenta_bancaria', 'La cuenta bancaria seleccionada no existe')
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

        factura = self._obtener_factura(self.datos['folio'])
        cuenta = self._obtener_cuenta(self.datos['cuenta_bancaria']) if self.datos.get('cuenta_bancaria') else None
        fecha_pago = self.datos.get('fecha_pago') or date.today().isoformat()

        try:
            pago = Pago.objects.create(
                factura=factura,
                empresa=self.empresa,
                fecha_pago=fecha_pago,
                monto=self.datos['monto'],
                forma_pago=self.datos['forma_pago'],
                cuenta_bancaria=cuenta,
                observaciones=self.datos.get('observaciones') or 'cobro aplicado Sherlock',
                registrado_por=self.usuario,
                identificado=True,
            )

            factura.actualizar_estatus()
            factura.refresh_from_db()

            mensaje = (
                f"✅ ¡Cobro de ${pago.monto:,.2f} registrado en la factura {factura.folio}!\n"
                f"Nuevo estatus: **{factura.get_estatus_display()}**"
            )
            if factura.estatus == 'pendiente':
                mensaje += f" (saldo pendiente: ${factura.saldo_pendiente:,.2f})"

            return {
                'exito': True,
                'mensaje': mensaje,
                'objeto_id': pago.id,
                'objeto_nombre': f"Cobro a {factura.folio}",
            }

        except Exception as e:
            return {
                'exito': False,
                'mensaje': f"❌ Error al registrar el cobro: {str(e)}",
                'errores': {'general': str(e)}
            }

    def _obtener_factura(self, folio: str) -> Optional[Factura]:
        try:
            return Factura.objects.get(empresa=self.empresa, folio=folio, activo=True)
        except Factura.DoesNotExist:
            return None
        except Factura.MultipleObjectsReturned:
            return Factura.objects.filter(empresa=self.empresa, folio=folio, activo=True).order_by('-fecha_emision').first()

    def _obtener_cuenta(self, valor: str) -> Optional[CuentaBancaria]:
        try:
            return CuentaBancaria.objects.get(id=int(valor), empresa=self.empresa)
        except (CuentaBancaria.DoesNotExist, ValueError, TypeError):
            return None

    @staticmethod
    def _parsear_decimal(valor: str) -> Optional[Decimal]:
        limpio = valor.strip().replace(',', '').replace('$', '')
        try:
            return Decimal(limpio)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _normalizar_fecha(valor: str) -> Optional[str]:
        """Acepta 'DD/MM/AAAA' o 'AAAA-MM-DD' y devuelve 'AAAA-MM-DD'."""
        valor = valor.strip()

        if re.match(r'^\d{4}-\d{2}-\d{2}$', valor):
            try:
                datetime.strptime(valor, '%Y-%m-%d')
                return valor
            except ValueError:
                return None

        m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', valor)
        if m:
            dia, mes, anio = m.groups()
            try:
                fecha = datetime(int(anio), int(mes), int(dia))
                return fecha.strftime('%Y-%m-%d')
            except ValueError:
                return None

        return None