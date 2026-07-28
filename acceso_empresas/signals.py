from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import UsuarioAcceso, AccesoEmpresa
from principal.models import VisitanteAcceso  # ajusta el import real
from empresas.models import Empresa  # ajusta el import real


@receiver(post_save, sender=UsuarioAcceso)
def sincronizar_visitante_desde_usuario_acceso(sender, instance, created, **kwargs):
    """Crea (o mantiene sincronizado) el VisitanteAcceso vinculado, para que
    todo usuario del portal de Empresas Administradoras / Comité pueda
    entrar también a la app con las mismas credenciales."""
    visitante, _ = VisitanteAcceso.objects.get_or_create(
        usuario_acceso_origen=instance,
        defaults={
            "nombre": instance.nombre,
            "username": instance.email,
            "email": instance.email,
            "es_admin": True,
            "acceso_api_reporte": True,
        }
    )
    visitante.nombre = instance.nombre
    visitante.email = instance.email
    visitante.activo = instance.activo
    visitante.es_admin = True
    visitante.acceso_api_reporte = True
    visitante.password = instance.password  # mismo hash -> misma contraseña
    visitante.save()


@receiver(post_save, sender=AccesoEmpresa)
def sincronizar_empresas_al_aprobar(sender, instance, **kwargs):
    """Cada vez que se aprueba/cambia un AccesoEmpresa, actualiza la lista
    de empresas visibles del VisitanteAcceso vinculado."""
    visitante = VisitanteAcceso.objects.filter(
        usuario_acceso_origen=instance.usuario_acceso
    ).first()
    if not visitante:
        return

    empresas_aprobadas = Empresa.objects.filter(
        accesos_usuarios__usuario_acceso=instance.usuario_acceso,
        accesos_usuarios__estado="aprobado",
        accesos_usuarios__activo=True,
    ).distinct()
    visitante.empresas.set(empresas_aprobadas)


@receiver(post_delete, sender=AccesoEmpresa)
def quitar_empresa_al_eliminar_acceso(sender, instance, **kwargs):
    """Si se elimina un AccesoEmpresa, quita esa empresa de la lista del
    VisitanteAcceso vinculado (revocación de acceso)."""
    visitante = VisitanteAcceso.objects.filter(
        usuario_acceso_origen=instance.usuario_acceso
    ).first()
    if visitante:
        visitante.empresas.remove(instance.empresa)