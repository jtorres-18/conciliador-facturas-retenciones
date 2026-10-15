"""Use case: reconcile the invoices file against the accounting file."""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

from app.domain.models import (
    ACCOUNTING_COLUMNS,
    INVOICE_COLUMNS,
    AccountingRecord,
    Finding,
    FindingCount,
    Invoice,
    InvoiceResult,
    InvoiceStatus,
    ReconciliationReport,
    ReconciliationSummary,
    Severity,
)
from app.domain.rules import DEFAULT_RULES, InvoiceRule, ReconciliationContext
from app.infrastructure.csv_reader import CsvRow, read_csv


class ReconciliationService:
    def __init__(self, rules: list[InvoiceRule] | None = None):
        self._rules = rules if rules is not None else DEFAULT_RULES

    def reconcile(self, invoices_csv: bytes, accounting_csv: bytes) -> ReconciliationReport:
        invoice_rows = read_csv(invoices_csv, "facturas.csv", INVOICE_COLUMNS)
        accounting_rows = read_csv(accounting_csv, "contabilidad.csv", ACCOUNTING_COLUMNS)

        invoices = [Invoice.from_csv_row(row.line_number, row.values) for row in invoice_rows]
        context = ReconciliationContext(
            row_numbers_by_invoice_id=_group_row_numbers(invoices),
            accounting_by_invoice_id=_group_accounting_lines(accounting_rows),
        )
        results = [self._evaluate(invoice, context) for invoice in invoices]
        summary = _build_summary(results, context, accounting_line_count=len(accounting_rows))
        return ReconciliationReport(summary=summary, results=results)

    def _evaluate(self, invoice: Invoice, context: ReconciliationContext) -> InvoiceResult:
        checks = [rule.check(invoice, context) for rule in self._rules]
        findings = [finding for finding in checks if finding is not None]
        return InvoiceResult(
            invoice=invoice,
            accounting=context.accounting_by_invoice_id.get(invoice.invoice_id),
            errors=[finding for finding in findings if finding.severity == Severity.ERROR],
            warnings=[finding for finding in findings if finding.severity == Severity.WARNING],
        )


def _group_row_numbers(invoices: list[Invoice]) -> dict[str, list[int]]:
    row_numbers: dict[str, list[int]] = defaultdict(list)
    for invoice in invoices:
        row_numbers[invoice.invoice_id].append(invoice.row_number)
    return dict(row_numbers)


def _group_accounting_lines(rows: list[CsvRow]) -> dict[str, AccountingRecord]:
    records: dict[str, AccountingRecord] = {}
    for row in rows:
        invoice_id = row.values.get("id_factura", "")
        record = records.setdefault(invoice_id, AccountingRecord(invoice_id))
        record.add_line(
            debit=_amount_or_zero(row.values.get("valor_debito", "")),
            credit=_amount_or_zero(row.values.get("valor_credito", "")),
            status=row.values.get("estado", ""),
        )
    return records


def _amount_or_zero(text: str) -> Decimal:
    """Accounting amounts that are empty or not numeric count as 0 (documented assumption)."""
    try:
        amount = Decimal(text) if text else Decimal(0)
    except InvalidOperation:
        return Decimal(0)
    return amount if amount.is_finite() else Decimal(0)


def _count_by_code(findings: list[Finding]) -> list[FindingCount]:
    counter = Counter(finding.code for finding in findings)
    descriptions = {finding.code: finding.description for finding in findings}
    return [FindingCount(code, descriptions[code], count) for code, count in counter.most_common()]


def _build_summary(
    results: list[InvoiceResult], context: ReconciliationContext, accounting_line_count: int
) -> ReconciliationSummary:
    inconsistent = sum(1 for result in results if result.status == InvoiceStatus.INCONSISTENT)
    invoice_ids = set(context.row_numbers_by_invoice_id)
    return ReconciliationSummary(
        total_invoices=len(results),
        unique_invoice_ids=len([invoice_id for invoice_id in invoice_ids if invoice_id]),
        correct=len(results) - inconsistent,
        inconsistent=inconsistent,
        correct_with_warnings=sum(
            1 for result in results if result.status == InvoiceStatus.CORRECT and result.warnings
        ),
        errors_by_code=_count_by_code([f for result in results for f in result.errors]),
        warnings_by_code=_count_by_code([f for result in results for f in result.warnings]),
        accounting_records=accounting_line_count,
        accounting_without_invoice=sorted(
            invoice_id
            for invoice_id in context.accounting_by_invoice_id
            if invoice_id and invoice_id not in invoice_ids
        ),
    )
