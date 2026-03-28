from django.core.management.base import BaseCommand
from clientes.models import Cliente
import uuid

class Command(BaseCommand):
    help = 'Asigna referencias únicas a los clientes que no la tienen'

    def handle(self, *args, **kwargs):
        clientes = Cliente.objects.filter(referencia_pago__isnull=True)
        total = 0
        for cliente in clientes:
            cliente.referencia_pago = f"CL-{uuid.uuid4().hex[:8].upper()}"
            cliente.save()
            total += 1
        self.stdout.write(self.style.SUCCESS(f'Referencias asignadas a {total} clientes.'))