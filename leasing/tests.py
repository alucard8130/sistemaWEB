"""Pruebas de reglas del segmento 'arrendamiento'.

Ejecutar con:  python manage.py test leasing
(las migraciones históricas de GESAC requieren PostgreSQL; en SQLite fallan por
una referencia entre ``facturacion`` y ``areas`` ajena a esta app).
"""
import hashlib
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from empresas.models import Empresa
from proveedores.models import Proveedor

from .models import (
    BitacoraAuditoria,
    ConceptoCobro,
    Contrato,
    ContratoUnidad,
    ContratoVersion,
    CuentaPredial,
    Documento,
    Incidencia,
    Inmueble,
    PartidaCalendario,
    RelacionMaestroSub,
    TerminoFinanciero,
    Unidad,
    normalizar_cuenta_predial,
)


class BaseLeasing(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.emp = Empresa.objects.create(
            nombre="La Comer demo", rfc="LCD010101AB1", direccion="CDMX", segmento="arrendamiento"
        )
        User = get_user_model()
        cls.u1 = User.objects.create(username="admin_contratos")
        cls.u2 = User.objects.create(username="aprobador")
        cls.inm = Inmueble.objects.create(
            empresa=cls.emp, clave="CC01", nombre="Centro Comercial 1", entidad_federativa="CDMX"
        )
        cls.local = Unidad.objects.create(empresa=cls.emp, inmueble=cls.inm, clave="L1", m2_rentables=100)

    def contrato(self, folio, rol, inicio, fin, subarr="NO", anticipo=0):
        c = Contrato.objects.create(empresa=self.emp, folio=folio, rol=rol)
        v = ContratoVersion(
            empresa=self.emp, contrato=c, numero=1, fecha_efectiva=inicio, fecha_inicio=inicio,
            fecha_fin=fin, subarriendo_permitido=subarr, anticipo_rentas_meses=anticipo,
        )
        v.full_clean()
        v.save()
        v.marcar_vigente()
        return c, v

    def relacion(self, sub, maestro, m2, consent="GENERAL"):
        return RelacionMaestroSub.objects.create(
            empresa=self.emp, sub=sub, maestro=maestro, m2_asignados=m2, tipo_consentimiento=consent
        )


class SegmentoYVersionesTests(BaseLeasing):
    def test_segmento_reconocido(self):
        self.assertTrue(self.emp.es_arrendamiento)
        self.assertFalse(self.emp.es_escuela)

    def test_inscribible(self):
        _, v10 = self.contrato("T10", "INGRESO", date(2026, 1, 1), date(2036, 1, 1))
        _, v3 = self.contrato("T3", "INGRESO", date(2026, 1, 1), date(2029, 1, 1))
        _, va = self.contrato("TA", "INGRESO", date(2026, 1, 1), date(2028, 1, 1), anticipo=48)
        self.assertTrue(v10.inscribible)
        self.assertFalse(v3.inscribible)
        self.assertTrue(va.inscribible)

    def test_fechas_invalidas(self):
        c, _ = self.contrato("T1", "INGRESO", date(2026, 1, 1), date(2029, 1, 1))
        v = ContratoVersion(
            empresa=self.emp, contrato=c, numero=9, fecha_efectiva=date(2026, 1, 1),
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2025, 1, 1),
        )
        with self.assertRaises(ValidationError):
            v.full_clean()

    def test_una_sola_version_vigente(self):
        c, _ = self.contrato("T1", "INGRESO", date(2026, 1, 1), date(2029, 1, 1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ContratoVersion.objects.create(
                empresa=self.emp, contrato=c, numero=2, es_vigente=True,
                fecha_efectiva=date(2026, 6, 1), fecha_inicio=date(2026, 1, 1), fecha_fin=date(2029, 1, 1),
            )

    def test_cuenta_predial_normalizada(self):
        self.assertEqual(normalizar_cuenta_predial("ABC-123"), "0000123")
        cp = CuentaPredial.objects.create(empresa=self.emp, inmueble=self.inm, numero="ABC-123")
        self.assertEqual(cp.numero_normalizado, "0000123")


class SubarriendoTests(BaseLeasing):
    def setUp(self):
        self.maestro, vm = self.contrato("M1", "EGRESO", date(2026, 1, 1), date(2030, 1, 1), subarr="GENERAL")
        ContratoUnidad.objects.create(empresa=self.emp, version=vm, unidad=self.local, m2_asignados=100)

    def test_subarriendo_valido(self):
        sub, _ = self.contrato("S1", "SUBARRIENDO", date(2026, 6, 1), date(2029, 6, 1))
        self.relacion(sub, self.maestro, 60)
        self.assertEqual(sub.maestro, self.maestro)

    def test_no_puede_exceder_vigencia_del_maestro(self):
        sub, _ = self.contrato("S2", "SUBARRIENDO", date(2026, 6, 1), date(2031, 6, 1))
        with self.assertRaises(ValidationError):
            self.relacion(sub, self.maestro, 10)

    def test_no_puede_exceder_m2_del_maestro(self):
        s1, _ = self.contrato("S1", "SUBARRIENDO", date(2026, 6, 1), date(2029, 6, 1))
        s3, _ = self.contrato("S3", "SUBARRIENDO", date(2026, 6, 1), date(2029, 6, 1))
        self.relacion(s1, self.maestro, 60)
        with self.assertRaises(ValidationError):
            self.relacion(s3, self.maestro, 50)

    def test_maestro_que_no_permite_subarriendo(self):
        maestro_no, _ = self.contrato("M2", "EGRESO", date(2026, 1, 1), date(2030, 1, 1), subarr="NO")
        sub, _ = self.contrato("S3", "SUBARRIENDO", date(2026, 6, 1), date(2029, 6, 1))
        with self.assertRaises(ValidationError):
            self.relacion(sub, maestro_no, 10)

    def test_consentimiento_expreso_requiere_documento(self):
        sub, _ = self.contrato("S3", "SUBARRIENDO", date(2026, 6, 1), date(2029, 6, 1))
        with self.assertRaises(ValidationError):
            self.relacion(sub, self.maestro, 10, consent="EXPRESO")

    def test_rol_incorrecto(self):
        otro, _ = self.contrato("T10", "INGRESO", date(2026, 1, 1), date(2036, 1, 1))
        with self.assertRaises(ValidationError):
            self.relacion(otro, self.maestro, 1)


@override_settings(MEDIA_ROOT="/tmp/leasing_tests_media")
class ActivacionDocumentosYPartidasTests(BaseLeasing):
    def test_activacion_requiere_documento_firmado(self):
        c, v = self.contrato("T10", "INGRESO", date(2026, 1, 1), date(2036, 1, 1))
        with self.assertRaises(ValidationError):
            c.activar()
        d = Documento.objects.create(
            empresa=self.emp, contrato=c, version=v, categoria="CONTRATO_FIRMADO", firmado=True,
            archivo=SimpleUploadedFile("contrato.pdf", b"contenido de prueba"),
        )
        self.assertEqual(d.sha256, hashlib.sha256(b"contenido de prueba").hexdigest())
        c.activar()
        c.refresh_from_db()
        self.assertEqual(c.estado, "ACTIVO")

    def _partida(self):
        c, v = self.contrato("T10", "INGRESO", date(2026, 1, 1), date(2036, 1, 1))
        conc = ConceptoCobro.objects.create(empresa=self.emp, clave="RENTA", nombre="Renta")
        t = TerminoFinanciero.objects.create(
            empresa=self.emp, version=v, concepto=conc, monto=Decimal("10000"), fecha_inicio=date(2026, 1, 1)
        )
        p = PartidaCalendario.objects.create(
            empresa=self.emp, contrato=c, termino=t, periodo=date(2026, 1, 1),
            fecha_vencimiento=date(2026, 1, 5), monto=Decimal("10000"), creado_por=self.u1,
        )
        return c, t, p

    def test_segregacion_de_funciones(self):
        _, _, p = self._partida()
        with self.assertRaises(ValidationError):
            p.aprobar(self.u1)
        p.aprobar(self.u2)
        self.assertEqual(p.estado, "APROBADA")

    def test_partida_normal_duplicada(self):
        c, t, _ = self._partida()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PartidaCalendario.objects.create(
                empresa=self.emp, contrato=c, termino=t, periodo=date(2026, 1, 1),
                fecha_vencimiento=date(2026, 1, 5), monto=1,
            )


class BitacoraYGestionTests(BaseLeasing):
    def test_cadena_y_solo_anexar(self):
        for i in range(3):
            BitacoraAuditoria.objects.create(
                empresa=self.emp, usuario=self.u1, accion="EDITAR", entidad="Contrato", entidad_id="1",
                valor_anterior={"x": i}, valor_nuevo={"x": i + 1}, motivo="prueba",
            )
        self.assertTrue(BitacoraAuditoria.verificar_cadena(self.emp))
        with self.assertRaises(RuntimeError):
            BitacoraAuditoria.objects.update(motivo="x")
        with self.assertRaises(RuntimeError):
            BitacoraAuditoria.objects.first().delete()
        BitacoraAuditoria.objects.filter(pk=BitacoraAuditoria.objects.all()[1].pk)  # lectura permitida
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("UPDATE leasing_bitacoraauditoria SET motivo='alterado' WHERE id = (SELECT id FROM leasing_bitacoraauditoria ORDER BY id OFFSET 1 LIMIT 1)")
        self.assertFalse(BitacoraAuditoria.verificar_cadena(self.emp))

    def test_incidencia_ligada_a_proveedor_de_gesac(self):
        prov = Proveedor.objects.create(empresa=self.emp, nombre="Limpieza SA", rfc="LSA010101AB1", repse_numero="R-123")
        inc = Incidencia.objects.create(
            empresa=self.emp, inmueble=self.inm, unidad=self.local, tipo="FILTRACION", naturaleza_gasto="OPEX",
            ejecutor="PROVEEDOR", proveedor=prov, descripcion="Filtración en azotea",
            costo_estimado=Decimal("50000"),
        )
        self.assertEqual(inc.proveedor.repse_numero, "R-123")
