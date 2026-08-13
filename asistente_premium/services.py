"""Servicios mejorados con sistema de handlers"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.sax import handler

import anthropic
from django.db import transaction
from django.db.models import F
from django.utils import timezone as django_timezone

from core import settings

from .handlers import HANDLERS_REGISTRY, obtener_handler
from .intents import extraer_datos_mensaje, recognizar_intencion
from .models import ConversacionAsistente, MensajeAsistente, UsoConsultaManual

# Nivel mínimo de membresía requerido para cada intención. Las intenciones
# que no aparecen aquí (ej. 'otro') no tienen restricción de nivel.
NIVEL_REQUERIDO_POR_INTENCION = {
    "crear_cliente": "plus",
    "crear_proveedor": "plus",
    "crear_empleado": "plus",
    "crear_cuenta_bancaria": "plus",
    "crear_tipo_gasto": "plus",
    "buscar_factura": "premium",
    # 'asignar_cobro': 'premium',
    "crear_solicitud_gasto": "plus",
    "subir_comprobante": "premium",
    "actualizar_cliente_constancia": "premium",
}

# Orden de jerarquía de planes, de menor a mayor acceso
NIVEL_ORDEN = {"demo": 0, "plus": 1, "premium": 2}

# Límite de consultas manuales por día según el plan de la empresa
LIMITE_CONSULTAS_MANUAL_POR_DIA = {
    "plus": 1,
    "premium": 2,
}


class AsistenteService:
    """Servicio orquestador que usa handlers"""

    def __init__(self, usuario, empresa=None):
        self.usuario = usuario
        self.empresa = empresa


    @staticmethod
    def _nivel_empresa(empresa) -> str:
        """Determina el nivel de membresía de la empresa: 'demo', 'plus' o 'premium'."""
        if empresa is None:
            return "demo"
        if getattr(empresa, "es_premium", False):
            return "premium"
        if getattr(empresa, "es_plus", False):
            return "plus"
        return "demo"


    def _respuesta_plan_insuficiente(
        self,
        mensaje_texto: str,
        nivel_requerido: str,
        intencion_detectada: Optional[str] = None,
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
            estado="cancelada",
        )
        MensajeAsistente.objects.create(
            conversacion=conversacion, tipo="usuario", contenido=mensaje_texto
        )

        # Si lo que se requiere es 'plus', significa que la empresa es demo y
        # no tiene NADA de acceso (bloqueo total: no tiene sentido ofrecerle
        # el menú de tareas). Si lo que se requiere es 'premium', la empresa
        # ya es plus y sí puede seguir usando el resto de tareas (bloqueo
        # parcial, solo para esta función en específico).
        bloqueo_total = nivel_requerido == "plus"

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

        MensajeAsistente.objects.create(
            conversacion=conversacion, tipo="asistente", contenido=mensaje
        )

        return {
            "estado": "error",
            "requiere_upgrade": nivel_requerido,
            "bloqueo_total": bloqueo_total,
            "upgrade_url": settings.PORTAL_PAGOS_URL,
            "mensaje": mensaje,
            "conversacion_id": conversacion.id,
        }



    def _responder_con_manual(self, mensaje_texto: str) -> Optional[str]:
        """
        Intenta responder una pregunta de "cómo funciona GESAC" usando el
        manual de usuario completo como contexto. Devuelve el texto de la
        respuesta, o None si el modelo determina que la pregunta no se
        puede resolver con el manual (para que el llamador decida mostrar
        el menú de opciones en su lugar).
        """
        from .manual_gesac import cargar_manual_gesac  # ajusta el import a tu ruta real

        manual = cargar_manual_gesac()
        if not manual:
            return None

        system_prompt = f"""Eres Sherlock, el asistente de GESAC (Sistema de Gestión \
Administrativa Condominal). Un usuario te hizo una pregunta sobre cómo funciona el \
sistema o cómo configurar algo.

Responde ÚNICAMENTE con información que aparezca en el MANUAL DE USUARIO que se te \
da a continuación. No inventes funciones, pantallas ni pasos que no estén en el manual.

Reglas de la respuesta:
- Responde en español, tono cercano y claro, como si le explicaras a un administrador \
de condominio sin conocimientos técnicos.
- Sé conciso: prioriza pasos numerados o viñetas cuando el manual los tenga, en vez de \
párrafos largos.
- Si la pregunta menciona una sección específica del manual, cítala por su número \
(ej. "sección 5.5") para que el usuario pueda ubicarla si abre el manual completo.
- Si la pregunta NO se puede responder con el contenido de este manual (porque es sobre \
algo que el manual no cubre, o porque en realidad parece una ACCIÓN que Sherlock podría \
ejecutar directamente -- como "dar de alta un cliente" -- en vez de una pregunta de \
"cómo funciona"), responde EXACTAMENTE con el texto: NO_ENCONTRADO
No agregues nada más en ese caso, ni expliques por qué.

MANUAL DE USUARIO COMPLETO:
{manual}
"""

        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            respuesta = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": mensaje_texto}],
            )
            texto = respuesta.content[0].text.strip()
        except Exception:
            return None

        if texto == "NO_ENCONTRADO" or not texto:
            return None

        return texto

    
    @transaction.atomic
    def procesar_mensaje(
        self,
        mensaje_texto: str,
        conversacion_id: int = None,
        intencion_sugerida: str = None,
        datos_comprobante: dict = None,
    ) -> Dict[str, Any]:
        """Procesa mensaje usando el sistema de handlers"""

        nivel_empresa = self._nivel_empresa(self.empresa)

        # Plan demo: Sherlock no está disponible en absoluto, sin importar
        # qué se le pida. Se corta aquí, antes de tocar cualquier conversación.
        if nivel_empresa == "demo":
            return self._respuesta_plan_insuficiente(
                mensaje_texto, nivel_requerido="plus"
            )

        if conversacion_id:
            conversacion = ConversacionAsistente.objects.get(
                id=conversacion_id, usuario=self.usuario
            )
            # Red de seguridad: si esta conversación quedó sin intención
            # reconocida ('otro') y ahora llega una intención sugerida (ej.
            # el usuario dio clic en un botón de opción), se "repara" la
            # conversación en vez de seguir atorada repitiendo "no entiendo".
            if conversacion.intencion in (None, "otro") and intencion_sugerida:
                nivel_requerido = NIVEL_REQUERIDO_POR_INTENCION.get(intencion_sugerida)
                if (
                    nivel_requerido
                    and NIVEL_ORDEN[nivel_empresa] < NIVEL_ORDEN[nivel_requerido]
                ):
                    return self._respuesta_plan_insuficiente(
                        mensaje_texto, nivel_requerido, intencion_sugerida
                    )
                conversacion.intencion = intencion_sugerida
                conversacion.estado = "iniciada"
                conversacion.save()
        else:
            if intencion_sugerida:
                intencion = intencion_sugerida
                confianza = 1.0
                print(f"[DEBUG] intencion_sugerida: {intencion_sugerida}")
                print(f"[DEBUG] intencion final: {intencion}")
            else:
                intencion, confianza = recognizar_intencion(mensaje_texto)

            # Bloquea aquí, antes de crear la conversación, si la intención
            # detectada requiere un nivel de membresía que la empresa no tiene.
            if confianza > 0.3:
                nivel_requerido = NIVEL_REQUERIDO_POR_INTENCION.get(intencion)
                if (
                    nivel_requerido
                    and NIVEL_ORDEN[nivel_empresa] < NIVEL_ORDEN[nivel_requerido]
                ):
                    return self._respuesta_plan_insuficiente(
                        mensaje_texto, nivel_requerido, intencion
                    )

            conversacion = ConversacionAsistente.objects.create(
                usuario=self.usuario,
                empresa=self.empresa,
                intencion=intencion if confianza > 0.3 else "otro",
                estado="iniciada",
            )
            # ← AGREGA ESTO: precargar datos del comprobante si vienen
            if datos_comprobante:
                if conversacion.intencion == "crear_solicitud_gasto":
                    conversacion.datos_recopilados.update(
                        {
                            "fecha": datos_comprobante.get("fecha"),
                            "monto": datos_comprobante.get("monto_total"),
                            "descripcion": datos_comprobante.get("descripcion"),
                            "retencion_iva": datos_comprobante.get("retencion_iva")
                            or 0,
                            "retencion_isr": datos_comprobante.get("retencion_isr")
                            or 0,
                            "rfc_proveedor": datos_comprobante.get("rfc_proveedor"),
                            "proveedor_nombre_comprobante": datos_comprobante.get(
                                "proveedor_nombre"
                            ),
                            "folio_comprobante": datos_comprobante.get("folio"),
                        }
                    )
                elif conversacion.intencion in (
                    "crear_cliente",
                    "actualizar_cliente_constancia",
                ):
                    conversacion.datos_recopilados.update(
                        {
                            k: v
                            for k, v in datos_comprobante.items()
                            if v not in (None, "")
                        }
                    )
                conversacion.save()

        MensajeAsistente.objects.create(
            conversacion=conversacion, tipo="usuario", contenido=mensaje_texto
        )

        handler = obtener_handler(
            conversacion.intencion, self.usuario, self.empresa or conversacion.empresa
        )

        if not handler:
            respuesta = self._manejar_intencion_desconocida(conversacion, mensaje_texto)
        elif conversacion.estado == "iniciada":
            respuesta = self._iniciar_conversacion(conversacion, handler, mensaje_texto)
        elif conversacion.estado == "solicitando_datos":
            respuesta = self._recopilar_datos(conversacion, handler, mensaje_texto)
        elif conversacion.estado == "validando":
            respuesta = self._procesar_handler(conversacion, handler)
        elif conversacion.estado == "completada":
            respuesta = {"estado": "completada", "mensaje": "Conversación completada"}
        else:
            respuesta = {"estado": "error", "mensaje": "Estado desconocido"}

        MensajeAsistente.objects.create(
            conversacion=conversacion,
            tipo="asistente",
            contenido=respuesta.get("mensaje", ""),
            opciones=respuesta.get("opciones", []),
        )

        respuesta["conversacion_id"] = conversacion.id
        return respuesta


    def _iniciar_conversacion(
        self, conversacion: ConversacionAsistente, handler, mensaje: str
    ) -> Dict[str, Any]:
        """Inicia una nueva conversación con el handler"""

        datos_extraidos = extraer_datos_mensaje(mensaje)
        conversacion.datos_recopilados.update(datos_extraidos)
        print(f"[DEBUG] mensaje: {mensaje!r}")
        print(f"[DEBUG] datos_extraidos: {datos_extraidos}")

        # ← AGREGA ESTO: pasar datos precargados al handler antes de obtener_campos
        handler.establecer_datos(conversacion.datos_recopilados)
        campos = handler.obtener_campos()

        # Guardar datos autocompletados por el handler (proveedor, tipo_gasto, etc.)
        conversacion.datos_recopilados.update(handler.datos)
        conversacion.save()  # ← guardar antes de calcular faltantes
        print(f"[DEBUG] datos_recopilados: {conversacion.datos_recopilados}")
        print(f"[DEBUG] campos_faltantes antes: {[c['nombre'] for c in campos]}")
        campos_faltantes = self._obtener_campos_faltantes(
            conversacion.datos_recopilados, campos
        )
        print(
            f"[DEBUG] campos_faltantes después: {[c['nombre'] for c in campos_faltantes]}"
        )

        conversacion.estado = "solicitando_datos"

        if campos_faltantes:
            siguiente_campo = campos_faltantes[0]
            conversacion.campo_actual = siguiente_campo["nombre"]
            conversacion.save()
            return self._respuesta_campo(
                siguiente_campo,
                len(campos_faltantes),
                mensaje_prefijo=handler.obtener_mensaje_bienvenida() + "\n\n",
            )

        conversacion.campo_actual = None
        conversacion.estado = "validando"
        conversacion.save()
        return self._procesar_handler(conversacion, handler)


    def _recopilar_datos(
        self, conversacion: ConversacionAsistente, handler, mensaje: str
    ) -> Dict[str, Any]:
        """Recopila datos en conversación continua, un campo a la vez"""

        campos = handler.obtener_campos()
        campo_actual = self._buscar_campo(campos, conversacion.campo_actual)
        mensaje_limpio = mensaje.strip()
        es_omitir = mensaje_limpio.lower() in ("omitir", "saltar")

        if campo_actual:
            if es_omitir:
                if campo_actual["requerido"]:
                    return self._respuesta_campo(
                        campo_actual,
                        len(
                            self._obtener_campos_faltantes(
                                conversacion.datos_recopilados, campos
                            )
                        ),
                        mensaje_prefijo="⚠️ Este dato es obligatorio y no se puede omitir.\n\n",
                    )
                # Campo opcional omitido: se marca como respondido, sin valor.
                # OJO: se guarda '' y no None -> los CharField de Django suelen
                # tener null=False (solo blank=True), así que None provoca un
                # IntegrityError (violación de NOT NULL) al crear el registro.
                conversacion.datos_recopilados[campo_actual["nombre"]] = ""

            elif campo_actual.get("tipo") == "select":
                # Validar/normalizar contra las opciones definidas (acepta el
                # código exacto que manda un botón, o el texto de la etiqueta
                # si el usuario prefirió escribirlo)
                valor = self._normalizar_valor_select(
                    mensaje_limpio, campo_actual.get("opciones") or []
                )
                if valor is None:
                    return self._respuesta_campo(
                        campo_actual,
                        len(
                            self._obtener_campos_faltantes(
                                conversacion.datos_recopilados, campos
                            )
                        ),
                        mensaje_prefijo="⚠️ Esa opción no es válida, elige una de la lista.\n\n",
                    )
                conversacion.datos_recopilados[campo_actual["nombre"]] = valor

            else:
                datos_extraidos = extraer_datos_mensaje(mensaje_limpio)
                valor = datos_extraidos.get(campo_actual["nombre"], mensaje_limpio)
                conversacion.datos_recopilados[campo_actual["nombre"]] = valor

        campos_faltantes = self._obtener_campos_faltantes(
            conversacion.datos_recopilados, campos
        )

        if campos_faltantes:
            siguiente = campos_faltantes[0]
            conversacion.campo_actual = siguiente["nombre"]
            conversacion.save()
            return self._respuesta_campo(siguiente, len(campos_faltantes))

        conversacion.campo_actual = None
        conversacion.estado = "validando"
        conversacion.save()
        return self._procesar_handler(conversacion, handler)


    def _procesar_handler(
        self, conversacion: ConversacionAsistente, handler
    ) -> Dict[str, Any]:
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
                "exito": False,
                "mensaje": f"❌ Error al procesar la solicitud: {str(e)}",
                "errores": {"general": str(e)},
            }

        if resultado.get("exito"):
            if "opciones" in resultado:
                # Hay opciones de seguimiento — no cerrar la conversación aún
                conversacion.estado = "completada"
                conversacion.fecha_finalizacion = datetime.now()
            else:
                conversacion.estado = "completada"
                conversacion.fecha_finalizacion = datetime.now()
        else:
            conversacion.errores = resultado.get("errores", {})
            conversacion.estado = "cancelada"

        conversacion.save()

        respuesta = {
            "estado": "completada" if resultado.get("exito") else "error",
            "mensaje": resultado.get("mensaje"),
            "intencion": conversacion.intencion,
            "exito": resultado.get("exito", False),
        }

        if "objeto_id" in resultado:
            respuesta["objeto_id"] = resultado["objeto_id"]

        # Permite que cualquier handler (no solo el flujo de "no entiendo")
        # ofrezca botones de acción tras completar su tarea. Ej: al buscar
        # una factura pendiente, BuscarFacturaHandler devuelve un botón
        # "Asignar pago" que arranca AsignarPagoHandler con el folio precargado.
        if "opciones" in resultado:
            respuesta["opciones"] = resultado["opciones"]

        return respuesta


    def _limite_consultas_manual_alcanzado(self) -> Optional[str]:
        """
        Revisa el contador diario de consultas al manual para esta empresa.

        Si todavía tiene cupo, incrementa el contador de inmediato (el costo
        de la llamada a la API se genera sin importar si Claude encuentra
        la respuesta o no, así que se descuenta ANTES de llamar) y devuelve
        None para indicar que puede continuar.

        Si ya se agotó su cupo del día, devuelve el mensaje a mostrar,
        listo para regresar como respuesta.
        """
    
        nivel = self._nivel_empresa(self.empresa)
        limite = LIMITE_CONSULTAS_MANUAL_POR_DIA.get(nivel)
        if limite is None:
            # Nivel sin límite definido (ej. algún plan futuro) -- no se
            # restringe. El nivel "demo" ya se corta antes, en procesar_mensaje.
            return None

        hoy = django_timezone.localdate()
        uso, _ = UsoConsultaManual.objects.get_or_create(
            empresa=self.empresa, fecha=hoy, defaults={"contador": 0}
        )

        if uso.contador >= limite:
            if nivel == "plus":
                limite_premium = LIMITE_CONSULTAS_MANUAL_POR_DIA.get("premium", limite)
                return (
                    f"📚 Ya usaste tus {limite} consultas a Sherlock de hoy con tu plan Plus. "
                    f"Con el plan Premium tienes hasta {limite_premium} consultas diarias. "
                    f"Contacta al administrador de tu sistema GESAC si necesitas más consultas a Sherlock."
                )
            return (
                f"📚 Ya usaste tus {limite} consultas a Sherlock de hoy. "
                f"Si necesitas más, contacta al administrador de tu sistema GESAC."
            )

        # Todavía tiene cupo -- se descuenta ahora, antes de llamar a la API
        UsoConsultaManual.objects.filter(pk=uso.pk).update(contador=F("contador") + 1)
        return None


    def _manejar_intencion_desconocida(
        self, conversacion: ConversacionAsistente, mensaje_texto: str
    ) -> Dict[str, Any]:
        """Maneja cuando no se reconoce la intención -- primero intenta
        responder con el manual de usuario; si no encuentra nada útil,
        cae al menú de opciones de siempre."""
        mensaje_limite = self._limite_consultas_manual_alcanzado()
        if mensaje_limite:
            return {
                "estado": "solicitando_intención",
                "mensaje": mensaje_limite,
                 "opciones": [],
                }
        
        respuesta_manual = self._responder_con_manual(mensaje_texto)

        if respuesta_manual:
            # Ya se encontró la respuesta en el manual -- se muestra sola,
            # sin el menú de opciones (no aplica, la pregunta ya se resolvió).
            return {
                "estado": "solicitando_intención",
                "mensaje": respuesta_manual,
                "opciones": [],
                "fuente": "manual",  # útil en el frontend si quieres mostrar un badge distinto
            }

        # No se encontró nada en el manual -- se arma el menú de opciones de siempre
        nivel_empresa = self._nivel_empresa(self.empresa)

        opciones = []
        for intencion, handler_class in HANDLERS_REGISTRY.items():
            if getattr(handler_class, 'oculto_en_menu', False):
                continue  # no ofrecer handlers de uso interno

            nivel_requerido = NIVEL_REQUERIDO_POR_INTENCION.get(intencion)
            if nivel_requerido and NIVEL_ORDEN[nivel_empresa] < NIVEL_ORDEN[nivel_requerido]:
                continue
            opciones.append(
                {
                    "texto": f"{handler_class.emoji} {handler_class.descripcion}",
                    "valor": f"Quiero {handler_class.descripcion.lower()}",
                    "intencion": intencion,
                }
            )

        return {
            "estado": "solicitando_intención",
            "mensaje": "❓ No entiendo bien. ¿Qué quieres hacer?",
            "opciones": opciones,
        }


    @staticmethod
    def _respuesta_campo(
        campo: Dict, campos_faltantes: int, mensaje_prefijo: str = ""
    ) -> Dict[str, Any]:
        """
        Construye la respuesta JSON estándar para pedir un campo, incluyendo
        la metadata que el frontend necesita para:
        - Mostrar un botón "Saltar" si el campo es opcional (campo_requerido=False)
        - Renderizar botones de selección si campo_tipo == 'select' (campo_opciones)
        """
        opciones = campo.get("opciones")
        return {
            "estado": "solicitando_datos",
            "mensaje": mensaje_prefijo + campo["label"],
            "campo_actual": campo["nombre"],
            "campo_tipo": campo.get("tipo", "text"),
            "campo_requerido": campo.get("requerido", False),
            "campo_opciones": [{"valor": v, "label": l} for v, l in opciones]
            if opciones
            else None,
            "campos_faltantes": campos_faltantes,
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
    def _obtener_campos_faltantes(
        datos_recopilados: Dict, campos: List[Dict]
    ) -> List[Dict]:
        """
        Obtiene los campos (requeridos Y opcionales) que aún no se le han
        preguntado al usuario. Un campo se considera "respondido" en cuanto
        existe su llave en datos_recopilados, aunque su valor sea None
        (caso de un opcional omitido).
        """
        return [c for c in campos if c["nombre"] not in datos_recopilados]


    @staticmethod
    def _buscar_campo(campos: List[Dict], nombre: Optional[str]) -> Optional[Dict]:
        """Busca la definición de un campo por su nombre"""
        if not nombre:
            return None
        for c in campos:
            if c["nombre"] == nombre:
                return c
        return None


    @staticmethod
    def obtener_handlers_disponibles() -> list:
        """Retorna todos los handlers disponibles"""
        return [
            {
                "intencion": intencion,
                "descripcion": handler_class.descripcion,
                "emoji": handler_class.emoji,
                "aliases": handler_class.intencion_aliases,
            }
            for intencion, handler_class in HANDLERS_REGISTRY.items()
        ]
