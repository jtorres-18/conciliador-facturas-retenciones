import { Component, computed, input, output, signal } from '@angular/core';

export interface ArchivosSeleccionados {
  facturas: File;
  contabilidad: File;
}

type Tipo = 'facturas' | 'contabilidad';

@Component({
  selector: 'app-carga-archivos',
  templateUrl: './carga-archivos.html',
  styleUrl: './carga-archivos.css',
})
export class CargaArchivos {
  readonly cargando = input(false);
  readonly procesar = output<ArchivosSeleccionados>();

  protected readonly facturas = signal<File | null>(null);
  protected readonly contabilidad = signal<File | null>(null);
  protected readonly aviso = signal<string | null>(null);

  protected readonly puedeProcesar = computed(
    () => !!this.facturas() && !!this.contabilidad() && !this.cargando(),
  );

  protected seleccionar(tipo: Tipo, evento: Event): void {
    const archivo = (evento.target as HTMLInputElement).files?.item(0) ?? null;
    this.aviso.set(null);
    if (archivo && !archivo.name.toLowerCase().endsWith('.csv')) {
      this.aviso.set(`"${archivo.name}" no es un archivo .csv.`);
      (evento.target as HTMLInputElement).value = '';
      return;
    }
    (tipo === 'facturas' ? this.facturas : this.contabilidad).set(archivo);
  }

  protected async usarEjemplos(): Promise<void> {
    this.aviso.set(null);
    try {
      const [f, c] = await Promise.all([
        this.descargar('facturas.csv'),
        this.descargar('contabilidad.csv'),
      ]);
      this.facturas.set(f);
      this.contabilidad.set(c);
    } catch {
      this.aviso.set('No se pudieron cargar los archivos de ejemplo.');
    }
  }

  protected enviar(): void {
    const facturas = this.facturas();
    const contabilidad = this.contabilidad();
    if (facturas && contabilidad) {
      this.procesar.emit({ facturas, contabilidad });
    }
  }

  private async descargar(nombre: string): Promise<File> {
    const respuesta = await fetch(`ejemplos/${nombre}`);
    if (!respuesta.ok) {
      throw new Error(nombre);
    }
    return new File([await respuesta.blob()], nombre, { type: 'text/csv' });
  }
}
