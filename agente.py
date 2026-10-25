"""Tu loop. El kit trae todo lo demás; acá falta `bucle`.

    uv run agente.py -p "¿Qué edad tenía el goleador del Mundial 1978 el día de la final?" --log trazas/mi_corrida
    uv run agente.py -p "..." --tarea mun-024 --log trazas/mi_corrida --config config.toml

Ya está hecho: leer y validar `config.toml`, abrir la traza y escribir `corrida_inicio` con la
configuración y la versión de Ollama, y escribir `corrida_fin` cuando `bucle` devuelve.
Sin implementar `bucle`, esto termina con estado `error` y no responde nada.

Lo que tiene que resolver `bucle` (Bloque 1, sección 4 del enunciado):
  1. el ciclo: llamar al modelo, ejecutar cada llamada a herramienta y devolver un resultado por
     llamada, hasta que el modelo termine;
  2. el contrato de herramientas: `FICHAS` trae los esquemas y `HERRAMIENTAS` las funciones;
  3. la salida mal formada: JSON roto, herramienta inexistente, argumentos del tipo equivocado;
  4. las herramientas que fallan: excepciones, resultados vacíos, timeouts;
  5. el contexto: recortar los resultados largos (`contexto.tope_resultado_caracteres`);
  6. los reintentos ante errores del servidor del modelo, con límite;
  7. la parada: tope de pasos y de tokens, y `terminar(respuesta, motivo)`, con `respuesta = None`
     cuando los datos no alcanzan;
  8. las trazas: un evento por cada cosa que pasa, con el esquema de la sección 7 del enunciado.

Qué usar:
  llm.chat(mensajes, modelo=..., num_ctx=..., herramientas=FICHAS)  -> llm.Respuesta
      una llamada; levanta llm.LLMError (y llm.ContextOverflow si el prompt no entra)
  registro.evento("llamada_modelo", paso=1, modelo=..., num_ctx=..., tokens_entrada=...,
                  tokens_salida=..., duracion_ms=...)
  HERRAMIENTAS[nombre](**argumentos)  -> datos, o {"error": ...}
"""
import argparse
import sys
from pathlib import Path

import config as configuracion
import llm
from herramientas.mundial import FICHAS, HERRAMIENTAS  # noqa: F401  (los vas a usar en `bucle`)
from trazas.registro import Registro, SinRegistro

RAIZ = Path(__file__).resolve().parent


def bucle(pregunta: str, config: dict, registro) -> tuple[str, str | None, int]:
    """Devuelve (estado, respuesta, pasos). Estados: respondida, negada, tope_pasos, tope_tokens, error."""
    raise NotImplementedError("el loop todavía no está implementado: es el trabajo del Bloque 1")


def entorno_del_servidor(modelo: str) -> dict:
    """La versión de Ollama y el digest del modelo; null si el servidor no responde."""
    try:
        return {"ollama_version": llm.version(), "modelo_digest": llm.digest(modelo)}
    except llm.LLMError:
        return {"ollama_version": None, "modelo_digest": None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Responde una pregunta sobre los Mundiales con herramientas.")
    parser.add_argument("-p", "--pregunta", required=True)
    parser.add_argument("--tarea", help="id de la tarea, para la traza")
    parser.add_argument("--log", type=Path, help="carpeta de trazas; sin esto no se escribe ninguna")
    parser.add_argument("--config", type=Path, default=configuracion.CONFIG)
    argumentos = parser.parse_args()

    config = configuracion.cargar(argumentos.config)
    registro = Registro(argumentos.log, argumentos.tarea) if argumentos.log else SinRegistro()
    modelo = config["modelo"]["nombre"]
    registro.evento("corrida_inicio", modelo=modelo, config=config | entorno_del_servidor(modelo))
    try:
        estado, respuesta, pasos = bucle(argumentos.pregunta, config, registro)
    except NotImplementedError as error:
        registro.evento("corrida_fin", estado="error", respuesta=None, pasos=0, motivo=str(error))
        print(error, file=sys.stderr)
        return 1
    registro.evento("corrida_fin", estado=estado, respuesta=respuesta, pasos=pasos)
    print(respuesta if respuesta is not None else f"({estado})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
