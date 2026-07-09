"""Servicios mejorados con sistema de handlers"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from .models import ConversacionAsistente, MensajeAsistente
from .intents import recognizar_intencion, extraer_datos_mensaje
from .handlers import obtener_handler, HANDLERS_REGISTRY
from django.db import transaction


# Nivel mínimo de membresía requerido para cada intención. Las intenciones
# que no aparecen aquí (ej. 'otro') no tienen restricción de nivel.
NIVEL_REQUERIDO_POR_INTENCION = {
    'crear_cliente': 'plus',
    'crear_proveedor': 'plus',
    'crear_empleado': 'plus',
    'crear_cuenta_bancaria': 'premium',
    'crear_tipo_gasto': 'premium',
    'buscar_factura': 'premium',
    'asignar_cobro': 'premium',
}

# Orden de jerarquía de planes, de menor a mayor acceso
NIVEL_ORDEN = {'demo': 0, 'plus': 1, 'premium': 2}


class AsistenteService:
    """Servicio orquestador que usa handlers"""

    def __init__(self, usuario, empresa=None):
        self.usuario = usuario
        self.empresa = empresa

    @staticmethod
    def _nivel_empresa(empresa) -> str:
        """Determina el nivel de membresía de la empresa: 'demo', 'plus' o 'premium'."""
        if empresa is None:
            return 'demo'
        if getattr(empresa, 'es_premium', False):
            return 'premium'
        if getattr(empresa, 'es_plus', False):
            return 'plus'
        return 'demo'

    def _respuesta_plan_insuficiente(
        self, mensaje_texto: str, nivel_requerido: str, intencion_detectada: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera la respuesta de Sherlock cuando la empresa no tiene el nivel
        de membresía necesario. Se deja registro en el historial (para poder
        ver, por ejemplo, cuántas empresas demo intentaron usar a Sherlock:
        son leads de upsell).
        """
        from django.conf import settings

        conversacion = ConversacionAsistente.objects.create(
            usuario=self.usuario,
            empresa=self.empresa,
            intencion=intencion_detectada,
            estado='cancelada',
        )
        MensajeAsistente.objects.create(conversacion=conversacion, tipo='usuario', contenido=mensaje_texto)

        # Si lo que se requiere es 'plus', significa que la empresa es demo y
        # no tiene NADA de acceso (bloqueo total: no tiene sentido ofrecerle
        # el menú de tareas). Si lo que se requiere es 'premium', la empresa
        # ya es plus y sí puede seguir usando el resto de tareas (bloqueo
        # parcial, solo para esta función en específico).
        bloqueo_total = nivel_requerido == 'plus'

        if bloqueo_total:
            mensaje = (
                "🔒 Todavía no puedo ayudarte — Sherlock no está disponible en tu plan actual (Demo). "
                "Necesitas al menos el plan **Plus** para usarme."
            )
        else:
            mensaje = (
                "🔒 Esta función es exclusiva del plan **Premium**. Con tu plan actual (Plus) sí puedo "
                "ayudarte a dar de alta clientes, proveedores y empleados. Para desbloquear cuentas "
                "bancarias, cuentas de gastos, búsqueda de facturas y asignación de pagos, necesitas "
                "actualizar a Premium."
            )

        MensajeAsistente.objects.create(conversacion=conversacion, tipo='asistente', contenido=mensaje)

        return {
            'estado': 'error',
            'requiere_upgrade': nivel_requerido,
            'bloqueo_total': bloqueo_total,
            'upgrade_url': settings.PORTAL_PAGOS_URL,
            'mensaje': mensaje,
            'conversacion_id': conversacion.id,
        }

    @transaction.atomic
    def procesar_mensaje(self, mensaje_texto: str, conversacion_id: int = None, intencion_sugerida: str = None) -> Dict[str, Any]:
        """Procesa mensaje usando el sistema de handlers"""

        nivel_empresa = self._nivel_empresa(self.empresa)

        # Plan demo: Sherlock no está disponible en absoluto, sin importar
        # qué se le pida. Se corta aquí, antes de tocar cualquier conversación.
        if nivel_empresa == 'demo':
            return self._respuesta_plan_insuficiente(mensaje_texto, nivel_requerido='plus')

        if conversacion_id:
            conversacion = ConversacionAsistente.objects.get(
                id=conversacion_id,
                usuario=self.usuario
            )
            # Red de seguridad: si esta conversación quedó sin intención
            # reconocida ('otro') y ahora llega una intención sugerida (ej.
            # el usuario dio clic en un botón de opción), se "repara" la
            # conversación en vez de seguir atorada repitiendo "no entiendo".
            if conversacion.intencion in (None, 'otro') and intencion_sugerida:
                nivel_requerido = NIVEL_REQUERIDO_POR_INTENCION.get(intencion_sugerida)
                if nivel_requerido and NIVEL_ORDEN[nivel_empresa] < NIVEL_ORDEN[nivel_requerido]:
                    return self._respuesta_plan_insuficiente(mensaje_texto, nivel_requerido, intencion_sugerida)
                conversacion.intencion = intencion_sugerida
                conversacion.estado = 'iniciada'
                conversacion.save()
        else:
            if intencion_sugerida:
                intencion = intencion_sugerida
                confianza = 1.0
            else:
                intencion, confianza = recognizar_intencion(mensaje_texto)

            # Bloquea aquí, antes de crear la conversación, si la intención
            # detectada requiere un nivel de membresía que la empresa no tiene.
            if confianza > 0.3:
                nivel_requerido = NIVEL_REQUERIDO_POR_INTENCION.get(intencion)
                if nivel_requerido and NIVEL_ORDEN[nivel_empresa] < NIVEL_ORDEN[nivel_requerido]:
                    return self._respuesta_plan_insuficiente(mensaje_texto, nivel_requerido, intencion)

            conversacion = ConversacionAsistente.objects.create(
                usuario=self.usuario,
                empresa=self.empresa,
                intencion=intencion if confianza > 0.3 else 'otro',
                estado='iniciada',
            )

        MensajeAsistente.objects.create(
            conversacion=conversacion,
            tipo='usuario',
            contenido=mensaje_texto
        )

        handler = obtener_handler(conversacion.intencion, self.usuario, self.empresa or conversacion.empresa)

        if not handler:
            respuesta = self._manejar_intencion_desconocida(conversacion)
        elif conversacion.estado == 'iniciada':
            respuesta = self._iniciar_conversacion(conversacion, handler, mensaje_texto)
        elif conversacion.estado == 'solicitando_datos':
            respuesta = self._recopilar_datos(conversacion, handler, mensaje_texto)
        elif conversacion.estado == 'validando':
            respuesta = self._procesar_handler(conversacion, handler)
        elif conversacion.estado == 'completada':
            respuesta = {'estado': 'completada', 'mensaje': 'Conversación completada'}
        else:
            respuesta = {'estado': 'error', 'mensaje': 'Estado desconocido'}

        MensajeAsistente.objects.create(
            conversacion=conversacion,
            tipo='asistente',
            contenido=respuesta.get('mensaje', ''),
            opciones=respuesta.get('opciones', [])
        )

        respuesta['conversacion_id'] = conversacion.id
        return respuesta

    def _iniciar_conversacion(self, conversacion: ConversacionAsistente, handler, mensaje: str) -> Dict[str, Any]:
        """Inicia una nueva conversación con el handler"""

        datos_extraidos = extraer_datos_mensaje(mensaje)
        conversacion.datos_recopilados.update(datos_extraidos)

        campos = handler.obtener_campos()
        campos_faltantes = self._obtener_campos_faltantes(conversacion.datos_recopilados, campos)

        conversacion.estado = 'solicitando_datos'

        if campos_faltantes:
            siguiente_campo = campos_faltantes[0]
            conversacion.campo_actual = siguiente_campo['nombre']
            conversacion.save()
            return self._respuesta_campo(
                siguiente_campo,
                len(campos_faltantes),
                mensaje_prefijo=handler.obtener_mensaje_bienvenida() + '\n\n'
            )

        conversacion.campo_actual = None
        conversacion.estado = 'validando'
        conversacion.save()
        return self._procesar_handler(conversacion, handler)

    def _recopilar_datos(self, conversacion: ConversacionAsistente, handler, mensaje: str) -> Dict[str, Any]:
        """Recopila datos en conversación continua, un campo a la vez"""

        campos = handler.obtener_campos()
        campo_actual = self._buscar_campo(campos, conversacion.campo_actual)
        mensaje_limpio = mensaje.strip()
        es_omitir = mensaje_limpio.lower() in ('omitir', 'saltar')

        if campo_actual:
            if es_omitir:
                if campo_actual['requerido']:
                    return self._respuesta_campo(
                        campo_actual,
                        len(self._obtener_campos_faltantes(conversacion.datos_recopilados, campos)),
                        mensaje_prefijo="⚠️ Este dato es obligatorio y no se puede omitir.\n\n"
                    )
                # Campo opcional omitido: se marca como respondido, sin valor.
                # OJO: se guarda '' y no None -> los CharField de Django suelen
                # tener null=False (solo blank=True), así que None provoca un
                # IntegrityError (violación de NOT NULL) al crear el registro.
                conversacion.datos_recopilados[campo_actual['nombre']] = ''

            elif campo_actual.get('tipo') == 'select':
                # Validar/normalizar contra las opciones definidas (acepta el
                # código exacto que manda un botón, o el texto de la etiqueta
                # si el usuario prefirió escribirlo)
                valor = self._normalizar_valor_select(mensaje_limpio, campo_actual.get('opciones') or [])
                if valor is None:
                    return self._respuesta_campo(
                        campo_actual,
                        len(self._obtener_campos_faltantes(conversacion.datos_recopilados, campos)),
                        mensaje_prefijo="⚠️ Esa opción no es válida, elige una de la lista.\n\n"
                    )
                conversacion.datos_recopilados[campo_actual['nombre']] = valor

            else:
                datos_extraidos = extraer_datos_mensaje(mensaje_limpio)
                valor = datos_extraidos.get(campo_actual['nombre'], mensaje_limpio)
                conversacion.datos_recopilados[campo_actual['nombre']] = valor

        campos_faltantes = self._obtener_campos_faltantes(conversacion.datos_recopilados, campos)

        if campos_faltantes:
            siguiente = campos_faltantes[0]
            conversacion.campo_actual = siguiente['nombre']
            conversacion.save()
            return self._respuesta_campo(siguiente, len(campos_faltantes))

        conversacion.campo_actual = None
        conversacion.estado = 'validando'
        conversacion.save()
        return self._procesar_handler(conversacion, handler)

    def _procesar_handler(self, conversacion: ConversacionAsistente, handler) -> Dict[str, Any]:
        """Ejecuta el handler con los datos recopilados"""

        # Se ejecuta en un savepoint anidado: si algo falla a nivel de base de
        # datos (ej. RFC duplicado, restricción NOT NULL, etc.), solo se
        # revierte este savepoint y no toda la transacción de procesar_mensaje.
        # Sin esto, cualquier error de BD deja la conexión en un estado donde
        # la siguiente query lanza TransactionManagementError en vez del error real.
        try:
            with transaction.atomic():
                resultado = handler.procesar(conversacion.datos_recopilados)
        except Exception as e:
            resultado = {
                'exito': False,
                'mensaje': f"❌ Error al procesar la solicitud: {str(e)}",
                'errores': {'general': str(e)},
            }

        if resultado.get('exito'):
            conversacion.estado = 'completada'
            conversacion.fecha_finalizacion = datetime.now()
        else:
            conversacion.errores = resultado.get('errores', {})
            conversacion.estado = 'cancelada'

        conversacion.save()

        respuesta = {
            'estado': 'completada' if resultado.get('exito') else 'error',
            'mensaje': resultado.get('mensaje'),
            'intencion': conversacion.intencion,
        }

        if 'objeto_id' in resultado:
            respuesta['objeto_id'] = resultado['objeto_id']

        # Permite que cualquier handler (no solo el flujo de "no entiendo")
        # ofrezca botones de acción tras completar su tarea. Ej: al buscar
        # una factura pendiente, BuscarFacturaHandler devuelve un botón
        # "Asignar pago" que arranca AsignarPagoHandler con el folio precargado.
        if 'opciones' in resultado:
            respuesta['opciones'] = resultado['opciones']

        return respuesta

    def _manejar_intencion_desconocida(self, conversacion: ConversacionAsistente) -> Dict[str, Any]:
        """Maneja cuando no se reconoce la intención"""

        nivel_empresa = self._nivel_empresa(self.empresa)

        opciones = []
        for intencion, handler_class in HANDLERS_REGISTRY.items():
            nivel_requerido = NIVEL_REQUERIDO_POR_INTENCION.get(intencion)
            if nivel_requerido and NIVEL_ORDEN[nivel_empresa] < NIVEL_ORDEN[nivel_requerido]:
                # No disponible en el plan actual: no se ofrece como opción
                continue
            opciones.append({
                'texto': f"{handler_class.emoji} {handler_class.descripcion}",
                'valor': f"Quiero {handler_class.descripcion.lower()}",
                'intencion': intencion
            })

        return {
            'estado': 'solicitando_intención',
            'mensaje': '❓ No entiendo bien. ¿Qué quieres hacer?',
            'opciones': opciones
        }

    @staticmethod
    def _respuesta_campo(campo: Dict, campos_faltantes: int, mensaje_prefijo: str = "") -> Dict[str, Any]:
        """
        Construye la respuesta JSON estándar para pedir un campo, incluyendo
        la metadata que el frontend necesita para:
        - Mostrar un botón "Saltar" si el campo es opcional (campo_requerido=False)
        - Renderizar botones de selección si campo_tipo == 'select' (campo_opciones)
        """
        opciones = campo.get('opciones')
        return {
            'estado': 'solicitando_datos',
            'mensaje': mensaje_prefijo + campo['label'],
            'campo_actual': campo['nombre'],
            'campo_tipo': campo.get('tipo', 'text'),
            'campo_requerido': campo.get('requerido', False),
            'campo_opciones': [{'valor': v, 'label': l} for v, l in opciones] if opciones else None,
            'campos_faltantes': campos_faltantes,
        }

    @staticmethod
    def _normalizar_valor_select(mensaje: str, opciones: List) -> Optional[str]:
        """
        Intenta hacer match del mensaje contra las opciones definidas (lista de
        tuplas (valor, label)). Acepta coincidencia exacta por valor (lo que
        manda un botón) o por texto de la etiqueta (si el usuario escribió).
        Retorna el 'valor' normalizado, o None si no hubo coincidencia.
        """
        mensaje_norm = mensaje.strip().lower()
        for valor, label in opciones:
            if mensaje_norm == str(valor).strip().lower():
                return valor
            if mensaje_norm == str(label).strip().lower():
                return valor
        return None

    @staticmethod
    def _obtener_campos_faltantes(datos_recopilados: Dict, campos: List[Dict]) -> List[Dict]:
        """
        Obtiene los campos (requeridos Y opcionales) que aún no se le han
        preguntado al usuario. Un campo se considera "respondido" en cuanto
        existe su llave en datos_recopilados, aunque su valor sea None
        (caso de un opcional omitido).
        """
        return [c for c in campos if c['nombre'] not in datos_recopilados]

    @staticmethod
    def _buscar_campo(campos: List[Dict], nombre: Optional[str]) -> Optional[Dict]:
        """Busca la definición de un campo por su nombre"""
        if not nombre:
            return None
        for c in campos:
            if c['nombre'] == nombre:
                return c
        return None

    @staticmethod
    def obtener_handlers_disponibles() -> list:
        """Retorna todos los handlers disponibles"""
        return [
            {
                'intencion': intencion,
                'descripcion': handler_class.descripcion,
                'emoji': handler_class.emoji,
                'aliases': handler_class.intencion_aliases
            }
            for intencion, handler_class in HANDLERS_REGISTRY.items()
        ]