from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import ConversacionAsistente
from .serializers import ConversacionSerializer, MensajeSerializer
from .services import AsistenteService


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
        import anthropic
        import base64

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
