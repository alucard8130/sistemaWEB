from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from clientes.models import Cliente
from .models import ConversacionAsistente
from .serializers import ConversacionSerializer, MensajeSerializer
from .services import AsistenteService
import anthropic
import base64
import json

@method_decorator(xframe_options_exempt, name="dispatch")
class ChatView(TemplateView):
    template_name = "asistente_premium/chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Necesario para que el chat pueda iniciar el checkout de Stripe
        # directamente (mismo mecanismo que ya usas en pantalla_inicio.html)
        context["stripe_public_key"] = settings.STRIPE_PUBLIC_KEY

        # Nivel de membresía de la empresa, para que el menú de opciones en
        # el frontend solo muestre lo que el plan actual permite (misma
        # lógica que ya usa AsistenteService para filtrar en el backend).
        empresa = None
        if self.request.user.is_authenticated:
            try:
                empresa = self.request.user.perfilusuario.empresa
            except Exception:
                empresa = None
        context["nivel_empresa"] = AsistenteService._nivel_empresa(empresa)

        return context


class ConversacionAsistenteViewSet(viewsets.ModelViewSet):
    """ViewSet para manejar conversaciones del asistente"""

    serializer_class = ConversacionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return ConversacionAsistente.objects.none()
        return ConversacionAsistente.objects.filter(usuario=self.request.user)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def enviar_mensaje(self, request):
        """
        Envía un mensaje usando la empresa del usuario.

        NOTA: ya no se bloquea aquí por nivel de membresía (antes se exigía
        empresa.es_premium con un 403). Sherlock ahora está disponible para
        cualquier empresa autenticada, y es el propio AsistenteService quien
        decide, según el nivel (demo/plus/premium), si puede ayudar con lo
        que se le pide o si debe explicar que esa función requiere un plan
        superior. Esto permite que Sherlock converse con empresas demo/plus
        en vez de que ni siquiera puedan llegar a intentarlo.
        """
        try:
            if not request.user.is_authenticated:
                return Response(
                    {"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED
                )

            try:
                empresa = request.user.perfilusuario.empresa
            except Exception as e:
                return Response(
                    {"error": f"Usuario sin empresa asignada: {str(e)}"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            mensaje_texto = request.data.get("mensaje", "").strip()
            conversacion_id = request.data.get("conversacion_id")
            intencion_sugerida = request.data.get("intencion")
            datos_comprobante = request.data.get("datos_comprobante")  # ← nuevo

            if not mensaje_texto:
                return Response(
                    {"error": "El mensaje es requerido"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            asistente = AsistenteService(request.user, empresa)
            respuesta = asistente.procesar_mensaje(
                mensaje_texto,
                conversacion_id,
                intencion_sugerida,
                datos_comprobante=datos_comprobante,
            )

            return Response(respuesta, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def obtener_mensajes(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({"error": "No autenticado"}, status=401)

        conversacion = self.get_object()
        mensajes = conversacion.mensajes_historial.all()
        serializer = MensajeSerializer(mensajes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({"error": "No autenticado"}, status=401)

        conversacion = self.get_object()
        conversacion.estado = "cancelada"
        conversacion.save()
        return Response({"estado": "cancelada"})

    # procesar comprobante facturas, notas de venta pdf o imagenes
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def procesar_comprobante(self, request):
        """Recibe un archivo PDF/imagen, extrae datos con Claude y los devuelve"""
        
        if not request.user.is_authenticated:
            return Response({"error": "No autenticado"}, status=401)

        archivo = request.FILES.get("comprobante")
        if not archivo:
            return Response({"error": "No se recibió archivo"}, status=400)

        # Leer y codificar en base64
        contenido = archivo.read()
        contenido_b64 = base64.standard_b64encode(contenido).decode("utf-8")

        # Detectar tipo
        nombre = archivo.name.lower()
        if nombre.endswith(".pdf"):
            media_type = "application/pdf"
        elif nombre.endswith(".png"):
            media_type = "image/png"
        elif nombre.endswith(".jpg") or nombre.endswith(".jpeg"):
            media_type = "image/jpeg"
        else:
            return Response(
                {"error": "Formato no soportado. Usa PDF, PNG o JPG"}, status=400
            )

        try:
            from django.conf import settings

            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            if media_type == "application/pdf":
                content = [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": contenido_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Extrae los siguientes datos de esta factura o comprobante fiscal mexicano y responde SOLO en JSON válido sin markdown:
                        {
                        "proveedor_nombre": "nombre del emisor/proveedor",
                        "rfc_proveedor": "RFC del emisor",
                        "fecha": "YYYY-MM-DD",
                        "monto_total": 0.00,
                        "subtotal": 0.00,
                        "iva": 0.00,
                        "retencion_iva": 0.00,
                        "retencion_isr": 0.00,
                        "descripcion": "descripción del concepto principal",
                        "folio": "folio COMPLETO tal como aparece en el documento incluyendo letras y números, ejemplo: H297, A-001, F-2026-045"
                        }
                        Si no encuentras algún dato pon null.""",
                    },
                ]
            else:
                content = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": contenido_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Extrae los siguientes datos de esta factura o comprobante fiscal mexicano y responde SOLO en JSON válido sin markdown:
                    {
                    "proveedor_nombre": "nombre del emisor/proveedor",
                    "rfc_proveedor": "RFC del emisor",
                    "fecha": "YYYY-MM-DD",
                    "monto_total": 0.00,
                    "subtotal": 0.00,
                    "iva": 0.00,
                    "retencion_iva": 0.00,
                    "retencion_isr": 0.00,
                    "descripcion": "descripción del concepto principal",
                    "folio": "folio COMPLETO tal como aparece en el documento incluyendo letras y números, ejemplo: H297, A-001, F-2026-045"
                    }
                    Si no encuentras algún dato pon null.""",
                    },
                ]

            respuesta = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1000,
                messages=[{"role": "user", "content": content}],
            )

            import json

            texto = respuesta.content[0].text.strip()
            # Limpiar posibles backticks
            texto = texto.replace("```json", "").replace("```", "").strip()
            datos = json.loads(texto)

            return Response({"exito": True, "datos": datos})

        except Exception as e:
            return Response({"exito": False, "error": str(e)}, status=500)



@api_view(['POST'])
def procesar_constancia_fiscal(request):
    """Recibe la Constancia de Situación Fiscal (PDF/imagen), extrae los
    datos con Claude, y determina si corresponde crear un cliente nuevo o
    completar uno existente (buscado por RFC)."""
    
    if not request.user.is_authenticated:
        return Response({"error": "No autenticado"}, status=401)

    perfil = getattr(request.user, 'perfilusuario', None)
    empresa = perfil.empresa if perfil else None
    if not empresa:
        return Response({"error": "No tienes una empresa asignada."}, status=400)

    archivo = request.FILES.get("constancia")
    if not archivo:
        return Response({"error": "No se recibió archivo"}, status=400)

    contenido = archivo.read()
    contenido_b64 = base64.standard_b64encode(contenido).decode("utf-8")

    nombre_archivo = archivo.name.lower()
    if nombre_archivo.endswith(".pdf"):
        media_type = "application/pdf"
        tipo_bloque = "document"
    elif nombre_archivo.endswith(".png"):
        media_type = "image/png"
        tipo_bloque = "image"
    elif nombre_archivo.endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
        tipo_bloque = "image"
    else:
        return Response({"error": "Formato no soportado. Usa PDF, PNG o JPG"}, status=400)

    prompt_extraccion = """Analiza esta Constancia de Situación Fiscal (CSF) emitida por el SAT (México)
y extrae los siguientes datos. Responde SOLO en JSON válido, sin markdown:

{
  "tipo_persona": "Fisica" o "Moral",
  "rfc": "RFC completo",
  "nombre_razon_social": "nombre completo o razón social",
  "regimen_fiscal_codigo": "código de 3 dígitos del régimen fiscal principal/vigente (el que no tenga fecha de baja, o el más reciente si hay varios)",
  "codigo_postal": "código postal del domicilio fiscal",
  "direccion": "domicilio fiscal completo concatenado en una sola línea: tipo y nombre de vialidad, número exterior/interior, colonia, municipio/alcaldía, entidad federativa"
}

Si algún dato no aparece en el documento, pon null. No inventes datos."""

    try:
        from django.conf import settings
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        if tipo_bloque == "document":
            bloque_archivo = {
                "type": "document",
                "source": {"type": "base64", "media_type": media_type, "data": contenido_b64},
            }
        else:
            bloque_archivo = {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": contenido_b64},
            }

        respuesta = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": [bloque_archivo, {"type": "text", "text": prompt_extraccion}],
            }],
        )

        texto = respuesta.content[0].text.strip()
        texto = texto.replace("```json", "").replace("```", "").strip()
        datos_extraidos = json.loads(texto)

    except Exception as e:
        return Response({"exito": False, "error": str(e)}, status=500)

    rfc = (datos_extraidos.get('rfc') or '').strip().upper()
    if not rfc:
        return Response({
            "exito": False,
            "error": "No se pudo leer el RFC en el documento. Revisa que sea legible e inténtalo de nuevo."
        })

    tipo_contribuyente = None
    if datos_extraidos.get('tipo_persona') in ('Fisica', 'Moral'):
        tipo_contribuyente = datos_extraidos.get('tipo_persona')

    datos_normalizados = {
        'nombre': datos_extraidos.get('nombre_razon_social'),
        'rfc': rfc,
        'tipo_contribuyente': tipo_contribuyente,
        'regimen_fiscal': datos_extraidos.get('regimen_fiscal_codigo'),
        'codigo_postal': datos_extraidos.get('codigo_postal'),
        'direccion_domicilio': datos_extraidos.get('direccion'),
    }

    cliente_existente = Cliente.objects.filter(empresa=empresa, rfc=rfc).first()

    if cliente_existente:
        campos_a_actualizar = {}
        for campo, valor_nuevo in datos_normalizados.items():
            if campo == 'rfc' or not valor_nuevo:
                continue
            valor_actual = getattr(cliente_existente, campo, None)
            if valor_actual != valor_nuevo:
                campos_a_actualizar[campo] = {
                    'anterior': valor_actual or '(vacío)',
                    'nuevo': valor_nuevo,
                }

        return Response({
            "exito": True,
            "modo": "actualizar",
            "cliente_id": cliente_existente.id,
            "cliente_nombre": cliente_existente.nombre,
            "datos": datos_normalizados,
            "campos_a_actualizar": campos_a_actualizar,
        })
    else:
        return Response({
            "exito": True,
            "modo": "crear",
            "datos": datos_normalizados,
        })     