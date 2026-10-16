from fastapi.testclient import TestClient

from app.main import app
from tests.sample_data import SAMPLE_DATA_DIR

client = TestClient(app)
ENDPOINT = "/api/reconciliations"


def upload(file_name: str, content: bytes | None = None) -> tuple[str, bytes, str]:
    if content is None:
        content = (SAMPLE_DATA_DIR / file_name).read_bytes()
    return file_name, content, "text/csv"


def post_files(invoices=None, accounting=None):
    return client.post(
        ENDPOINT,
        files={
            "invoices": invoices or upload("facturas.csv"),
            "accounting": accounting or upload("contabilidad.csv"),
        },
    )


def test_returns_summary_and_details():
    response = post_files()
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["totalInvoices"] == 50
    assert len(body["details"]) == 50


def test_details_explain_expected_values():
    details = post_files().json()["details"]
    invoice = next(d for d in details if d["invoiceId"] == "FAC-0006")
    assert invoice["status"] == "Con inconsistencia"
    assert invoice["expectedVat"] == 190000
    assert invoice["vatAmount"] == 215000
    assert invoice["expectedTotal"] == 4015000
    assert invoice["totalAmount"] == invoice["totalWithRecalculatedVat"] == 3990000
    assert invoice["errors"][0]["description"] == "IVA diferente a base × tarifa"


def test_rejects_wrong_extension():
    response = post_files(invoices=upload("facturas.xlsx", b"x"))
    assert response.status_code == 400
    assert ".csv" in response.json()["detail"]


def test_missing_column_returns_400():
    response = post_files(accounting=upload("contabilidad.csv", b"id_factura\nF1\n"))
    assert response.status_code == 400
    assert "contabilidad.csv" in response.json()["detail"]


def test_missing_file_returns_422():
    response = client.post(ENDPOINT, files={"invoices": upload("facturas.csv", b"x")})
    assert response.status_code == 422


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_empty_accounting_invoice_id_returns_400_with_file_row_and_field():
    accounting = b",2026-01-02,511010,CC1,5,5,Contabilizada\n"
    header = b"id_factura,fecha_contabilizacion,cuenta_contable,centro_costo,valor_debito,valor_credito,estado\n"
    response = post_files(accounting=upload("contabilidad.csv", header + accounting))
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "contabilidad.csv" in detail and "fila 2" in detail and "id_factura" in detail


def test_not_calculable_posted_amount_is_flagged_in_the_response():
    header = b"id_factura,fecha_contabilizacion,cuenta_contable,centro_costo,valor_debito,valor_credito,estado\n"
    invoices = (
        b"id_factura,nit_proveedor,fecha_factura,concepto,base_gravable,tarifa_iva,valor_iva,"
        b"tarifa_retencion,valor_retencion,total_factura\n"
        b"F1,900,2026-01-01,Soporte,1000000,0,0,0,0,1000000\n"
    )
    response = post_files(
        invoices=upload("facturas.csv", invoices),
        accounting=upload("contabilidad.csv", header + b"F1,2026-01-02,511010,CC1,abc,1000000,Contabilizada\n"),
    )
    detail = response.json()["details"][0]
    assert detail["postedAmount"] is None
    assert detail["postedAmountCalculable"] is False
