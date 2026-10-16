from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from app.domain.models import AccountingRecord, Finding, Invoice, Severity
from app.domain.money import amounts_differ, format_pesos


@dataclass(frozen=True)
class ReconciliationContext:
    row_numbers_by_invoice_id: dict[str, list[int]]
    accounting_by_invoice_id: dict[str, AccountingRecord]


class InvoiceRule(ABC):
    code: str
    description: str
    severity: Severity = Severity.ERROR

    @abstractmethod
    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        ...

    def _finding(self, message: str) -> Finding:
        return Finding(self.code, self.description, message, self.severity)


class AccountingRule(InvoiceRule, ABC):

    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        record = context.accounting_by_invoice_id.get(invoice.invoice_id)
        if not invoice.invoice_id or record is None:
            return None
        return self.check_record(invoice, record)

    @abstractmethod
    def check_record(self, invoice: Invoice, record: AccountingRecord) -> Finding | None: ...


class RequiredFieldsRule(InvoiceRule):
    code = "EMPTY_FIELD"
    description = "Campo obligatorio vacío"

    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        if invoice.empty_fields:
            return self._finding(f"Campos vacíos: {', '.join(invoice.empty_fields)}")
        return None


class IssueDateFormatRule(InvoiceRule):
    code = "INVALID_DATE"
    description = "Fecha inválida"

    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        if not invoice.issue_date:
            return None
        try:
            date.fromisoformat(invoice.issue_date)
            return None
        except ValueError:
            return self._finding(
                f"'fecha_factura' no tiene formato AAAA-MM-DD: '{invoice.issue_date}'"
            )


class NumericValuesRule(InvoiceRule):
    code = "NON_NUMERIC_VALUE"
    description = "Valor no numérico"

    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        if not invoice.non_numeric_fields:
            return None
        details = ", ".join(f"'{column}' = '{text}'" for column, text in invoice.non_numeric_fields.items())
        return self._finding(f"Valores no numéricos: {details}")


class DuplicateInvoiceRule(InvoiceRule):
    code = "DUPLICATE_INVOICE"
    description = "Factura duplicada"

    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        row_numbers = context.row_numbers_by_invoice_id.get(invoice.invoice_id, [])
        if not invoice.invoice_id or len(row_numbers) <= 1:
            return None
        other_rows = [str(number) for number in row_numbers if number != invoice.row_number]
        return self._finding(
            f"{invoice.invoice_id} aparece {len(row_numbers)} veces "
            f"(también en la fila {', '.join(other_rows)})"
        )


class VatRule(InvoiceRule):
    code = "VAT_MISMATCH"
    description = "IVA diferente a base × tarifa"

    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        expected_vat = invoice.expected_vat()
        if expected_vat is None or invoice.vat_amount is None:
            return None
        if not amounts_differ(expected_vat, invoice.vat_amount):
            return None
        return self._finding(
            f"IVA esperado {format_pesos(expected_vat)} "
            f"({format_pesos(invoice.taxable_base)} × {invoice.vat_rate}) "
            f"pero la factura trae {format_pesos(invoice.vat_amount)}"
        )


class WithholdingRule(InvoiceRule):
    code = "WITHHOLDING_MISMATCH"
    description = "Retención diferente a base × tarifa"

    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        expected_withholding = invoice.expected_withholding()
        if expected_withholding is None or invoice.withholding_amount is None:
            return None
        if not amounts_differ(expected_withholding, invoice.withholding_amount):
            return None
        return self._finding(
            f"Retención esperada {format_pesos(expected_withholding)} "
            f"pero la factura trae {format_pesos(invoice.withholding_amount)}"
        )


class InvoiceTotalRule(InvoiceRule):
    code = "TOTAL_MISMATCH"
    description = "Total diferente a base + IVA − retención"

    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        expected_total = invoice.expected_total()
        if expected_total is None or invoice.total_amount is None:
            return None
        if not amounts_differ(expected_total, invoice.total_amount):
            return None
        difference = invoice.total_amount - expected_total
        message = (
            f"Total esperado {format_pesos(expected_total)} (base + IVA informado − retención informada) "
            f"pero la factura trae {format_pesos(invoice.total_amount)}; "
            f"diferencia {format_pesos(difference)}"
        )
        recalculated_total = invoice.total_with_recalculated_vat()
        if recalculated_total is not None and amounts_differ(recalculated_total, expected_total):
            message += f". Referencia con IVA recalculado: {format_pesos(recalculated_total)}"
        return self._finding(message)


class MissingAccountingRecordRule(InvoiceRule):
    code = "MISSING_ACCOUNTING_RECORD"
    description = "Sin registro contable"

    def check(self, invoice: Invoice, context: ReconciliationContext) -> Finding | None:
        if invoice.invoice_id and invoice.invoice_id in context.accounting_by_invoice_id:
            return None
        return self._finding("No existe ningún registro contable para esta factura")


class AccountingDataQualityRule(AccountingRule):
    code = "INVALID_ACCOUNTING_DATA"
    description = "Datos contables inválidos"

    def check_record(self, invoice: Invoice, record: AccountingRecord) -> Finding | None:
        if not record.data_issues:
            return None
        return self._finding("; ".join(record.data_issues))


class PendingPostingRule(AccountingRule):
    code = "PENDING_POSTING"
    description = "Contabilización pendiente"

    def check_record(self, invoice: Invoice, record: AccountingRecord) -> Finding | None:
        pending = record.pending_statuses()
        if not pending:
            return None
        return self._finding(f"Estado contable: {', '.join(pending)}")


class UnbalancedEntryRule(AccountingRule):
    code = "UNBALANCED_ENTRY"
    description = "Débito diferente al crédito"

    def check_record(self, invoice: Invoice, record: AccountingRecord) -> Finding | None:
        if record.total_debit is None or record.total_credit is None:
            return None
        if not amounts_differ(record.total_debit, record.total_credit):
            return None
        return self._finding(
            f"Débito {format_pesos(record.total_debit)} ≠ crédito {format_pesos(record.total_credit)}"
        )


class DuplicateAccountingEntryRule(AccountingRule):
    code = "DUPLICATE_ACCOUNTING_ENTRY"
    description = "Varios registros contables con valor"
    severity = Severity.WARNING

    def check_record(self, invoice: Invoice, record: AccountingRecord) -> Finding | None:
        if record.lines_with_amount <= 1:
            return None
        return self._finding(f"{record.lines_with_amount} líneas contables con valor")


class AccountingAmountRule(AccountingRule):
    code = "ACCOUNTING_AMOUNT_MISMATCH"
    description = "Valor contable diferente al total"

    def check_record(self, invoice: Invoice, record: AccountingRecord) -> Finding | None:
        if invoice.total_amount is None or record.total_debit is None:
            return None
        if not amounts_differ(record.total_debit, invoice.total_amount):
            return None
        return self._finding(
            f"Contabilizado {format_pesos(record.total_debit)} "
            f"pero la factura dice {format_pesos(invoice.total_amount)}"
        )


class ZeroAmountLineRule(AccountingRule):
    code = "ZERO_AMOUNT_ACCOUNTING_LINE"
    description = "Línea contable con valor 0"
    severity = Severity.WARNING

    def check_record(self, invoice: Invoice, record: AccountingRecord) -> Finding | None:
        if not record.zero_amount_lines:
            return None
        return self._finding(
            f"{record.zero_amount_lines} línea(s) contable(s) con débito y crédito en 0 "
            "(ignoradas en el cálculo)"
        )


DEFAULT_RULES: list[InvoiceRule] = [
    RequiredFieldsRule(),
    IssueDateFormatRule(),
    DuplicateInvoiceRule(),
    NumericValuesRule(),
    VatRule(),
    WithholdingRule(),
    InvoiceTotalRule(),
    MissingAccountingRecordRule(),
    AccountingDataQualityRule(),
    PendingPostingRule(),
    UnbalancedEntryRule(),
    DuplicateAccountingEntryRule(),
    AccountingAmountRule(),
    ZeroAmountLineRule(),
]
