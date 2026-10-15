"""Reglas de negocio de la conciliación de facturas y retenciones.

Este módulo no conoce FastAPI: recibe los bytes de dos CSV y devuelve un
diccionario con el resumen y el detalle, de modo que se pueda probar solo.
"""
import csv
import io
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

# Diferencia máxima (en pesos) que se tolera por redondeo.
TOLERANCIA = Decimal("1")

COLUMNAS_FACTURAS = [
    "id_factura", "nit_proveedor", "fecha_factura", "concepto", "base_gravable",
    "tarifa_iva", "valor_iva", "tarifa_retencion", "valor_retencion", "total_factura",
]
COLUMNAS_CONTABILIDAD = [
    "id_factura", "fecha_contabilizacion", "cuenta_contable", "centro_costo",
    "valor_debito", "valor_credito", "estado",
]
ESTADO_CONTABILIZADO = "contabilizada"

# Código de cada causa -> descripción corta (se usa en el resumen).
CAUSAS = {
    "CAMPO_VACIO": "Campo obligatorio vacío",
    "VALOR_NO_NUMERICO": "Valor no numérico",
    "FECHA_INVALIDA": "Fecha inválida",
    "DUPLICADA": "Factura duplicada",
    "IVA_INCORRECTO": "IVA diferente a base × tarifa",
    "RETENCION_INCORRECTA": "Retención diferente a base × tarifa",
    "TOTAL_INCORRECTO": "Total diferente a base + IVA − retención",
    "SIN_CONTABILIDAD": "Sin registro contable",
    "ESTADO_PENDIENTE": "Contabilización pendiente",
    "VALOR_CONTABLE_DIFERENTE": "Valor contable diferente al total",
    "DESCUADRE_CONTABLE": "Débito diferente al crédito",
    "CONTABILIDAD_DUPLICADA": "Varios registros contables con valor",
}
ADVERTENCIAS = {
    "LINEA_CONTABLE_EN_CERO": "Línea contable con valor 0",
}


class ErrorArchivo(Exception):
    """Archivo ilegible o con estructura inválida (se responde como HTTP 400)."""


# --------------------------------------------------------------------------- #
# Lectura de archivos
# --------------------------------------------------------------------------- #
def leer_csv(contenido: bytes, nombre: str, columnas_requeridas: list[str]) -> list[dict]:
    """Lee un CSV y devuelve sus filas como dicts, con la clave `_fila` (línea del archivo)."""
    if not contenido.strip():
        raise ErrorArchivo(f"El archivo '{nombre}' está vacío.")
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1")

    # Excel en español suele exportar con ';' en lugar de ','.
    primera_linea = texto.splitlines()[0]
    delimitador = ";" if primera_linea.count(";") > primera_linea.count(",") else ","

    lector = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    encabezados = [(h or "").strip().lower() for h in (lector.fieldnames or [])]
    faltantes = [c for c in columnas_requeridas if c not in encabezados]
    if faltantes:
        raise ErrorArchivo(
            f"Al archivo '{nombre}' le faltan las columnas: {', '.join(faltantes)}."
        )

    filas = []
    for fila in lector:
        limpia = {(k or "").strip().lower(): (v or "").strip() for k, v in fila.items() if k}
        if not any(limpia.values()):
            continue  # fila totalmente en blanco
        limpia["_fila"] = lector.line_num
        filas.append(limpia)
    if not filas:
        raise ErrorArchivo(f"El archivo '{nombre}' no tiene registros.")
    return filas


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def _causa(codigo: str, mensaje: str) -> dict:
    return {"codigo": codigo, "mensaje": mensaje}


def _numero(fila: dict, campo: str, causas: list) -> Decimal | None:
    """Convierte un campo a Decimal. Devuelve None si está vacío o no es numérico."""
    texto = fila.get(campo, "")
    if not texto:
        return None  # el vacío se reporta aparte como CAMPO_VACIO
    try:
        return Decimal(texto)
    except InvalidOperation:
        causas.append(_causa("VALOR_NO_NUMERICO", f"'{campo}' no es numérico: '{texto}'"))
        return None


def _distinto(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) > TOLERANCIA


def _pesos(valor: Decimal) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def _numero_o_cero(texto: str) -> Decimal:
    try:
        return Decimal(texto) if texto else Decimal(0)
    except InvalidOperation:
        return Decimal(0)


# --------------------------------------------------------------------------- #
# Contabilidad: se agrupa por factura
# --------------------------------------------------------------------------- #
def _indexar_contabilidad(filas: list[dict]) -> dict[str, dict]:
    indice: dict[str, dict] = defaultdict(lambda: {
        "debito": Decimal(0), "credito": Decimal(0), "estados": set(),
        "lineas_con_valor": 0, "lineas_en_cero": 0,
    })
    for fila in filas:
        datos = indice[fila.get("id_factura", "")]
        debito = _numero_o_cero(fila.get("valor_debito", ""))
        credito = _numero_o_cero(fila.get("valor_credito", ""))
        datos["debito"] += debito
        datos["credito"] += credito
        datos["estados"].add(fila.get("estado", ""))
        if debito == 0 and credito == 0:
            datos["lineas_en_cero"] += 1
        else:
            datos["lineas_con_valor"] += 1
    return indice


# --------------------------------------------------------------------------- #
# Evaluación de una factura
# --------------------------------------------------------------------------- #
def _evaluar(fila: dict, filas_por_id: dict[str, list[int]], contabilidad: dict[str, dict]) -> dict:
    causas: list[dict] = []
    advertencias: list[dict] = []
    id_factura = fila["id_factura"]

    # Campos obligatorios
    vacios = [c for c in COLUMNAS_FACTURAS if not fila.get(c)]
    if vacios:
        causas.append(_causa("CAMPO_VACIO", f"Campos vacíos: {', '.join(vacios)}"))

    # Fecha
    fecha = fila.get("fecha_factura", "")
    if fecha:
        try:
            date.fromisoformat(fecha)
        except ValueError:
            causas.append(_causa("FECHA_INVALIDA", f"'fecha_factura' no tiene formato AAAA-MM-DD: '{fecha}'"))

    # Duplicados
    if id_factura and len(filas_por_id[id_factura]) > 1:
        otras = [str(n) for n in filas_por_id[id_factura] if n != fila["_fila"]]
        causas.append(_causa(
            "DUPLICADA", f"{id_factura} aparece {len(filas_por_id[id_factura])} veces "
                         f"(también en la fila {', '.join(otras)})"
        ))

    # Cálculos tributarios
    base = _numero(fila, "base_gravable", causas)
    tarifa_iva = _numero(fila, "tarifa_iva", causas)
    valor_iva = _numero(fila, "valor_iva", causas)
    tarifa_ret = _numero(fila, "tarifa_retencion", causas)
    valor_ret = _numero(fila, "valor_retencion", causas)
    total = _numero(fila, "total_factura", causas)

    iva_esperado = total_esperado = None
    if base is not None and tarifa_iva is not None:
        iva_esperado = base * tarifa_iva
        if valor_iva is not None and _distinto(iva_esperado, valor_iva):
            causas.append(_causa(
                "IVA_INCORRECTO",
                f"IVA esperado {_pesos(iva_esperado)} ({_pesos(base)} × {tarifa_iva}) "
                f"pero la factura trae {_pesos(valor_iva)}"
            ))
    if base is not None and tarifa_ret is not None and valor_ret is not None:
        ret_esperada = base * tarifa_ret
        if _distinto(ret_esperada, valor_ret):
            causas.append(_causa(
                "RETENCION_INCORRECTA",
                f"Retención esperada {_pesos(ret_esperada)} pero la factura trae {_pesos(valor_ret)}"
            ))
    # El total se valida con el IVA esperado, para que un error de IVA no se reporte dos veces.
    if iva_esperado is not None and valor_ret is not None:
        total_esperado = base + iva_esperado - valor_ret
        if total is not None and _distinto(total_esperado, total):
            causas.append(_causa(
                "TOTAL_INCORRECTO",
                f"Total esperado {_pesos(total_esperado)} (base + IVA − retención) "
                f"pero la factura trae {_pesos(total)}; diferencia {_pesos(total - total_esperado)}"
            ))

    # Cruce con contabilidad
    contab = contabilidad.get(id_factura) if id_factura else None
    valor_contabilizado = estado_contable = None
    if contab is None:
        causas.append(_causa("SIN_CONTABILIDAD", "No existe ningún registro contable para esta factura"))
    else:
        valor_contabilizado = contab["debito"]
        estado_contable = ", ".join(sorted(e or "(vacío)" for e in contab["estados"]))
        pendientes = [e for e in contab["estados"] if e.casefold() != ESTADO_CONTABILIZADO]
        if pendientes:
            causas.append(_causa("ESTADO_PENDIENTE", f"Estado contable: {', '.join(pendientes)}"))
        if _distinto(contab["debito"], contab["credito"]):
            causas.append(_causa(
                "DESCUADRE_CONTABLE",
                f"Débito {_pesos(contab['debito'])} ≠ crédito {_pesos(contab['credito'])}"
            ))
        if contab["lineas_con_valor"] > 1:
            causas.append(_causa(
                "CONTABILIDAD_DUPLICADA", f"{contab['lineas_con_valor']} líneas contables con valor"
            ))
        if total is not None and _distinto(contab["debito"], total):
            causas.append(_causa(
                "VALOR_CONTABLE_DIFERENTE",
                f"Contabilizado {_pesos(contab['debito'])} pero la factura dice {_pesos(total)}"
            ))
        if contab["lineas_en_cero"]:
            advertencias.append(_causa(
                "LINEA_CONTABLE_EN_CERO",
                f"{contab['lineas_en_cero']} línea(s) contable(s) con débito y crédito en 0 (ignoradas en el cálculo)"
            ))

    def monto(valor):
        return None if valor is None else float(valor)

    return {
        "fila": fila["_fila"],
        "id_factura": id_factura,
        "nit_proveedor": fila.get("nit_proveedor", ""),
        "fecha_factura": fecha,
        "concepto": fila.get("concepto", ""),
        "base_gravable": monto(base),
        "valor_iva": monto(valor_iva),
        "iva_esperado": monto(iva_esperado),
        "valor_retencion": monto(valor_ret),
        "total_factura": monto(total),
        "total_esperado": monto(total_esperado),
        "valor_contabilizado": monto(valor_contabilizado),
        "estado_contable": estado_contable,
        "estado": "Con inconsistencia" if causas else "Correcta",
        "causas": causas,
        "advertencias": advertencias,
    }


# --------------------------------------------------------------------------- #
# Punto de entrada
# --------------------------------------------------------------------------- #
def conciliar(facturas_csv: bytes, contabilidad_csv: bytes) -> dict:
    facturas = leer_csv(facturas_csv, "facturas.csv", COLUMNAS_FACTURAS)
    asientos = leer_csv(contabilidad_csv, "contabilidad.csv", COLUMNAS_CONTABILIDAD)

    filas_por_id: dict[str, list[int]] = defaultdict(list)
    for f in facturas:
        filas_por_id[f.get("id_factura", "")].append(f["_fila"])
    contabilidad = _indexar_contabilidad(asientos)

    detalle = [_evaluar(f, filas_por_id, contabilidad) for f in facturas]

    por_causa = Counter(c["codigo"] for d in detalle for c in d["causas"])
    por_advertencia = Counter(a["codigo"] for d in detalle for a in d["advertencias"])
    ids_facturas = set(filas_por_id)
    inconsistentes = sum(1 for d in detalle if d["estado"] != "Correcta")

    resumen = {
        "total_facturas": len(detalle),
        "ids_unicos": len([i for i in ids_facturas if i]),
        "correctas": len(detalle) - inconsistentes,
        "con_inconsistencia": inconsistentes,
        "correctas_con_advertencia": sum(
            1 for d in detalle if d["estado"] == "Correcta" and d["advertencias"]
        ),
        "por_causa": [
            {"codigo": cod, "descripcion": CAUSAS[cod], "cantidad": n}
            for cod, n in por_causa.most_common()
        ],
        "por_advertencia": [
            {"codigo": cod, "descripcion": ADVERTENCIAS[cod], "cantidad": n}
            for cod, n in por_advertencia.most_common()
        ],
        "registros_contables": len(asientos),
        "contabilidad_sin_factura": sorted(i for i in contabilidad if i not in ids_facturas),
    }
    return {"resumen": resumen, "detalle": detalle}
