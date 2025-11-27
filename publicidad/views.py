from django.shortcuts import render
from .models import Anuncio
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import AnuncioSerializer
from django.core.mail import send_mail

def anuncios_publicos(request):
    anuncios = Anuncio.objects.filter(activo=True).order_by('-fecha_publicacion')
    return render(request, 'publicidad/lista_anuncios.html', {'anuncios': anuncios})

@api_view(['GET'])
def anuncios_api(request):
    anuncios = Anuncio.objects.filter(activo=True).order_by('-fecha_publicacion')
    serializer = AnuncioSerializer(anuncios, many=True)
    return Response(serializer.data)



@api_view(['POST'])
def solicitud_publicidad_api(request):
    data = request.data
    try:
        asunto = f"Nueva solicitud de publicidad: {data.get('nombre_negocio')}"
        mensaje = f"""
        Ha recibido una nueva solicitud de información para publicidad desde la App.

        Detalles de la solicitud:
        --------------------------------------------------
        Nombre del Negocio: {data.get('nombre_negocio')}
        Persona de Contacto: {data.get('nombre_responsable')}
        Teléfono: {data.get('telefono')}
        Correo Electrónico: {data.get('email')}
        --------------------------------------------------
        
        Motivo o Mensaje:
        {data.get('motivo')}
        """
        
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=None,  # Usará el DEFAULT_FROM_EMAIL de tu settings
            recipient_list=['publicidad@gesacadmin.com'], # Tu correo
            fail_silently=False,
        )
        
        return Response({"ok": True, "message": "Correo enviado."})
    except Exception as e:
        return Response({"ok": False, "error": str(e)}, status=500)
