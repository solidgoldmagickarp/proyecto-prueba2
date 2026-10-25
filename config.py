"""Carga y valida `config.toml`. Una clave obligatoria que falta es un error, no un valor por defecto."""
import tomllib
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "config.toml"

NUMERO = (int, float)
OBLIGATORIAS = {
    "modelo": {"nombre": str, "num_ctx": int, "temperatura": NUMERO, "semilla": int, "think": bool,
               "num_predict": int, "timeout_s": NUMERO},
    "frenos": {"max_pasos": int, "max_tokens": int},
    "contexto": {"tope_resultado_caracteres": int},
}


class ConfigError(ValueError):
    pass


def _es(valor, tipo) -> bool:
    if tipo is int or tipo == NUMERO:
        return isinstance(valor, tipo) and not isinstance(valor, bool)
    return isinstance(valor, tipo)


def validar(config: dict) -> dict:
    for seccion, claves in OBLIGATORIAS.items():
        if seccion not in config:
            raise ConfigError(f"falta la sección [{seccion}]")
        for clave, tipo in claves.items():
            if clave not in config[seccion]:
                raise ConfigError(f"falta {seccion}.{clave}")
            if not _es(config[seccion][clave], tipo):
                raise ConfigError(f"{seccion}.{clave} tiene el tipo equivocado: {config[seccion][clave]!r}")
    if ":" not in config["modelo"]["nombre"]:
        raise ConfigError("modelo.nombre necesita el tag explícito, por ejemplo qwen3:8b")
    if config["modelo"]["num_ctx"] < 1 or config["frenos"]["max_pasos"] < 1 or config["frenos"]["max_tokens"] < 1:
        raise ConfigError("num_ctx, max_pasos y max_tokens tienen que ser positivos")
    return config


def cargar(ruta: Path = CONFIG) -> dict:
    with open(ruta, "rb") as archivo:
        return validar(tomllib.load(archivo))
