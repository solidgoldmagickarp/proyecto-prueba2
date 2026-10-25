"""El archivo de tareas públicas cumple el formato y coincide con el recálculo desde la base."""
import datetime as dt
import json
import sqlite3
from collections import Counter

import pytest

from tareas import verificadores

TIPOS = {"numero", "texto", "lista", "fecha"}
DIFICULTADES = {"facil", "media", "dificil"}
CAMPOS = {"id", "pregunta", "respuesta", "tipo", "tolerancia", "dificultad", "respondible"}


@pytest.fixture(scope="module")
def tareas():
    return json.loads(verificadores.TAREAS_JSON.read_text(encoding="utf-8"))


def test_formato_de_cada_tarea(tareas):
    for t in tareas:
        assert set(t) == CAMPOS, t["id"]
        assert t["tipo"] in TIPOS and t["dificultad"] in DIFICULTADES, t["id"]
        assert isinstance(t["tolerancia"], (int, float)) and t["tolerancia"] >= 0, t["id"]
        assert t["pregunta"].endswith("?") or t["pregunta"].endswith("."), t["id"]


def test_ids_unicos_y_ordenados(tareas):
    ids = [t["id"] for t in tareas]
    assert ids == sorted(set(ids))


def test_respuesta_nula_si_y_solo_si_no_es_respondible(tareas):
    for t in tareas:
        assert (t["respuesta"] is None) == (not t["respondible"]), t["id"]


def test_tipo_de_cada_respuesta(tareas):
    for t in tareas:
        r = t["respuesta"]
        if r is None:
            continue
        if t["tipo"] == "numero":
            assert isinstance(r, (int, float)) and not isinstance(r, bool), t["id"]
        elif t["tipo"] == "fecha":
            dt.date.fromisoformat(r)
        elif t["tipo"] == "lista":
            assert isinstance(r, list) and r and all(isinstance(x, str) for x in r), t["id"]
        else:
            assert isinstance(r, str) and r, t["id"]


def test_mezcla_de_dificultades_e_imposibles(tareas):
    por_nivel = Counter(t["dificultad"] for t in tareas)
    assert set(por_nivel) == DIFICULTADES
    assert por_nivel["dificil"] >= 5
    assert sum(not t["respondible"] for t in tareas) >= 3
    assert 25 <= len(tareas) <= 35


def test_preguntas_sin_repetir(tareas):
    preguntas = [t["pregunta"] for t in tareas]
    assert len(set(preguntas)) == len(preguntas)


def test_coincide_con_el_recalculo(db):
    assert verificadores.comparar(sqlite3.connect(db)) == []


def test_detecta_una_respuesta_adulterada(db, tmp_path):
    adulteradas = json.loads(verificadores.TAREAS_JSON.read_text(encoding="utf-8"))
    adulteradas[2]["respuesta"] += 1
    ruta = tmp_path / "adulteradas.json"
    ruta.write_text(json.dumps(adulteradas), encoding="utf-8")
    diferencias = verificadores.comparar(sqlite3.connect(db), ruta)
    assert len(diferencias) == 1 and adulteradas[2]["id"] in diferencias[0]


def test_una_imposible_deja_de_serlo_si_aparecen_los_datos(db, tmp_path):
    copia = tmp_path / "con_2026.sqlite"
    conexion = sqlite3.connect(copia)
    sqlite3.connect(db).backup(conexion)
    conexion.execute("INSERT INTO tournaments (tournament_id, tournament_name, year) VALUES "
                     "('WC-2026', '2026 FIFA Men''s World Cup', 2026)")
    with pytest.raises(AssertionError):
        verificadores.ausencia_de_datos(conexion, anio=2026)
