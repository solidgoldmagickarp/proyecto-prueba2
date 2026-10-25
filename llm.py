"""Una llamada al modelo por la API nativa de Ollama.

Es plomería: manda `num_ctx` en cada llamada, pide que falle en lugar de recortar el prompt en
silencio, y devuelve los contadores del servidor. No reintenta ni decide qué hacer con un error:
los reintentos y la política ante fallas son del loop.
"""
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


class LLMError(RuntimeError):
    """El servidor no respondió, o respondió con un error."""

    def __init__(self, mensaje: str, estado: int | None = None):
        super().__init__(mensaje)
        self.estado = estado


class ContextOverflow(LLMError):
    """El prompt no entra en `num_ctx`."""


@dataclass
class Respuesta:
    mensaje: dict
    tokens_entrada: int
    tokens_salida: int
    duracion_ms: int
    razon_fin: str | None = None   # lo que informa el servidor: «stop», o «length» si se cortó por num_predict


def host() -> str:
    valor = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    return valor if valor.startswith("http") else f"http://{valor}"


def _post(ruta: str, cuerpo: dict, timeout_s: float) -> dict:
    pedido = urllib.request.Request(host() + ruta, data=json.dumps(cuerpo).encode(),
                                    headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout_s) as respuesta:
            return json.loads(respuesta.read())
    except urllib.error.HTTPError as error:
        texto = error.read().decode("utf-8", errors="replace")
        clase = ContextOverflow if "exceeds the available context size" in texto else LLMError
        raise clase(f"HTTP {error.code}: {texto[:300]}", error.code) from error
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        raise LLMError(f"sin respuesta de {host()}: {error}") from error


def chat(mensajes: list[dict], *, modelo: str, num_ctx: int, temperatura: float = 0, semilla: int = 1337,
         think: bool = False, num_predict: int = 800, herramientas: list[dict] | None = None,
         formato: dict | None = None, timeout_s: float = 300) -> Respuesta:
    """`formato` es un esquema JSON: el servidor restringe la salida para que lo cumpla."""
    cuerpo = {"model": modelo, "messages": mensajes, "stream": False, "think": think, "truncate": False,
              "options": {"num_ctx": num_ctx, "temperature": temperatura, "seed": semilla,
                          "num_predict": num_predict}}
    if herramientas:
        cuerpo["tools"] = herramientas
    if formato:
        cuerpo["format"] = formato
    inicio = time.perf_counter()
    datos = _post("/api/chat", cuerpo, timeout_s)
    duracion_ms = round((time.perf_counter() - inicio) * 1000)
    if "message" not in datos or "prompt_eval_count" not in datos or "eval_count" not in datos:
        raise LLMError(f"la respuesta no trae el mensaje o los contadores de tokens: {sorted(datos)}")
    return Respuesta(datos["message"], datos["prompt_eval_count"], datos["eval_count"], duracion_ms,
                     datos.get("done_reason"))


def _get(ruta: str) -> dict:
    try:
        with urllib.request.urlopen(host() + ruta, timeout=5) as respuesta:
            return json.loads(respuesta.read())
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        raise LLMError(f"no pude leer {ruta} de {host()}: {error}") from error


def version() -> str:
    return _get("/api/version")["version"]


def digest(modelo: str) -> str | None:
    """El digest del modelo descargado, o None si el servidor no lo tiene."""
    return next((m["digest"] for m in _get("/api/tags").get("models", []) if m["name"] == modelo), None)
