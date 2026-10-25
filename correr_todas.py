"""Corre `agente.py` una vez por tarea, cada una en su proceso y con un tope de tiempo.

    uv run correr_todas.py --corrida trazas/mi_corrida
    uv run correr_todas.py --corrida trazas/mi_corrida --solo mun-001,mun-014
    uv run correr_todas.py --corrida trazas/mi_corrida --reanudar   # saltea las tareas con traza válida

A cada pregunta le agrega el formato de respuesta de su `tipo`. Si el agente se cuelga o termina sin
cerrar su traza, este script agrega un `corrida_fin` con estado `error` y `origen: correr_todas`, para
que la falla quede registrada y no se confunda con una tarea que nunca corrió.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

from tareas.formato import pregunta_con_formato
from trazas import esquema

RAIZ = Path(__file__).resolve().parent
TAREAS = RAIZ / "tareas" / "mundial_publicas.json"


def _cerrar_si_falta(ruta: Path, motivo: str) -> bool:
    """Agrega un corrida_fin de error a una traza abierta. Devuelve si lo agregó."""
    if not ruta.exists():
        return False
    eventos, _ = esquema.leer_eventos(ruta)
    if not eventos or eventos[0][1].get("evento") != "corrida_inicio" or eventos[-1][1].get("evento") == "corrida_fin":
        return False
    primero = eventos[0][1]
    pasos = max((e.get("paso", 0) for _, e in eventos if isinstance(e.get("paso"), int)), default=0)
    fin = {"evento": "corrida_fin", "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
           "corrida": primero.get("corrida"), "tarea": primero.get("tarea"), "estado": "error",
           "respuesta": None, "pasos": pasos, "motivo": motivo, "origen": "correr_todas"}
    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(fin, ensure_ascii=False) + "\n")
    return True


def correr_tarea(tarea: dict, carpeta: Path, agente: Path, python: str, timeout_s: float,
                 config: Path | None = None) -> dict:
    carpeta.mkdir(parents=True, exist_ok=True)
    orden = [python, str(agente), "-p", pregunta_con_formato(tarea), "--tarea", tarea["id"], "--log", str(carpeta)]
    if config:
        orden += ["--config", str(config)]
    inicio = time.perf_counter()
    motivo = None
    with open(carpeta / f"{tarea['id']}.salida.txt", "w", encoding="utf-8") as salida:
        try:
            codigo = subprocess.run(orden, stdout=salida, stderr=subprocess.STDOUT, timeout=timeout_s,
                                    cwd=RAIZ).returncode
            if codigo != 0:
                motivo = f"el agente terminó con código {codigo} sin cerrar la traza"
        except subprocess.TimeoutExpired:
            codigo, motivo = None, f"el agente pasó el tope de {timeout_s:g} s y se lo cortó"
    ruta = carpeta / f"{tarea['id']}.jsonl"
    cerrada = _cerrar_si_falta(ruta, motivo or "el agente terminó sin escribir corrida_fin")
    estado = "timeout" if codigo is None else "ok" if codigo == 0 and not cerrada else "fallo"
    if not ruta.exists():
        estado = "sin_traza"
    return {"tarea": tarea["id"], "estado": estado, "segundos": round(time.perf_counter() - inicio, 1),
            "codigo": codigo}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--corrida", type=Path, required=True, help="carpeta de salida de las trazas")
    parser.add_argument("--tareas", type=Path, default=TAREAS)
    parser.add_argument("--agente", type=Path, default=RAIZ / "agente.py")
    parser.add_argument("--config", type=Path, help="config.toml alternativo, que se le pasa al agente")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--timeout", type=float, default=600, help="segundos por tarea")
    parser.add_argument("--solo", help="ids separados por coma")
    parser.add_argument("--reanudar", action="store_true")
    argumentos = parser.parse_args()
    tareas = json.loads(argumentos.tareas.read_text(encoding="utf-8"))
    if argumentos.solo:
        pedidas = set(argumentos.solo.split(","))
        desconocidas = pedidas - {t["id"] for t in tareas}
        if desconocidas:
            sys.exit(f"Tareas que no existen: {sorted(desconocidas)}")
        tareas = [t for t in tareas if t["id"] in pedidas]
    resultados = []
    for tarea in tareas:
        ruta = argumentos.corrida / f"{tarea['id']}.jsonl"
        if argumentos.reanudar and ruta.exists() and not esquema.validar_archivo(ruta):
            print(f"{tarea['id']}  ya tiene traza válida, se saltea")
            continue
        resultado = correr_tarea(tarea, argumentos.corrida, argumentos.agente, argumentos.python, argumentos.timeout,
                                  argumentos.config)
        resultados.append(resultado)
        print(f"{resultado['tarea']}  {resultado['estado']:<9} {resultado['segundos']:>6} s")
    fallas = [r for r in resultados if r["estado"] != "ok"]
    print(f"\n{len(resultados) - len(fallas)} de {len(resultados)} sin problemas del proceso."
          f"\nPuntuar: uv run evaluar.py --corrida {argumentos.corrida}")


if __name__ == "__main__":
    main()
