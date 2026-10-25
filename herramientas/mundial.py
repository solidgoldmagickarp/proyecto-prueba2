"""Herramientas del Mundial sobre la base SQLite del kit, y sus esquemas JSON.

Las funciones devuelven datos o {"error": ...}; no levantan excepciones por datos que faltan. Validar
los argumentos que escribe el modelo es trabajo del loop, no de estas funciones.
"""
import ast
import datetime as dt
import operator
import os
import re
import sqlite3
import unicodedata
from functools import lru_cache
from pathlib import Path

DB_POR_DEFECTO = Path(__file__).resolve().parent.parent / "datos" / "worldcup.sqlite"
SIN_DATO = {"", "not applicable", "not available"}
MAX_COINCIDENCIAS = 5


# --- acceso a la base ---------------------------------------------------------------------------

def _ruta_db() -> Path:
    return Path(os.environ.get("MUNDIAL_DB", DB_POR_DEFECTO))


@lru_cache(maxsize=None)
def _conexion(ruta: str) -> sqlite3.Connection:
    if not Path(ruta).exists():
        raise FileNotFoundError(f"No existe {ruta}. Armala con: uv run datos/descargar.py")
    conexion = sqlite3.connect(Path(ruta).resolve().as_uri() + "?mode=ro", uri=True)
    conexion.row_factory = sqlite3.Row
    return conexion


def _sql(consulta: str, *parametros) -> list[sqlite3.Row]:
    return _conexion(str(_ruta_db())).execute(consulta, parametros).fetchall()


def _dato(valor):
    """None cuando la base dice que el dato no existe: nunca se inventa."""
    return None if valor in SIN_DATO else valor


# --- nombres ------------------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return sin_tildes.casefold()


def _tokens(texto: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", _normalizar(texto)))


@lru_cache(maxsize=None)
def _jugadores(ruta: str) -> tuple[dict, ...]:
    filas = _conexion(ruta).execute(
        "SELECT player_id, given_name, family_name, birth_date, count_tournaments FROM players").fetchall()
    jugadores = []
    for fila in filas:
        nombre = " ".join(p for p in (_dato(fila["given_name"]), fila["family_name"]) if p)
        jugadores.append({"id": fila["player_id"], "nombre": nombre, "tokens": _tokens(nombre),
                          "nacimiento": _dato(fila["birth_date"]),
                          "torneos_jugados": int(fila["count_tournaments"])})
    return tuple(jugadores)


ID_JUGADOR = re.compile(r"P-\d+")


def _coincidencias(nombre: str) -> list[dict]:
    """Jugadores cuyos nombres contienen todas las palabras de la consulta, o el de ese id.

    El id existe porque un nombre puede ser ambiguo sin remedio: "Ronaldo" también está contenido en
    "Cristiano Ronaldo", y repetir el nombre nunca desambigua.
    """
    if ID_JUGADOR.fullmatch(nombre.strip()):
        return [j for j in _jugadores(str(_ruta_db())) if j["id"] == nombre.strip()]
    palabras = _tokens(nombre)
    if not palabras:
        return []
    encontrados = [j for j in _jugadores(str(_ruta_db())) if palabras <= j["tokens"]]
    return sorted(encontrados, key=lambda j: (-j["torneos_jugados"], _normalizar(j["nombre"])))


def _ficha_jugador(jugador: dict) -> dict:
    selecciones = [f["team_name"] for f in _sql(
        "SELECT DISTINCT team_name FROM squads WHERE player_id = ? ORDER BY team_name", jugador["id"])]
    torneos = [int(f["year"]) for f in _sql(
        "SELECT DISTINCT t.year FROM squads s JOIN tournaments t USING (tournament_id) "
        "WHERE s.player_id = ? ORDER BY t.year", jugador["id"])]
    return {"id": jugador["id"], "jugador": jugador["nombre"], "nacimiento": jugador["nacimiento"],
            "selecciones": selecciones, "torneos": torneos}


def _aviso_de_recorte(total: int) -> dict:
    return {"aviso": f"Hay {total} coincidencias; se muestran {MAX_COINCIDENCIAS}. "
                     "Usá el nombre completo o el id."}


# --- torneos ------------------------------------------------------------------------------------

def _id_torneo(anio: int) -> str | None:
    filas = _sql("SELECT tournament_id FROM tournaments WHERE year = ?", int(anio))
    return filas[0]["tournament_id"] if filas else None


def _anios_disponibles() -> list[int]:
    return [int(f["year"]) for f in _sql("SELECT year FROM tournaments ORDER BY year")]


def _error_torneo(anio: int) -> dict:
    return {"error": f"No hubo un Mundial en {anio}.", "torneos_disponibles": _anios_disponibles()}


def buscar_torneos(campeon: str | None = None, anio: int | None = None, femenino: bool = False):
    # La final es el partido de etapa 'final'; 1950 se definió en una rueda final y devuelve None.
    finales = {f["tournament_id"]: f["match_date"] for f in _sql(
        "SELECT tournament_id, match_date FROM matches WHERE stage_name = 'final'")}
    resultados = []
    for fila in _sql("SELECT tournament_id, tournament_name, year, host_country, winner "
                     "FROM tournaments ORDER BY year"):
        if ("women" in fila["tournament_name"].casefold()) != bool(femenino):
            continue
        if anio is not None and int(fila["year"]) != int(anio):
            continue
        if campeon is not None and _normalizar(fila["winner"]) != _normalizar(campeon):
            continue
        resultados.append({"torneo": int(fila["year"]), "sede": fila["host_country"],
                           "campeon": fila["winner"], "final": finales.get(fila["tournament_id"])})
    return resultados or {"error": "No encontré Mundiales con ese filtro."}


def goleadores(torneo: int, n: int = 5):
    id_torneo = _id_torneo(torneo)
    if id_torneo is None:
        return _error_torneo(torneo)
    n = int(n)
    if n < 1:
        return {"error": "n tiene que ser al menos 1."}
    filas = _sql(
        "SELECT p.given_name, p.family_name, t.team_name, COUNT(*) AS goles "
        "FROM goals g JOIN players p ON p.player_id = g.player_id "
        "JOIN teams t ON t.team_id = g.player_team_id "
        "WHERE g.tournament_id = ? AND g.own_goal = 0 "
        "GROUP BY p.player_id ORDER BY goles DESC, p.family_name, p.given_name", id_torneo)
    ranking = [{"jugador": " ".join(x for x in (_dato(f["given_name"]), f["family_name"]) if x),
                "seleccion": f["team_name"], "goles": f["goles"]} for f in filas]
    empate = len(ranking) > n and ranking[n]["goles"] == ranking[n - 1]["goles"]
    return {"torneo": int(torneo), "goleadores": ranking[:n], "empate_en_el_corte": empate}


def partidos(torneo: int):
    id_torneo = _id_torneo(torneo)
    if id_torneo is None:
        return _error_torneo(torneo)
    filas = _sql(
        "SELECT m.match_date, m.stage_name, h.team_name AS local, a.team_name AS visitante, m.score, "
        "m.penalty_shootout, m.score_penalties, s.stadium_name, s.city_name "
        "FROM matches m JOIN teams h ON h.team_id = m.home_team_id "
        "JOIN teams a ON a.team_id = m.away_team_id JOIN stadiums s ON s.stadium_id = m.stadium_id "
        "WHERE m.tournament_id = ? ORDER BY m.match_date, m.match_id", id_torneo)
    return [{"fecha": f["match_date"], "etapa": f["stage_name"], "local": f["local"],
             "visitante": f["visitante"], "resultado": f["score"],
             "penales": f["score_penalties"] if int(f["penalty_shootout"]) else None,
             "estadio": f["stadium_name"], "ciudad": f["city_name"]} for f in filas]


# --- jugadores ----------------------------------------------------------------------------------

def buscar_jugador(nombre: str):
    encontrados = _coincidencias(nombre)
    if not encontrados:
        return {"error": f"No encontré ningún jugador que coincida con «{nombre}»."}
    resultado = [_ficha_jugador(j) for j in encontrados[:MAX_COINCIDENCIAS]]
    if len(encontrados) > MAX_COINCIDENCIAS:
        resultado.append(_aviso_de_recorte(len(encontrados)))
    return resultado


def goles(jugador: str, torneo: int | None = None):
    encontrados = _coincidencias(jugador)
    if not encontrados:
        return {"error": f"No encontré ningún jugador que coincida con «{jugador}»."}
    if len(encontrados) > 1:
        candidatos = [_ficha_jugador(j) for j in encontrados[:MAX_COINCIDENCIAS]]
        if len(encontrados) > MAX_COINCIDENCIAS:
            candidatos.append(_aviso_de_recorte(len(encontrados)))
        return {"error": "ambiguo: hay más de un jugador con ese nombre. Volvé a llamar a goles con el id del que corresponda (por ejemplo P-12345), escrito en el parámetro `jugador`.", "candidatos": candidatos}
    elegido = encontrados[0]
    if torneo is None:
        filas = _sql(
            "SELECT t.year, COUNT(*) AS goles FROM goals g JOIN tournaments t USING (tournament_id) "
            "WHERE g.player_id = ? AND g.own_goal = 0 GROUP BY t.year ORDER BY t.year", elegido["id"])
        por_torneo = {str(int(f["year"])): f["goles"] for f in filas}
        return {"jugador": elegido["nombre"], "por_torneo": por_torneo,
                "total": sum(por_torneo.values())}
    id_torneo = _id_torneo(torneo)
    if id_torneo is None:
        return _error_torneo(torneo)
    if not _sql("SELECT 1 FROM squads WHERE player_id = ? AND tournament_id = ?", elegido["id"], id_torneo):
        return {"error": f"{elegido['nombre']} no figura en ningún plantel del Mundial {torneo}."}
    cantidad = _sql("SELECT COUNT(*) AS n FROM goals WHERE player_id = ? AND tournament_id = ? "
                    "AND own_goal = 0", elegido["id"], id_torneo)[0]["n"]
    return {"jugador": elegido["nombre"], "torneo": int(torneo), "goles": cantidad}


# --- calcular -----------------------------------------------------------------------------------

OPERADORES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}
UNARIOS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
DOS_FECHAS = re.compile(r"\s*(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})\s*")
MAX_EXPONENTE = 100


def _evaluar(nodo):
    if isinstance(nodo, ast.Expression):
        return _evaluar(nodo.body)
    if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
        return nodo.value
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in UNARIOS:
        return UNARIOS[type(nodo.op)](_evaluar(nodo.operand))
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in OPERADORES:
        izquierda, derecha = _evaluar(nodo.left), _evaluar(nodo.right)
        if isinstance(nodo.op, ast.Pow) and abs(derecha) > MAX_EXPONENTE:
            raise ValueError(f"el exponente no puede pasar de {MAX_EXPONENTE}")
        return OPERADORES[type(nodo.op)](izquierda, derecha)
    raise ValueError("solo se aceptan números y las operaciones + - * / ** %")


def _diferencia_de_fechas(posterior: str, anterior: str) -> dict:
    try:
        despues, antes = dt.date.fromisoformat(posterior), dt.date.fromisoformat(anterior)
    except ValueError as error:
        return {"error": f"Fecha inválida: {error}."}
    if despues < antes:
        return {"error": "La primera fecha es anterior a la segunda."}
    anios = despues.year - antes.year - ((despues.month, despues.day) < (antes.month, antes.day))
    return {"anios_cumplidos": anios, "dias": (despues - antes).days}


def calcular(expresion: str):
    fechas = DOS_FECHAS.fullmatch(expresion)
    if fechas:
        return _diferencia_de_fechas(*fechas.groups())
    try:
        valor = _evaluar(ast.parse(expresion.strip(), mode="eval"))
    except ZeroDivisionError:
        return {"error": "División por cero."}
    except (ValueError, SyntaxError, OverflowError) as error:
        return {"error": f"No pude calcular «{expresion}»: {error}"}
    return {"resultado": round(valor, 10) if isinstance(valor, float) else valor}


# --- esquemas JSON ------------------------------------------------------------------------------

def _ficha(nombre: str, descripcion: str, propiedades: dict, requeridos: tuple = ()) -> dict:
    return {"type": "function", "function": {
        "name": nombre, "description": descripcion,
        "parameters": {"type": "object", "properties": propiedades, "required": list(requeridos),
                       "additionalProperties": False}}}


FICHAS_POR_NOMBRE = {
    "buscar_torneos": _ficha(
        "buscar_torneos",
        "Busca Mundiales de fútbol. Devuelve, de cada torneo, el año, la sede, el campeón y la fecha "
        "de la final. Sin argumentos, devuelve todos los Mundiales masculinos. Los nombres de las "
        "selecciones están en inglés.",
        {"campeon": {"type": "string", "description": "Selección campeona, en inglés. Ejemplo: Argentina"},
         "anio": {"type": "integer", "description": "Año del torneo. Ejemplo: 1978"},
         "femenino": {"type": "boolean",
                      "description": "true para los Mundiales femeninos; por defecto, los masculinos"}}),
    "goleadores": _ficha(
        "goleadores",
        "Ranking de goleadores de un Mundial: los que más goles hicieron, sin contar los goles en contra.",
        {"torneo": {"type": "integer", "description": "Año del torneo. Ejemplo: 1978"},
         "n": {"type": "integer", "description": "Cuántos jugadores devolver (por defecto, 5)"}},
        ("torneo",)),
    "buscar_jugador": _ficha(
        "buscar_jugador",
        "Devuelve los datos de un jugador de Mundiales: id, fecha de nacimiento, selección y torneos jugados.",
        {"nombre": {"type": "string",
                    "description": "Apellido, nombre completo o id del jugador (por ejemplo P-14758)"}},
        ("nombre",)),
    "goles": _ficha(
        "goles",
        "Devuelve los goles de un jugador en Mundiales: por torneo y el total de su carrera. Con "
        "`torneo`, solo ese Mundial. No cuenta los goles en contra.",
        {"jugador": {"type": "string",
                     "description": "Apellido, nombre completo o id del jugador (por ejemplo P-14758)"},
         "torneo": {"type": "integer", "description": "Año del torneo, para limitar a un Mundial"}},
        ("jugador",)),
    "partidos": _ficha(
        "partidos",
        "Lista los partidos de un Mundial: fecha, etapa, equipos, resultado y estadio.",
        {"torneo": {"type": "integer", "description": "Año del torneo. Ejemplo: 1986"}},
        ("torneo",)),
    "calcular": _ficha(
        "calcular",
        "Hace una cuenta: una expresión aritmética, o la diferencia entre dos fechas AAAA-MM-DD, que "
        "devuelve en años cumplidos y en días.",
        {"expresion": {"type": "string", "description": "Ejemplos: 6 + 6 + 8 · 1978-06-25 - 1954-07-15"}},
        ("expresion",)),
    "terminar": _ficha(
        "terminar",
        "Terminá acá. `respuesta` es tu respuesta final, o null si los datos no alcanzan para "
        "responder la pregunta. `motivo` explica en una frase de dónde sale la respuesta o qué dato falta.",
        {"respuesta": {"type": ["string", "null"],
                       "description": "La respuesta final, o null si no se puede responder con los datos"},
         "motivo": {"type": "string", "description": "Una frase: de dónde sale la respuesta o qué dato falta"}},
        ("respuesta", "motivo")),
}

ORDEN_HERRAMIENTAS = ["buscar_torneos", "goleadores", "buscar_jugador", "goles", "partidos", "calcular",
                      "terminar"]
FICHAS = [FICHAS_POR_NOMBRE[nombre] for nombre in ORDEN_HERRAMIENTAS]

# `terminar` no está acá: la atiende el loop, que es quien decide cómo termina la corrida.
HERRAMIENTAS = {"buscar_torneos": buscar_torneos, "goleadores": goleadores,
                "buscar_jugador": buscar_jugador, "goles": goles, "partidos": partidos,
                "calcular": calcular}
