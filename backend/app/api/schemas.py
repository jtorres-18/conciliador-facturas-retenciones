"""Response contract of the API (what the Angular frontend receives).

Keeping these schemas apart from the domain lets the domain change without
breaking the frontend, and FastAPI documents them automatically in /docs.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.domain.models import (
    Finding,
    FindingCount,
    InvoiceResult,
    InvoiceStatus,
    ReconciliationReport,
    ReconciliationSummary,
)


class CamelCaseModel(BaseModel):
    """Python uses snake_case and TypeScript camelCase: the JSON is sent in camelCase."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def _to_float(amount: Decimal | None) -> float | None:
    return None if amount is None else float(amount)


class FindingResponse(CamelCaseModel):
    code: str
    description: str
    message: str

    @classmethod
    def from_domain(cls, finding: Finding) -> "FindingResponse":
        return cls(code=finding.code, description=finding.description, message=finding.message)


class FindingCountResponse(CamelCaseModel):
    code: str
    description: str
    count: int

    @classmethod
    def from_domain(cls, finding_count: FindingCount) -> "FindingCountResponse":
        return cls(
            code=finding_count.code,
            description=finding_count.description,
            count=finding_count.count,
        )


class InvoiceResultResponse(CamelCaseModel):
    row_number: int
    invoice_id: str
    supplier_tax_id: str
    issue_date: str
    concept: str
    taxable_base: float | None
    vat_amount: float | None
    expected_vat: float | None
    withholding_amount: float | None
    total_amount: float | None
    expected_total: float | None
    posted_amount: float | None
    posting_status: str | None
    status: InvoiceStatus
    errors: list[FindingResponse]
    warnings: list[FindingResponse]

    @classmethod
    def from_domain(cls, result: InvoiceResult) -> "InvoiceResultResponse":
        invoice = result.invoice
        accounting = result.accounting
        return cls(
            row_number=invoice.row_number,
            invoice_id=invoice.invoice_id,
            supplier_tax_id=invoice.supplier_tax_id,
            issue_date=invoice.issue_date,
            concept=invoice.concept,
            taxable_base=_to_float(invoice.taxable_base),
            vat_amount=_to_float(invoice.vat_amount),
            expected_vat=_to_float(invoice.expected_vat()),
            withholding_amount=_to_float(invoice.withholding_amount),
            total_amount=_to_float(invoice.total_amount),
            expected_total=_to_float(invoice.expected_total()),
            posted_amount=_to_float(accounting.total_debit) if accounting else None,
            posting_status=accounting.status_label() if accounting else None,
            status=result.status,
            errors=[FindingResponse.from_domain(finding) for finding in result.errors],
            warnings=[FindingResponse.from_domain(finding) for finding in result.warnings],
        )


class SummaryResponse(CamelCaseModel):
    total_invoices: int
    unique_invoice_ids: int
    correct: int
    inconsistent: int
    correct_with_warnings: int
    errors_by_code: list[FindingCountResponse]
    warnings_by_code: list[FindingCountResponse]
    accounting_records: int
    accounting_without_invoice: list[str]

    @classmethod
    def from_domain(cls, summary: ReconciliationSummary) -> "SummaryResponse":
        return cls(
            total_invoices=summary.total_invoices,
            unique_invoice_ids=summary.unique_invoice_ids,
            correct=summary.correct,
            inconsistent=summary.inconsistent,
            correct_with_warnings=summary.correct_with_warnings,
            errors_by_code=[FindingCountResponse.from_domain(c) for c in summary.errors_by_code],
            warnings_by_code=[FindingCountResponse.from_domain(c) for c in summary.warnings_by_code],
            accounting_records=summary.accounting_records,
            accounting_without_invoice=summary.accounting_without_invoice,
        )


class ReconciliationResponse(CamelCaseModel):
    summary: SummaryResponse
    details: list[InvoiceResultResponse]

    @classmethod
    def from_domain(cls, report: ReconciliationReport) -> "ReconciliationResponse":
        return cls(
            summary=SummaryResponse.from_domain(report.summary),
            details=[InvoiceResultResponse.from_domain(result) for result in report.results],
        )


class HealthResponse(CamelCaseModel):
    status: str
