"""Handler para tareas relacionadas con proveedores"""
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from .base_handler import BaseHandler
from proveedores.models import Proveedor


class ProveedorHandler(BaseHandler):
    """Handler para crear proveedores"""

    intencion_principal = 'proveedor'
    intencion_aliases = ['alta_proveedor', 'nuevo_proveedor', 'agregar_proveedor','registrar_proveedor', 
                         'registrar_nuevo_proveedor','generar_proveedor', 'generar_nuevo_proveedor',
                         'crear_proveedor', 'crear_nuevo_proveedor', 'crea_proveedor_nuevo', 'crea_proveedor']
    descripcion = "Dar de alta un nuevo proveedor"
    emoji = "🏢"

    campos_requeridos = ['nombre', 'rfc']
    campos_opcionales = ['email', 'telefono', 'direccion', 'repse_numero', 'repse_vigencia']

    def obtener_campos(self) -> List[Dict]:
        return [
            {
                'nombre': 'nombre',
                'label': '¿Cuál es el nombre del proveedor?',
                'tipo': 'text',
                'requerido': True
            },
            {
                'nombre': 'rfc',
                'label': '¿Cuál es el RFC del proveedor?',
                'tipo': 'text',
                'requerido': True,
                'validacion': 'rfc_mexicano'
            },
            {
                'nombre': 'email',
                'label': '¿Cuál es el email? (opcional)',
                'tipo': 'email',
                'requerido': False
            },
            {
                'nombre': 'telefono',
                'label': '¿Cuál es el teléfono? (opcional)',
                'tipo': 'tel',
                'requerido': False
            },
            {
                'nombre': 'direccion',
                'label': '¿Cuál es la dirección? (opcional)',
                'tipo': 'textarea',
                'requerido': False
            },
            {
                'nombre': 'repse_numero',
                'label': '¿Cuál es el número REPSE? (opcional)',
                'tipo': 'text',
                'requerido': False
            },
            {
                'nombre': 'repse_vigencia',
                'label': '¿Cuál es la vigencia REPSE? (opcional, formato DD/MM/AAAA)',
                'tipo': 'date',
                'requerido': False
            }
        ]

    def validar(self) -> bool:
        self.limpiar_errores()

        # Nombre
        if not self.datos.get('nombre'):
            self.agregar_error('nombre', 'El nombre es requerido')
            return False

        # RFC: requerido y con formato válido
        if not self.datos.get('rfc'):
            self.agregar_error('rfc', 'El RFC es requerido')
            return False

        if not self._validar_rfc(self.datos['rfc']):
            self.agregar_error('rfc', 'RFC inválido')
            return False

        # Evitar duplicados: mismo RFC ya registrado para esta empresa
        if Proveedor.objects.filter(empresa=self.empresa, rfc=self.datos['rfc']).exists():
            self.agregar_error('rfc', 'Ya existe un proveedor registrado con este RFC')
            return False

        # Email: opcional, pero si viene debe tener formato válido
        if self.datos.get('email'):
            if not self._validar_email(self.datos['email']):
                self.agregar_error('email', 'Email inválido')
                return False

        # Fecha de vigencia REPSE: opcional, pero si viene debe ser una fecha
        # válida en DD/MM/AAAA o AAAA-MM-DD. Se normaliza a AAAA-MM-DD (lo
        # que espera Django) y se guarda de vuelta en self.datos.
        if self.datos.get('repse_vigencia'):
            fecha_normalizada = self._normalizar_fecha(self.datos['repse_vigencia'])
            if fecha_normalizada is None:
                self.agregar_error('repse_vigencia', 'Fecha inválida, usa el formato DD/MM/AAAA')
                return False
            self.datos['repse_vigencia'] = fecha_normalizada

        return True

    def _normalizar_datos(self):
        """
        Normaliza el formato de los datos antes de guardarlos:
        - nombre: MAYÚSCULAS (se conserva completo, incluyendo SA de CV si lo trae).
        - rfc: mayúsculas.
        - email: minúsculas.
        Los campos vacíos ('' de un opcional omitido) se dejan intactos aquí;
        la conversión a None para campos no-texto ocurre en procesar().
        """
        if self.datos.get('nombre'):
            self.datos['nombre'] = self._formatear_nombre(self.datos['nombre'])

        if self.datos.get('rfc'):
            self.datos['rfc'] = self.datos['rfc'].strip().upper()

        if self.datos.get('email'):
            self.datos['email'] = self.datos['email'].strip().lower()

    @staticmethod
    def _formatear_nombre(nombre: str) -> str:
        """Convierte el nombre del proveedor a MAYÚSCULAS (se conserva completo, sin quitar sufijos)."""
        limpio = re.sub(r'\s+', ' ', nombre.strip())
        return limpio.upper()

    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        self.establecer_datos(datos)
        self._normalizar_datos()

        if not self.validar():
            return {
                'exito': False,
                'errores': self.errores,
                'mensaje': '❌ Hay errores en los datos'
            }

        # repse_vigencia es un DateField en el modelo: '' (opcional omitido)
        # no es una fecha válida para Django/Postgres, así que se convierte
        # a None antes de guardar.
        repse_vigencia = self.datos.get('repse_vigencia') or None

        try:
            proveedor = Proveedor.objects.create(
                empresa=self.empresa,
                nombre=self.datos.get('nombre'),
                rfc=self.datos.get('rfc'),
                email=self.datos.get('email'),
                telefono=self.datos.get('telefono'),
                direccion=self.datos.get('direccion'),
                repse_numero=self.datos.get('repse_numero'),
                repse_vigencia=repse_vigencia,
                activo=True
            )

            return {
                'exito': True,
                'mensaje': f"✅ ¡Proveedor '{proveedor.nombre}' creado exitosamente!",
                'objeto_id': proveedor.id,
                'objeto_nombre': proveedor.nombre
            }

        except Exception as e:
            return {
                'exito': False,
                'mensaje': f"❌ Error: {str(e)}",
                'errores': {'general': str(e)}
            }

    @staticmethod
    def _validar_rfc(rfc: str) -> bool:
        """Valida formato RFC mexicano (persona física o moral)"""
        pattern = r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$'
        return bool(re.match(pattern, rfc.upper()))

    @staticmethod
    def _validar_email(email: str) -> bool:
        """Valida formato email"""
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def _normalizar_fecha(valor: str) -> Optional[str]:
        """
        Acepta 'DD/MM/AAAA' o 'AAAA-MM-DD' y devuelve 'AAAA-MM-DD'
        (formato que Django espera para un DateField), o None si el
        formato no es válido.
        """
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