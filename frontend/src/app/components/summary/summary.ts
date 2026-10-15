import { Component, computed, input } from '@angular/core';

import { ReconciliationSummary } from '../../models/reconciliation.model';

@Component({
  selector: 'app-summary',
  templateUrl: './summary.html',
  styleUrl: './summary.css',
})
export class Summary {
  readonly summary = input.required<ReconciliationSummary>();

  protected readonly correctPercentage = computed(() => {
    const { totalInvoices, correct } = this.summary();
    return totalInvoices ? Math.round((correct / totalInvoices) * 100) : 0;
  });

  protected readonly inconsistentPercentage = computed(() =>
    this.summary().totalInvoices ? 100 - this.correctPercentage() : 0,
  );

  protected readonly maxErrorCount = computed(() =>
    Math.max(1, ...this.summary().errorsByCode.map((item) => item.count)),
  );
}
