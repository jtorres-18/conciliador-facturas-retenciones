from pathlib import Path

SAMPLE_DATA_DIR = Path(__file__).resolve().parents[2] / "datos_prueba"

INVOICES_HEADER = (
    "id_factura,nit_proveedor,fecha_factura,concepto,base_gravable,"
    "tarifa_iva,valor_iva,tarifa_retencion,valor_retencion,total_factura\n"
)
ACCOUNTING_HEADER = (
    "id_factura,fecha_contabilizacion,cuenta_contable,centro_costo,"
    "valor_debito,valor_credito,estado\n"
)
