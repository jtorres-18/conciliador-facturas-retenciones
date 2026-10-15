import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Resultado } from '../models/conciliacion.model';

/** Dirección del backend Python. Cámbiala aquí si el backend corre en otro puerto. */
export const API_URL = 'http://localhost:8000/api';

@Injectable({ providedIn: 'root' })
export class ConciliacionService {
  private readonly http = inject(HttpClient);

  procesar(facturas: File, contabilidad: File): Observable<Resultado> {
    const datos = new FormData();
    datos.append('facturas', facturas);
    datos.append('contabilidad', contabilidad);
    return this.http.post<Resultado>(`${API_URL}/conciliacion`, datos);
  }
}

/** Traduce un error HTTP a un mensaje entendible para el usuario. */
export function mensajeDeError(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) {
    return 'Ocurrió un error inesperado al procesar los archivos.';
  }
  if (error.status === 0) {
    return `No se pudo conectar con el servicio de conciliación (${API_URL}). Verifica que el backend esté iniciado.`;
  }
  if (error.status === 422) {
    return 'Debes seleccionar los dos archivos: facturas y contabilidad.';
  }
  const detalle = error.error?.detail;
  if (typeof detalle === 'string') {
    return detalle;
  }
  return `El servicio respondió con un error (${error.status}). Inténtalo de nuevo.`;
}
