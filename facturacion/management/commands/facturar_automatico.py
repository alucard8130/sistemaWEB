import datetime as dt
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.conf import settings
from empresas.models import Empresa
from facturacion.utils import generar_facturas_mes


class Command(BaseCommand):
    help = "Genera automáticamente la facturación mensual de cuotas para empresas que no la hayan hecho, a partir del día 3 del mes."

    def handle(self, *args, **options):
        hoy = dt.date.today()

        if hoy.day < 3:
            self.stdout.write(f"Hoy es día {hoy.day} -- todavía no toca facturación automática (a partir del día 3).")
            return

        año, mes = hoy.year, hoy.month
        resumen = []

        #empresas = Empresa.objects.all()
         # NUEVO -- solo empresas activas
        empresas = Empresa.objects.filter(estado='activa', es_premium=True)
        self.stdout.write(f"Procesando {empresas.count()} empresa(s) activa(s)...")

        for empresa in empresas:
            try:
                creadas, omitidas = generar_facturas_mes(empresa, año, mes, facturar_locales=True, facturar_areas=True)
                if creadas > 0:
                    resumen.append(f"{empresa.nombre}: {creadas} facturas generadas automáticamente, {omitidas} ya existían.")
                    self.stdout.write(self.style.SUCCESS(f"{empresa.nombre}: {creadas} facturas creadas."))
                else:
                    self.stdout.write(f"{empresa.nombre}: nada pendiente ({omitidas} ya existían).")
            except Exception as e:
                resumen.append(f"⚠️ {empresa.nombre}: ERROR -- {str(e)}")
                self.stdout.write(self.style.ERROR(f"{empresa.nombre}: error -- {str(e)}"))

        if resumen:
            admin_email = getattr(settings, 'EMAIL_HOST_USER', None)
            if admin_email:
                EmailMessage(
                    subject=f"Facturación automática ejecutada -- {hoy.strftime('%d/%m/%Y')}",
                    body="Resumen de la facturación automática de hoy:\n\n" + "\n".join(resumen),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[admin_email],
                ).send(fail_silently=True)

        self.stdout.write(self.style.SUCCESS("Facturación automática completada."))