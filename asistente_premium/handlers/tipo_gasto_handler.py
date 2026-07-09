"""Handler para tareas relacionadas con cuentas/tipos de gasto"""
import re
from typing import Dict, List, Any, Optional
from .base_handler import BaseHandler
from gastos.models import TipoGasto, SubgrupoGasto


class TipoGastoHandler(BaseHandler):
    """
    Handler para dar de alta una 'cuenta de gastos' (TipoGasto).

    NOTA: GrupoGasto y SubgrupoGasto se asumen como catálogo ya existente
    (no tienen campo 'empresa', son compartidos). Este handler solo crea el
    TipoGasto -que sí es por empresa- bajo un subgrupo ya existente. Si
    algún día se necesita también dar de alta grupos/subgrupos nuevos desde
    el chat, se puede agregar otro handler para eso.
    """

    intencion_principal = 'cuenta_gastos'
    intencion_aliases = [
        'alta_cuenta_gastos', 'nueva_cuenta_gastos', 'agregar_cuenta_gastos',
        'alta_tipo_gasto', 'nuevo_tipo_gasto', 'agregar_tipo_gasto', 'registrar_tipo_gasto',
        'crear_cuenta_de_gastos', 'dar_de_alta_cuenta_gastos', 'cuenta_gastos_nueva',
        'registrar_nueva_cuenta_gastos', 'agregar_nueva_cuenta_gastos', 'crear_nueva_cuenta_gastos',
        'agrega_cuenta_gastos', 'dar_alta_cuenta_gastos', 'nueva_cuenta_gastos_registro', 'cuenta_gastos_registro',
        'cuenta_gastos_agregar', 'cuenta_gastos_crear', 'cuenta_gastos_dar_alta', 
        'cuenta_gastos_nueva_registro', 'cuenta_gastos_agregar', 'cuenta_gastos_crear',
    ]
    descripcion = "Dar de alta una cuenta de gastos"
    emoji = "🧾"

    campos_requeridos = ['subgrupo', 'nombre']
    campos_opcionales = ['descripcion']

    def obtener_campos(self) -> List[Dict]:
        subgrupos = SubgrupoGasto.objects.select_related('grupo').order_by('grupo__nombre', 'nombre')
        opciones_subgrupo = [(str(s.id), str(s)) for s in subgrupos]

        return [
            {
                'nombre': 'subgrupo',
                'label': '¿A qué grupo/subgrupo pertenece esta cuenta de gastos?',
                'tipo': 'select',
                'requerido': True,
                'opciones': opciones_subgrupo,
            },
            {
                'nombre': 'nombre',
                'label': '¿Cuál es el nombre de la cuenta de gastos?',
                'tipo': 'text',
                'requerido': True,
            },
            {
                'nombre': 'descripcion',
                'label': '¿Alguna descripción adicional? (opcional)',
                'tipo': 'textarea',
                'requerido': False,
            },
        ]

    def validar(self) -> bool:
        self.limpiar_errores()

        # Subgrupo: requerido, debe existir en el catálogo
        if not self.datos.get('subgrupo'):
            self.agregar_error('subgrupo', 'El grupo/subgrupo es requerido')
            return False

        subgrupo = self._obtener_subgrupo(self.datos['subgrupo'])
        if subgrupo is None:
            self.agregar_error('subgrupo', 'El subgrupo seleccionado no existe')
            return False

        # Nombre: requerido
        if not self.datos.get('nombre'):
            self.agregar_error('nombre', 'El nombre es requerido')
            return False

        if len(self.datos['nombre']) < 2:
            self.agregar_error('nombre', 'El nombre debe tener al menos 2 caracteres')
            return False

        # Evitar duplicados: mismo nombre de cuenta dentro del mismo subgrupo
        # y la misma empresa
        if TipoGasto.objects.filter(
            empresa=self.empresa, subgrupo=subgrupo, nombre__iexact=self.datos['nombre']
        ).exists():
            self.agregar_error('nombre', 'Ya existe una cuenta de gastos con este nombre en ese subgrupo')
            return False

        return True

    def _normalizar_datos(self):
        """Formato título para el nombre; espacios limpiados en descripción."""
        if self.datos.get('nombre'):
            self.datos['nombre'] = re.sub(r'\s+', ' ', self.datos['nombre'].strip()).title()

        if self.datos.get('descripcion'):
            self.datos['descripcion'] = re.sub(r'\s+', ' ', self.datos['descripcion'].strip())

    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        self.establecer_datos(datos)
        self._normalizar_datos()

        if not self.validar():
            return {
                'exito': False,
                'errores': self.errores,
                'mensaje': '❌ Hay errores en los datos ingresados'
            }

        subgrupo = self._obtener_subgrupo(self.datos['subgrupo'])

        try:
            tipo_gasto = TipoGasto.objects.create(
                empresa=self.empresa,
                subgrupo=subgrupo,
                nombre=self.datos.get('nombre'),
                descripcion=self.datos.get('descripcion') or '',
            )

            return {
                'exito': True,
                'mensaje': f"✅ ¡Cuenta de gastos '{tipo_gasto.nombre}' ({subgrupo}) creada exitosamente!",
                'objeto_id': tipo_gasto.id,
                'objeto_nombre': tipo_gasto.nombre,
            }

        except Exception as e:
            return {
                'exito': False,
                'mensaje': f"❌ Error al crear la cuenta de gastos: {str(e)}",
                'errores': {'general': str(e)}
            }

    @staticmethod
    def _obtener_subgrupo(valor: str) -> Optional[SubgrupoGasto]:
        """Convierte el id (string) recibido del selector en la instancia real."""
        try:
            return SubgrupoGasto.objects.select_related('grupo').get(id=int(valor))
        except (SubgrupoGasto.DoesNotExist, ValueError, TypeError):
            return None