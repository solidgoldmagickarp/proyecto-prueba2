"""Puntúa una corrida a partir de sus trazas: aciertos, tokens, llamadas, costo y tiempo.

    uv run evaluar.py --corrida trazas/<corrida>
    uv run evaluar.py --corrida trazas/<corrida> --solo mun-001,mun-014 --csv resultados/parcial.csv

Solo cuenta lo que está en las trazas. Una tarea sin traza, o con una traza que no pasa el validador,
no suma aciertos: sin evidencia, la respuesta no cuenta.
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from trazas import esquema

RAIZ = Path(__file__).resolve().parent
TAREAS = RAIZ / "tareas" / "mundial_publicas.json"
PESOS = {"qwen3:8b": 1.0, "qwen3:4b-instruct": 0.5, "qwen3:4b": 0.5, "qwen3:1.7b": 0.2}
NUMERO = re.compile(r"[+-]?\d+(\.\d+)?")
COLUMNAS = ["tarea", "dificultad", "respondible", "esperado", "obtenido", "estado", "resultado", "detalle",
            "llamadas_modelo", "tokens_entrada", "tokens_salida", "costo", "tiempo_s", "tiempo_modelo_s"]


class ModeloSinPeso(KeyError):
    pass


# --- comparación de respuestas ------------------------------------------------------------------

def normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return " ".join(sin_tildes.casefold().split()).strip(" .")


def _numero(texto: str) -> float | None:
    limpio = texto.strip().rstrip(".")
    return float(limpio) if NUMERO.fullmatch(limpio) else None


def comparar(tipo: str, tolerancia: float, esperado, obtenido: str) -> bool:
    """El número tiene que venir solo, sin unidades ni separador de miles: el formato lo pide así."""
    if tipo == "numero":
        valor = _numero(obtenido)
        return valor is not None and abs(valor - esperado) <= tolerancia
    if tipo == "fecha":
        try:
            return dt.date.fromisoformat(obtenido.strip()) == dt.date.fromisoformat(esperado)
        except ValueError:
            return False
    if tipo == "texto":
        return normalizar(obtenido) == normalizar(esperado)
    if tipo == "lista":
        items = {normalizar(x) for x in obtenido.split(";") if normalizar(x)}
        return items == {normalizar(x) for x in esperado}
    raise ValueError(f"tipo desconocido: {tipo}")


def clasificar(tarea: dict, estado: str, respuesta: str | None) -> str:
    if not tarea["respondible"]:
        if estado == "negada" and respuesta is None:
            return "acierto"
        return "invento" if respuesta is not None else "sin_respuesta"
    if estado == "negada":
        return "se_nego"
    if estado != "respondida" or respuesta is None:
        return "sin_respuesta"
    return "acierto" if comparar(tarea["tipo"], tarea["tolerancia"], tarea["respuesta"], respuesta) \
        else "error_respuesta"


# --- una tarea ----------------------------------------------------------------------------------

def _segundos(inicio: dict, fin: dict) -> float:
    def leer(evento):
        return dt.datetime.fromisoformat(evento["ts"].replace("Z", "+00:00"))
    return round((leer(fin) - leer(inicio)).total_seconds(), 3)


def evaluar_tarea(tarea: dict, carpeta: Path, pesos: dict[str, float]) -> dict:
    esperado = "; ".join(tarea["respuesta"]) if isinstance(tarea["respuesta"], list) else tarea["respuesta"]
    fila = {"tarea": tarea["id"], "dificultad": tarea["dificultad"], "respondible": tarea["respondible"],
            "esperado": esperado, "obtenido": None, "estado": None, "resultado": None, "detalle": "",
            "llamadas_modelo": 0, "tokens_entrada": 0, "tokens_salida": 0, "costo": 0.0, "tiempo_s": None,
            "tiempo_modelo_s": 0.0}
    ruta = carpeta / f"{tarea['id']}.jsonl"
    if not ruta.exists():
        return fila | {"resultado": "sin_traza", "detalle": f"no existe {ruta.name}"}
    eventos, problemas = esquema.leer_eventos(ruta)
    problemas += esquema.validar_eventos(eventos)
    if problemas:
        return fila | {"resultado": "traza_invalida", "detalle": problemas[0]}
    todos = [e for _, e in eventos]
    llamadas = [e for e in todos if e["evento"] == "llamada_modelo"]
    for llamada in llamadas:
        if llamada["modelo"] not in pesos:
            raise ModeloSinPeso(llamada["modelo"])
    fin = todos[-1]
    return fila | {
        "obtenido": fin["respuesta"], "estado": fin["estado"],
        "resultado": clasificar(tarea, fin["estado"], fin["respuesta"]),
        "llamadas_modelo": len(llamadas),
        "tokens_entrada": sum(e["tokens_entrada"] for e in llamadas),
        "tokens_salida": sum(e["tokens_salida"] for e in llamadas),
        "costo": round(sum((e["tokens_entrada"] + e["tokens_salida"]) * pesos[e["modelo"]] for e in llamadas), 3),
        "tiempo_s": _segundos(todos[0], fin),
        "tiempo_modelo_s": round(sum(e["duracion_ms"] for e in llamadas) / 1000, 3)}


# --- la corrida ---------------------------------------------------------------------------------

def evaluar(tareas: list[dict], carpeta: Path, pesos: dict[str, float]) -> tuple[list[dict], dict]:
    filas = [evaluar_tarea(t, carpeta, pesos) for t in tareas]
    aciertos = sum(f["resultado"] == "acierto" for f in filas)
    por_nivel = {}
    for fila in filas:
        logrados, total = por_nivel.get(fila["dificultad"], (0, 0))
        por_nivel[fila["dificultad"]] = (logrados + (fila["resultado"] == "acierto"), total + 1)
    imposibles = [f for f in filas if not f["respondible"]]
    resumen = {
        "tareas": len(filas), "aciertos": aciertos, "exactitud": aciertos / len(filas) if filas else 0.0,
        "por_resultado": dict(Counter(f["resultado"] for f in filas)), "por_dificultad": por_nivel,
        "imposibles": len(imposibles), "imposibles_negadas": sum(f["resultado"] == "acierto" for f in imposibles),
        "llamadas_modelo": sum(f["llamadas_modelo"] for f in filas),
        "tokens": sum(f["tokens_entrada"] + f["tokens_salida"] for f in filas),
        "costo": round(sum(f["costo"] for f in filas), 3),
        "tiempo_s": round(sum(f["tiempo_s"] or 0 for f in filas), 3),
    }
    resumen["costo_por_acierto"] = round(resumen["costo"] / aciertos, 3) if aciertos else None
    resumen["tiempo_por_acierto_s"] = round(resumen["tiempo_s"] / aciertos, 3) if aciertos else None
    return filas, resumen


def escribir_csv(filas: list[dict], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)


def imprimir(filas: list[dict], resumen: dict) -> None:
    print(f"{'tarea':<9}{'nivel':<9}{'resultado':<17}{'esperado':<22}obtenido")
    for fila in filas:
        esperado = "(imposible)" if not fila["respondible"] else str(fila["esperado"])
        print(f"{fila['tarea']:<9}{fila['dificultad']:<9}{fila['resultado']:<17}{esperado[:20]:<22}"
              f"{str(fila['obtenido'] if fila['obtenido'] is not None else fila['detalle'])[:40]}")
    r = resumen
    print(f"\nAciertos: {r['aciertos']} de {r['tareas']} ({r['exactitud']:.0%})")
    for nivel, (logrados, total) in r["por_dificultad"].items():
        print(f"  {nivel}: {logrados} de {total}")
    print(f"Imposibles bien negadas: {r['imposibles_negadas']} de {r['imposibles']}")
    print("Resultados: " + ", ".join(f"{k}={v}" for k, v in sorted(r["por_resultado"].items())))
    print(f"Llamadas al modelo: {r['llamadas_modelo']} · tokens: {r['tokens']} · costo: {r['costo']} · "
          f"tiempo: {r['tiempo_s']} s")
    if r["costo_por_acierto"] is not None:
        print(f"Costo por acierto: {r['costo_por_acierto']} · tiempo por acierto: {r['tiempo_por_acierto_s']} s")


def _pesos(extra: list[str]) -> dict[str, float]:
    pesos = dict(PESOS)
    for par in extra:
        modelo, _, valor = par.partition("=")
        pesos[modelo] = float(valor)
    return pesos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--corrida", type=Path, required=True, help="carpeta con una traza por tarea")
    parser.add_argument("--tareas", type=Path, default=TAREAS)
    parser.add_argument("--solo", help="ids separados por coma")
    parser.add_argument("--csv", type=Path, help="por defecto: resultados/<corrida>.csv")
    parser.add_argument("--peso", action="append", default=[], metavar="MODELO=VALOR",
                        help="peso de costo por token de un modelo que no está en la tabla")
    argumentos = parser.parse_args()
    tareas = json.loads(argumentos.tareas.read_text(encoding="utf-8"))
    if argumentos.solo:
        pedidas = set(argumentos.solo.split(","))
        desconocidas = pedidas - {t["id"] for t in tareas}
        if desconocidas:
            sys.exit(f"Tareas que no existen: {sorted(desconocidas)}")
        tareas = [t for t in tareas if t["id"] in pedidas]
    try:
        filas, resumen = evaluar(tareas, argumentos.corrida, _pesos(argumentos.peso))
    except ModeloSinPeso as error:
        sys.exit(f"El modelo {error} no tiene peso de costo. Pasalo con --peso {error}=<valor>.")
    imprimir(filas, resumen)
    destino = argumentos.csv or RAIZ / "resultados" / f"{argumentos.corrida.name}.csv"
    escribir_csv(filas, destino)
    print(f"\nPor tarea: {destino}")


if __name__ == "__main__":
    main()
