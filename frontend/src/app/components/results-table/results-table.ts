import { Component, computed, input, signal } from '@angular/core';

import { InvoiceResult, InvoiceStatus } from '../../models/reconciliation.model';
import { CopCurrencyPipe } from '../../pipes/cop-currency.pipe';

export type StatusFilter = 'Todas' | InvoiceStatus;

interface FilterOption {
  value: StatusFilter;
  label: string;
  count: number;
}

@Component({
  selector: 'app-results-table',
  imports: [CopCurrencyPipe],
  templateUrl: './results-table.html',
  styleUrl: './results-table.css',
})
export class ResultsTable {
  readonly results = input.required<InvoiceResult[]>();

  protected readonly selectedFilter = signal<StatusFilter>('Todas');

  protected readonly filterOptions = computed<FilterOption[]>(() => {
    const results = this.results();
    const countByStatus = (status: InvoiceStatus) =>
      results.filter((result) => result.status === status).length;
    return [
      { value: 'Todas', label: 'Todas', count: results.length },
      { value: 'Correcta', label: 'Correctas', count: countByStatus('Correcta') },
      { value: 'Con inconsistencia', label: 'Con inconsistencia', count: countByStatus('Con inconsistencia') },
    ];
  });

  protected readonly filteredResults = computed(() => {
    const filter = this.selectedFilter();
    const results = this.results();
    return filter === 'Todas' ? results : results.filter((result) => result.status === filter);
  });

  protected selectFilter(filter: StatusFilter): void {
    this.selectedFilter.set(filter);
  }
}
