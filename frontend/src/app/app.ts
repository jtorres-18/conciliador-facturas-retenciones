import { Component, inject, signal } from '@angular/core';

import { FileUpload, SelectedFiles } from './components/file-upload/file-upload';
import { ResultsTable } from './components/results-table/results-table';
import { Summary } from './components/summary/summary';
import { ReconciliationResponse } from './models/reconciliation.model';
import { ReconciliationService, toUserMessage } from './services/reconciliation.service';

@Component({
  selector: 'app-root',
  imports: [FileUpload, Summary, ResultsTable],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly reconciliationService = inject(ReconciliationService);

  protected readonly loading = signal(false);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly reconciliation = signal<ReconciliationResponse | null>(null);

  protected reconcile({ invoices, accounting }: SelectedFiles): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    this.reconciliation.set(null);

    this.reconciliationService.reconcile(invoices, accounting).subscribe({
      next: (response) => {
        this.reconciliation.set(response);
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.errorMessage.set(toUserMessage(error));
        this.loading.set(false);
      },
    });
  }
}
