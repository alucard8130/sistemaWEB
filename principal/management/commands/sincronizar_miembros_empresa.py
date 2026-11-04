from django.core.management.base import BaseCommand

from principal.models import PerfilUsuario


class Command(BaseCommand):
    help = (
        "Copia plan y vencimiento del usuario con la vigencia mas larga de "
        "cada empresa a sus demas usuarios (invitados). Solo extiende."
    )

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true", help="Sin esto solo muestra que cambiaria.")

    def handle(self, *args, **options):
        aplicar = options["aplicar"]
        perfiles = (
            PerfilUsuario.objects.exclude(es_contador=True)
            .exclude(empresa__isnull=True)
            .exclude(fecha_vencimiento__isnull=True)
            .exclude(tipo_usuario__in=["demo", "gratis"])
            .order_by("empresa_id", "-fecha_vencimiento")
        )
        vistas = set()
        total = 0
        for maestro in perfiles:
            if maestro.empresa_id in vistas:
                continue
            vistas.add(maestro.empresa_id)
            miembros = (
                PerfilUsuario.objects.filter(empresa_id=maestro.empresa_id)
                .exclude(pk=maestro.pk).exclude(es_contador=True)
            )
            for m in miembros:
                if m.fecha_vencimiento and m.fecha_vencimiento >= maestro.fecha_vencimiento:
                    continue
                self.stdout.write(
                    f"{maestro.empresa.nombre}: {m.usuario.username} "
                    f"{m.tipo_usuario}/{m.fecha_vencimiento} -> {maestro.tipo_usuario}/{maestro.fecha_vencimiento}"
                )
                if aplicar:
                    m.tipo_usuario = maestro.tipo_usuario
                    m.fecha_vencimiento = maestro.fecha_vencimiento
                    m.save(update_fields=["tipo_usuario", "fecha_vencimiento"])
                total += 1
        self.stdout.write(self.style.SUCCESS(f"{total} usuario(s) {'actualizados' if aplicar else 'por actualizar (usa --aplicar)'}."))
