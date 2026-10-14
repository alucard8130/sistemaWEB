from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from empresas.models import Empresa
from principal.models import PerfilUsuario

from .models import BitacoraAuditoria, Contrato, Documento, PartidaCalendario

User = get_user_model()


def usuario(nombre, empresa, todos=True, superuser=False):
    u = User.objects.create(username=nombre, is_superuser=superuser)
    PerfilUsuario.objects.update_or_create(usuario=u, defaults={"empresa": empresa})
    if todos:
        u.user_permissions.add(*Permission.objects.filter(content_type__app_label="leasing"))
    return User.objects.get(pk=u.pk)


@override_settings(MEDIA_ROOT="/tmp/leasing_tests_media")
class FrontTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("sembrar_demo_leasing", verbosity=0)
        cls.emp = Empresa.objects.get(nombre="DEMO Arrendamientos")
        cls.otra = Empresa.objects.create(nombre="Otra arr", rfc="OTR010101AA1", direccion="x", segmento="arrendamiento")
        cls.comercial = Empresa.objects.create(nombre="Plaza", rfc="PLA010101AA1", direccion="x", segmento="comercial")
        cls.ana = usuario("ana", cls.emp)          # captura / aprueba (todos los permisos)
        cls.beto = usuario("beto", cls.emp)        # segundo usuario, para segregación
        cls.ingreso = Contrato.objects.get(empresa=cls.emp, folio="DEMO-I01")

    def setUp(self):
        self.client.force_login(self.ana)

    # ---- acceso ----
    def test_anonimo_va_a_login(self):
        self.client.logout()
        r = self.client.get(reverse("leasing:inicio"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])

    def test_sin_permiso_403(self):
        sin = usuario("sin", self.emp, todos=False)
        self.client.force_login(sin)
        self.assertEqual(self.client.get(reverse("leasing:inicio")).status_code, 403)

    def test_empresa_de_otro_segmento_redirige(self):
        u = usuario("plaza", self.comercial)
        self.client.force_login(u)
        r = self.client.get(reverse("leasing:contratos"))
        self.assertEqual(r.status_code, 302)

    def test_superusuario_con_una_sola_empresa_arrendamiento(self):
        self.otra.delete()
        su = usuario("root", self.emp, todos=False, superuser=True)
        self.client.force_login(su)
        self.assertEqual(self.client.get(reverse("leasing:inicio")).status_code, 200)

    # ---- pantallas ----
    def test_pantallas_cargan_con_datos_demo(self):
        for nombre, args in (("inicio", []), ("contratos", []), ("calendario", []), ("incidencias", []),
                             ("contrato", [self.ingreso.pk])):
            r = self.client.get(reverse(f"leasing:{nombre}", args=args))
            self.assertEqual(r.status_code, 200, nombre)
        r = self.client.get(reverse("leasing:contrato", args=[self.ingreso.pk]))
        self.assertContains(r, "DEMO-I01")
        self.assertContains(r, "Ajuste por INPC")
        self.assertContains(r, "Calendario de rentas")

    def test_contratos_busqueda_y_filtros(self):
        r = self.client.get(reverse("leasing:contratos"), {"q": "DEMO-S01"})
        self.assertContains(r, "DEMO-S01")
        self.assertNotContains(r, "DEMO-I01")
        r = self.client.get(reverse("leasing:contratos"), {"rol": "EGRESO"})
        self.assertContains(r, "DEMO-M01")
        self.assertNotContains(r, "DEMO-I01")

    def test_maestro_muestra_m2_subarrendados(self):
        maestro = Contrato.objects.get(empresa=self.emp, folio="DEMO-M01")
        r = self.client.get(reverse("leasing:contrato", args=[maestro.pk]))
        self.assertContains(r, "60.00 de 120.00 m")

    # ---- aislamiento multiempresa ----
    def test_no_ve_contratos_de_otra_empresa(self):
        u = usuario("zoe", self.otra)
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("leasing:contrato", args=[self.ingreso.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("leasing:contratos")), "DEMO-I01")
        p = PartidaCalendario.objects.filter(contrato=self.ingreso).first()
        self.assertEqual(self.client.post(reverse("leasing:partida_aprobar", args=[p.pk])).status_code, 404)

    # ---- acciones ----
    def test_acciones_exigen_post(self):
        p = PartidaCalendario.objects.filter(contrato=self.ingreso).first()
        self.assertEqual(self.client.get(reverse("leasing:partida_aprobar", args=[p.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("leasing:contrato_activar", args=[self.ingreso.pk])).status_code, 405)

    def test_segregacion_de_funciones_al_aprobar(self):
        p = PartidaCalendario.objects.filter(contrato=self.ingreso, estado="PROYECTADA").first()
        p.creado_por = self.ana
        p.save(update_fields=["creado_por"])
        # quien la creó no puede aprobarla
        self.client.post(reverse("leasing:partida_aprobar", args=[p.pk]))
        p.refresh_from_db()
        self.assertEqual(p.estado, "PROYECTADA")
        # otro usuario sí
        self.client.force_login(self.beto)
        self.client.post(reverse("leasing:partida_aprobar", args=[p.pk]), {"next": "/leasing/calendario/"})
        p.refresh_from_db()
        self.assertEqual(p.estado, "APROBADA")
        self.assertEqual(p.aprobada_por, self.beto)
        self.assertTrue(BitacoraAuditoria.objects.filter(accion="APROBAR_PARTIDA", entidad_id=str(p.pk)).exists())
        self.assertTrue(BitacoraAuditoria.verificar_cadena(self.emp))

    def test_aprobar_requiere_permiso(self):
        p = PartidaCalendario.objects.filter(contrato=self.ingreso, estado="PROYECTADA").first()
        self.client.force_login(usuario("lector", self.emp, todos=False))
        # solo lectura: tiene ver, no cambiar
        u = User.objects.get(username="lector")
        u.user_permissions.add(Permission.objects.get(content_type__app_label="leasing", codename="view_contrato"))
        self.client.force_login(User.objects.get(pk=u.pk))
        self.assertEqual(self.client.post(reverse("leasing:partida_aprobar", args=[p.pk])).status_code, 403)

    def test_next_externo_no_se_sigue(self):
        p = PartidaCalendario.objects.filter(contrato=self.ingreso, estado="PROYECTADA").first()
        self.client.force_login(self.beto)
        r = self.client.post(reverse("leasing:partida_aprobar", args=[p.pk]), {"next": "https://malo.example/x"})
        self.assertEqual(r["Location"], reverse("leasing:calendario"))

    def test_activar_exige_documento_firmado(self):
        self.client.post(reverse("leasing:contrato_activar", args=[self.ingreso.pk]))
        self.ingreso.refresh_from_db()
        self.assertEqual(self.ingreso.estado, "BORRADOR")
        Documento.objects.create(
            empresa=self.emp, contrato=self.ingreso, version=self.ingreso.version_vigente,
            categoria="CONTRATO_FIRMADO", firmado=True, archivo=SimpleUploadedFile("c.pdf", b"x"),
        )
        self.client.post(reverse("leasing:contrato_activar", args=[self.ingreso.pk]))
        self.ingreso.refresh_from_db()
        self.assertEqual(self.ingreso.estado, "ACTIVO")
        self.assertTrue(BitacoraAuditoria.objects.filter(accion="ACTIVAR", entidad_id=str(self.ingreso.pk)).exists())

    def test_generar_calendario_desde_la_pantalla(self):
        PartidaCalendario.objects.filter(contrato=self.ingreso).delete()
        r = self.client.post(reverse("leasing:contrato_generar", args=[self.ingreso.pk]), {"hasta": "2026-12-31"}, follow=True)
        self.assertEqual(PartidaCalendario.objects.filter(contrato=self.ingreso).count(), 12)
        self.assertContains(r, "Calendario generado")

    def test_generar_con_fecha_invalida(self):
        r = self.client.post(reverse("leasing:contrato_generar", args=[self.ingreso.pk]), {"hasta": "no"}, follow=True)
        self.assertContains(r, "Fecha inválida")
