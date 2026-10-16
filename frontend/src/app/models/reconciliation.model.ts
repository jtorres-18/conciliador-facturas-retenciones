
export type InvoiceStatus = 'Correcta' | 'Con inconsistencia';

export interface Finding {
  code: string;
  description: string;
  message: string;
}

export interface InvoiceResult {
  rowNumber: number;
  invoiceId: string;
  supplierTaxId: string;
  issueDate: string;
  concept: string;
  taxableBase: number | null;
  vatAmount: number | null;
  expectedVat: number | null;
  withholdingAmount: number | null;
  totalAmount: number | null;
  expectedTotal: number | null;
  totalWithRecalculatedVat: number | null;
  postedAmount: number | null;
  postingStatus: string | null;
  status: InvoiceStatus;
  errors: Finding[];
  warnings: Finding[];
}

export interface FindingCount {
  code: string;
  description: string;
  count: number;
}

export interface ReconciliationSummary {
  totalInvoices: number;
  uniqueInvoiceIds: number;
  correct: number;
  inconsistent: number;
  correctWithWarnings: number;
  errorsByCode: FindingCount[];
  warningsByCode: FindingCount[];
  accountingRecords: number;
  accountingWithoutInvoice: string[];
}

export interface ReconciliationResponse {
  summary: ReconciliationSummary;
  details: InvoiceResult[];
}
