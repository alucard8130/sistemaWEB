from django.db import models


class Proveedor(models.Model):
    nombre = models.CharField(
        max_length=100,
    )
    rfc = models.CharField(max_length=13)
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    activo = models.BooleanField(default=True)
    empresa = models.ForeignKey(
        "empresas.Empresa", on_delete=models.CASCADE, related_name="proveedores"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    repse_numero = models.CharField(max_length=50, blank=True, null=True)
    repse_vigencia = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.nombre
