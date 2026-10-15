import { Component, computed, input, signal } from '@angular/core';

import { DetalleFactura, EstadoFactura } from '../../models/conciliacion.model';
import { PesosPipe } from '../../pipes/pesos.pipe';

export type FiltroEstado = 'Todas' | EstadoFactura;

@Component({
  selector: 'app-tabla-resultados',
  imports: [PesosPipe],
  templateUrl: './tabla-resultados.html',
  styleUrl: './tabla-resultados.css',
})
export class TablaResultados {
  readonly detalle = input.required<DetalleFactura[]>();

  protected readonly filtro = signal<FiltroEstado>('Todas');

  protected readonly opciones = computed(() => {
    const filas = this.detalle();
    const cuenta = (estado: EstadoFactura) => filas.filter((f) => f.estado === estado).length;
    return [
      { valor: 'Todas' as FiltroEstado, etiqueta: 'Todas', cantidad: filas.length },
      { valor: 'Correcta' as FiltroEstado, etiqueta: 'Correctas', cantidad: cuenta('Correcta') },
      {
        valor: 'Con inconsistencia' as FiltroEstado,
        etiqueta: 'Con inconsistencia',
        cantidad: cuenta('Con inconsistencia'),
      },
    ];
  });

  protected readonly filas = computed(() => {
    const filtro = this.filtro();
    return filtro === 'Todas' ? this.detalle() : this.detalle().filter((f) => f.estado === filtro);
  });

  protected seleccionar(filtro: FiltroEstado): void {
    this.filtro.set(filtro);
  }
}
