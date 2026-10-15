# Conciliador de facturas y retenciones

Prototipo web que cruza las **facturas de proveedores** con los **registros contables**, aplica reglas básicas de validación tributaria y muestra qué facturas están correctas y cuáles tienen inconsistencias, con la causa de cada una.

- **Backend:** Python 3.12 + FastAPI (API REST).
- **Frontend:** Angular 22 (componentes standalone, signals).
- **Datos:** CSV ficticios en [`datos_prueba/`](datos_prueba/). No hay credenciales ni información real.

```
conciliador/
├── backend/            API en Python (app/conciliador.py = reglas, app/main.py = endpoints, tests/)
├── frontend/           Aplicación Angular
├── datos_prueba/       facturas.csv y contabilidad.csv de ejemplo
├── Presentacion_Conciliador.pptx   Presentación ejecutiva (5 diapositivas)
└── DECLARACION_IA.md   Declaración sobre el uso de IA generativa
```

## Requisitos

| Herramienta | Versión con la que se probó | Descarga |
|---|---|---|
| Python | 3.12.10 (3.11 o superior debería funcionar) | https://www.python.org/downloads/ |
| Node.js | 24.20.0 LTS (Angular 22 exige Node 22.22.3 o superior, o 24.15 o superior) | https://nodejs.org/ |
| npm | 11.19.0 (se instala con Node) | — |

Las dependencias exactas están en `backend/requirements.txt` y `frontend/package.json`. Todo es software libre. Se necesita conexión a internet solo para instalar paquetes.

## Cómo ejecutarlo

Se necesitan **dos terminales**: una para el backend y otra para el frontend. Los comandos son para PowerShell en Windows; en macOS/Linux solo cambia la activación del entorno virtual (se indica abajo).

### 1. Backend (puerto 8000)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Debe aparecer `Uvicorn running on http://127.0.0.1:8000`. Comprobación rápida: abrir http://localhost:8000/api/salud (responde `{"estado":"ok"}`). La documentación interactiva de la API queda en http://localhost:8000/docs.

> Si PowerShell bloquea el script de activación, ejecuta antes `Set-ExecutionPolicy -Scope Process Bypass`.

### 2. Frontend (puerto 4200)

```powershell
cd frontend
npm install
npm start
```

Cuando termine de compilar, abrir **http://localhost:4200**.

### 3. Probar el flujo

1. En la pantalla, pulsar **"Usar archivos de ejemplo"** (carga `datos_prueba/facturas.csv` y `datos_prueba/contabilidad.csv`) o seleccionar los archivos manualmente.
2. Pulsar **"Procesar conciliación"**.
3. Revisar el resumen y la tabla de detalle; filtrar por **Todas / Correctas / Con inconsistencia**.

**Resultado esperado con los archivos de ejemplo:** 50 filas de factura (48 números distintos), **32 correctas y 18 con inconsistencia**.

| Causa | Cantidad | Facturas |
|---|---|---|
| Factura duplicada | 4 filas | FAC-0004, FAC-0015 (cada una aparece 2 veces) |
| Sin registro contable | 4 | FAC-0007, 0021, 0034, 0042 |
| Total ≠ base + IVA − retención | 3 | FAC-0009, 0023, 0036 |
| Contabilización pendiente | 3 | FAC-0011, 0027, 0039 |
| Campo obligatorio vacío | 3 | FAC-0013 (NIT), 0029 (concepto), 0042 (fecha) |
| IVA ≠ base × tarifa | 2 | FAC-0006, 0018 |
| Valor contable ≠ total de la factura | 2 | segunda fila de FAC-0004 y FAC-0015 |

Una factura puede tener varias causas (por eso la suma supera 18). Además hay 4 facturas correctas con una *advertencia* (ver supuesto 5).

### Pruebas automáticas

```powershell
cd backend ; pytest                          # 31 pruebas (reglas y API), con el entorno virtual activo
cd frontend ; npm test -- --watch=false      # 4 pruebas (flujo de la pantalla, filtro y errores)
```

## Reglas de negocio implementadas

Para cada fila de `facturas.csv` se evalúa (módulo [`backend/app/conciliador.py`](backend/app/conciliador.py)):

| Código | Regla |
|---|---|
| `IVA_INCORRECTO` | `valor_iva` ≠ `base_gravable × tarifa_iva` |
| `TOTAL_INCORRECTO` | `total_factura` ≠ `base_gravable + IVA esperado − valor_retencion` |
| `DUPLICADA` | El `id_factura` aparece más de una vez en `facturas.csv` |
| `SIN_CONTABILIDAD` | No existe ningún registro con ese `id_factura` en `contabilidad.csv` |
| `ESTADO_PENDIENTE` | Algún registro contable no está en estado `Contabilizada` |
| `VALOR_CONTABLE_DIFERENTE` | La suma de `valor_debito` ≠ `total_factura` |
| `CAMPO_VACIO` | Falta alguno de los 10 campos de la factura |
| `RETENCION_INCORRECTA` | `valor_retencion` ≠ `base_gravable × tarifa_retencion` *(adicional)* |
| `DESCUADRE_CONTABLE` | Suma de débitos ≠ suma de créditos *(adicional)* |
| `CONTABILIDAD_DUPLICADA` | Más de una línea contable con valor para la misma factura *(adicional)* |
| `VALOR_NO_NUMERICO`, `FECHA_INVALIDA` | Formato inválido (fecha esperada `AAAA-MM-DD`) *(adicional)* |

Una factura es **Correcta** si no tiene ninguna causa; si tiene al menos una, es **Con inconsistencia** y se listan todas.

## API

`POST /api/conciliacion` — `multipart/form-data` con los campos `facturas` y `contabilidad` (archivos `.csv`).

Respuesta 200:

```json
{
  "resumen": {
    "total_facturas": 50, "ids_unicos": 48, "correctas": 32, "con_inconsistencia": 18,
    "correctas_con_advertencia": 4,
    "por_causa": [{"codigo": "DUPLICADA", "descripcion": "Factura duplicada", "cantidad": 4}],
    "por_advertencia": [], "registros_contables": 50, "contabilidad_sin_factura": []
  },
  "detalle": [{
    "fila": 7, "id_factura": "FAC-0006", "estado": "Con inconsistencia",
    "iva_esperado": 190000, "valor_iva": 215000, "total_esperado": 3990000, "total_factura": 3990000,
    "valor_contabilizado": 3990000,
    "causas": [{"codigo": "IVA_INCORRECTO", "mensaje": "IVA esperado 190.000 (3.800.000 × 0.05) pero la factura trae 215.000"}],
    "advertencias": []
  }]
}
```

`fila` es el número de línea en `facturas.csv`, para poder ubicar el registro en el archivo original.

Errores: `400` con `{"detail": "<mensaje>"}` si el archivo no es `.csv`, está vacío, no tiene registros o le faltan columnas; `413` si pesa más de 5 MB; `422` si falta alguno de los dos archivos.

`GET /api/salud` — verificación de que el servicio está activo.

## Supuestos y decisiones

1. **Tolerancia de $1** en toda comparación de valores, para absorber redondeos.
2. **El total se valida con el IVA esperado** (base × tarifa), no con el IVA que trae la factura. Así un error en el campo `valor_iva` (FAC-0006 y FAC-0018, donde el total sí es consistente) se reporta una sola vez en lugar de generar además un falso error de total. El detalle muestra IVA esperado, IVA informado, total esperado y total informado.
3. **La retención se toma del campo `valor_retencion`** al validar el total, y se verifica aparte contra `base × tarifa_retencion`. La retención se calcula sobre la base gravable, que es como cuadran los datos de ejemplo.
4. **Contabilidad agrupada por `id_factura`**: se suman los débitos y créditos de todas sus líneas y se compara con `total_factura`.
5. **Líneas contables con débito y crédito en 0** (FAC-0001 a 0006 tienen una segunda línea así): no cuentan como inconsistencia ni afectan los cálculos; la factura queda con una **advertencia** visible.
6. **"Pendiente" es inconsistencia**, porque el proceso busca diferencias de estado de contabilización.
7. **Duplicados:** todas las filas que comparten `id_factura` se marcan como duplicadas (no se asume cuál es la "original"). Los duplicados se detectan solo por `id_factura`, no por combinación de proveedor + valor.
8. **Campo vacío es inconsistencia** para cualquiera de los 10 campos de la factura. En `contabilidad.csv` solo se exige que existan las columnas.
9. **"Total de facturas" cuenta filas procesadas** (50), e informa aparte los números de factura distintos (48).
10. **Formato de archivos:** UTF-8 o Latin-1; separador coma o punto y coma (se detecta); fechas `AAAA-MM-DD`; tarifas como decimal (`0.19`).
11. **Sin persistencia:** el servicio no guarda nada; cada procesamiento es independiente.
12. **Datos de ejemplo duplicados:** `frontend/public/ejemplos/` contiene copia de los CSV de `datos_prueba/` solo para el botón "Usar archivos de ejemplo" (Angular no permite servir archivos fuera de su carpeta).

## Funcionalidades no incluidas

- Exportar el detalle (CSV/Excel) o paginar la tabla (con ~50 filas no hizo falta).
- Autenticación, persistencia, histórico de conciliaciones y manejo de varios periodos.
- Conciliación contra otras fuentes o corrección automática de las inconsistencias: el prototipo solo las reporta.
- Pruebas end-to-end automatizadas con navegador (el flujo completo se verificó manualmente).
- Despliegue o configuración de producción: el CORS permite solo `localhost:4200` y la URL del backend está en `frontend/src/app/services/conciliacion.service.ts` (`API_URL`).

## Declaración sobre IA generativa

Ver [`DECLARACION_IA.md`](DECLARACION_IA.md).
