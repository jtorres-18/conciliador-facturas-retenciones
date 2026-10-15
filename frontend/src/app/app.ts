import { Component, inject, signal } from '@angular/core';

import { ArchivosSeleccionados, CargaArchivos } from './components/carga-archivos/carga-archivos';
import { ResumenConciliacion } from './components/resumen/resumen';
import { TablaResultados } from './components/tabla-resultados/tabla-resultados';
import { Resultado } from './models/conciliacion.model';
import { ConciliacionService, mensajeDeError } from './services/conciliacion.service';

@Component({
  selector: 'app-root',
  imports: [CargaArchivos, ResumenConciliacion, TablaResultados],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly servicio = inject(ConciliacionService);

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly resultado = signal<Resultado | null>(null);

  protected procesar({ facturas, contabilidad }: ArchivosSeleccionados): void {
    this.cargando.set(true);
    this.error.set(null);
    this.resultado.set(null);

    this.servicio.procesar(facturas, contabilidad).subscribe({
      next: (resultado) => {
        this.resultado.set(resultado);
        this.cargando.set(false);
      },
      error: (error) => {
        this.error.set(mensajeDeError(error));
        this.cargando.set(false);
      },
    });
  }
}
