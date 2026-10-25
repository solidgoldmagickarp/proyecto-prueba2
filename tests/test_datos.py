"""La base se arma completa, con fechas ISO, y de forma reproducible."""
import sqlite3

import pytest

from datos import descargar


def test_filas_de_cada_tabla_coinciden_con_el_csv(csv_dir, db):
    conexion = sqlite3.connect(db)
    for tabla in descargar.TABLAS:
        _, filas = descargar.filas_csv(csv_dir / f"{tabla}.csv")
        assert conexion.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0] == len(filas)


def test_fechas_iso_y_no_numeros_de_r(db):
    conexion = sqlite3.connect(db)
    assert conexion.execute("SELECT match_date FROM matches WHERE tournament_id = 'WC-1978' "
                            "AND stage_name = 'final'").fetchone()[0] == "1978-06-25"
    assert conexion.execute("SELECT start_date FROM tournaments WHERE year = 1930").fetchone()[0] == "1930-07-13"


def test_columnas_enteras_son_enteras(db):
    conexion = sqlite3.connect(db)
    assert conexion.execute("SELECT typeof(year) FROM tournaments LIMIT 1").fetchone()[0] == "integer"
    assert conexion.execute("SELECT typeof(own_goal) FROM goals LIMIT 1").fetchone()[0] == "integer"


def test_los_marcadores_de_dato_ausente_se_conservan(db):
    conexion = sqlite3.connect(db)
    assert conexion.execute("SELECT COUNT(*) FROM players WHERE birth_date = 'not available'").fetchone()[0] > 0


def test_la_base_es_reproducible(csv_dir, tmp_path):
    descargar.construir_db(csv_dir, tmp_path / "a.sqlite")
    descargar.construir_db(csv_dir, tmp_path / "b.sqlite")
    consulta = "SELECT * FROM matches ORDER BY match_id"
    a = sqlite3.connect(tmp_path / "a.sqlite").execute(consulta).fetchall()
    b = sqlite3.connect(tmp_path / "b.sqlite").execute(consulta).fetchall()
    assert a == b


def test_el_manifiesto_coincide_con_los_csv_locales(csv_dir):
    if csv_dir != descargar.CSV_DIR:
        pytest.skip("El manifiesto se compara con datos/csv/")
    descargar.verificar(csv_dir)


def test_tipo_columna():
    assert descargar.tipo_columna(["1", "-2", "30"]) == "INTEGER"
    assert descargar.tipo_columna(["1", "not applicable"]) == "TEXT"
    assert descargar.tipo_columna(["1", ""]) == "TEXT"
    assert descargar.tipo_columna([]) == "TEXT"
