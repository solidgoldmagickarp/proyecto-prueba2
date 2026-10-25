"""Arma trazas sintéticas válidas para los tests del validador, del evaluador y del runner."""
from pathlib import Path

from trazas.registro import Registro


def traza(carpeta: Path, tarea: str, *, estado: str = "respondida", respuesta: str | None = "x",
          modelo: str = "qwen3:8b", llamadas=((100, 20),), con_herramientas: bool = True,
          num_ctx: int = 8192, duracion_ms: int = 500) -> Path:
    """Una corrida con una llamada al modelo por cada par (tokens_entrada, tokens_salida).

    Cada llamada menos la última pide una herramienta, cuyo resultado vuelve en el paso siguiente.
    """
    registro = Registro(carpeta, tarea)
    registro.evento("corrida_inicio", modelo=modelo, config={"num_ctx": num_ctx, "temperatura": 0})
    for paso, (entrada, salida) in enumerate(llamadas, start=1):
        registro.evento("llamada_modelo", paso=paso, modelo=modelo, num_ctx=num_ctx, tokens_entrada=entrada,
                        tokens_salida=salida, duracion_ms=duracion_ms)
        if con_herramientas and paso < len(llamadas):
            identificador = f"call_{paso}"
            registro.evento("llamada_herramienta", paso=paso, id=identificador, nombre="calcular",
                            argumentos={"expresion": "1 + 1"})
            registro.evento("resultado_herramienta", paso=paso, id=identificador, ok=True, truncado=False,
                            caracteres=12, duracion_ms=3)
    registro.evento("corrida_fin", estado=estado, respuesta=respuesta, pasos=len(llamadas))
    return registro.ruta


def leer(ruta: Path) -> list[dict]:
    import json
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]


def reescribir(ruta: Path, eventos: list[dict]) -> None:
    import json
    ruta.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in eventos), encoding="utf-8")
