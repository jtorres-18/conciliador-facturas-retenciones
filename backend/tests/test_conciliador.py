from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.conciliador import ErrorArchivo, conciliar
from app.main import app

DATOS = Path(__file__).resolve().parents[2] / "datos_prueba"
ENCABEZADO_FACTURAS = (
    "id_factura,nit_proveedor,fecha_factura,concepto,base_gravable,"
    "tarifa_iva,valor_iva,tarifa_retencion,valor_retencion,total_factura\n"
)
ENCABEZADO_CONTAB = (
    "id_factura,fecha_contabilizacion,cuenta_contable,centro_costo,"
    "valor_debito,valor_credito,estado\n"
)


@pytest.fixture(scope="module")
def resultado():
    return conciliar(
        (DATOS / "facturas.csv").read_bytes(), (DATOS / "contabilidad.csv").read_bytes()
    )


def causas(resultado, id_factura):
    """Códigos de causa por cada fila de esa factura."""
    return [
        sorted(c["codigo"] for c in d["causas"])
        for d in resultado["detalle"]
        if d["id_factura"] == id_factura
    ]


# ------------------------------ datos de ejemplo ------------------------------ #
def test_resumen_de_los_archivos_de_ejemplo(resultado):
    r = resultado["resumen"]
    assert r["total_facturas"] == 50
    assert r["ids_unicos"] == 48
    assert r["con_inconsistencia"] == 18
    assert r["correctas"] == 32
    assert r["correctas"] + r["con_inconsistencia"] == r["total_facturas"]
    assert r["contabilidad_sin_factura"] == []


@pytest.mark.parametrize("id_factura, esperado", [
    ("FAC-0002", [[]]),                               # correcta (con línea en 0 como advertencia)
    ("FAC-0006", [["IVA_INCORRECTO"]]),               # IVA 215.000 vs 190.000
    ("FAC-0018", [["IVA_INCORRECTO"]]),               # IVA 645.500 vs 655.500
    ("FAC-0009", [["TOTAL_INCORRECTO"]]),             # total sobra 50.000
    ("FAC-0023", [["TOTAL_INCORRECTO"]]),
    ("FAC-0036", [["TOTAL_INCORRECTO"]]),
    ("FAC-0007", [["SIN_CONTABILIDAD"]]),
    ("FAC-0021", [["SIN_CONTABILIDAD"]]),
    ("FAC-0034", [["SIN_CONTABILIDAD"]]),
    ("FAC-0042", [["CAMPO_VACIO", "SIN_CONTABILIDAD"]]),
    ("FAC-0013", [["CAMPO_VACIO"]]),
    ("FAC-0029", [["CAMPO_VACIO"]]),
    ("FAC-0011", [["ESTADO_PENDIENTE"]]),
    ("FAC-0027", [["ESTADO_PENDIENTE"]]),
    ("FAC-0039", [["ESTADO_PENDIENTE"]]),
    ("FAC-0004", [["DUPLICADA"], ["DUPLICADA", "VALOR_CONTABLE_DIFERENTE"]]),
    ("FAC-0015", [["DUPLICADA"], ["DUPLICADA", "VALOR_CONTABLE_DIFERENTE"]]),
])
def test_causas_por_factura(resultado, id_factura, esperado):
    assert causas(resultado, id_factura) == esperado


def test_lineas_contables_en_cero_son_advertencia_no_inconsistencia(resultado):
    d = next(x for x in resultado["detalle"] if x["id_factura"] == "FAC-0001")
    assert d["estado"] == "Correcta"
    assert [a["codigo"] for a in d["advertencias"]] == ["LINEA_CONTABLE_EN_CERO"]
    assert resultado["resumen"]["correctas_con_advertencia"] == 4  # FAC-0001, 0002, 0003, 0005


def test_el_detalle_explica_los_valores_esperados(resultado):
    d = next(x for x in resultado["detalle"] if x["id_factura"] == "FAC-0006")
    assert d["iva_esperado"] == 190000
    assert d["valor_iva"] == 215000
    assert d["total_esperado"] == d["total_factura"] == 3990000


# ------------------------------ casos sintéticos ------------------------------ #
def test_retencion_incorrecta():
    facturas = ENCABEZADO_FACTURAS + "F1,900,2026-01-01,Soporte,1000000,0.19,190000,0.04,50000,1140000\n"
    contab = ENCABEZADO_CONTAB + "F1,2026-01-02,511010,CC1,1140000,1140000,Contabilizada\n"
    r = conciliar(facturas.encode(), contab.encode())
    assert [c["codigo"] for c in r["detalle"][0]["causas"]] == ["RETENCION_INCORRECTA"]


def test_contabilidad_sin_factura():
    facturas = ENCABEZADO_FACTURAS + "F1,900,2026-01-01,Soporte,1000000,0,0,0,0,1000000\n"
    contab = (
        ENCABEZADO_CONTAB
        + "F1,2026-01-02,511010,CC1,1000000,1000000,Contabilizada\n"
        + "F9,2026-01-02,511010,CC1,5,5,Contabilizada\n"
    )
    r = conciliar(facturas.encode(), contab.encode())
    assert r["resumen"]["contabilidad_sin_factura"] == ["F9"]


def test_valor_no_numerico_y_fecha_invalida():
    facturas = ENCABEZADO_FACTURAS + "F1,900,01/02/2026,Soporte,abc,0,0,0,0,100\n"
    contab = ENCABEZADO_CONTAB + "F1,2026-01-02,511010,CC1,100,100,Contabilizada\n"
    codigos = {c["codigo"] for c in conciliar(facturas.encode(), contab.encode())["detalle"][0]["causas"]}
    assert {"VALOR_NO_NUMERICO", "FECHA_INVALIDA"} <= codigos


def test_acepta_punto_y_coma_y_latin1():
    facturas = (ENCABEZADO_FACTURAS.replace(",", ";")
                + "F1;900;2026-01-01;Capacitación;1000000;0;0;0;0;1000000\n").encode("latin-1")
    contab = (ENCABEZADO_CONTAB.replace(",", ";")
              + "F1;2026-01-02;511010;CC1;1000000;1000000;Contabilizada\n").encode()
    assert conciliar(facturas, contab)["resumen"]["correctas"] == 1


# ------------------------------ manejo de errores ------------------------------ #
def test_columna_faltante():
    malo = b"id_factura,nit_proveedor\nF1,900\n"
    with pytest.raises(ErrorArchivo, match="le faltan las columnas"):
        conciliar(malo, (DATOS / "contabilidad.csv").read_bytes())


def test_archivo_vacio_o_sin_registros():
    with pytest.raises(ErrorArchivo, match="vacío"):
        conciliar(b"   ", (DATOS / "contabilidad.csv").read_bytes())
    with pytest.raises(ErrorArchivo, match="no tiene registros"):
        conciliar(ENCABEZADO_FACTURAS.encode(), (DATOS / "contabilidad.csv").read_bytes())


# ------------------------------ API ------------------------------ #
client = TestClient(app)


def _post(facturas=("facturas.csv", None), contabilidad=("contabilidad.csv", None)):
    def archivo(par):
        nombre, contenido = par
        return (nombre, contenido if contenido is not None else (DATOS / nombre).read_bytes(), "text/csv")
    return client.post(
        "/api/conciliacion",
        files={"facturas": archivo(facturas), "contabilidad": archivo(contabilidad)},
    )


def test_api_ok():
    respuesta = _post()
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["resumen"]["total_facturas"] == 50
    assert len(cuerpo["detalle"]) == 50


def test_api_rechaza_extension_incorrecta():
    respuesta = _post(facturas=("facturas.xlsx", b"x"))
    assert respuesta.status_code == 400
    assert ".csv" in respuesta.json()["detail"]


def test_api_columna_faltante_devuelve_400():
    respuesta = _post(contabilidad=("contabilidad.csv", b"id_factura\nF1\n"))
    assert respuesta.status_code == 400
    assert "contabilidad.csv" in respuesta.json()["detail"]


def test_api_falta_un_archivo_devuelve_422():
    respuesta = client.post("/api/conciliacion", files={"facturas": ("facturas.csv", b"x", "text/csv")})
    assert respuesta.status_code == 422


def test_api_salud():
    assert client.get("/api/salud").json() == {"estado": "ok"}
