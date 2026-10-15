"""API REST del conciliador de facturas y retenciones."""
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.conciliador import ErrorArchivo, conciliar

TAMANO_MAXIMO = 5 * 1024 * 1024  # 5 MB por archivo

app = FastAPI(
    title="Conciliador de facturas y retenciones",
    description="Cruza facturas de proveedores con los registros contables y reporta inconsistencias.",
    version="1.0.0",
)

# El frontend Angular corre en el puerto 4200 durante el desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _leer(archivo: UploadFile, nombre: str) -> bytes:
    if not (archivo.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, f"El archivo de {nombre} debe ser un .csv (recibido: '{archivo.filename}').")
    contenido = await archivo.read(TAMANO_MAXIMO + 1)
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(413, f"El archivo de {nombre} supera los 5 MB permitidos.")
    return contenido


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}


@app.post("/api/conciliacion")
async def procesar_conciliacion(
    facturas: UploadFile = File(..., description="facturas.csv"),
    contabilidad: UploadFile = File(..., description="contabilidad.csv"),
):
    """Recibe los dos CSV y devuelve `resumen` y `detalle` de la conciliación."""
    facturas_csv = await _leer(facturas, "facturas")
    contabilidad_csv = await _leer(contabilidad, "contabilidad")
    try:
        return conciliar(facturas_csv, contabilidad_csv)
    except ErrorArchivo as error:
        raise HTTPException(400, str(error)) from error
