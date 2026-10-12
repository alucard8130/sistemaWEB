from datetime import date
from decimal import Decimal

from .models import (
    BitacoraAuditoria,
    ConceptoCobro,
    Escalador,
    IndiceValor,
    PartidaCalendario,
    TerminoFinanciero,
)
from .services.calendario import calcular_montos, generar_calendario
from .tests import BaseLeasing

D = Decimal


class CalendarioTests(BaseLeasing):
    def termino(self, inicio=date(2026, 1, 1), fin=date(2028, 1, 1), monto="10000", frec="MENSUAL", dia=5, folio="C1"):
        c, v = self.contrato(folio, "INGRESO", inicio, fin)
        conc, _ = ConceptoCobro.objects.get_or_create(empresa=self.emp, clave="RENTA", defaults={"nombre": "Renta"})
        t = TerminoFinanciero.objects.create(
            empresa=self.emp, version=v, concepto=conc, monto=D(monto), frecuencia=frec,
            dia_vencimiento=dia, fecha_inicio=inicio,
        )
        return t

    def esc(self, t, tipo, **kw):
        return Escalador.objects.create(empresa=self.emp, termino=t, tipo=tipo, aplicar_desde=kw.pop("desde", date(2027, 1, 1)), **kw)

    def inpc(self, **vals):
        for ym, v in vals.items():
            y, m = ym[1:].split("_")
            IndiceValor.objects.create(indice="INPC", periodo=date(int(y), int(m), 1), valor=D(v))

    def test_sin_escalador_e_idempotencia(self):
        t = self.termino(fin=date(2026, 12, 31))
        r = generar_calendario(t, date(2030, 1, 1), usuario=self.u1)
        self.assertEqual(r.creadas, 12)
        self.assertEqual(PartidaCalendario.objects.filter(termino=t).count(), 12)
        self.assertEqual(PartidaCalendario.objects.filter(termino=t).first().fecha_vencimiento, date(2026, 1, 5))
        r2 = generar_calendario(t, date(2030, 1, 1), usuario=self.u1)
        self.assertEqual((r2.creadas, r2.actualizadas, r2.sin_cambio), (0, 0, 12))

    def test_hasta_limita(self):
        t = self.termino()
        r = generar_calendario(t, date(2026, 6, 30))
        self.assertEqual(r.creadas, 6)

    def test_vencimiento_31_en_febrero(self):
        t = self.termino(dia=31, fin=date(2026, 3, 31))
        generar_calendario(t, date(2026, 3, 31))
        feb = PartidaCalendario.objects.get(termino=t, periodo=date(2026, 2, 1))
        self.assertEqual(feb.fecha_vencimiento, date(2026, 2, 28))

    def test_trimestral(self):
        t = self.termino(frec="TRIMESTRAL", fin=date(2026, 12, 31))
        montos, _ = calcular_montos(t, date(2030, 1, 1))
        self.assertEqual([p for p, _ in montos], [date(2026, 1, 1), date(2026, 4, 1), date(2026, 7, 1), date(2026, 10, 1)])

    def test_pct_fijo_compuesto(self):
        t = self.termino(fin=date(2029, 1, 1))
        self.esc(t, "FIJO_PCT", porcentaje_fijo=D("5"))
        m = dict(calcular_montos(t, date(2030, 1, 1))[0])
        self.assertEqual(m[date(2026, 12, 1)], D("10000.00"))
        self.assertEqual(m[date(2027, 1, 1)], D("10500.00"))
        self.assertEqual(m[date(2028, 1, 1)], D("11025.00"))

    def test_inpc_con_rezago(self):
        # aniversario 2027-01, rezago 1 -> INPC dic-2026 / INPC dic-2025
        self.inpc(y2025_12="100", y2026_12="104")
        t = self.termino()
        self.esc(t, "INPC", rezago_meses=1)
        m = dict(calcular_montos(t, date(2027, 12, 1))[0])
        self.assertEqual(m[date(2026, 12, 1)], D("10000.00"))
        self.assertEqual(m[date(2027, 1, 1)], D("10400.00"))

    def test_piso_y_tope(self):
        self.inpc(y2025_12="100", y2026_12="108")
        t = self.termino()
        self.esc(t, "INPC", tope_pct=D("5"))
        self.assertEqual(dict(calcular_montos(t, date(2027, 6, 1))[0])[date(2027, 1, 1)], D("10500.00"))
        IndiceValor.objects.filter(periodo=date(2026, 12, 1)).update(valor=D("101"))
        t2 = self.termino(folio="C2")  # segundo contrato
        self.esc(t2, "INPC", piso_pct=D("3"))
        self.assertEqual(dict(calcular_montos(t2, date(2027, 6, 1))[0])[date(2027, 1, 1)], D("10300.00"))

    def test_inpc_faltante_no_inventa_y_se_completa_despues(self):
        t = self.termino()
        self.esc(t, "INPC")
        r = generar_calendario(t, date(2027, 12, 1), usuario=self.u1)
        self.assertEqual(r.creadas, 12)  # solo 2026; desde 2027-01 falta el INPC
        self.assertTrue(any("falta cargar INPC" in p for p in r.pendientes))
        self.assertFalse(PartidaCalendario.objects.filter(termino=t, periodo__gte=date(2027, 1, 1)).exists())
        self.inpc(y2025_12="100", y2026_12="104")
        r2 = generar_calendario(t, date(2027, 12, 1), usuario=self.u1)
        self.assertEqual((r2.creadas, r2.pendientes), (12, []))
        self.assertEqual(PartidaCalendario.objects.get(termino=t, periodo=date(2027, 1, 1)).monto, D("10400.00"))

    def test_no_toca_partidas_no_proyectadas_pero_si_recalcula_proyectadas(self):
        t = self.termino(fin=date(2028, 1, 1))
        self.esc(t, "FIJO_PCT", porcentaje_fijo=D("5"))
        generar_calendario(t, date(2027, 12, 1), usuario=self.u1)
        ene = PartidaCalendario.objects.get(termino=t, periodo=date(2027, 1, 1))
        feb = PartidaCalendario.objects.get(termino=t, periodo=date(2027, 2, 1))
        ene.aprobar(self.u2)
        Escalador.objects.filter(termino=t).update(porcentaje_fijo=D("6"))
        r = generar_calendario(t, date(2027, 12, 1), usuario=self.u1)
        ene.refresh_from_db(); feb.refresh_from_db()
        self.assertEqual(ene.monto, D("10500.00"))  # aprobada: intacta
        self.assertEqual(feb.monto, D("10600.00"))  # proyectada: recalculada
        self.assertEqual(r.omitidas_no_proyectadas, 1)
        self.assertEqual(r.actualizadas, 11)

    def test_mercado_queda_pendiente(self):
        t = self.termino()
        self.esc(t, "MERCADO")
        montos, pend = calcular_montos(t, date(2027, 6, 1))
        self.assertEqual(dict(montos)[date(2027, 1, 1)], D("10000.00"))
        self.assertTrue(any("mercado" in p for p in pend))

    def test_vigencia_del_contrato_limita_y_dry_run(self):
        t = self.termino(fin=date(2026, 3, 31))
        r = generar_calendario(t, date(2030, 1, 1), dry_run=True)
        self.assertEqual(r.creadas, 3)
        self.assertEqual(PartidaCalendario.objects.filter(termino=t).count(), 0)
        self.assertFalse(BitacoraAuditoria.objects.filter(empresa=self.emp).exists())

    def test_bitacora_registra_y_cadena_valida(self):
        t = self.termino(fin=date(2026, 6, 30))
        generar_calendario(t, date(2030, 1, 1), usuario=self.u1)
        reg = BitacoraAuditoria.objects.get(empresa=self.emp, accion="GENERAR_CALENDARIO")
        self.assertEqual(reg.valor_nuevo["creadas"], 6)
        self.assertTrue(BitacoraAuditoria.verificar_cadena(self.emp))

    def test_comando_generar_calendario(self):
        from io import StringIO

        from django.core.management import call_command

        self.termino(fin=date(2026, 6, 30))
        out = StringIO()
        call_command("generar_calendario", empresa=self.emp.pk, contrato="C1", hasta="2030-01-01", stdout=out)
        self.assertIn("creadas=6", out.getvalue())

    def test_sembrar_demo(self):
        from io import StringIO

        from django.core.management import call_command

        from empresas.models import Empresa

        for _ in range(2):  # idempotente
            out = StringIO()
            call_command("sembrar_demo_leasing", stdout=out)
        demo = Empresa.objects.get(nombre="DEMO Arrendamientos")
        self.assertEqual(demo.segmento, "arrendamiento")
        self.assertEqual(Empresa.objects.filter(nombre="DEMO Arrendamientos").count(), 1)
        self.assertIn("partidas nuevas: 0", out.getvalue())  # 2a corrida no duplica
        self.assertTrue(PartidaCalendario.objects.filter(empresa=demo).exists())
