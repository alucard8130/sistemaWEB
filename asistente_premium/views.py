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


@method_decorator(xframe_options_exempt, name='dispatch')
class ChatView(TemplateView):
    template_name = 'asistente_premium/chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Necesario para que el chat pueda iniciar el checkout de Stripe
        # directamente (mismo mecanismo que ya usas en pantalla_inicio.html)
        context['stripe_public_key'] = settings.STRIPE_PUBLIC_KEY

        # Nivel de membresía de la empresa, para que el menú de opciones en
        # el frontend solo muestre lo que el plan actual permite (misma
        # lógica que ya usa AsistenteService para filtrar en el backend).
        empresa = None
        if self.request.user.is_authenticated:
            try:
                empresa = self.request.user.perfilusuario.empresa
            except Exception:
                empresa = None
        context['nivel_empresa'] = AsistenteService._nivel_empresa(empresa)

        return context


class ConversacionAsistenteViewSet(viewsets.ModelViewSet):
    """ViewSet para manejar conversaciones del asistente"""
    serializer_class = ConversacionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return ConversacionAsistente.objects.none()
        return ConversacionAsistente.objects.filter(usuario=self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
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
                    {'error': 'No autenticado'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            try:
                empresa = request.user.perfilusuario.empresa
            except Exception as e:
                return Response(
                    {'error': f'Usuario sin empresa asignada: {str(e)}'},
                    status=status.HTTP_403_FORBIDDEN
                )

            mensaje_texto = request.data.get('mensaje', '').strip()
            conversacion_id = request.data.get('conversacion_id')
            intencion_sugerida = request.data.get('intencion')

            if not mensaje_texto:
                return Response(
                    {'error': 'El mensaje es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            asistente = AsistenteService(request.user, empresa)
            respuesta = asistente.procesar_mensaje(
                mensaje_texto,
                conversacion_id,
                intencion_sugerida
            )

            return Response(respuesta, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def obtener_mensajes(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'No autenticado'}, status=401)

        conversacion = self.get_object()
        mensajes = conversacion.mensajes_historial.all()
        serializer = MensajeSerializer(mensajes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'No autenticado'}, status=401)

        conversacion = self.get_object()
        conversacion.estado = 'cancelada'
        conversacion.save()
        return Response({'estado': 'cancelada'})