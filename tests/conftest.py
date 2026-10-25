"""Arma una base desde los CSV una sola vez; si no hay CSV, los tests que la usan se saltean.

Los CSV salen de `datos/csv/` o de la carpeta indicada en WORLDCUP_CSV_DIR.
"""
import os
from pathlib import Path

import pytest

from datos import descargar
from herramientas import mundial


def _carpeta_csv() -> Path | None:
    indicada = os.environ.get("WORLDCUP_CSV_DIR")
    candidatas = [Path(indicada)] if indicada else []
    candidatas.append(descargar.CSV_DIR)
    return next((c for c in candidatas if (c / "tournaments.csv").exists()), None)


@pytest.fixture(scope="session")
def csv_dir() -> Path:
    carpeta = _carpeta_csv()
    if carpeta is None:
        pytest.skip("Faltan los CSV: corré `uv run datos/descargar.py` o definí WORLDCUP_CSV_DIR")
    return carpeta


@pytest.fixture(scope="session")
def db(csv_dir, tmp_path_factory) -> Path:
    ruta = tmp_path_factory.mktemp("datos") / "worldcup.sqlite"
    descargar.construir_db(csv_dir, ruta)
    return ruta


@pytest.fixture
def herramientas_con_db(db, monkeypatch):
    """Las herramientas leen la base armada para el test, no la del disco."""
    monkeypatch.setenv("MUNDIAL_DB", str(db))
    mundial._conexion.cache_clear()
    mundial._jugadores.cache_clear()
    yield mundial
    mundial._conexion.cache_clear()
    mundial._jugadores.cache_clear()
