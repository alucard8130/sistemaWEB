"""Generador del calendario de rentas esperadas (con escaladores INPC / % fijo).

Reglas:
- Idempotente: volver a correrlo no duplica. Crea las partidas que faltan y
  re-calcula las PROYECTADAS cuyo monto cambió; nunca toca APROBADA, FACTURADA,
  COBRADA ni CANCELADA.
- INPC: en cada aniversario (``aplicar_desde`` + k * periodicidad) el factor es
  INPC[aniv - rezago] / INPC[aniv - rezago - periodicidad], acotado por piso/tope.
  Si falta un valor de INPC, NO se inventa: se detiene en ese aniversario y se
  reporta en ``pendientes``. Las rentas posteriores se generan al cargar el índice.
- Escalador MERCADO: no cambia el monto; se reporta en ``pendientes`` para captura manual.
- Cada ajuste se aplica sobre la renta vigente (compuesto), redondeo a centavos
  (mitad hacia arriba).
- No prorratea: el primer periodo sale completo (pendiente de definir con La Comer).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from ..models import (
    BitacoraAuditoria,
    Escalador,
    IndiceValor,
    PartidaCalendario,
    TerminoFinanciero,
)

CENTAVOS = Decimal("0.01")


def mas_meses(d: date, n: int) -> date:
    """Suma n meses al primer día del mes de ``d`` (el día se ignora)."""
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def _venc(periodo: date, dia: int) -> date:
    ultimo = calendar.monthrange(periodo.year, periodo.month)[1]
    return periodo.replace(day=min(dia, ultimo))


def _redondear(x: Decimal) -> Decimal:
    return x.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


@dataclass
class Resultado:
    termino_id: int
    creadas: int = 0
    actualizadas: int = 0
    sin_cambio: int = 0
    omitidas_no_proyectadas: int = 0
    pendientes: list[str] = field(default_factory=list)
    partidas: list[tuple[date, Decimal]] = field(default_factory=list)  # (periodo, monto) calculadas

    def __str__(self):
        return (
            f"termino {self.termino_id}: creadas={self.creadas} actualizadas={self.actualizadas} "
            f"sin_cambio={self.sin_cambio} omitidas={self.omitidas_no_proyectadas} "
            f"pendientes={len(self.pendientes)}"
        )


def _inpc(periodo: date):
    iv = IndiceValor.objects.filter(indice="INPC", periodo=periodo.replace(day=1)).first()
    return iv.valor if iv else None


def _factor_escalador(esc: Escalador, aniversario: date):
    """Devuelve (porcentaje_decimal | None, motivo_pendiente | None). Ej.: 0.0385 = +3.85 %."""
    if esc.tipo == Escalador.Tipo.FIJO_PCT:
        pct = Decimal(esc.porcentaje_fijo) / Decimal(100)
    elif esc.tipo == Escalador.Tipo.INPC:
        fin = mas_meses(aniversario, -esc.rezago_meses)
        ini = mas_meses(fin, -esc.periodicidad_meses)
        v_fin, v_ini = _inpc(fin), _inpc(ini)
        if v_fin is None or v_ini is None:
            faltan = [f"{p:%Y-%m}" for p, v in ((ini, v_ini), (fin, v_fin)) if v is None]
            return None, f"Ajuste INPC {aniversario:%Y-%m}: falta cargar INPC de {', '.join(faltan)}"
        pct = v_fin / v_ini - Decimal(1)
    else:  # MERCADO
        return None, f"Ajuste a mercado {aniversario:%Y-%m}: captura manual del nuevo monto"
    if esc.piso_pct is not None:
        pct = max(pct, Decimal(esc.piso_pct) / Decimal(100))
    if esc.tope_pct is not None:
        pct = min(pct, Decimal(esc.tope_pct) / Decimal(100))
    return pct, None


def _periodos(termino: TerminoFinanciero, hasta: date):
    paso = TerminoFinanciero.MESES[termino.frecuencia]
    inicio = termino.fecha_inicio.replace(day=1)
    limites = [hasta]
    if termino.fecha_fin:
        limites.append(termino.fecha_fin)
    if termino.version.fecha_fin:
        limites.append(termino.version.fecha_fin)
    fin = min(limites)
    if paso == 0:
        return [inicio] if inicio <= fin else []
    out, p = [], inicio
    while p <= fin:
        out.append(p)
        p = mas_meses(p, paso)
    return out


def calcular_montos(termino: TerminoFinanciero, hasta: date):
    """Calcula [(periodo, monto)] sin escribir en BD. Devuelve (lista, pendientes)."""
    periodos = _periodos(termino, hasta)
    escaladores = list(termino.escaladores.all())
    eventos = []  # (fecha, escalador)
    for esc in escaladores:
        k, f = 0, esc.aplicar_desde.replace(day=1)
        while f <= hasta:
            eventos.append((f, esc))
            k += esc.periodicidad_meses or 12
            f = mas_meses(esc.aplicar_desde, k)
    eventos.sort(key=lambda e: e[0])

    monto = Decimal(termino.monto)
    pendientes: list[str] = []
    bloqueado_desde = None
    resultado = []
    i = 0
    for periodo in periodos:
        while i < len(eventos) and eventos[i][0] <= periodo:
            fecha, esc = eventos[i]
            i += 1
            if fecha <= termino.fecha_inicio.replace(day=1):
                continue  # el monto base ya es el vigente al inicio
            pct, motivo = _factor_escalador(esc, fecha)
            if pct is None:
                pendientes.append(motivo)
                if esc.tipo == Escalador.Tipo.INPC and bloqueado_desde is None:
                    bloqueado_desde = fecha
            else:
                monto = _redondear(monto * (Decimal(1) + pct))
        if bloqueado_desde is not None and periodo >= bloqueado_desde:
            break  # no se inventa la renta posterior a un INPC faltante
        resultado.append((periodo, _redondear(monto)))
    return resultado, pendientes


@transaction.atomic
def generar_calendario(termino: TerminoFinanciero, hasta: date, usuario=None, dry_run=False) -> Resultado:
    res = Resultado(termino_id=termino.pk)
    montos, res.pendientes = calcular_montos(termino, hasta)
    res.partidas = montos
    contrato = termino.version.contrato
    existentes = {
        p.periodo: p
        for p in PartidaCalendario.objects.filter(
            termino=termino, origen=PartidaCalendario.Origen.NORMAL
        )
    }
    for periodo, monto in montos:
        p = existentes.get(periodo)
        if p is None:
            res.creadas += 1
            if not dry_run:
                PartidaCalendario.objects.create(
                    empresa=termino.empresa, contrato=contrato, termino=termino, periodo=periodo,
                    fecha_vencimiento=_venc(periodo, termino.dia_vencimiento), monto=monto,
                    creado_por=usuario,
                )
        elif p.estado != PartidaCalendario.Estado.PROYECTADA:
            res.omitidas_no_proyectadas += 1
        elif p.monto != monto:
            res.actualizadas += 1
            if not dry_run:
                p.monto = monto
                p.save(update_fields=["monto", "actualizado_en"])
        else:
            res.sin_cambio += 1
    if not dry_run and (res.creadas or res.actualizadas):
        BitacoraAuditoria.objects.create(
            empresa=termino.empresa, usuario=usuario, accion="GENERAR_CALENDARIO",
            entidad="TerminoFinanciero", entidad_id=str(termino.pk),
            valor_nuevo={"hasta": hasta.isoformat(), "creadas": res.creadas,
                         "actualizadas": res.actualizadas, "pendientes": res.pendientes},
            motivo="Generación de calendario de rentas esperadas",
        )
    return res
