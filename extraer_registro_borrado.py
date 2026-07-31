"""
Extrae el contenido COMPLETO de la fila de FacturaOtrosIngresos con
folio 'OI-F0002' y su(s) CobroOtrosIngresos relacionado(s), desde la
base RECUPERADA -- para poder reinsertarlos en la base EN VIVO.

También confirma que ya NO existen en la base EN VIVO (para verificar
que sí es el registro borrado).

Uso:
    python extraer_registro_borrado.py
"""

import psycopg2
import psycopg2.extras

# --- AJUSTA ESTAS DOS URLs (las mismas que ya usaste) ---
URL_EN_VIVO = 'postgresql://usuario:contraseña@host:puerto/base_en_vivo'
URL_RECUPERADA = 'postgresql://usuario:contraseña@host:puerto/base_recuperada'

FOLIO_BUSCADO = "OI-F00002"


def obtener_columnas(conn, tabla):
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s ORDER BY ordinal_position;
    """, (tabla,))
    cols = [row[0] for row in cur.fetchall()]
    cur.close()
    return cols


def imprimir_insert(tabla, columnas, fila):
    valores = []
    for v in fila:
        if v is None:
            valores.append("NULL")
        elif isinstance(v, str):
            escapado = v.replace("'", "''")
            valores.append(f"'{escapado}'")
        else:
            valores.append(f"'{v}'")
    cols_str = ", ".join(f'"{c}"' for c in columnas)
    vals_str = ", ".join(valores)
    print(f'INSERT INTO "{tabla}" ({cols_str}) VALUES ({vals_str});')


def main():
    conn_rec = psycopg2.connect(URL_RECUPERADA)
    conn_vivo = psycopg2.connect(URL_EN_VIVO)

    cur_rec = conn_rec.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur_vivo = conn_vivo.cursor()

    # --- 1) Buscar la factura en RECUPERADA ---
    cur_rec.execute(
        'SELECT * FROM facturacion_facturaotrosingresos WHERE folio = %s;',
        (FOLIO_BUSCADO,)
    )
    factura = cur_rec.fetchone()

    if not factura:
        print(f"❌ No se encontró la factura {FOLIO_BUSCADO} en la base RECUPERADA.")
        print("   Puede que el punto de restauración haya quedado antes de que")
        print("   se creara ese registro, o el folio sea distinto. Verifica en pgAdmin.")
        return

    print(f"✅ Factura {FOLIO_BUSCADO} encontrada en RECUPERADA (id={factura['id']}).\n")

    # --- 2) Confirmar que YA NO existe en vivo ---
    cur_vivo.execute(
        'SELECT id FROM facturacion_facturaotrosingresos WHERE folio = %s;',
        (FOLIO_BUSCADO,)
    )
    existe_en_vivo = cur_vivo.fetchone()
    if existe_en_vivo:
        print(f"⚠️  ATENCIÓN: la factura {FOLIO_BUSCADO} SÍ existe en la base EN VIVO")
        print(f"   (id={existe_en_vivo[0]}). Puede que ya la hayas recuperado, o que")
        print("   no sea la que borraste. Revisa antes de continuar.\n")
    else:
        print(f"✅ Confirmado: {FOLIO_BUSCADO} NO existe en la base EN VIVO (fue borrada).\n")

    # --- 3) Buscar el/los cobros relacionados en RECUPERADA ---
    cur_rec.execute(
        'SELECT * FROM facturacion_cobrootrosingresos WHERE factura_id = %s;',
        (factura["id"],)
    )
    cobros = cur_rec.fetchall()

    print(f"Se encontraron {len(cobros)} cobro(s) relacionado(s) a esa factura.\n")

    print("=" * 75)
    print("DATOS DE LA FACTURA (FacturaOtrosIngresos):")
    print("=" * 75)
    for k, v in factura.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 75)
    print("DATOS DEL/LOS COBRO(S) (CobroOtrosIngresos):")
    print("=" * 75)
    for cobro in cobros:
        for k, v in cobro.items():
            print(f"  {k}: {v}")
        print("-" * 40)

    print("\n" + "=" * 75)
    print("SENTENCIAS INSERT SUGERIDAS (revísalas antes de correrlas)")
    print("=" * 75)
    print("\n-- Factura --")
    cols_factura = list(factura.keys())
    imprimir_insert("facturacion_facturaotrosingresos", cols_factura, list(factura.values()))

    print("\n-- Cobro(s) --")
    for cobro in cobros:
        cols_cobro = list(cobro.keys())
        imprimir_insert("facturacion_cobrootrosingresos", cols_cobro, list(cobro.values()))

    cur_rec.close()
    cur_vivo.close()
    conn_rec.close()
    conn_vivo.close()


if __name__ == "__main__":
    main()
