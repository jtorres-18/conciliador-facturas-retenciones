"""Unit tests of the domain: each rule can be tested on its own, without files or HTTP."""
from decimal import Decimal

from app.domain.models import AccountingRecord, Invoice, Severity
from app.domain.rules import (
    AccountingAmountRule,
    InvoiceTotalRule,
    ReconciliationContext,
    VatRule,
    ZeroAmountLineRule,
)

EMPTY_CONTEXT = ReconciliationContext(row_numbers_by_invoice_id={}, accounting_by_invoice_id={})


def make_invoice(**overrides) -> Invoice:
    values = {
        "id_factura": "F1", "nit_proveedor": "900", "fecha_factura": "2026-01-01",
        "concepto": "Soporte", "base_gravable": "1000000", "tarifa_iva": "0.19",
        "valor_iva": "190000", "tarifa_retencion": "0.04", "valor_retencion": "40000",
        "total_factura": "1150000",
    }
    values.update(overrides)
    return Invoice.from_csv_row(row_number=2, values=values)


def test_invoice_calculates_expected_vat_and_total():
    invoice = make_invoice()
    assert invoice.expected_vat() == Decimal("190000")
    assert invoice.expected_total() == Decimal("1150000")


def test_vat_rule_detects_wrong_vat_and_shows_expected_value():
    finding = VatRule().check(make_invoice(valor_iva="200000"), EMPTY_CONTEXT)
    assert finding is not None
    assert "190.000" in finding.message


def test_vat_rule_tolerates_one_peso_of_rounding():
    assert VatRule().check(make_invoice(valor_iva="190001"), EMPTY_CONTEXT) is None


def test_total_rule_uses_expected_vat_so_a_vat_error_is_not_reported_twice():
    # The VAT field is wrong, but the total is consistent with base × rate.
    invoice = make_invoice(valor_iva="200000", total_factura="1150000")
    assert InvoiceTotalRule().check(invoice, EMPTY_CONTEXT) is None


def test_non_numeric_amounts_are_not_used_in_calculations():
    invoice = make_invoice(base_gravable="abc")
    assert invoice.non_numeric_fields == {"base_gravable": "abc"}
    assert invoice.expected_vat() is None
    assert VatRule().check(invoice, EMPTY_CONTEXT) is None


def test_accounting_rules_are_skipped_when_there_is_no_record():
    assert AccountingAmountRule().check(make_invoice(), EMPTY_CONTEXT) is None


def test_zero_amount_line_is_a_warning():
    record = AccountingRecord("F1")
    record.add_line(Decimal("1150000"), Decimal("1150000"), "Contabilizada")
    record.add_line(Decimal(0), Decimal(0), "Contabilizada")
    context = ReconciliationContext({"F1": [2]}, {"F1": record})

    finding = ZeroAmountLineRule().check(make_invoice(), context)

    assert finding is not None
    assert finding.severity == Severity.WARNING
    assert AccountingAmountRule().check(make_invoice(), context) is None
