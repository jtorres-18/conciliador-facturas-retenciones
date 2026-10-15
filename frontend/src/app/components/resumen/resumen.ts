import { Component, computed, input } from '@angular/core';

import { Resumen } from '../../models/conciliacion.model';

@Component({
  selector: 'app-resumen',
  templateUrl: './resumen.html',
  styleUrl: './resumen.css',
})
export class ResumenConciliacion {
  readonly resumen = input.required<Resumen>();

  protected readonly porcentajeInconsistentes = computed(() => {
    const { total_facturas, con_inconsistencia } = this.resumen();
    return total_facturas ? Math.round((con_inconsistencia / total_facturas) * 100) : 0;
  });

  protected readonly maximoCausa = computed(() =>
    Math.max(1, ...this.resumen().por_causa.map((c) => c.cantidad)),
  );
}
