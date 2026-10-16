from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum

INVOICE_COLUMNS = [
    "id_factura", "nit_proveedor", "fecha_factura", "concepto", "base_gravable",
    "tarifa_iva", "valor_iva", "tarifa_retencion", "valor_retencion", "total_factura",
]
ACCOUNTING_COLUMNS = [
    "id_factura", "fecha_contabilizacion", "cuenta_contable", "centro_costo",
    "valor_debito", "valor_credito", "estado",
]
POSTED_STATUS = "contabilizada"


class Severity(str, Enum):
    ERROR = "error"      
    WARNING = "warning"  


class InvoiceStatus(str, Enum):
    CORRECT = "Correcta"
    INCONSISTENT = "Con inconsistencia"


@dataclass(frozen=True)
class Finding:
    code: str
    description: str
    message: str
    severity: Severity = Severity.ERROR


@dataclass(frozen=True)
class Invoice:
    row_number: int
    invoice_id: str
    supplier_tax_id: str
    issue_date: str
    concept: str
    taxable_base: Decimal | None
    vat_rate: Decimal | None
    vat_amount: Decimal | None
    withholding_rate: Decimal | None
    withholding_amount: Decimal | None
    total_amount: Decimal | None
    empty_fields: list[str] = field(default_factory=list)
    non_numeric_fields: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_csv_row(cls, row_number: int, values: dict[str, str]) -> "Invoice":
        non_numeric_fields: dict[str, str] = {}

        def amount(column: str) -> Decimal | None:
            text = values.get(column, "")
            if not text:
                return None  
            try:
                number = Decimal(text)
            except InvalidOperation:
                number = None
            if number is None or not number.is_finite():
                non_numeric_fields[column] = text
                return None
            return number

        return cls(
            row_number=row_number,
            invoice_id=values.get("id_factura", ""),
            supplier_tax_id=values.get("nit_proveedor", ""),
            issue_date=values.get("fecha_factura", ""),
            concept=values.get("concepto", ""),
            taxable_base=amount("base_gravable"),
            vat_rate=amount("tarifa_iva"),
            vat_amount=amount("valor_iva"),
            withholding_rate=amount("tarifa_retencion"),
            withholding_amount=amount("valor_retencion"),
            total_amount=amount("total_factura"),
            empty_fields=[column for column in INVOICE_COLUMNS if not values.get(column)],
            non_numeric_fields=non_numeric_fields,
        )

    def expected_vat(self) -> Decimal | None:
        if self.taxable_base is None or self.vat_rate is None:
            return None
        return self.taxable_base * self.vat_rate

    def expected_withholding(self) -> Decimal | None:
        if self.taxable_base is None or self.withholding_rate is None:
            return None
        return self.taxable_base * self.withholding_rate

    def expected_total(self) -> Decimal | None:
        if self.taxable_base is None or self.vat_amount is None or self.withholding_amount is None:
            return None
        return self.taxable_base + self.vat_amount - self.withholding_amount

    def total_with_recalculated_vat(self) -> Decimal | None:
        expected_vat = self.expected_vat()
        if expected_vat is None or self.withholding_amount is None:
            return None
        return self.taxable_base + expected_vat - self.withholding_amount


@dataclass(frozen=True)
class AccountingLine:
    row_number: int
    invoice_id: str
    status: str
    debit: Decimal | None
    credit: Decimal | None
    issues: list[str] = field(default_factory=list)

    @classmethod
    def from_csv_row(cls, row_number: int, values: dict[str, str]) -> "AccountingLine":
        issues: list[str] = []

        for column in ACCOUNTING_COLUMNS:
            if column != "id_factura" and not values.get(column):
                issues.append(f"fila {row_number}: '{column}' está vacío")

        def amount(column: str) -> Decimal | None:
            text = values.get(column, "")
            if not text:
                return None
            try:
                number = Decimal(text)
            except InvalidOperation:
                number = None
            if number is None or not number.is_finite():
                issues.append(f"fila {row_number}: '{column}' no es numérico ('{text}')")
                return None
            return number

        debit = amount("valor_debito")
        credit = amount("valor_credito")

        posting_date = values.get("fecha_contabilizacion", "")
        if posting_date:
            try:
                date.fromisoformat(posting_date)
            except ValueError:
                issues.append(
                    f"fila {row_number}: 'fecha_contabilizacion' no tiene formato AAAA-MM-DD ('{posting_date}')"
                )

        return cls(row_number, values.get("id_factura", ""), values.get("estado", ""), debit, credit, issues)


@dataclass
class AccountingRecord:
    invoice_id: str
    total_debit: Decimal | None = Decimal(0)
    total_credit: Decimal | None = Decimal(0)
    statuses: set[str] = field(default_factory=set)
    lines_with_amount: int = 0
    zero_amount_lines: int = 0
    data_issues: list[str] = field(default_factory=list)

    def add_line(self, line: AccountingLine) -> None:
        if line.debit is None:
            self.total_debit = None
        elif self.total_debit is not None:
            self.total_debit += line.debit
        if line.credit is None:
            self.total_credit = None
        elif self.total_credit is not None:
            self.total_credit += line.credit
        self.statuses.add(line.status)
        self.data_issues.extend(line.issues)
        if line.debit is None or line.credit is None:
            pass
        elif line.debit == 0 and line.credit == 0:
            self.zero_amount_lines += 1
        else:
            self.lines_with_amount += 1

    def pending_statuses(self) -> list[str]:
        return sorted(status for status in self.statuses if status.casefold() != POSTED_STATUS)

    def status_label(self) -> str:
        return ", ".join(sorted(status or "(vacío)" for status in self.statuses))


@dataclass(frozen=True)
class InvoiceResult:
    invoice: Invoice
    accounting: AccountingRecord | None
    errors: list[Finding]
    warnings: list[Finding]

    @property
    def status(self) -> InvoiceStatus:
        return InvoiceStatus.INCONSISTENT if self.errors else InvoiceStatus.CORRECT


@dataclass(frozen=True)
class FindingCount:
    code: str
    description: str
    count: int


@dataclass(frozen=True)
class ReconciliationSummary:
    total_invoices: int
    unique_invoice_ids: int
    correct: int
    inconsistent: int
    correct_with_warnings: int
    errors_by_code: list[FindingCount]
    warnings_by_code: list[FindingCount]
    accounting_records: int
    accounting_without_invoice: list[str]


@dataclass(frozen=True)
class ReconciliationReport:
    summary: ReconciliationSummary
    results: list[InvoiceResult]
