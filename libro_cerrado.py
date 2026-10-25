"""La línea de base a libro cerrado: las mismas tareas, el modelo sin herramientas.

    uv run libro_cerrado.py --corrida trazas/libro_cerrado
    uv run evaluar.py --corrida trazas/libro_cerrado

Escribe trazas con el mismo esquema que el agente, así que `evaluar.py` las puntúa igual. Sirve para
saber cuánto del Mundial ya sabe el modelo: lo que el agente compra es la respuesta correcta, con
datos que se pueden verificar, y un «los datos no alcanzan» en lugar de una invención.
"""
import argparse
import json
import sys
from pathlib import Path

import llm
from evaluar import normalizar
from tareas.formato import pregunta_con_formato
from trazas.registro import Registro

RAIZ = Path(__file__).resolve().parent
TAREAS = RAIZ / "tareas" / "mundial_publicas.json"
SISTEMA = ("Contestás preguntas sobre los Mundiales de fútbol, de memoria y sin herramientas. "
           "Si no lo sabés o no se puede saber, respondé exactamente: NO SE.")
NO_SE = {"no se", "null"}


def responder_tarea(tarea: dict, carpeta: Path, *, modelo: str, num_ctx: int, num_predict: int = 200,
                    temperatura: float = 0, semilla: int = 1337, chat=llm.chat) -> str:
    """Escribe la traza de una tarea y devuelve el estado final."""
    registro = Registro(carpeta, tarea["id"])
    config = {"num_ctx": num_ctx, "temperatura": temperatura, "semilla": semilla, "think": False,
              "num_predict": num_predict, "linea_de_base": "libro_cerrado"}
    registro.evento("corrida_inicio", modelo=modelo, config=config)
    mensajes = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": pregunta_con_formato(tarea)}]
    try:
        respuesta = chat(mensajes, modelo=modelo, num_ctx=num_ctx, temperatura=temperatura, semilla=semilla,
                         think=False, num_predict=num_predict)
    except llm.LLMError as error:
        registro.evento("corrida_fin", estado="error", respuesta=None, pasos=1, motivo=str(error))
        return "error"
    registro.evento("llamada_modelo", paso=1, modelo=modelo, num_ctx=num_ctx,
                    tokens_entrada=respuesta.tokens_entrada, tokens_salida=respuesta.tokens_salida,
                    duracion_ms=respuesta.duracion_ms)
    texto = respuesta.mensaje.get("content", "").strip()
    if normalizar(texto) in NO_SE:
        registro.evento("corrida_fin", estado="negada", respuesta=None, pasos=1)
        return "negada"
    registro.evento("corrida_fin", estado="respondida", respuesta=texto, pasos=1)
    return "respondida"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--corrida", type=Path, default=RAIZ / "trazas" / "libro_cerrado")
    parser.add_argument("--tareas", type=Path, default=TAREAS)
    parser.add_argument("--modelo", default="qwen3:8b")
    parser.add_argument("--num-ctx", type=int, default=8192)
    argumentos = parser.parse_args()
    tareas = json.loads(argumentos.tareas.read_text(encoding="utf-8"))
    print(f"Ollama {llm.version()} · {argumentos.modelo} · num_ctx {argumentos.num_ctx}")
    for tarea in tareas:
        estado = responder_tarea(tarea, argumentos.corrida, modelo=argumentos.modelo, num_ctx=argumentos.num_ctx)
        print(f"{tarea['id']}  {estado}")
    print(f"\nPuntuar: uv run evaluar.py --corrida {argumentos.corrida}")


if __name__ == "__main__":
    try:
        main()
    except llm.LLMError as error:
        sys.exit(f"No pude hablar con Ollama: {error}")
