from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from empresas.models import Empresa
from principal.models import PerfilUsuario


class NavbarSegmentoTests(TestCase):
    def render(self, segmento, staff=True):
        emp = Empresa.objects.create(nombre=f"E {segmento}", rfc="AAA010101AA1", direccion="x", segmento=segmento)
        u = get_user_model().objects.create(username=f"u_{segmento}_{staff}", is_staff=staff)
        PerfilUsuario.objects.update_or_create(usuario=u, defaults={"empresa": emp})
        u.refresh_from_db()
        req = RequestFactory().get("/")
        req.user = u
        req.session = {}
        return render_to_string("navbar.html", {"empresa_actual": emp, "request": req, "user": u}, request=req)

    def test_arrendamiento(self):
        h = self.render("arrendamiento")
        self.assertIn("Arrendamientos", h)
        self.assertIn("/admin/leasing/contrato/", h)
        for oculto in ("tour-facturacion", "tour-ingresos", "tour-propiedades"):
            self.assertNotIn(oculto, h)

    def test_arrendamiento_no_staff_sin_menu(self):
        self.assertNotIn("/admin/leasing/", self.render("arrendamiento", staff=False))

    def test_comercial_intacto(self):
        h = self.render("comercial")
        for visible in ("tour-facturacion", "tour-ingresos", "tour-propiedades"):
            self.assertIn(visible, h)
        self.assertNotIn("/admin/leasing/", h)

    def test_escuela_intacta(self):
        h = self.render("escuela")
        self.assertNotIn("tour-facturacion", h)
        self.assertIn("Roster de Alumnos", h)
