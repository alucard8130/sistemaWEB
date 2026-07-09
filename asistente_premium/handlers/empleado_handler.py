"""Handler para tareas relacionadas con empleados"""
import re
from typing import Dict, List, Any
from .base_handler import BaseHandler
from empleados.models import Empleado


class EmpleadoHandler(BaseHandler):
    """Handler para dar de alta un empleado"""

    intencion_principal = 'empleado'
    intencion_aliases = [
        'alta_empleado', 'nuevo_empleado', 'agregar_empleado', 'registrar_empleado',
        'crear_empleado', 'dar_de_alta_empleado', 'empleado_nuevo',
        'registrar_nuevo_empleado', 'agregar_nuevo_empleado', 'crear_nuevo_empleado',
        'agrega_empleado', 'dar_alta_empleado', 'nuevo_empleado_registro', 'empleado_registro',
        'empleado_agregar', 'empleado_crear', 'empleado_dar_alta', 'empleado_nuevo_registro', 'empleado_agregar_nuevo', 'empleado_crear_nuevo',
    ]
    descripcion = "Dar de alta un nuevo empleado"
    emoji = "🧑‍💼"

    campos_requeridos = ['nombre', 'rfc', 'puesto', 'departamento']
    campos_opcionales = ['telefono', 'email']

    def obtener_campos(self) -> List[Dict]:
        return [
            {
                'nombre': 'nombre',
                'label': '¿Cuál es el nombre del empleado?',
                'tipo': 'text',
                'requerido': True,
            },
            {
                'nombre': 'rfc',
                'label': '¿Cuál es el RFC del empleado?',
                'tipo': 'text',
                'requerido': True,
                'validacion': 'rfc_mexicano',
            },
            {
                'nombre': 'puesto',
                'label': '¿Cuál es el puesto?',
                'tipo': 'select',
                'requerido': True,
                'opciones': Empleado.PUESTOS_CHOICES,
            },
            {
                'nombre': 'departamento',
                'label': '¿A qué departamento pertenece?',
                'tipo': 'select',
                'requerido': True,
                'opciones': Empleado.DEPARTAMENTO_CHOICES,
            },
            {
                'nombre': 'telefono',
                'label': '¿Cuál es el teléfono? (opcional)',
                'tipo': 'tel',
                'requerido': False,
            },
            {
                'nombre': 'email',
                'label': '¿Cuál es el email? (opcional)',
                'tipo': 'email',
                'requerido': False,
            },
        ]

    def validar(self) -> bool:
        self.limpiar_errores()

        # Nombre
        if not self.datos.get('nombre'):
            self.agregar_error('nombre', 'El nombre es requerido')
            return False

        if len(self.datos['nombre']) < 2:
            self.agregar_error('nombre', 'El nombre debe tener al menos 2 caracteres')
            return False

        # RFC: requerido, formato válido y sin duplicados en la empresa
        if not self.datos.get('rfc'):
            self.agregar_error('rfc', 'El RFC es requerido')
            return False

        if not self._validar_rfc(self.datos['rfc']):
            self.agregar_error('rfc', 'RFC inválido')
            return False

        if Empleado.objects.filter(empresa=self.empresa, rfc=self.datos['rfc']).exists():
            self.agregar_error('rfc', 'Ya existe un empleado registrado con este RFC')
            return False

        # Puesto: requerido, debe ser una opción válida del catálogo
        puestos_validos = dict(Empleado.PUESTOS_CHOICES)
        if not self.datos.get('puesto'):
            self.agregar_error('puesto', 'El puesto es requerido')
            return False
        if self.datos['puesto'] not in puestos_validos:
            self.agregar_error('puesto', 'Puesto no válido')
            return False

        # Departamento: requerido, debe ser una opción válida del catálogo
        departamentos_validos = dict(Empleado.DEPARTAMENTO_CHOICES)
        if not self.datos.get('departamento'):
            self.agregar_error('departamento', 'El departamento es requerido')
            return False
        if self.datos['departamento'] not in departamentos_validos:
            self.agregar_error('departamento', 'Departamento no válido')
            return False

        # Email: opcional, pero si viene debe tener formato válido
        if self.datos.get('email'):
            if not self._validar_email(self.datos['email']):
                self.agregar_error('email', 'Email inválido')
                return False

        return True

    def _normalizar_datos(self):
        """
        Normaliza el formato de los datos antes de guardarlos:
        - nombre: MAYÚSCULAS.
        - rfc: mayúsculas.
        - email: minúsculas.
        Los campos vacíos ('' de un opcional omitido) se dejan intactos.
        """
        if self.datos.get('nombre'):
            self.datos['nombre'] = re.sub(r'\s+', ' ', self.datos['nombre'].strip()).upper()

        if self.datos.get('rfc'):
            self.datos['rfc'] = self.datos['rfc'].strip().upper()

        if self.datos.get('email'):
            self.datos['email'] = self.datos['email'].strip().lower()

    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        self.establecer_datos(datos)
        self._normalizar_datos()

        if not self.validar():
            return {
                'exito': False,
                'errores': self.errores,
                'mensaje': '❌ Hay errores en los datos ingresados'
            }

        try:
            empleado = Empleado.objects.create(
                empresa=self.empresa,
                nombre=self.datos.get('nombre'),
                rfc=self.datos.get('rfc'),
                puesto=self.datos.get('puesto'),
                departamento=self.datos.get('departamento'),
                telefono=self.datos.get('telefono') or None,
                email=self.datos.get('email') or None,
                activo=True,
            )

            puesto_display = dict(Empleado.PUESTOS_CHOICES).get(empleado.puesto, empleado.puesto)

            return {
                'exito': True,
                'mensaje': f"✅ ¡Empleado '{empleado.nombre}' ({puesto_display}) creado exitosamente!",
                'objeto_id': empleado.id,
                'objeto_nombre': empleado.nombre,
            }

        except Exception as e:
            return {
                'exito': False,
                'mensaje': f"❌ Error al crear el empleado: {str(e)}",
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