"""Descarga las tablas de la Fjelstul World Cup Database y arma la base SQLite del kit.

La base se arma acá, a partir de los CSV, porque el worldcup.db del repositorio original guarda las
fechas como números de días de R (por ejemplo '-14417.0' para 1930-07-13). Los CSV traen fechas ISO.

    uv run datos/descargar.py                       # baja los CSV del commit fijado y arma la base
    uv run datos/descargar.py --desde <carpeta>     # usa una copia local de data-csv/
    uv run datos/descargar.py --escribir-manifest   # mantenimiento: registra los sha256 actuales
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import sqlite3
import sys
import urllib.request
from pathlib import Path

REPO = "jfjelstul/worldcup"
COMMIT = "35a8667f518b07469182ae16d35574dd0e7a00fb"
TABLAS = ("tournaments", "matches", "goals", "players", "squads", "teams", "stadiums", "award_winners")

RAIZ = Path(__file__).resolve().parent
CSV_DIR = RAIZ / "csv"
DB = RAIZ / "worldcup.sqlite"
MANIFEST = RAIZ / "MANIFEST.json"
URL = "https://raw.githubusercontent.com/{repo}/{commit}/data-csv/{tabla}.csv"

ENTERO = re.compile(r"-?\d+")


def sha256_archivo(ruta: Path) -> str:
    digest = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def filas_csv(ruta: Path) -> tuple[list[str], list[list[str]]]:
    with open(ruta, encoding="utf-8", newline="") as archivo:
        lector = csv.reader(archivo)
        encabezado = next(lector)
        return encabezado, list(lector)


def descargar(destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for tabla in TABLAS:
        url = URL.format(repo=REPO, commit=COMMIT, tabla=tabla)
        print(f"bajando {url}")
        with urllib.request.urlopen(url, timeout=60) as respuesta:
            (destino / f"{tabla}.csv").write_bytes(respuesta.read())


def copiar_desde(origen: Path, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for tabla in TABLAS:
        archivo = origen / f"{tabla}.csv"
        if not archivo.exists():
            sys.exit(f"Falta {archivo}")
        shutil.copyfile(archivo, destino / archivo.name)


def escribir_manifest(carpeta: Path) -> None:
    archivos = {}
    for tabla in TABLAS:
        ruta = carpeta / f"{tabla}.csv"
        archivos[ruta.name] = {"sha256": sha256_archivo(ruta), "filas": len(filas_csv(ruta)[1])}
    MANIFEST.write_text(
        json.dumps({"repo": REPO, "commit": COMMIT, "archivos": archivos}, indent=2) + "\n",
        encoding="utf-8")


def verificar(carpeta: Path) -> None:
    """Falla si algún CSV no coincide con el manifiesto: no se arma la base con datos distintos."""
    esperado = json.loads(MANIFEST.read_text(encoding="utf-8"))["archivos"]
    distintos = [nombre for nombre, datos in esperado.items()
                 if sha256_archivo(carpeta / nombre) != datos["sha256"]]
    if distintos:
        sys.exit(f"Los CSV no coinciden con MANIFEST.json: {', '.join(distintos)}. "
                 "Si el manifiesto se escribió desde una copia local, revisá las diferencias "
                 "antes de regenerarlo con --escribir-manifest.")


def tipo_columna(valores: list[str]) -> str:
    """INTEGER solo si todos los valores son enteros; si no, TEXT con los valores tal cual vienen."""
    return "INTEGER" if valores and all(ENTERO.fullmatch(v) for v in valores) else "TEXT"


def construir_db(carpeta: Path, destino: Path) -> dict[str, int]:
    """Arma la base SQLite y devuelve las filas de cada tabla."""
    parcial = destino.with_suffix(".parcial")
    parcial.unlink(missing_ok=True)
    conteos = {}
    conexion = sqlite3.connect(parcial)
    try:
        for tabla in TABLAS:
            encabezado, filas = filas_csv(carpeta / f"{tabla}.csv")
            columnas = ", ".join(
                f'"{nombre}" {tipo_columna([fila[i] for fila in filas])}'
                for i, nombre in enumerate(encabezado))
            conexion.execute(f'CREATE TABLE "{tabla}" ({columnas})')
            marcas = ", ".join("?" * len(encabezado))
            conexion.executemany(f'INSERT INTO "{tabla}" VALUES ({marcas})', filas)
            conteos[tabla] = conexion.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
            if conteos[tabla] != len(filas):
                sys.exit(f"{tabla}: se cargaron {conteos[tabla]} filas de {len(filas)}")
        conexion.commit()
    finally:
        conexion.close()
    parcial.replace(destino)
    return conteos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--desde", type=Path, help="carpeta data-csv/ local, en lugar de la descarga")
    parser.add_argument("--escribir-manifest", action="store_true",
                        help="registra los sha256 de los CSV actuales (mantenimiento)")
    argumentos = parser.parse_args()

    if argumentos.desde:
        copiar_desde(argumentos.desde, CSV_DIR)
    elif not argumentos.escribir_manifest:
        descargar(CSV_DIR)

    if argumentos.escribir_manifest:
        escribir_manifest(CSV_DIR)
        print(f"Manifiesto escrito en {MANIFEST}")
        return

    verificar(CSV_DIR)
    conteos = construir_db(CSV_DIR, DB)
    print(f"Base armada en {DB}")
    for tabla, filas in conteos.items():
        print(f"  {tabla}: {filas} filas")


if __name__ == "__main__":
    main()
