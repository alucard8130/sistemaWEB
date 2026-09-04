
import secrets
from decimal import ROUND_HALF_UP, Decimal

from django import forms
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models

from areas.models import AreaComun
from empresas.models import Empresa
from locales.models import LocalComercial


#perfil de usuario extendido
class PerfilUsuario(models.Model):
    TIPO_USUARIOS = [  # noqa: RUF012
        ('demo', 'Demo'),
        ('plus', 'Plus'),
        ('premium', 'Premium'),
        ('gratis', 'Gratis'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIOS, default='demo')
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_plus_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_premium_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    mostrar_wizard = models.BooleanField(default=False)
    ultima_visita_changelog= models.DateTimeField(null=True, blank=True)
    fecha_vencimiento = models.DateTimeField(null=True, blank=True)
      # NUEVO
    es_contador = models.BooleanField(
        default=False,
        help_text="Si está activo, este usuario solo ve el menú reducido de reportes contables al iniciar sesión."
    )
      # NUEVO
    debe_cambiar_password = models.BooleanField(
        default=False,
        help_text="Si está activo, se le fuerza a cambiar su contraseña en el próximo inicio de sesión."
    )
    empresas_contador = models.ManyToManyField(
        Empresa, blank=True, related_name='contadores',
        help_text="Empresas a las que este contador tiene acceso (solo aplica si es_contador=True)."
    )
    ha_visto_tour_inicial = models.BooleanField(
        default=False,
        help_text="Si ya vio el recorrido guiado de bienvenida al sistema."
    )
    
    def __str__(self):
       return f"{self.usuario.username} → {self.empresa.nombre if self.empresa else 'Sin empresa'}"


# Modulo de auditoria 
class AuditoriaCambio(models.Model):
    MODELOS_AUDITABLES = [  # noqa: RUF012
        ('local', 'Local Comercial'),
        ('area', 'Área Común'),
        ('factura', 'Factura'),
    ]
    modelo = models.CharField(max_length=20, choices=MODELOS_AUDITABLES)
    objeto_id = models.PositiveIntegerField()
    campo = models.CharField(max_length=100)
    valor_anterior = models.TextField(null=True, blank=True)
    valor_nuevo = models.TextField(null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.get_modelo_display()} {self.objeto_id} - {self.campo}'

# Modulo de eventos y notificaciones    
class Evento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE) 
    titulo = models.CharField(max_length=200)
    fecha = models.DateField()
    descripcion = models.TextField(blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    enviado_correo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.titulo} ({self.fecha})"    
    

# Modulo de tickets de mantenimiento
class TicketMantenimiento(models.Model):
    ESTADO_CHOICES = [  # noqa: RUF012
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('resuelto', 'Resuelto'),
    ]
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    empleado_asignado = models.ForeignKey('empleados.Empleado', on_delete=models.SET_NULL, null=True, related_name='tickets_asignados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    solucion = models.TextField(blank=True, null=True)
    fecha_solucion = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.titulo} ({self.get_estado_display()})"    

class SeguimientoTicket(models.Model):
    ticket = models.ForeignKey('TicketMantenimiento', on_delete=models.CASCADE, related_name='seguimientos')
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    comentario = models.TextField()

    def __str__(self):
        return f"Seguimiento {self.fecha} - {self.usuario}"    

# Modulo de acceso para condominos, inquilinos y prpietarios de locales comerciales 
class VisitanteAcceso(models.Model):
    nombre=models.CharField(max_length=100, blank=True,null=True, verbose_name="Nombre Completo")
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128) 
    empresas = models.ManyToManyField(Empresa)
    locales = models.ManyToManyField(LocalComercial, blank=True, verbose_name="Locales")
    areas = models.ManyToManyField(AreaComun, blank=True, verbose_name="Áreas comunes")
    acceso_api_reporte = models.BooleanField(default=False)
    email= models.EmailField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro",blank=True, null=True)
    activo= models.BooleanField(default=True, verbose_name="Activo")
    es_admin= models.BooleanField(default=False, verbose_name="Es administrador")
    membresia_tipo=models.CharField(max_length=20,choices=[('basica','Básica'),('plus','Plus'),('premium','Premium')], default='basica', verbose_name="Tipo de membresía")
    usuario_acceso_origen = models.OneToOneField(
        'acceso_empresas.UsuarioAcceso',  # ajusta 'acceso_empresas' al app_label real donde vive UsuarioAcceso
        on_delete=models.CASCADE, null=True, blank=True, related_name='visitante_vinculado'
    )

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.username  
          
class VisitanteToken(models.Model):
    visitante = models.OneToOneField('VisitanteAcceso', on_delete=models.CASCADE)
    key = models.CharField(max_length=40, unique=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_key():
        return secrets.token_hex(20)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)
  

    
# Modulo de votaciones por correo electrónico    
class TemaGeneral(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

class VotacionCorreo(models.Model):
    VOTO_CHOICES = (
        ('si', 'Sí'),
        ('no', 'No'),
        ('abstencion', 'Abstención'),
    )
    tema = models.ForeignKey(TemaGeneral, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    voto = models.CharField(max_length=20, choices=VOTO_CHOICES, null=True, blank=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_voto = models.DateTimeField(null=True, blank=True)

    def ya_voto(self):
        return self.voto is not None    
    
    
#Modulo de Avisos y recordatorios
class Aviso(models.Model):
    empresa= models.ForeignKey(Empresa, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.titulo


class CapturarEmailForm(forms.Form):
    email = forms.EmailField(label="Email del cliente", required=True)




###################### Modulo de pagos de membresía ususrios GESAC por transferencia bancaria ######################

class PagoMembresiaTransferencia(models.Model):
    PLAN_CHOICES = [  # noqa: RUF012
        ('plus', 'Plus'),
        ('premium', 'Premium'),
    ]
    ESTATUS_CHOICES = [  # noqa: RUF012
        ('pendiente', 'Pendiente de revisión'),
        ('confirmado', 'Confirmado'),
        ('rechazado', 'Rechazado'),
    ]

    perfil_usuario = models.ForeignKey(
        PerfilUsuario, on_delete=models.CASCADE, related_name='pagos_transferencia'
    )
    plan_solicitado = models.CharField(max_length=20, choices=PLAN_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    meses_cubiertos = models.PositiveIntegerField(
        default=1, help_text="Cuántos meses de membresía cubre este pago."
    )
    fecha_transferencia = models.DateField(
        help_text="Fecha en que el cliente dice haber hecho la transferencia."
    )
    referencia = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Número de referencia o folio de la transferencia, si lo tienen."
    )
    comprobante = models.FileField(upload_to='comprobantes_membresia/')
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    confirmado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pagos_membresia_confirmados'
    )
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-fecha_solicitud']  # noqa: RUF012

    def __str__(self):
        return (
            f"{self.perfil_usuario.usuario.username} — {self.get_plan_solicitado_display()} "
            f"— ${self.monto} ({self.get_estatus_display()})"
        )


class ConfiguracionMembresia(models.Model):
    """Configuración global de GESAC para el pago de membresías por
    transferencia -- se captura UNA sola vez desde el admin (no es por
    empresa, es la cuenta a la que TODOS los clientes le depositan)."""

    banco = models.CharField(max_length=100, help_text="Ej. BBVA, Santander, etc.")
    titular = models.CharField(max_length=150, help_text="A nombre de quién está la cuenta.")
    clabe = models.CharField(max_length=18, blank=True, null=True, help_text="CLABE interbancaria (18 dígitos).")
    numero_cuenta = models.CharField(max_length=30, blank=True, null=True, help_text="Número de cuenta, si aplica además de la CLABE.")
    precio_plus = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio mensual fijo del plan Plus.")
    precio_premium = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio mensual fijo del plan Premium.")

    class Meta:
        verbose_name = "Configuración de Membresía"
        verbose_name_plural = "Configuración de Membresía"

    def __str__(self):
        return f"Cuenta para pagos de membresía — {self.banco}"

    IVA_TASA = Decimal("0.16")

    @property
    def precio_plus_con_iva(self):
        return (self.precio_plus * (1 + self.IVA_TASA)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def precio_premium_con_iva(self):
        return (self.precio_premium * (1 + self.IVA_TASA)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    @classmethod
    def obtener(cls):
        """Regresa la configuración activa -- siempre debe existir un
        solo registro. Si por alguna razón hay más de uno, usa el más
        reciente en vez de tronar."""
        return cls.objects.order_by('-id').first()    