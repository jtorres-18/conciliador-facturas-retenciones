// Contrato de la API (los nombres en snake_case son los mismos que devuelve FastAPI).

export type EstadoFactura = 'Correcta' | 'Con inconsistencia';

export interface Causa {
  codigo: string;
  mensaje: string;
}

export interface DetalleFactura {
  fila: number;
  id_factura: string;
  nit_proveedor: string;
  fecha_factura: string;
  concepto: string;
  base_gravable: number | null;
  valor_iva: number | null;
  iva_esperado: number | null;
  valor_retencion: number | null;
  total_factura: number | null;
  total_esperado: number | null;
  valor_contabilizado: number | null;
  estado_contable: string | null;
  estado: EstadoFactura;
  causas: Causa[];
  advertencias: Causa[];
}

export interface ConteoCausa {
  codigo: string;
  descripcion: string;
  cantidad: number;
}

export interface Resumen {
  total_facturas: number;
  ids_unicos: number;
  correctas: number;
  con_inconsistencia: number;
  correctas_con_advertencia: number;
  por_causa: ConteoCausa[];
  por_advertencia: ConteoCausa[];
  registros_contables: number;
  contabilidad_sin_factura: string[];
}

export interface Resultado {
  resumen: Resumen;
  detalle: DetalleFactura[];
}
