import pytest

from tests.sample_data import SAMPLE_DATA_DIR


@pytest.fixture(scope="session")
def sample_invoices_csv() -> bytes:
    return (SAMPLE_DATA_DIR / "facturas.csv").read_bytes()


@pytest.fixture(scope="session")
def sample_accounting_csv() -> bytes:
    return (SAMPLE_DATA_DIR / "contabilidad.csv").read_bytes()
