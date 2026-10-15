import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { App } from './app';
import { Resultado } from './models/conciliacion.model';
import { API_URL } from './services/conciliacion.service';

const RESULTADO: Resultado = {
  resumen: {
    total_facturas: 2,
    ids_unicos: 2,
    correctas: 1,
    con_inconsistencia: 1,
    correctas_con_advertencia: 0,
    por_causa: [{ codigo: 'SIN_CONTABILIDAD', descripcion: 'Sin registro contable', cantidad: 1 }],
    por_advertencia: [],
    registros_contables: 1,
    contabilidad_sin_factura: [],
  },
  detalle: [
    {
      fila: 2, id_factura: 'F1', nit_proveedor: '900', fecha_factura: '2026-01-01', concepto: 'Soporte',
      base_gravable: 100, valor_iva: 0, iva_esperado: 0, valor_retencion: 0, total_factura: 100,
      total_esperado: 100, valor_contabilizado: 100, estado_contable: 'Contabilizada',
      estado: 'Correcta', causas: [], advertencias: [],
    },
    {
      fila: 3, id_factura: 'F2', nit_proveedor: '901', fecha_factura: '2026-01-02', concepto: 'Soporte',
      base_gravable: 200, valor_iva: 0, iva_esperado: 0, valor_retencion: 0, total_factura: 200,
      total_esperado: 200, valor_contabilizado: null, estado_contable: null,
      estado: 'Con inconsistencia',
      causas: [{ codigo: 'SIN_CONTABILIDAD', mensaje: 'No existe ningún registro contable para esta factura' }],
      advertencias: [],
    },
  ],
};

function archivo(nombre: string): File {
  return new File(['id_factura\n'], nombre, { type: 'text/csv' });
}

describe('App', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  function procesar() {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    (fixture.componentInstance as any).procesar({
      facturas: archivo('facturas.csv'),
      contabilidad: archivo('contabilidad.csv'),
    });
    fixture.detectChanges();
    return fixture;
  }

  it('envía los dos archivos al backend y muestra el resumen y el detalle', () => {
    const fixture = procesar();
    const peticion = http.expectOne(`${API_URL}/conciliacion`);
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body.get('facturas').name).toBe('facturas.csv');
    expect(peticion.request.body.get('contabilidad').name).toBe('contabilidad.csv');
    expect(fixture.nativeElement.textContent).toContain('Procesando');

    peticion.flush(RESULTADO);
    fixture.detectChanges();
    const texto = fixture.nativeElement.textContent as string;
    expect(texto).not.toContain('Procesando');
    expect(texto).toContain('Facturas procesadas');
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(2);
  });

  it('filtra la tabla por estado', () => {
    const fixture = procesar();
    http.expectOne(`${API_URL}/conciliacion`).flush(RESULTADO);
    fixture.detectChanges();

    const botones = Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll('.filtro'));
    botones.find((b) => b.textContent?.includes('Con inconsistencia'))!.click();
    fixture.detectChanges();

    const filas = fixture.nativeElement.querySelectorAll('tbody tr');
    expect(filas.length).toBe(1);
    expect(filas[0].textContent).toContain('F2');
  });

  it('muestra el mensaje del backend cuando hay un error de archivo', () => {
    const fixture = procesar();
    http.expectOne(`${API_URL}/conciliacion`).flush(
      { detail: "Al archivo 'facturas.csv' le faltan las columnas: nit_proveedor." },
      { status: 400, statusText: 'Bad Request' },
    );
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role=alert]').textContent).toContain('le faltan las columnas');
    expect(fixture.nativeElement.querySelector('app-resumen')).toBeNull();
  });

  it('avisa cuando no se puede conectar con el backend', () => {
    const fixture = procesar();
    http.expectOne(`${API_URL}/conciliacion`).error(new ProgressEvent('error'));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role=alert]').textContent).toContain('No se pudo conectar');
  });
});
