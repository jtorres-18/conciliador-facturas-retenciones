import { Component, WritableSignal, computed, input, output, signal } from '@angular/core';

export interface SelectedFiles {
  invoices: File;
  accounting: File;
}

type FileKind = 'invoices' | 'accounting';

interface UploadSlot {
  kind: FileKind;
  title: string;
  expectedFileName: string;
  file: WritableSignal<File | null>;
}

const SAMPLE_FILES_PATH = 'ejemplos';

@Component({
  selector: 'app-file-upload',
  templateUrl: './file-upload.html',
  styleUrl: './file-upload.css',
})
export class FileUpload {
  readonly loading = input(false);
  readonly submitted = output<SelectedFiles>();

  protected readonly invoicesFile = signal<File | null>(null);
  protected readonly accountingFile = signal<File | null>(null);
  protected readonly warning = signal<string | null>(null);

  protected readonly slots: UploadSlot[] = [
    { kind: 'invoices', title: 'Facturas de proveedores', expectedFileName: 'facturas.csv', file: this.invoicesFile },
    { kind: 'accounting', title: 'Registros contables', expectedFileName: 'contabilidad.csv', file: this.accountingFile },
  ];

  protected readonly canSubmit = computed(
    () => !!this.invoicesFile() && !!this.accountingFile() && !this.loading(),
  );

  protected onFileSelected(slot: UploadSlot, event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.item(0) ?? null;
    input.value = ''; // allows selecting the same file again
    this.warning.set(null);

    if (!file) {
      return;
    }
    if (!file.name.toLowerCase().endsWith('.csv')) {
      this.warning.set(`"${file.name}" no es un archivo .csv.`);
      return;
    }
    slot.file.set(file);
  }

  protected async useSampleFiles(): Promise<void> {
    this.warning.set(null);
    try {
      const [invoices, accounting] = await Promise.all([
        this.downloadSampleFile('facturas.csv'),
        this.downloadSampleFile('contabilidad.csv'),
      ]);
      this.invoicesFile.set(invoices);
      this.accountingFile.set(accounting);
    } catch {
      this.warning.set('No se pudieron cargar los archivos de ejemplo.');
    }
  }

  protected submit(): void {
    const invoices = this.invoicesFile();
    const accounting = this.accountingFile();
    if (invoices && accounting) {
      this.submitted.emit({ invoices, accounting });
    }
  }

  protected formatSize(file: File): string {
    return file.size < 1024 ? `${file.size} B` : `${(file.size / 1024).toFixed(1)} KB`;
  }

  private async downloadSampleFile(fileName: string): Promise<File> {
    const response = await fetch(`${SAMPLE_FILES_PATH}/${fileName}`);
    if (!response.ok) {
      throw new Error(`Sample file not found: ${fileName}`);
    }
    return new File([await response.blob()], fileName, { type: 'text/csv' });
  }
}
