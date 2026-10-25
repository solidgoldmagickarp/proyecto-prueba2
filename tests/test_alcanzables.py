"""Cada tarea respondible se puede resolver solo con las herramientas del kit.

Cada solucionador usa únicamente lo que devuelven las herramientas; su resultado se compara con la
respuesta que recalculó el SQL de `verificadores.py`. Si las dos rutas coinciden, la respuesta está
bien y las herramientas alcanzan para llegar a ella.
"""
import json

import pytest

from tareas import verificadores

pytestmark = pytest.mark.usefixtures("herramientas_con_db")


def _resolver(m, nombre, seleccion=None):
    """Un nombre ambiguo se elige por selección entre los candidatos, y se vuelve a llamar con el id."""
    respuesta = m.goles(nombre)
    if "candidatos" not in respuesta:
        return respuesta
    elegidos = [c for c in respuesta["candidatos"] if "id" in c and c["selecciones"] == [seleccion]]
    assert len(elegidos) == 1, respuesta
    return m.goles(elegidos[0]["id"])


def _final(m, anio):
    return m.buscar_torneos(anio=anio)[0]["final"]


def _nacimiento(m, nombre):
    return m.buscar_jugador(nombre)[0]["nacimiento"]


def _edad_del_goleador(m, anio):
    goleador = m.goleadores(anio, 1)["goleadores"][0]["jugador"]
    return m.calcular(f"{_final(m, anio)} - {_nacimiento(m, goleador)}")["anios_cumplidos"]


def _goles_de_francia_1998(m):
    total = 0
    for p in m.partidos(1998):
        local, visitante = (int(x) for x in p["resultado"].split("–"))
        total += local if p["local"] == "France" else visitante if p["visitante"] == "France" else 0
    return total


def _tres_de_2002(m):
    total = 0
    for goleador in m.goleadores(2002, 3)["goleadores"]:
        total += _resolver(m, goleador["jugador"], goleador["seleccion"])["total"]
    return total


def _sin_goles(m):
    messi = m.buscar_jugador("Messi")[0]
    return len(messi["torneos"]) - len(m.goles(messi["id"])["por_torneo"])


SOLUCIONADORES = {
    "mun-001": lambda m: [str(t["torneo"]) for t in m.buscar_torneos(campeon="Uruguay")],
    "mun-002": lambda m: m.buscar_torneos(anio=2015, femenino=True)[0]["campeon"],
    "mun-003": lambda m: m.goles("Messi", torneo=2014)["goles"],
    "mun-004": lambda m: len(m.partidos(1986)),
    "mun-005": lambda m: _final(m, 2010),
    "mun-006": lambda m: _nacimiento(m, "Diego Maradona"),
    "mun-007": lambda m: m.buscar_torneos(anio=1994)[0]["sede"],
    "mun-008": lambda m: m.goleadores(2002, 1)["goleadores"][0]["goles"],
    "mun-009": lambda m: len(m.buscar_torneos()),
    "mun-010": lambda m: m.goles("Pelé")["total"],
    "mun-011": lambda m: m.goles("Messi")["total"],
    "mun-014": lambda m: m.calcular(f"{_final(m, 1990)} - {_final(m, 1986)}")["dias"],
    "mun-015": lambda m: m.goles("Mbappé", torneo=2022)["goles"] - m.goles("Messi", torneo=2022)["goles"],
    "mun-016": _sin_goles,
    "mun-017": lambda m: m.calcular(f"2022 - {m.buscar_torneos()[0]['torneo']}")["resultado"],
    "mun-018": lambda m: sum(1 for p in m.partidos(2022) if p["penales"]),
    "mun-019": lambda m: [g["jugador"] for g in m.goleadores(1982, 2)["goleadores"]],
    "mun-020": lambda m: m.calcular(f"{_final(m, 2022)} - {_nacimiento(m, 'Lionel Messi')}")["anios_cumplidos"],
    "mun-021": lambda m: m.buscar_torneos(campeon="Argentina")[0]["sede"],
    "mun-024": lambda m: _edad_del_goleador(m, 1978),
    "mun-025": lambda m: sum(m.goleadores(t["torneo"], 1)["goleadores"][0]["goles"]
                             for t in m.buscar_torneos(campeon="Argentina")),
    "mun-026": lambda m: m.calcular(f"{_nacimiento(m, 'Lionel Messi')} - {_nacimiento(m, 'Diego Maradona')}")["dias"],
    "mun-027": _goles_de_francia_1998,
    "mun-028": lambda m: m.goleadores(1986, 1)["goleadores"][0]["goles"] - m.goles("Maradona", torneo=1986)["goles"],
    "mun-029": lambda m: _edad_del_goleador(m, 2014),
    "mun-030": _tres_de_2002,
}


def _tareas():
    return json.loads(verificadores.TAREAS_JSON.read_text(encoding="utf-8"))


def test_hay_un_solucionador_por_cada_tarea_respondible():
    respondibles = {t["id"] for t in _tareas() if t["respondible"]}
    assert respondibles == set(SOLUCIONADORES)


@pytest.mark.parametrize("tarea", [t for t in _tareas() if t["respondible"]], ids=lambda t: t["id"])
def test_las_herramientas_llegan_a_la_respuesta(herramientas_con_db, tarea):
    obtenida = SOLUCIONADORES[tarea["id"]](herramientas_con_db)
    if tarea["tipo"] == "lista":
        assert sorted(obtenida) == sorted(tarea["respuesta"])
    else:
        assert obtenida == tarea["respuesta"]


def test_ninguna_herramienta_da_lo_que_piden_las_imposibles(herramientas_con_db):
    m = herramientas_con_db
    assert "error" in m.buscar_torneos(anio=2026)
    assert "error" in m.buscar_torneos(anio=2023, femenino=True)
    campos = set(m.partidos(1990)[0])
    assert not any(palabra in campo for campo in campos for palabra in ("espectador", "asistencia", "posesion"))
