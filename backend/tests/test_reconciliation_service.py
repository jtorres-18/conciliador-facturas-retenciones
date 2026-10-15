import pytest

from app.domain.models import InvoiceStatus
from app.infrastructure.csv_reader import InvalidFileError
from app.services.reconciliation_service import ReconciliationService
from tests.sample_data import ACCOUNTING_HEADER, INVOICES_HEADER

service = ReconciliationService()


def reconcile(invoices: str, accounting: str):
    return service.reconcile(invoices.encode(), accounting.encode())


def error_codes(result) -> list[str]:
    return [finding.code for finding in result.errors]


@pytest.fixture(scope="module")
def sample_report(sample_invoices_csv, sample_accounting_csv):
    return service.reconcile(sample_invoices_csv, sample_accounting_csv)


def error_codes_by_row(report, invoice_id: str) -> list[list[str]]:
    """Sorted error codes for every row that has that invoice id."""
    return [
        sorted(error_codes(result))
        for result in report.results
        if result.invoice.invoice_id == invoice_id
    ]



def test_summary_of_sample_files(sample_report):
    summary = sample_report.summary
    assert summary.total_invoices == 50
    assert summary.unique_invoice_ids == 48
    assert summary.inconsistent == 18
    assert summary.correct == 32
    assert summary.correct_with_warnings == 4  
    assert summary.accounting_without_invoice == []


@pytest.mark.parametrize("invoice_id, expected", [
    ("FAC-0002", [[]]),                                  
    ("FAC-0006", [["VAT_MISMATCH"]]),                    
    ("FAC-0018", [["VAT_MISMATCH"]]),                    
    ("FAC-0009", [["TOTAL_MISMATCH"]]),                  
    ("FAC-0023", [["TOTAL_MISMATCH"]]),
    ("FAC-0036", [["TOTAL_MISMATCH"]]),
    ("FAC-0007", [["MISSING_ACCOUNTING_RECORD"]]),
    ("FAC-0021", [["MISSING_ACCOUNTING_RECORD"]]),
    ("FAC-0034", [["MISSING_ACCOUNTING_RECORD"]]),
    ("FAC-0042", [["EMPTY_FIELD", "MISSING_ACCOUNTING_RECORD"]]),
    ("FAC-0013", [["EMPTY_FIELD"]]),
    ("FAC-0029", [["EMPTY_FIELD"]]),
    ("FAC-0011", [["PENDING_POSTING"]]),
    ("FAC-0027", [["PENDING_POSTING"]]),
    ("FAC-0039", [["PENDING_POSTING"]]),
    ("FAC-0004", [["DUPLICATE_INVOICE"], ["ACCOUNTING_AMOUNT_MISMATCH", "DUPLICATE_INVOICE"]]),
    ("FAC-0015", [["DUPLICATE_INVOICE"], ["ACCOUNTING_AMOUNT_MISMATCH", "DUPLICATE_INVOICE"]]),
])
def test_errors_by_invoice(sample_report, invoice_id, expected):
    assert error_codes_by_row(sample_report, invoice_id) == expected


def test_zero_amount_accounting_lines_are_warnings_not_errors(sample_report):
    result = next(r for r in sample_report.results if r.invoice.invoice_id == "FAC-0001")
    assert result.status == InvoiceStatus.CORRECT
    assert [warning.code for warning in result.warnings] == ["ZERO_AMOUNT_ACCOUNTING_LINE"]


def test_wrong_withholding():
    report = reconcile(
        INVOICES_HEADER + "F1,900,2026-01-01,Soporte,1000000,0.19,190000,0.04,50000,1140000\n",
        ACCOUNTING_HEADER + "F1,2026-01-02,511010,CC1,1140000,1140000,Contabilizada\n",
    )
    assert error_codes(report.results[0]) == ["WITHHOLDING_MISMATCH"]


def test_unbalanced_accounting_entry():
    report = reconcile(
        INVOICES_HEADER + "F1,900,2026-01-01,Soporte,1000000,0,0,0,0,1000000\n",
        ACCOUNTING_HEADER + "F1,2026-01-02,511010,CC1,1000000,900000,Contabilizada\n",
    )
    assert error_codes(report.results[0]) == ["UNBALANCED_ENTRY"]


def test_accounting_without_invoice():
    report = reconcile(
        INVOICES_HEADER + "F1,900,2026-01-01,Soporte,1000000,0,0,0,0,1000000\n",
        ACCOUNTING_HEADER
        + "F1,2026-01-02,511010,CC1,1000000,1000000,Contabilizada\n"
        + "F9,2026-01-02,511010,CC1,5,5,Contabilizada\n",
    )
    assert report.summary.accounting_without_invoice == ["F9"]


def test_non_numeric_value_and_invalid_date():
    report = reconcile(
        INVOICES_HEADER + "F1,900,01/02/2026,Soporte,abc,0,0,0,0,100\n",
        ACCOUNTING_HEADER + "F1,2026-01-02,511010,CC1,100,100,Contabilizada\n",
    )
    assert {"NON_NUMERIC_VALUE", "INVALID_DATE"} <= set(error_codes(report.results[0]))


def test_accepts_semicolon_and_latin1():
    invoices = (
        INVOICES_HEADER.replace(",", ";") + "F1;900;2026-01-01;Capacitación;1000000;0;0;0;0;1000000\n"
    ).encode("latin-1")
    accounting = (
        ACCOUNTING_HEADER.replace(",", ";") + "F1;2026-01-02;511010;CC1;1000000;1000000;Contabilizada\n"
    ).encode()
    assert service.reconcile(invoices, accounting).summary.correct == 1


def test_missing_column(sample_accounting_csv):
    with pytest.raises(InvalidFileError, match="le faltan las columnas"):
        service.reconcile(b"id_factura,nit_proveedor\nF1,900\n", sample_accounting_csv)


def test_empty_file_or_without_records(sample_accounting_csv):
    with pytest.raises(InvalidFileError, match="vacío"):
        service.reconcile(b"   ", sample_accounting_csv)
    with pytest.raises(InvalidFileError, match="vacío"):
        service.reconcile("﻿".encode(), sample_accounting_csv) 
    with pytest.raises(InvalidFileError, match="no tiene registros"):
        service.reconcile(INVOICES_HEADER.encode(), sample_accounting_csv)
