from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.schemas import HealthResponse, ReconciliationResponse
from app.config import MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB
from app.infrastructure.csv_reader import InvalidFileError
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/api")


def get_reconciliation_service() -> ReconciliationService:
    return ReconciliationService()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/reconciliations", response_model=ReconciliationResponse)
async def create_reconciliation(
    invoices: UploadFile = File(..., description="facturas.csv"),
    accounting: UploadFile = File(..., description="contabilidad.csv"),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationResponse:
    invoices_csv = await _read_upload(invoices, "facturas")
    accounting_csv = await _read_upload(accounting, "contabilidad")
    try:
        report = service.reconcile(invoices_csv, accounting_csv)
    except InvalidFileError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return ReconciliationResponse.from_domain(report)


async def _read_upload(upload: UploadFile, label: str) -> bytes:
    if not (upload.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El archivo de {label} debe ser un .csv (recibido: '{upload.filename}').",
        )
    content = await upload.read(MAX_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"El archivo de {label} supera los {MAX_FILE_SIZE_MB} MB permitidos.",
        )
    return content
