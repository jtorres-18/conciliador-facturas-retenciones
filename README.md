# Conciliador de facturas y retenciones

Prototipo web que cruza las **facturas de proveedores** con los **registros contables**, aplica reglas básicas de validación tributaria y muestra qué facturas están correctas y cuáles tienen inconsistencias, con la causa de cada una.

- **Backend:** Python 3.12 + FastAPI (API REST).
- **Frontend:** Angular 22 (componentes standalone, signals).
- **Datos:** CSV ficticios en [`datos_prueba/`](datos_prueba/). No hay credenciales ni información real.

```
conciliador/
├── backend/            API en Python (ver "Arquitectura")
├── frontend/           Aplicación Angular
├── datos_prueba/       facturas.csv y contabilidad.csv de ejemplo
├── docker-compose.yml  Levanta backend y frontend con Docker
├── Presentacion_Conciliador.pptx   Presentación ejecutiva (5 diapositivas)
└── DECLARACION_IA.md   Declaración sobre el uso de IA generativa
```

El código (clases, funciones, variables) está en inglés; los textos que ve el usuario están en español. Las columnas de los CSV se mantienen en español porque así las entrega el área de negocio.

## Arquitectura

El backend está separado en capas sencillas, inspiradas en *Clean Architecture*. Cada capa solo depende de las que están más adentro, y las reglas de negocio no saben nada de FastAPI ni de HTTP:

```
backend/app/
├── main.py                         Crea la app FastAPI, CORS y registra las rutas
├── config.py                       Configuración (tamaño máximo de archivo, orígenes CORS)
├── api/                            Capa HTTP
│   ├── reconciliation_router.py    Endpoints: recibe archivos, traduce errores a códigos HTTP
│   └── schemas.py                  Contrato de respuesta (Pydantic, JSON en camelCase)
├── services/
│   └── reconciliation_service.py   Caso de uso: leer → evaluar reglas → armar resumen
├── domain/                         Corazón del negocio (sin dependencias externas)
│   ├── models.py                   Invoice, AccountingRecord, Finding, resultados
│   ├── rules.py                    Una clase por regla de validación
│   └── money.py                    Tolerancia de redondeo y formato en pesos
└── infrastructure/
    └── csv_reader.py               Lectura de CSV (codificación, separador, columnas)
```

Principios aplicados:

- **Responsabilidad única:** cada regla de negocio es una clase pequeña (`VatRule`, `InvoiceTotalRule`, `DuplicateInvoiceRule`…) que valida una sola cosa y se puede probar por separado (`tests/test_rules.py`).
- **Abierto/cerrado:** para agregar una regla nueva se crea una clase que herede de `InvoiceRule` y se registra en `DEFAULT_RULES`; el servicio no cambia.
- **Inversión de dependencias:** el servicio recibe la lista de reglas en su constructor y el endpoint recibe el servicio con `Depends`, así se pueden reemplazar en pruebas.
- **Cálculos en la entidad:** `Invoice.expected_vat()` y `Invoice.expected_total()` concentran las fórmulas tributarias en un solo lugar.

El frontend sigue la misma idea: un **servicio** (`ReconciliationService`) que habla con la API, un **modelo** con el contrato tipado y tres **componentes** de presentación (`FileUpload`, `Summary`, `ResultsTable`) que se comunican con `input()` / `output()`.

## Cómo ejecutarlo

Hay dos formas. Las dos dejan la aplicación en el mismo lugar: **frontend en http://localhost:4200** y **backend en http://localhost:8000**.

- **Opción A: Docker.** Es la más rápida: un solo comando y no hace falta instalar Python ni Node.
- **Opción B: manual.** Backend y frontend en dos terminales, útil para desarrollar.

### Opción A: Docker

Requisito: [Docker Desktop](https://www.docker.com/products/docker-desktop/) abierto (se probó con Docker 29.7 y Docker Compose 5.4).

Desde la carpeta raíz del proyecto:

```powershell
docker compose up --build
```

La primera vez tarda unos minutos porque descarga las imágenes y compila el frontend. Cuando aparezca que los dos contenedores iniciaron, abrir **http://localhost:4200** y seguir los pasos de [Probar el flujo](#probar-el-flujo).

Para detenerlo: `Ctrl + C` y luego `docker compose down`.

Qué levanta (`docker-compose.yml`):

| Servicio | Imagen | Puerto |
|---|---|---|
| `backend` | `python:3.12-slim` con FastAPI y Uvicorn | 8000 |
| `frontend` | Angular compilado con `node:24-alpine` y servido con `nginx:1.27-alpine` | 4200 |

El frontend espera a que el backend responda en `/api/health` antes de iniciar.

> Si los puertos 4200 u 8000 ya están ocupados (por ejemplo, por la opción B corriendo al mismo tiempo), detén esos procesos primero.

### Opción B: manual

#### Requisitos

| Herramienta | Versión con la que se probó | Descarga |
|---|---|---|
| Python | 3.12.10 (3.11 o superior debería funcionar) | https://www.python.org/downloads/ |
| Node.js | 24.20.0 LTS (Angular 22 exige Node 22.22.3 o superior, o 24.15 o superior) | https://nodejs.org/ |
| npm | 11.19.0 (se instala con Node) | — |

Las dependencias exactas están en `backend/requirements.txt` y `frontend/package.json`. Todo es software libre. Se necesita conexión a internet solo para instalar paquetes.

Se necesitan **dos terminales**: una para el backend y otra para el frontend. Los comandos son para PowerShell en Windows; en macOS/Linux solo cambia la activación del entorno virtual (se indica abajo).

#### 1. Backend (puerto 8000)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Debe aparecer `Uvicorn running on http://127.0.0.1:8000`. Comprobación rápida: abrir http://localhost:8000/api/health (responde `{"status":"ok"}`). La documentación interactiva de la API queda en http://localhost:8000/docs.

> Si PowerShell bloquea el script de activación, ejecuta antes `Set-ExecutionPolicy -Scope Process Bypass`.

#### 2. Frontend (puerto 4200)

```powershell
cd frontend
npm install
npm start
```

Cuando termine de compilar, abrir **http://localhost:4200**.

### Probar el flujo

1. En la pantalla, pulsar **"Usar archivos de ejemplo"** (carga `datos_prueba/facturas.csv` y `datos_prueba/contabilidad.csv`) o seleccionar los archivos manualmente.
2. Pulsar **"Procesar conciliación"**.
3. Revisar el resumen y la tabla de detalle; filtrar por **Todas / Correctas / Con inconsistencia**.

**Resultado esperado con los archivos de ejemplo:** 50 registros procesados (48 facturas distintas), **32 correctos y 18 con inconsistencia**.

| Causa | Cantidad | Facturas |
|---|---|---|
| Factura duplicada | 4 filas | FAC-0004, FAC-0015 (cada una aparece 2 veces) |
| Sin registro contable | 4 | FAC-0007, 0021, 0034, 0042 |
| Total ≠ base + IVA informado − retención | 5 | FAC-0009, 0023, 0036 y, por arrastre del IVA, FAC-0006 y 0018 |
| Contabilización pendiente | 3 | FAC-0011, 0027, 0039 |
| Campo obligatorio vacío | 3 | FAC-0013 (NIT), 0029 (concepto), 0042 (fecha) |
| IVA ≠ base × tarifa | 2 | FAC-0006, 0018 |
| Valor contable ≠ total de la factura | 2 | segunda fila de FAC-0004 y FAC-0015 |

Una factura puede tener varias causas (por eso la suma supera 18). Además hay 4 facturas correctas con una *advertencia* (ver supuesto 5).

### Pruebas automáticas

```powershell
cd backend ; python -m pytest                # 39 pruebas (reglas, servicio y API), con el entorno virtual activo
cd frontend ; npm test -- --watch=false      # 4 pruebas (flujo de la pantalla, filtro y errores)
```

## Reglas de negocio implementadas

Para cada fila de `facturas.csv` se evalúan estas reglas (archivo [`backend/app/domain/rules.py`](backend/app/domain/rules.py)):

| Código | Clase | Regla |
|---|---|---|
| `VAT_MISMATCH` | `VatRule` | `valor_iva` ≠ `base_gravable × tarifa_iva` |
| `TOTAL_MISMATCH` | `InvoiceTotalRule` | `total_factura` ≠ `base_gravable + valor_iva − valor_retencion` (valores informados); muestra además el total con IVA recalculado como referencia |
| `DUPLICATE_INVOICE` | `DuplicateInvoiceRule` | El `id_factura` aparece más de una vez en `facturas.csv` |
| `MISSING_ACCOUNTING_RECORD` | `MissingAccountingRecordRule` | No existe ningún registro con ese `id_factura` en `contabilidad.csv` |
| `PENDING_POSTING` | `PendingPostingRule` | Algún registro contable no está en estado `Contabilizada` |
| `ACCOUNTING_AMOUNT_MISMATCH` | `AccountingAmountRule` | La suma de `valor_debito` ≠ `total_factura` |
| `EMPTY_FIELD` | `RequiredFieldsRule` | Falta alguno de los 10 campos de la factura |
| `WITHHOLDING_MISMATCH` | `WithholdingRule` | `valor_retencion` ≠ `base_gravable × tarifa_retencion` *(adicional)* |
| `UNBALANCED_ENTRY` | `UnbalancedEntryRule` | Suma de débitos ≠ suma de créditos *(adicional)* |
| `DUPLICATE_ACCOUNTING_ENTRY` | `DuplicateAccountingEntryRule` | Más de una línea contable con valor para la misma factura *(solo advertencia: varias líneas no prueban un duplicado; pendiente de definición funcional)* |
| `NON_NUMERIC_VALUE`, `INVALID_DATE` | `NumericValuesRule`, `IssueDateFormatRule` | Formato inválido (fecha esperada `AAAA-MM-DD`) *(adicional)* |
| `INVALID_ACCOUNTING_DATA` | `AccountingDataQualityRule` | Campo contable vacío, débito/crédito no numérico o fecha inválida (fila y campo) |
| `ZERO_AMOUNT_ACCOUNTING_LINE` | `ZeroAmountLineRule` | Línea contable con débito y crédito en 0 *(solo advertencia)* |

Una factura es **Correcta** si pasó las validaciones del prototipo, es decir, no tiene ninguna inconsistencia; si tiene al menos una, es **Con inconsistencia** y se listan todas. En pantalla se muestra la descripción en español de cada causa, no el código.

## API

`POST /api/reconciliations` — `multipart/form-data` con los campos `invoices` (facturas.csv) y `accounting` (contabilidad.csv).

Respuesta 200 (JSON en camelCase, el estándar de JavaScript/TypeScript):

```json
{
  "summary": {
    "totalInvoices": 50, "uniqueInvoiceIds": 48, "correct": 32, "inconsistent": 18,
    "correctWithWarnings": 4,
    "errorsByCode": [{"code": "DUPLICATE_INVOICE", "description": "Factura duplicada", "count": 4}],
    "warningsByCode": [{"code": "ZERO_AMOUNT_ACCOUNTING_LINE", "description": "Línea contable con valor 0", "count": 7}],
    "accountingRecords": 50, "accountingWithoutInvoice": []
  },
  "details": [{
    "rowNumber": 7, "invoiceId": "FAC-0006", "status": "Con inconsistencia",
    "expectedVat": 190000, "vatAmount": 215000, "expectedTotal": 4015000, "totalWithRecalculatedVat": 3990000, "totalAmount": 3990000,
    "postedAmount": 3990000, "postingStatus": "Contabilizada",
    "errors": [{"code": "VAT_MISMATCH", "description": "IVA diferente a base × tarifa",
                "message": "IVA esperado 190.000 (3.800.000 × 0.05) pero la factura trae 215.000"}],
    "warnings": []
  }]
}
```

`rowNumber` es el número de línea en `facturas.csv`, para poder ubicar el registro en el archivo original. El esquema completo queda documentado en http://localhost:8000/docs.

Errores: `400` con `{"detail": "<mensaje>"}` si el archivo no es `.csv`, está vacío, no tiene registros o le faltan columnas; `413` si pesa más de 5 MB; `422` si falta alguno de los dos archivos.

`GET /api/health` — verificación de que el servicio está activo.

## Supuestos y decisiones

1. **Tolerancia de $1** en toda comparación de valores, para absorber redondeos.
2. **IVA y total son dos comprobaciones independientes.** El IVA se compara con `base × tarifa` (¿está bien calculado?). El total se compara con `base + valor_iva − valor_retencion`, usando los valores tal como están escritos en la factura (¿suman bien?). Si el `valor_iva` está mal, el total puede quedar mal por arrastre y se reportan ambos errores (FAC-0006 y FAC-0018); el detalle muestra el total con IVA recalculado como referencia.
3. **La retención se toma del campo `valor_retencion`** al validar el total, y se verifica aparte contra `base × tarifa_retencion`. La retención se calcula sobre la base gravable, que es como cuadran los datos de ejemplo.
4. **Contabilidad agrupada por `id_factura`**: se suman los débitos y créditos de todas sus líneas y se compara con `total_factura`.
5. **Líneas contables con débito y crédito en 0** (FAC-0001 a 0006 tienen una segunda línea así): no cuentan como inconsistencia ni afectan los cálculos; la factura queda con una **advertencia** visible.
6. **"Pendiente" es inconsistencia**, porque el proceso busca diferencias de estado de contabilización.
7. **Duplicados:** todas las filas que comparten `id_factura` se marcan como duplicadas (no se asume cuál es la "original"). Los duplicados se detectan solo por `id_factura`, no por combinación de proveedor + valor.
8. **Campo vacío es inconsistencia** para cualquiera de los 10 campos de la factura. En `contabilidad.csv` también: un campo vacío, un débito/crédito no numérico o una fecha de contabilización que no sea AAAA-MM-DD genera `INVALID_ACCOUNTING_DATA`, indicando fila y campo. Un valor vacío o ilegible nunca se convierte en 0; solo un `0` explícito es cero.
9. **El total cuenta registros procesados** (50, una fila de `facturas.csv` cada uno), e informa aparte las facturas distintas (48).
10. **Formato de archivos:** UTF-8 o Latin-1; separador coma o punto y coma (se detecta); fechas `AAAA-MM-DD`; tarifas como decimal (`0.19`).
11. **Sin persistencia:** el servicio no guarda nada; cada procesamiento es independiente.
12. **Datos de ejemplo duplicados:** `frontend/public/ejemplos/` contiene copia de los CSV de `datos_prueba/` solo para el botón "Usar archivos de ejemplo" (Angular no permite servir archivos fuera de su carpeta).

## Funcionalidades no incluidas

- Exportar el detalle (CSV/Excel) o paginar la tabla (con ~50 filas no hizo falta).
- Autenticación, persistencia, histórico de conciliaciones y manejo de varios periodos.
- Conciliación contra otras fuentes o corrección automática de las inconsistencias: el prototipo solo las reporta.
- Pruebas end-to-end automatizadas con navegador (el flujo completo se verificó manualmente).
- Despliegue o configuración de producción: el CORS permite solo `localhost:4200` y la URL del backend está en `frontend/src/app/services/reconciliation.service.ts` (`API_URL`).

## Declaración sobre IA generativa

Ver [`DECLARACION_IA.md`](DECLARACION_IA.md).
