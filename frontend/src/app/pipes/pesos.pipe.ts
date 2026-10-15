import { Pipe, PipeTransform } from '@angular/core';

const formato = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
});

/** Formatea un valor como pesos colombianos; muestra "—" si no hay valor. */
@Pipe({ name: 'pesos' })
export class PesosPipe implements PipeTransform {
  transform(valor: number | null | undefined): string {
    return valor === null || valor === undefined ? '—' : formato.format(valor);
  }
}
