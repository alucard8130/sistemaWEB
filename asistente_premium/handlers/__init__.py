"""Inicializador de handlers"""
from asistente_premium.handlers.cuenta_bancaria_handler import CuentaBancariaHandler
from asistente_premium.handlers.solicitud_gasto_handler import SolicitudGastoHandler
from .tipo_gasto_handler import TipoGastoHandler
from .base_handler import BaseHandler
from .cliente_handler import ClienteHandler
from .proveedor_handler import ProveedorHandler
from .empleado_handler import EmpleadoHandler
from .buscar_factura_handler import BuscarFacturaHandler
from .pago_handler import AsignarPagoHandler



# Registro de todos los handlers disponibles
HANDLERS_REGISTRY = {
    'crear_cliente': ClienteHandler,
    'crear_proveedor': ProveedorHandler,
    'crear_cuenta_bancaria': CuentaBancariaHandler,
    'crear_empleado': EmpleadoHandler,
    'crear_tipo_gasto': TipoGastoHandler,
    'buscar_factura': BuscarFacturaHandler,
    'asignar_pago': AsignarPagoHandler,
    'registrar_cobro': AsignarPagoHandler,  # ← alias directo
    'crear_solicitud_gasto': SolicitudGastoHandler,
}

def obtener_handler(intencion: str, usuario, empresa=None):
    """Obtiene el handler correspondiente a una intención"""
    handler_class = HANDLERS_REGISTRY.get(intencion)
    if handler_class:
        return handler_class(usuario, empresa)
    return None


def obtener_todos_handlers():
    """Retorna instancias de todos los handlers disponibles"""
    return [handler_class for handler_class in HANDLERS_REGISTRY.values()]