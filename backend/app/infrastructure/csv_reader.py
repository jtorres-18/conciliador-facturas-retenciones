"""Reads the uploaded CSV files and checks their structure."""
import csv
import io
from dataclasses import dataclass


class InvalidFileError(Exception):
    """Unreadable file or invalid structure (answered as HTTP 400)."""


@dataclass(frozen=True)
class CsvRow:
    line_number: int  
    values: dict[str, str]


def read_csv(content: bytes, file_name: str, required_columns: list[str]) -> list[CsvRow]:
    text = _decode(content)
    if not text.strip():
        raise InvalidFileError(f"El archivo '{file_name}' está vacío.")

    reader = csv.DictReader(io.StringIO(text), delimiter=_detect_delimiter(text))
    headers = [_normalize_header(header) for header in (reader.fieldnames or [])]
    missing_columns = [column for column in required_columns if column not in headers]
    if missing_columns:
        raise InvalidFileError(
            f"Al archivo '{file_name}' le faltan las columnas: {', '.join(missing_columns)}."
        )

    rows = []
    for raw_row in reader:
        values = {
            _normalize_header(header): (value or "").strip()
            for header, value in raw_row.items()
            if header
        }
        if any(values.values()):
            rows.append(CsvRow(line_number=reader.line_num, values=values))

    if not rows:
        raise InvalidFileError(f"El archivo '{file_name}' no tiene registros.")
    return rows


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _detect_delimiter(text: str) -> str:
    """Excel in Spanish usually exports with ';' instead of ','."""
    first_line = next(line for line in text.splitlines() if line.strip())
    return ";" if first_line.count(";") > first_line.count(",") else ","


def _normalize_header(header: str | None) -> str:
    return (header or "").strip().lower()
