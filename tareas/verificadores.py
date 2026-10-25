"""Define las tareas públicas del Mundial y recalcula cada respuesta con SQL, sin pasar por el modelo ni por las herramientas.

    uv run tareas/verificadores.py              # recalcula y compara con mundial_publicas.json
    uv run tareas/verificadores.py --escribir   # regenera mundial_publicas.json desde las definiciones
"""
import argparse
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / "datos" / "worldcup.sqlite"
TAREAS_JSON = Path(__file__).resolve().parent / "mundial_publicas.json"

SOLO_HOMBRES = "tournament_name NOT LIKE '%Women%'"


def _uno(c, consulta: str, *parametros):
    filas = c.execute(consulta, parametros).fetchall()
    assert len(filas) == 1, f"se esperaba una fila y hay {len(filas)}: {consulta} {parametros}"
    return filas[0][0]


def _fecha(texto: str) -> dt.date:
    return dt.date.fromisoformat(texto)


def _edad(nacimiento: str, fecha: str) -> int:
    n, f = _fecha(nacimiento), _fecha(fecha)
    return f.year - n.year - ((f.month, f.day) < (n.month, n.day))


def _final(c, anio: int) -> str:
    return _uno(c, "SELECT m.match_date FROM matches m JOIN tournaments t USING (tournament_id) "
                   "WHERE t.year = ? AND m.stage_name = 'final'", anio)


def _nacimiento(c, apellido: str, nombre: str | None = None) -> str:
    if nombre is None:
        return _uno(c, "SELECT birth_date FROM players WHERE family_name = ? AND given_name = 'not applicable'",
                    apellido)
    return _uno(c, "SELECT birth_date FROM players WHERE family_name = ? AND given_name = ?", apellido, nombre)


def _goles_en(c, apellido: str, anio: int) -> int:
    return _uno(c, "SELECT COUNT(*) FROM goals g JOIN players p USING (player_id) JOIN tournaments t USING "
                   "(tournament_id) WHERE p.family_name = ? AND t.year = ? AND g.own_goal = 0", apellido, anio)


def _goleadores(c, anio: int, n: int) -> list[tuple]:
    """Los n primeros del ranking; falla si hay un empate en el corte."""
    filas = c.execute(
        "SELECT p.player_id, p.given_name, p.family_name, COUNT(*) AS n FROM goals g JOIN players p USING "
        "(player_id) JOIN tournaments t USING (tournament_id) WHERE t.year = ? AND g.own_goal = 0 "
        "GROUP BY p.player_id ORDER BY n DESC, p.family_name", (anio,)).fetchall()
    assert filas[n - 1][3] != filas[n][3], f"empate en el corte del ranking de {anio}"
    return filas[:n]


def _goles_de_carrera(c, player_id: str) -> int:
    return _uno(c, "SELECT COUNT(*) FROM goals WHERE player_id = ? AND own_goal = 0", player_id)


def _nombre(fila) -> str:
    return " ".join(p for p in (fila[1] if fila[1] != "not applicable" else None, fila[2]) if p)


# --- respuestas ---------------------------------------------------------------------------------

def uruguay(c):
    return [str(a) for (a,) in c.execute(
        f"SELECT year FROM tournaments WHERE winner = 'Uruguay' AND {SOLO_HOMBRES} ORDER BY year")]


def dos_goleadores_1982(c):
    return [_nombre(f) for f in _goleadores(c, 1982, 2)]


def campeones_argentina(c):
    return [a for (a,) in c.execute("SELECT year FROM tournaments WHERE winner = 'Argentina' ORDER BY year")]


def suma_goleadores_de_argentina(c):
    return sum(_goleadores(c, anio, 1)[0][3] for anio in campeones_argentina(c))


def goles_de_francia_1998(c):
    francia = _uno(c, "SELECT team_id FROM teams WHERE team_name = 'France'")
    return _uno(c, "SELECT SUM(CASE WHEN home_team_id = ? THEN home_team_score ELSE away_team_score END) "
                   "FROM matches m JOIN tournaments t USING (tournament_id) WHERE t.year = 1998 "
                   "AND (home_team_id = ? OR away_team_id = ?)", francia, francia, francia)


def goles_de_carrera_de_los_tres_de_2002(c):
    return sum(_goles_de_carrera(c, f[0]) for f in _goleadores(c, 2002, 3))


def edad_del_goleador_en_la_final(anio: int):
    def respuesta(c):
        [goleador] = _goleadores(c, anio, 1)
        nacimiento = _uno(c, "SELECT birth_date FROM players WHERE player_id = ?", goleador[0])
        return _edad(nacimiento, _final(c, anio))
    return respuesta


def ausencia_de_datos(c, *, columnas: tuple[str, ...] = (), anio: int | None = None, femenino: bool = False):
    """Comprueba que los datos no alcanzan: devuelve None solo si de verdad no hay con qué responder."""
    if anio is not None:
        hay = c.execute("SELECT COUNT(*) FROM tournaments WHERE year = ? AND tournament_name "
                        f"{'' if femenino else 'NOT '}LIKE '%Women%'", (anio,)).fetchone()[0]
        assert hay == 0, f"hay datos del Mundial {anio}"
    for tabla in [t for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]:
        existentes = [col[1].lower() for col in c.execute(f'PRAGMA table_info("{tabla}")')]
        for palabra in columnas:
            assert not any(palabra in col for col in existentes), f"{tabla} tiene una columna «{palabra}»"
    return None


# --- definiciones -------------------------------------------------------------------------------
# (id, dificultad, tipo, tolerancia, pregunta, respuesta)

DEFINICIONES = [
    ("mun-001", "facil", "lista", 0, "¿En qué años ganó Uruguay un Mundial masculino?", uruguay),
    ("mun-002", "facil", "texto", 0,
     "¿Qué selección ganó el Mundial femenino de 2015? Respondé con el nombre en inglés.",
     lambda c: _uno(c, "SELECT winner FROM tournaments WHERE year = 2015")),
    ("mun-003", "facil", "numero", 0, "¿Cuántos goles hizo Lionel Messi en el Mundial 2014?",
     lambda c: _goles_en(c, "Messi", 2014)),
    ("mun-004", "facil", "numero", 0, "¿Cuántos partidos se jugaron en el Mundial 1986?",
     lambda c: _uno(c, "SELECT COUNT(*) FROM matches m JOIN tournaments t USING (tournament_id) "
                       "WHERE t.year = 1986")),
    ("mun-005", "facil", "fecha", 0, "¿En qué fecha se jugó la final del Mundial 2010?",
     lambda c: _final(c, 2010)),
    ("mun-006", "facil", "fecha", 0, "¿En qué fecha nació Diego Maradona?",
     lambda c: _nacimiento(c, "Maradona", "Diego")),
    ("mun-007", "facil", "texto", 0,
     "¿Qué selección fue sede del Mundial 1994? Respondé con el nombre en inglés.",
     lambda c: _uno(c, "SELECT host_country FROM tournaments WHERE year = 1994")),
    ("mun-008", "facil", "numero", 0, "¿Cuántos goles hizo el máximo goleador del Mundial 2002?",
     lambda c: _goleadores(c, 2002, 1)[0][3]),
    ("mun-009", "facil", "numero", 0,
     "¿Cuántos Mundiales masculinos se jugaron de 1930 a 2022, ambos incluidos?",
     lambda c: _uno(c, f"SELECT COUNT(*) FROM tournaments WHERE {SOLO_HOMBRES}")),
    ("mun-010", "facil", "numero", 0, "¿Cuántos goles hizo Pelé en total en los Mundiales?",
     lambda c: _goles_de_carrera(c, _uno(c, "SELECT player_id FROM players WHERE family_name = 'Pelé' "
                                            "AND given_name = 'not applicable'"))),
    ("mun-011", "facil", "numero", 0, "¿Cuántos goles hizo Lionel Messi en total en los Mundiales?",
     lambda c: _goles_de_carrera(c, _uno(c, "SELECT player_id FROM players WHERE family_name = 'Messi'"))),
    ("mun-012", "facil", "texto", 0,
     "¿Quién ganó el Mundial masculino de 2026? Respondé con el nombre de la selección en inglés.",
     lambda c: ausencia_de_datos(c, anio=2026)),
    ("mun-013", "facil", "texto", 0,
     "¿Qué selección ganó el Mundial femenino de 2023? Respondé con el nombre en inglés.",
     lambda c: ausencia_de_datos(c, anio=2023, femenino=True)),

    ("mun-014", "media", "numero", 0,
     "¿Cuántos días pasaron entre la final del Mundial 1986 y la final del Mundial 1990?",
     lambda c: (_fecha(_final(c, 1990)) - _fecha(_final(c, 1986))).days),
    ("mun-015", "media", "numero", 0,
     "¿Cuántos goles más que Lionel Messi hizo Kylian Mbappé en el Mundial 2022?",
     lambda c: _goles_en(c, "Mbappé", 2022) - _goles_en(c, "Messi", 2022)),
    ("mun-016", "media", "numero", 0,
     "¿En cuántos Mundiales integró Lionel Messi el plantel de Argentina sin hacer ningún gol?",
     lambda c: _uno(c, "SELECT COUNT(*) FROM squads s WHERE s.player_id = 'P-14758' AND NOT EXISTS "
                       "(SELECT 1 FROM goals g WHERE g.player_id = s.player_id AND g.tournament_id = "
                       "s.tournament_id AND g.own_goal = 0)")),
    ("mun-017", "media", "numero", 0, "¿Cuántos años separan el primer Mundial masculino del Mundial 2022?",
     lambda c: 2022 - _uno(c, f"SELECT MIN(year) FROM tournaments WHERE {SOLO_HOMBRES}")),
    ("mun-018", "media", "numero", 0, "¿Cuántos partidos del Mundial 2022 se definieron por penales?",
     lambda c: _uno(c, "SELECT COUNT(*) FROM matches m JOIN tournaments t USING (tournament_id) "
                       "WHERE t.year = 2022 AND m.penalty_shootout = 1")),
    ("mun-019", "media", "lista", 0,
     "¿Quiénes fueron los dos máximos goleadores del Mundial 1982? Respondé con nombre y apellido.",
     dos_goleadores_1982),
    ("mun-020", "media", "numero", 0, "¿Qué edad tenía Lionel Messi el día de la final del Mundial 2022?",
     lambda c: _edad(_nacimiento(c, "Messi", "Lionel"), _final(c, 2022))),
    ("mun-021", "media", "texto", 0,
     "¿Qué país fue sede del primer Mundial que ganó Argentina? Respondé con el nombre en inglés.",
     lambda c: _uno(c, "SELECT host_country FROM tournaments WHERE year = (SELECT MIN(year) FROM "
                       "tournaments WHERE winner = 'Argentina')")),
    ("mun-022", "media", "numero", 0, "¿Cuántos espectadores asistieron a la final del Mundial 1990?",
     lambda c: ausencia_de_datos(c, columnas=("attend", "spectator", "crowd"))),
    ("mun-023", "media", "numero", 0,
     "¿Qué porcentaje de posesión de la pelota tuvo Argentina en la final del Mundial 1978?",
     lambda c: ausencia_de_datos(c, columnas=("possess",))),

    ("mun-024", "dificil", "numero", 0,
     "¿Qué edad tenía el goleador del Mundial 1978 el día de la final?", edad_del_goleador_en_la_final(1978)),
    ("mun-025", "dificil", "numero", 0,
     "¿Cuántos goles hizo, en cada Mundial que ganó Argentina, el máximo goleador de ese torneo? "
     "Respondé con la suma de los tres.", suma_goleadores_de_argentina),
    ("mun-026", "dificil", "numero", 0,
     "¿Cuántos días de diferencia hay entre el nacimiento de Lionel Messi y el de Diego Maradona?",
     lambda c: (_fecha(_nacimiento(c, "Messi", "Lionel")) - _fecha(_nacimiento(c, "Maradona", "Diego"))).days),
    ("mun-027", "dificil", "numero", 0,
     "¿Cuántos goles hizo Francia en el Mundial 1998, sin contar los penales de desempate?",
     goles_de_francia_1998),
    ("mun-028", "dificil", "numero", 0,
     "¿Cuántos goles más que Diego Maradona hizo el máximo goleador del Mundial 1986 en ese torneo?",
     lambda c: _goleadores(c, 1986, 1)[0][3] - _goles_en(c, "Maradona", 1986)),
    ("mun-029", "dificil", "numero", 0,
     "¿Qué edad tenía el goleador del Mundial 2014 el día de la final?", edad_del_goleador_en_la_final(2014)),
    ("mun-030", "dificil", "numero", 0,
     "¿Cuántos goles hicieron en total en los Mundiales, a lo largo de su carrera, los tres máximos "
     "goleadores del Mundial 2002?", goles_de_carrera_de_los_tres_de_2002),
]


def tareas(c: sqlite3.Connection) -> list[dict]:
    resultado = []
    for id_, dificultad, tipo, tolerancia, pregunta, respuesta in DEFINICIONES:
        oro = respuesta(c)
        resultado.append({"id": id_, "pregunta": pregunta, "respuesta": oro, "tipo": tipo,
                          "tolerancia": tolerancia, "dificultad": dificultad, "respondible": oro is not None})
    return resultado


def comparar(c: sqlite3.Connection, ruta: Path = TAREAS_JSON) -> list[str]:
    """Diferencias entre el archivo y el recálculo; vacío si coinciden."""
    guardadas = {t["id"]: t for t in json.loads(ruta.read_text(encoding="utf-8"))}
    diferencias = []
    for tarea in tareas(c):
        otra = guardadas.pop(tarea["id"], None)
        if otra != tarea:
            diferencias.append(f"{tarea['id']}: archivo={otra} recálculo={tarea}")
    diferencias += [f"{id_}: está en el archivo y no en las definiciones" for id_ in guardadas]
    return diferencias


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escribir", action="store_true", help="regenera mundial_publicas.json")
    parser.add_argument("--db", type=Path, default=DB)
    argumentos = parser.parse_args()
    conexion = sqlite3.connect(argumentos.db)
    if argumentos.escribir:
        TAREAS_JSON.write_text(json.dumps(tareas(conexion), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Escrito {TAREAS_JSON}")
        return
    diferencias = comparar(conexion)
    for linea in diferencias:
        print(linea)
    print(f"{len(DEFINICIONES) - len(diferencias)} de {len(DEFINICIONES)} tareas coinciden con el recálculo")
    sys.exit(1 if diferencias else 0)


if __name__ == "__main__":
    main()
