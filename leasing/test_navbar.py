from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from empresas.models import Empresa
from principal.models import PerfilUsuario


class NavbarSegmentoTests(TestCase):
    def render(self, segmento, perm=False, staff=False):
        emp = Empresa.objects.create(nombre=f"E {segmento}", rfc="AAA010101AA1", direccion="x", segmento=segmento)
        u = get_user_model().objects.create(username=f"u_{segmento}_{perm}_{staff}", is_staff=staff)
        PerfilUsuario.objects.update_or_create(usuario=u, defaults={"empresa": emp})
        if perm:
            u.user_permissions.add(Permission.objects.get(content_type__app_label="leasing", codename="view_contrato"))
        u = get_user_model().objects.get(pk=u.pk)  # limpia caché de permisos
        req = RequestFactory().get("/")
        req.user = u
        req.session = {}
        return render_to_string("navbar.html", {"empresa_actual": emp, "request": req, "user": u}, request=req)

    def test_arrendamiento_con_permiso(self):
        h = self.render("arrendamiento", perm=True)
        self.assertIn("Arrendamientos", h)
        self.assertIn("/leasing/contratos/", h)
        self.assertIn("global-sidebar-wrapper tema-leasing", h)
        self.assertNotIn("/admin/leasing/", h)  # catalogos del admin solo para staff
        for oculto in ("tour-facturacion", "tour-ingresos", "tour-propiedades"):
            self.assertNotIn(oculto, h)

    def test_arrendamiento_staff_ve_catalogos(self):
        self.assertIn("/admin/leasing/inmueble/", self.render("arrendamiento", perm=True, staff=True))

    def test_arrendamiento_sin_permiso_sin_menu(self):
        h = self.render("arrendamiento", staff=True)
        self.assertNotIn("/leasing/contratos/", h)
        self.assertNotIn("/admin/leasing/", h)

    def test_comercial_intacto(self):
        h = self.render("comercial")
        for visible in ("tour-facturacion", "tour-ingresos", "tour-propiedades"):
            self.assertIn(visible, h)
        self.assertNotIn("/leasing/contratos/", h)
        self.assertNotIn("global-sidebar-wrapper tema-leasing", h)

    def test_escuela_intacta(self):
        h = self.render("escuela")
        self.assertNotIn("tour-facturacion", h)
        self.assertIn("Roster de Alumnos", h)
        self.assertIn("global-sidebar-wrapper tema-campus", h)
