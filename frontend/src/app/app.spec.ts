import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { App } from './app';
import { FileUpload } from './components/file-upload/file-upload';
import { ReconciliationResponse } from './models/reconciliation.model';
import { API_URL } from './services/reconciliation.service';

const RECONCILIATION_URL = `${API_URL}/reconciliations`;

const RESPONSE: ReconciliationResponse = {
  summary: {
    totalInvoices: 2,
    uniqueInvoiceIds: 2,
    correct: 1,
    inconsistent: 1,
    correctWithWarnings: 0,
    errorsByCode: [{ code: 'MISSING_ACCOUNTING_RECORD', description: 'Sin registro contable', count: 1 }],
    warningsByCode: [],
    accountingRecords: 1,
    accountingWithoutInvoice: [],
  },
  details: [
    {
      rowNumber: 2, invoiceId: 'F1', supplierTaxId: '900', issueDate: '2026-01-01', concept: 'Soporte',
      taxableBase: 100, vatAmount: 0, expectedVat: 0, withholdingAmount: 0, totalAmount: 100,
      expectedTotal: 100, postedAmount: 100, postingStatus: 'Contabilizada',
      status: 'Correcta', errors: [], warnings: [],
    },
    {
      rowNumber: 3, invoiceId: 'F2', supplierTaxId: '901', issueDate: '2026-01-02', concept: 'Soporte',
      taxableBase: 200, vatAmount: 0, expectedVat: 0, withholdingAmount: 0, totalAmount: 200,
      expectedTotal: 200, postedAmount: null, postingStatus: null,
      status: 'Con inconsistencia',
      errors: [{
        code: 'MISSING_ACCOUNTING_RECORD',
        description: 'Sin registro contable',
        message: 'No existe ningún registro contable para esta factura',
      }],
      warnings: [],
    },
  ],
};

function csvFile(name: string): File {
  return new File(['id_factura\n'], name, { type: 'text/csv' });
}

describe('App', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function submitFiles(): ComponentFixture<App> {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const fileUpload = fixture.debugElement.query(By.directive(FileUpload)).componentInstance as FileUpload;
    fileUpload.submitted.emit({ invoices: csvFile('facturas.csv'), accounting: csvFile('contabilidad.csv') });
    fixture.detectChanges();
    return fixture;
  }

  it('sends both files to the backend and shows the summary and the details', () => {
    const fixture = submitFiles();
    const request = http.expectOne(RECONCILIATION_URL);
    expect(request.request.method).toBe('POST');
    expect(request.request.body.get('invoices').name).toBe('facturas.csv');
    expect(request.request.body.get('accounting').name).toBe('contabilidad.csv');
    expect(fixture.nativeElement.textContent).toContain('Procesando');

    request.flush(RESPONSE);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).not.toContain('Procesando');
    expect(text).toContain('Facturas procesadas');
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(2);
  });

  it('filters the table by status', () => {
    const fixture = submitFiles();
    http.expectOne(RECONCILIATION_URL).flush(RESPONSE);
    fixture.detectChanges();

    const buttons = Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll('.filter'));
    buttons.find((button) => button.textContent?.includes('Con inconsistencia'))!.click();
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('tbody tr');
    expect(rows.length).toBe(1);
    expect(rows[0].textContent).toContain('F2');
  });

  it('shows the backend message when a file is invalid', () => {
    const fixture = submitFiles();
    http.expectOne(RECONCILIATION_URL).flush(
      { detail: "Al archivo 'facturas.csv' le faltan las columnas: nit_proveedor." },
      { status: 400, statusText: 'Bad Request' },
    );
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role=alert]').textContent).toContain('le faltan las columnas');
    expect(fixture.nativeElement.querySelector('app-summary')).toBeNull();
  });

  it('warns when the backend is not reachable', () => {
    const fixture = submitFiles();
    http.expectOne(RECONCILIATION_URL).error(new ProgressEvent('error'));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role=alert]').textContent).toContain('No se pudo conectar');
  });
});
