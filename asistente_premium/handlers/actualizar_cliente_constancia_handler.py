
from typing import Any, Dict, List
from typing import Any

from asistente_premium.handlers.base_handler import BaseHandler
from clientes.models import Cliente


class ActualizarClienteConstanciaHandler(BaseHandler):
    """Completa los datos fiscales de un cliente EXISTENTE usando lo
    extraído de su Constancia de Situación Fiscal. Solo llena los campos
    que el cliente tiene vacíos -- nunca sobrescribe un dato ya capturado."""

    intencion_principal = 'actualizar_cliente_constancia'
    intencion_aliases = []
    descripcion = "Actualizar cliente con datos de constancia fiscal"
    emoji = "📄"
    oculto_en_menu = True

    def obtener_campos(self) -> List[Dict]:
        # Todo llega precargado desde la vista que procesó la constancia
        # -- no hay nada más que preguntarle al usuario.
        return []

    def validar(self) -> bool:
        self.limpiar_errores()
        if not self.datos.get('cliente_id'):
            self.agregar_error('cliente_id', 'No se especificó el cliente a actualizar')
            return False
        return True

    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        self.establecer_datos(datos)
        if not self.validar():
            return {
                'exito': False,
                'errores': self.errores,
                'mensaje': '❌ ' + list(self.errores.values())[0],
            }

        try:
            cliente = Cliente.objects.get(id=self.datos['cliente_id'], empresa=self.empresa)
        except Cliente.DoesNotExist:
            return {'exito': False, 'mensaje': '❌ No se encontró el cliente a actualizar.'}

        campos_actualizables = [
            'nombre', 'tipo_contribuyente', 'regimen_fiscal',
            'codigo_postal', 'direccion_domicilio',
        ]
        actualizados = []

        for campo in campos_actualizables:
            valor_nuevo = self.datos.get(campo)
            if not valor_nuevo:
                continue  # la constancia no trajo este dato, no se toca lo existente
            valor_actual = getattr(cliente, campo, None)
            if valor_actual != valor_nuevo:
                setattr(cliente, campo, valor_nuevo)
                actualizados.append(campo)

        if actualizados:
            cliente.save()
            return {
                'exito': True,
                'mensaje': f"✅ Cliente '{cliente.nombre}' actualizado con la constancia. Campos completados: {', '.join(actualizados)}.",
                'objeto_id': cliente.id,
            }
        return {
            'exito': True,
            'mensaje': f"ℹ️ El cliente '{cliente.nombre}' ya tenía estos mismos datos. No hubo cambios.",
            'objeto_id': cliente.id,
        }