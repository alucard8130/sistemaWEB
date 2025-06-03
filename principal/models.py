
from django.contrib.auth.models import User
from django.db import models
from empresas.models import Empresa

# Create your models here.
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
       return f"{self.usuario.username} → {self.empresa.nombre if self.empresa else 'Sin empresa'}"