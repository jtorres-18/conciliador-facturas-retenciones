import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ReconciliationResponse } from '../models/reconciliation.model';

export const API_URL = 'http://localhost:8000/api';

@Injectable({ providedIn: 'root' })
export class ReconciliationService {
  private readonly http = inject(HttpClient);

  reconcile(invoicesFile: File, accountingFile: File): Observable<ReconciliationResponse> {
    const formData = new FormData();
    formData.append('invoices', invoicesFile);
    formData.append('accounting', accountingFile);
    return this.http.post<ReconciliationResponse>(`${API_URL}/reconciliations`, formData);
  }
}

/** Turns an HTTP error into a message the user can understand. */
export function toUserMessage(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) {
    return 'Ocurrió un error inesperado al procesar los archivos.';
  }
  if (error.status === 0) {
    return `No se pudo conectar con el servicio de conciliación (${API_URL}). Verifica que el backend esté iniciado.`;
  }
  if (error.status === 422) {
    return 'Debes seleccionar los dos archivos: facturas y contabilidad.';
  }
  const detail = error.error?.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  return `El servicio respondió con un error (${error.status}). Inténtalo de nuevo.`;
}
